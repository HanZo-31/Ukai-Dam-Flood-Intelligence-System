"""Explicit loopback-only receiver HTTP verification; never starts a service."""
import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler

from services.api.app.receiving import ReceiptError, now, inventory, raw_hash
from services.api.app.prototype_settings import regular_json
from services.api.app.published_contract import PublishedScenarioManifest


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def local_base(value):
    parts = urlsplit(value)
    if (parts.scheme != "http" or parts.hostname not in {"127.0.0.1", "::1"}
            or parts.username is not None or parts.password is not None
            or parts.path not in {"", "/"} or parts.query or parts.fragment
            or parts.port is None or not 1 <= parts.port <= 65535):
        raise ReceiptError("explicit_literal_loopback_http_url_required")
    return value.rstrip("/")


def request(base, path, *, method="GET", headers=None, max_bytes=1024 * 1024, checksum=None):
    if not path.startswith("/api/v1/") or path.startswith("//") or any(char in path for char in "\\\r\n#"):
        raise ReceiptError("unexpected_api_reference")
    opener = build_opener(ProxyHandler({}), NoRedirect())
    req = Request(local_base(base) + path, method=method, headers=headers or {})
    try:
        response = opener.open(req, timeout=30)
    except HTTPError as error:
        response = error
    digest = hashlib.sha256()
    payload = bytearray()
    size = 0
    with response:
        for block in iter(lambda: response.read(1024 * 1024), b""):
            size += len(block)
            if size > max_bytes:
                raise ReceiptError("api_response_byte_limit")
            digest.update(block)
            if checksum is None:
                payload.extend(block)
        if checksum is not None and response.status == 200 and "sha256:" + digest.hexdigest() != checksum:
            raise ReceiptError("api_download_checksum_mismatch")
        return {"status": response.status, "headers": {key.lower(): value for key, value in response.headers.items()},
                "body": bytes(payload), "bytes": size, "checksum": "sha256:" + digest.hexdigest()}


def checked_json(base, path):
    result = request(base, path)
    if result["status"] != 200:
        raise ReceiptError("required_preview_response_unavailable")
    try:
        return json.loads(result["body"])
    except (ValueError, UnicodeDecodeError) as error:
        raise ReceiptError("invalid_api_json") from error


def warnings(payload):
    if (payload.get("status") != "draft" or payload.get("validation_status") != "pending"
            or payload.get("approved_by") is not None or payload.get("approved_at") is not None
            or payload.get("prototype") is not True or payload.get("scientifically_validated") is not False
            or payload.get("calibration_status") != "uncalibrated"
            or payload.get("label") != "Uncalibrated prototype — simulated"
            or payload.get("data_mode") != "production" or payload.get("data_kind") != "simulated"
            or set(payload.get("warnings", [])) != {"uncalibrated", "not_scientifically_validated", "simulated"}):
        raise ReceiptError("prototype_warning_or_status_mismatch")


def verify_preview(report, manifest_key, *, base_url, expect_unadmitted=False):
    """Rechecks the receipt then probes a service already started by its operator."""
    if not report["passed"]:
        raise ReceiptError("preflight_must_pass_before_http_verification")
    base = local_base(base_url)
    root = Path(report["root"])
    manifest = PublishedScenarioManifest.model_validate(regular_json(root / manifest_key, 1024 * 1024))
    identity = manifest.scenario_id
    preview = "/api/v1/prototypes/scenarios/" + identity
    entries = inventory(root)

    def check(name, callback, requirements):
        started = now()
        try:
            callback()
        except Exception as error:
            report["steps"].append({"step": name, "required": True, "performed": True,
                "passed": False, "exit_status": 1, "started_at": started, "finished_at": now(),
                "requirements": requirements, "reason": error.reason if isinstance(error, ReceiptError) else type(error).__name__})
            raise
        report["steps"].append({"step": name, "required": True, "performed": True,
            "passed": True, "exit_status": 0, "started_at": started, "finished_at": now(), "requirements": requirements})

    def lists(path, mode=None):
        found = []
        offset = 0
        for _ in range(11):
            payload = checked_json(base, path + "?limit=100&offset=" + str(offset) + ("&data_mode=" + mode if mode else ""))
            found.extend(payload["items"])
            pagination = payload.get("pagination", {})
            next_offset = pagination.get("next_offset")
            if next_offset is None:
                return found
            if type(next_offset) is not int or next_offset <= offset:
                raise ReceiptError("invalid_api_pagination")
            offset = next_offset
        raise ReceiptError("verification_catalogue_budget_exceeded")

    def hidden():
        for mode in ("demo", "production"):
            for suffix in ("", "/layers", "/impact", "/assumptions", *["/assets/" + role for role in manifest.assets]):
                path = "/api/v1/scenarios/" + identity + suffix + "?data_mode=" + mode
                if request(base, path)["status"] != 404:
                    raise ReceiptError("draft_visible_in_approved_namespace")
            for format_name in ("geojson", "kml"):
                if request(base, "/api/v1/exports/" + identity + "?format=" + format_name + "&data_mode=" + mode)["status"] != 404:
                    raise ReceiptError("draft_export_visible_in_approved_namespace")
            if any(item.get("scenario_id") == identity for item in lists("/api/v1/scenarios", mode)):
                raise ReceiptError("draft_listed_in_approved_namespace")

    def removed():
        for suffix in ("", "/layers", "/impact", "/assumptions", "/quality-report",
                       *["/assets/" + role for role in manifest.assets]):
            if request(base, preview + suffix)["status"] != 404:
                raise ReceiptError("unadmitted_preview_resource_accessible")
        if any(item.get("scenario_id") == identity for item in lists("/api/v1/prototypes/scenarios")):
            raise ReceiptError("unadmitted_preview_listed")

    def metadata():
        detail = checked_json(base, preview)
        warnings(detail)
        for name in ("scenario_id", "run_id", "model_version", "input_dataset_version", "time_step_minutes", "crs"):
            if detail.get(name) != getattr(manifest, name):
                raise ReceiptError("api_manifest_identity_mismatch")
        if detail.get("summary") != manifest.summary.model_dump(mode="json"):
            raise ReceiptError("api_summary_mismatch")
        for suffix in ("/layers", "/impact"):
            result = checked_json(base, preview + suffix)
            warnings(result)
            if result.get("scenario_id") != identity or result.get("run_id") != manifest.run_id:
                raise ReceiptError("api_resource_identity_mismatch")
            if suffix == "/impact" and any(result.get(key) != value for key, value in manifest.summary.model_dump(mode="json").items()):
                raise ReceiptError("api_impact_mismatch")
            if suffix == "/layers":
                layers = result.get("layers", [])
                if {item.get("asset_type") for item in layers} != set(manifest.assets) or len(layers) != len(manifest.assets):
                    raise ReceiptError("api_layer_set_mismatch")
                for item in layers:
                    role = item["asset_type"]
                    if item.get("url") != preview + "/assets/" + role or item.get("checksum") != manifest.asset_metadata[role].checksum:
                        raise ReceiptError("api_layer_reference_mismatch")
        listed = [item for item in lists("/api/v1/prototypes/scenarios") if item.get("scenario_id") == identity]
        if len(listed) != 1:
            raise ReceiptError("admitted_preview_not_listed_exactly_once")
        warnings(listed[0])

    def downloads():
        resources = [("/assets/" + role, value.checksum, 512 * 1024 * 1024) for role, value in manifest.asset_metadata.items()]
        resources.extend([("/assumptions", manifest.assumptions_checksum, 65536),
                          ("/quality-report", manifest.quality.report_checksum, 512 * 1024 * 1024)])
        report["download_results"] = []
        for suffix, checksum, maximum in resources:
            path = preview + suffix
            full = request(base, path, max_bytes=maximum, checksum=checksum)
            head = request(base, path, method="HEAD", max_bytes=0)
            if full["status"] != 200 or head["status"] != 200 or head["bytes"] != 0:
                raise ReceiptError("api_full_or_head_failed")
            for result in (full, head):
                headers = result["headers"]
                if (headers.get("cache-control") != "no-store" or headers.get("x-ukai-prototype") != "true"
                        or headers.get("x-ukai-scientific-validation") != "not_validated"
                        or headers.get("etag") != full["headers"].get("etag")
                        or int(headers.get("content-length", -1)) != full["bytes"]):
                    raise ReceiptError("api_download_headers_mismatch")
            partial = request(base, path, headers={"Range": "bytes=0-0"}, max_bytes=1)
            if partial["status"] != 206 or partial["bytes"] != 1:
                raise ReceiptError("api_range_failed")
            fallback = request(base, path, headers={"Range": "bytes=0-0", "If-Range": '"not-current"'}, max_bytes=maximum, checksum=checksum)
            invalid = request(base, path, headers={"Range": "bytes=" + str(full["bytes"]) + "-"})
            if fallback["status"] != 200 or invalid["status"] != 416:
                raise ReceiptError("api_if_range_or_invalid_range_failed")
            report["download_results"].append({"resource": suffix, "checksum": full["checksum"], "bytes": full["bytes"], "passed": True})

    report.update(operation="verify-preview", base_url=base, admission_expected=not expect_unadmitted,
                  api_verification_started_at=now(), real_api_roundtrip_verified=False)
    try:
        check("approved_namespace_isolation", hidden, ["I07", "G05"])
        if expect_unadmitted:
            check("admission_removal_http", removed, ["G06", "T03"])
        else:
            if manifest.data_mode != "production" or manifest.data_kind != "simulated":
                raise ReceiptError("demo_fixture_cannot_claim_admitted_real_preview")
            check("preview_metadata_http", metadata, ["G02", "G03", "T10"])
            check("preview_verified_downloads_http", downloads, ["G04", "T09"])
        check("post_http_original_hashes", lambda: inventory(root) == entries or (_ for _ in ()).throw(ReceiptError("originals_changed_during_http_checks")), ["RUN07"])
        report["real_api_roundtrip_verified"] = not expect_unadmitted and report["evidence_kind"] == "real_receipt"
    except Exception as error:
        report["passed"] = False
        report["steps"].append({"step": "http_acceptance_gate", "required": True, "performed": True,
            "passed": False, "exit_status": 1, "reason": error.reason if isinstance(error, ReceiptError) else type(error).__name__})
    report["finished_at"] = now()
    report["source_hashes"]["receiving_http.py"] = raw_hash(Path(__file__))
    return report

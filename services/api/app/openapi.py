"""One deterministic documentation contract shared by live docs and export.

Examples are package-local and verified against real isolated HTTP responses.
Building the document does not open a database session or inspect working data.
"""
from copy import deepcopy
import json
from pathlib import Path

from fastapi.openapi.utils import get_openapi
from services.api.app.api.v1.responses import problem_spec

EXAMPLES_PATH = Path(__file__).parent / "api_examples/v1.json"
JSON_ENDPOINTS = {
    "/api/v1/health": "health",
    "/api/v1/scenarios": "scenario_list",
    "/api/v1/scenarios/{scenario_id}": "scenario_detail",
    "/api/v1/scenarios/{scenario_id}/layers": "layers",
    "/api/v1/scenarios/{scenario_id}/impact": "impact",
    "/api/v1/historical-events": "historical_events",
    "/api/v1/status/current": "current_status",
    "/api/v1/exports/{scenario_id}": "export",
}
ASSET_PATH = "/api/v1/scenarios/{scenario_id}/assets/{asset_type}"
ASSUMPTIONS_PATH = "/api/v1/scenarios/{scenario_id}/assumptions"
PROBLEM_KEYS = {404: "not_found", 405: "method_not_allowed", 416: "range",
                422: "invalid_request", 500: "unexpected", 503: "unavailable"}
DESCRIPTIONS = {
    "health": "API liveness only; no database readiness or live-telemetry guarantee.",
    "scenario_list": "Lists only approved, completed B1 published bundles in the selected mode. "
        "Offset pagination is stable only for an unchanged catalog. Inclusive timezone-aware "
        "coverage-overlap filters apply. dataset_version requires dataset_id. Bbox is ordered "
        "WGS84 west,south,east,north; no dateline wrapping. An empty catalog returns 200.",
    "scenario_detail": "Returns explicit public parameters/units, registered impacts, passing "
        "run review, dataset provenance and safe links. Private manifests/storage paths are omitted. "
        "Null measurements stay null; hidden or wrong-mode scenarios return 404.",
    "layers": "Returns registered map layers with CRS, units, SHA-256, coverage and mode-preserving "
        "download URLs. Export roles are excluded. No style or hazard classification is invented.",
    "impact": "Returns B1-registered summary measurements and model/input identity. "
        "Field suffixes declare units; exposure fields are counts. Null is unavailable, not zero. "
        "No hydraulic or exposure calculation is performed by B2.",
    "historical_events": "Registered event metadata/provenance is separate from approved replay "
        "availability. The example replay represents only its actual coverage, not full-event "
        "acceptance. Empty catalogs return 200. Missing historical records are never invented. "
        "Source links are not fetched; private/query/credential-bearing links are omitted.",
    "current_status": "Latest persisted demo reading only, always data_mode/data_kind demo and "
        "is_live false. The timestamp is the stored reading time, not request time. "
        "Production/live requests are rejected. No reading returns 404; null values stay null.",
    "export": "Returns metadata and a verified safe link for an existing approved export_geojson "
        "or export_kml derivative. Format is required. No conversion, file generation or extent "
        "fallback. Absent derivatives return 404; unsafe/tampered/unavailable objects return 503. "
        "Delivery rechecks approval/integrity. KML transport support is not KML GIS/scientific approval.",
}
PARAMETER_DOCS = {
    "data_mode": ("Local default demo; passed explicitly to B1. Status accepts demo only.", "demo"),
    "scenario_id": ("Registered scenario identifier; hidden/unknown/wrong-mode IDs return 404.", "b2-approved-001"),
    "asset_type": ("Registered role on the approved published run; never an arbitrary filename.", "max_depth_cog"),
    "format": ("Required existing export format; unavailable derivatives return 404.", "geojson"),
    "limit": ("Page size 1..999; default 20. One additional row is used for lookahead.", 20),
    "offset": ("Nonnegative offset; follow next_offset until null. Concurrent publications may change later pages.", 0),
    "scenario_type": ("Exact scenario type filter.", "hypothetical"),
    "historical_event_id": ("Exact registered event identifier filter.", "b2-catalog-event"),
    "model_version": ("Exact registered model version filter.", "synthetic-gis-fixture-1.0.0"),
    "dataset_id": ("Exact linked dataset identifier; required when dataset_version is supplied.", "synthetic-gis-input"),
    "dataset_version": ("Exact linked dataset version; requires dataset_id.", "1.0.0"),
    "data_kind": ("Source provenance label, distinct from deployment data_mode.", "demo"),
    "start": ("Timezone-aware ISO date/time with seconds; inclusive overlap start, not after end.", "2026-01-01T00:00:00Z"),
    "end": ("Timezone-aware ISO date/time with seconds; inclusive overlap end, not before start.", "2026-01-01T06:00:00Z"),
    "bbox": ("Four finite, ordered WGS84 west,south,east,north bounds; no dateline wrapping.", "72,20,74,22"),
}
UNITS = {
    "reservoir_level_m": "Reservoir elevation in metres; vertical datum remains a shared review decision.",
    "peak_inflow_m3s": "Peak inflow in cubic metres per second.",
    "peak_release_m3s": "Peak release in cubic metres per second.",
    "breach_width_m": "Breach width in metres.",
    "breach_formation_minutes": "Breach formation time in minutes.",
    "max_depth_m": "Maximum depth in metres.",
    "flooded_area_km2": "Flooded area in square kilometres.",
    "population_exposed": "Exposed population count.",
    "buildings_exposed": "Exposed building count.",
    "roads_affected_km": "Affected road length in kilometres.",
    "critical_facilities_exposed": "Exposed critical-facility count.",
    "inflow_m3s": "Persisted demo inflow in cubic metres per second.",
    "release_m3s": "Persisted demo release in cubic metres per second.",
}


def load_examples():
    return json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))


def _header(description, example=None):
    result = {"description": description, "schema": {"type": "string"}}
    if example is not None:
        result["example"] = example
    return result


def _canonicalize_enums(value):
    # Python's Literal cache may reuse an equivalent literal with a different
    # declaration order depending on imports. Enum order has no schema meaning.
    if isinstance(value, dict):
        if isinstance(value.get("enum"), list):
            value["enum"].sort(key=lambda item: json.dumps(item, sort_keys=True))
        for nested in value.values():
            _canonicalize_enums(nested)
    elif isinstance(value, list):
        for nested in value:
            _canonicalize_enums(nested)


def build_openapi(app):
    if app.openapi_schema is not None:
        return app.openapi_schema
    # FastAPI can reuse nested route/schema metadata. Documentation enrichment
    # must not mutate that source when rebuilding or testing cache invalidation.
    spec = deepcopy(get_openapi(title=app.title, version=app.version, description=app.description,
                               routes=app.routes, openapi_version="3.1.0"))
    spec["servers"] = [{"url": "/", "description": "Same-origin API; development server binds to 127.0.0.1."}]
    spec["info"]["description"] += (
        " Local B2 candidate, pending B1/Team A contract freeze and scientific/production acceptance. "
        "Read-only precomputed results; no runtime simulations, publication writes or live telemetry. "
        "Examples are synthetic and do not populate the working catalog. "
        "Local development is loopback-only and has no login authority. Production safeguards "
        "validate hosts, restrict configured browser origins and disable HTTP documentation. "
        "CORS is not authorization. Public-versus-protected access and external TLS/proxy policy "
        "require deployment-owner agreement before external exposure.")
    samples = load_examples()
    spec["info"]["x-example-notice"] = samples["notice"]
    spec["tags"] = [{"name": name, "description": description} for name, description in (
        ("health", "Local API liveness"), ("scenarios", "Approved precomputed scenarios and artifacts"),
        ("historical-events", "Registered events and approved replay availability"),
        ("status", "Persisted demo status, never live telemetry"),
        ("exports", "Existing approved derivatives, never generated exports"),
    )]
    for path, name in JSON_ENDPOINTS.items():
        operation = spec["paths"][path]["get"]
        operation["description"] = DESCRIPTIONS[name]
        media = operation["responses"]["200"]["content"]["application/json"]
        if name in samples["responses"]:
            media["examples"] = {"synthetic": {"summary": "Synthetic engineering fixture only",
                                              "value": samples["responses"][name]}}
        if name in {"scenario_list", "historical_events"}:
            media.setdefault("examples", {})["empty"] = {"summary": "Successful empty catalog",
                "value": {"items": [], "pagination": {"limit": 20, "offset": 0, "next_offset": None}}}
        if name == "export":
            operation["responses"]["200"]["headers"] = {"Cache-Control": _header("Do not cache export availability.", "no-store")}
    for path in (ASSET_PATH, ASSUMPTIONS_PATH):
        media_types = ["text/plain"] if path == ASSUMPTIONS_PATH else [
            "image/tiff", "application/geo+json", "application/vnd.google-earth.kml+xml"]
        operation = spec["paths"][path]["get"]
        operation["description"] = (
            "Serves only checksum-verified disk snapshot bytes from the configured local object root. "
            "Approval/mode is rechecked on every request. Missing, remote, changed or unsafe artifacts "
            "return 503. Supports one byte range; If-Range must match the quoted SHA-256 ETag or the "
            "full representation is returned. Full integrity verification occurs even for ranges/HEAD. "
            "Large-file throughput/disk capacity and production storage remain review gates.")
        operation.setdefault("parameters", []).extend([
            {"name": "Range", "in": "header", "required": False, "schema": {"type": "string"},
             "description": "Optional single bytes range, suffix or open-ended; invalid/multiple ranges return 416.",
             "example": "bytes=0-15"},
            {"name": "If-Range", "in": "header", "required": False, "schema": {"type": "string"},
             "description": "Exact quoted current ETag honors Range; any other supplied value returns full bytes."},
        ])
        headers = {
            "Accept-Ranges": _header("Single byte ranges supported.", "bytes"),
            "ETag": _header("Quoted registered SHA-256 checksum."),
            "Content-Disposition": _header("Attachment with a safe role-based filename."),
            "Content-Length": _header("Number of bytes in this representation or range."),
            "Cache-Control": _header("Do not cache approved artifact availability.", "no-store"),
            "X-Content-Type-Options": _header("Prevent content-type sniffing.", "nosniff"),
        }
        download_sample = samples["downloads"].get("assumptions" if path == ASSUMPTIONS_PATH else "cog", {})
        for name, header in headers.items():
            value = download_sample.get("headers", {}).get(name.lower())
            if value is not None:
                header["example"] = value
        content = {media: {"schema": {"type": "string", "format": "binary"}} for media in media_types}
        for code in ("200", "206"):
            operation["responses"][code]["content"] = deepcopy(content)
            operation["responses"][code]["headers"] = deepcopy(headers)
        operation["responses"]["206"]["headers"]["Content-Range"] = _header("Actual inclusive returned byte range and full size.")
        for name, value in download_sample.get("partial_headers", {}).items():
            for header_name, header in operation["responses"]["206"]["headers"].items():
                if header_name.lower() == name:
                    header["example"] = value
        if path == ASSUMPTIONS_PATH and "text" in download_sample:
            operation["responses"]["200"]["content"]["text/plain"]["examples"] = {
                "synthetic": {"value": download_sample["text"]}}
        operation["responses"]["416"]["headers"] = {"Content-Range": _header("Unsatisfied range: bytes */full-size.")}
        head = spec["paths"][path]["head"]
        head["summary"] = "Check verified artifact headers without a response body"
        head["description"] = "Same approval and full-checksum verification as GET; returns no body. Range is ignored for HEAD."
        head["responses"]["200"] = {"description": "Verified artifact headers; no body", "headers": deepcopy(headers)}
    for path, methods in spec["paths"].items():
        for method, operation in methods.items():
            if method not in {"get", "head"}:
                continue
            operation["responses"].setdefault("405", problem_spec("Method not allowed"))
            operation["responses"]["405"]["headers"] = {"Allow": _header("Permitted methods for this resource.")}
            for parameter in operation.get("parameters", []):
                if parameter["name"] in PARAMETER_DOCS:
                    description, example = PARAMETER_DOCS[parameter["name"]]
                    parameter["description"], parameter["example"] = description, example
                    if parameter["name"] in {"dataset_id", "dataset_version"} and "scenario_detail" in samples["responses"]:
                        source = samples["responses"]["scenario_detail"]["datasets"][0]
                        parameter["example"] = source["dataset_id" if parameter["name"] == "dataset_id" else "version"]
            for code, response in operation["responses"].items():
                problem_media = response.get("content", {}).get("application/problem+json")
                if problem_media is not None:
                    key = PROBLEM_KEYS.get(int(code))
                    if code == "404" and path == "/api/v1/status/current":
                        key = "status_not_found"
                    if key in samples["problems"]:
                        value = deepcopy(samples["problems"][key])
                        # Each example uses a concrete path for this operation.
                        value["instance"] = path.replace("{scenario_id}", "b2-approved-001").replace("{asset_type}", "max_depth_cog")
                        problem_media["examples"] = {"safe_problem": {"value": value}}
                    response.setdefault("headers", {}).update({
                        "Cache-Control": _header("Do not cache error responses.", "no-store"),
                        "X-Content-Type-Options": _header("Prevent content-type sniffing.", "nosniff"),
                    })
                if method == "head":
                    response.pop("content", None)
    for schema_name, schema in spec["components"]["schemas"].items():
        for name, prop in schema.get("properties", {}).items():
            if name in UNITS:
                prop["description"] = ("Required companion unit literal; not nullable." if schema_name == "ParameterUnits"
                                       else UNITS[name] + " Null means unavailable/not applicable; no inferred zero.")
    _canonicalize_enums(spec)
    app.openapi_schema = spec
    return spec

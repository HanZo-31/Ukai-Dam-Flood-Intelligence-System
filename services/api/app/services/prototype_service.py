"""Verified, explicitly admitted pending prototypes; no simulation or writes."""
from dataclasses import replace
import hashlib
import json
import re
import time
from urllib.parse import quote

from fastapi import HTTPException, Request
from services.api.app.published_contract import PublishedScenarioManifest, resolve_reference
from services.api.app.prototype_context import MAX_CONTEXT_BYTES, PrototypeContext, validate_bound_context
from services.api.app.prototype_settings import parse_json_bytes
from services.api.app.services.asset_service import verified_download
from services.api.app.services.download_policy import download_policy
from services.api.app.api_schemas.prototype import (
    PrototypeSummary, PrototypeList, PrototypePagination, PrototypeDetail, PrototypeLayers,
    PrototypeImpact, PrototypeLinks, PublicProvenance, PublicTiming, PublicArrival, PrototypeLayer,
)
from services.api.app.api_schemas.scenario import DatasetProvenance

MAP_ROLES = {"max_depth_cog", "max_velocity_cog", "arrival_time_cog", "extent_geojson", "duration_cog", "hazard_cog", "exposure_geojson"}
PRIVATE = re.compile(r"(?i)(?:(?<![a-z0-9])[a-z]:[\\/]|file://|postgres(?:ql)?(?:\+[a-z_]+)?://|https?://[^\s/@]+:[^\s/@]+@|(?:^|[\s\"'])/(?!api/v1/prototypes/scenarios/)(?:[a-z0-9_.-]+/)*[a-z0-9_.-]+)")


def canonical_checksum(manifest):
    raw = json.dumps(manifest.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def safe_public(value):
    if isinstance(value, dict):
        for item in value.values():
            safe_public(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            safe_public(item)
    elif isinstance(value, str) and not value.startswith("/api/v1/prototypes/scenarios/") and PRIVATE.search(value):
        raise ValueError("Private locator cannot be emitted")


def public_url(identity, suffix=""):
    return "/api/v1/prototypes/scenarios/" + quote(identity, safe="") + suffix


class PrototypeService:
    def __init__(self, repository, store, settings):
        self.repository, self.store, self.settings = repository, store, settings

    def admission(self):
        try:
            return self.settings.admission()
        except (ValueError, OSError) as error:
            raise HTTPException(503, "Prototype admission is unavailable.") from error

    def _manifest(self, row):
        scenario, bundle, run = row
        if (scenario.status != "completed" or scenario.publication_status != "draft"
                or run.status != "completed" or run.validation_status != "pending"
                or run.approved_by is not None or run.approved_at is not None):
            raise ValueError("Prototype state is not eligible")
        manifest = PublishedScenarioManifest.model_validate(bundle.manifest_json)
        if canonical_checksum(manifest) != bundle.manifest_checksum:
            raise ValueError("Canonical manifest mismatch")
        for name in ("scenario_id", "model_version", "input_dataset_version", "scenario_type", "data_mode", "data_kind", "crs", "time_step_minutes"):
            if getattr(scenario, name) != getattr(manifest, name):
                raise ValueError("Scenario metadata mismatch")
        if (bundle.run_id != manifest.run_id or run.run_id != manifest.run_id
                or run.scenario_id != manifest.scenario_id or run.run_timestamp != manifest.run_timestamp
                or run.model_version != manifest.model_version or run.input_dataset_version != manifest.input_dataset_version
                or manifest.status != "draft" or manifest.quality.validation_status != "pending"
                or manifest.quality.approved_by is not None or manifest.quality.approved_at is not None):
            raise ValueError("Run/snapshot mismatch")
        if scenario.coverage_start != manifest.time_coverage.start or scenario.coverage_end != manifest.time_coverage.end:
            raise ValueError("Coverage mismatch")
        if scenario.parameters != manifest.parameters.model_dump() or scenario.parameter_units != manifest.parameter_units.model_dump():
            raise ValueError("Parameter mismatch")
        expected = self.store.resolve_uri(resolve_reference(bundle.bundle_root_uri, manifest.assumptions_url)).as_uri()
        if expected != self.store.resolve_uri(scenario.assumptions_url).as_uri() or scenario.assumptions_checksum != manifest.assumptions_checksum:
            raise ValueError("Context reference mismatch")
        if (run.quality_report_checksum != manifest.quality.report_checksum
                or self.store.resolve_uri(run.quality_report_uri).as_uri() != self.store.resolve_uri(resolve_reference(bundle.bundle_root_uri, manifest.quality.report_reference)).as_uri()):
            raise ValueError("Report reference mismatch")
        return manifest

    def _context(self, scenario, manifest):
        policy = replace(download_policy(), max_bytes=MAX_CONTEXT_BYTES)
        download = verified_download(self.store, scenario.assumptions_url, manifest.assumptions_checksum,
                                     media_type="application/json", filename="prototype-context.json", policy=policy)
        try:
            payload = parse_json_bytes(download.handle.read(MAX_CONTEXT_BYTES + 1), MAX_CONTEXT_BYTES)
            context = validate_bound_context(PrototypeContext.model_validate(payload), manifest)
            safe_public(context.model_dump(mode="json"))
            return context
        finally:
            download.handle.close()

    def _assets(self, manifest, bundle):
        rows = self.repository.assets(manifest.scenario_id, manifest.run_id)
        result = {}
        for asset, spatial in rows:
            role = asset.asset_type
            if role not in MAP_ROLES or role not in manifest.assets or role in result:
                raise ValueError("Unexpected asset")
            metadata = manifest.asset_metadata[role]
            fields = ("checksum", "format", "crs", "unit", "nodata")
            if any(getattr(asset, key) != getattr(metadata, key) for key in fields):
                raise ValueError("Asset metadata mismatch")
            if (asset.run_id != manifest.run_id or asset.scenario_id != manifest.scenario_id
                    or asset.data_mode != "production" or asset.coverage_start != metadata.time_coverage.start
                    or asset.coverage_end != metadata.time_coverage.end):
                raise ValueError("Asset identity mismatch")
            expected = self.store.resolve_uri(resolve_reference(bundle.bundle_root_uri, manifest.assets[role])).as_uri()
            if expected != self.store.resolve_uri(asset.storage_uri).as_uri():
                raise ValueError("Asset reference mismatch")
            if spatial is None or spatial.asset_id != asset.id or spatial.source_checksum != asset.checksum or not isinstance(spatial.details, dict):
                raise ValueError("Missing coherent GIS inspection")
            details = spatial.details
            if not details.get("inspector_version") or details.get("native_crs") != asset.crs:
                raise ValueError("GIS inspection identity mismatch")
            if metadata.format == "cog":
                if details.get("cog_valid") is not True or any(type(details.get(key)) is not int or details[key] <= 0 for key in ("width", "height", "valid_cells")):
                    raise ValueError("Invalid raster inspection")
            elif type(details.get("feature_count")) is not int or details["feature_count"] <= 0:
                raise ValueError("Invalid vector inspection")
            result[role] = asset
        if set(result) != set(manifest.assets):
            raise ValueError("Asset set differs from snapshot")
        return result

    def _datasets(self, manifest, bundle):
        rows = self.repository.datasets(manifest.scenario_id)
        registered = {(item.dataset_id, item.version): item for item in rows}
        if set(registered) != {(item.dataset_id, item.version) for item in manifest.datasets}:
            raise ValueError("Dataset links mismatch")
        for item in manifest.datasets:
            row = registered[(item.dataset_id, item.version)]
            if any(getattr(row, field) != getattr(item, field) for field in ("checksum", "source_label", "license", "crs", "quality_notes")):
                raise ValueError("Dataset provenance mismatch")
            start = item.time_coverage.start if item.time_coverage else None
            end = item.time_coverage.end if item.time_coverage else None
            if row.coverage_start != start or row.coverage_end != end:
                raise ValueError("Dataset coverage mismatch")
            source = row.source_reference
            if not source.startswith("file:"):
                source = self.store.path_for_key(source).as_uri()
            if self.store.resolve_uri(source).as_uri() != self.store.resolve_uri(resolve_reference(bundle.bundle_root_uri, item.source_reference)).as_uri():
                raise ValueError("Dataset reference mismatch")

    def verified(self, row):
        try:
            scenario, bundle, _ = row
            manifest = self._manifest(row)
            context = self._context(scenario, manifest)
            assets = self._assets(manifest, bundle)
            summary = self.repository.summary(manifest.scenario_id)
            if summary is None or any(getattr(summary, key) != value for key, value in manifest.summary.model_dump().items()):
                raise ValueError("Impact mismatch")
            self._datasets(manifest, bundle)
            return manifest, context, assets
        except HTTPException:
            raise
        except (ValueError, OSError, TypeError, AttributeError, KeyError, RecursionError) as error:
            raise HTTPException(503, "The registered prototype data is unavailable.") from error

    def get(self, identity):
        admission = self.admission()
        if not any(item.scenario_id == identity for item in admission.entries):
            raise HTTPException(404, "The prototype is not available.")
        row = self.repository.get(identity, entries=admission.entries)
        if row is None:
            raise HTTPException(404, "The prototype is not available.")
        return row, self.verified(row)

    @staticmethod
    def summary(manifest):
        return PrototypeSummary(scenario_id=manifest.scenario_id, run_id=manifest.run_id,
            scenario_type=manifest.scenario_type, model_version=manifest.model_version,
            input_dataset_version=manifest.input_dataset_version)

    def list(self, *, limit, offset):
        entries = self.admission().entries
        rows = self.repository.list(entries=entries, limit=limit + 1, offset=offset) if entries else []
        items = []
        for row in rows[:limit]:
            manifest, _, _ = self.verified(row)
            item = self.summary(manifest)
            safe_public(item.model_dump(mode="json"))
            items.append(item)
        return PrototypeList(items=items, pagination=PrototypePagination(limit=limit, offset=offset,
                             next_offset=offset + limit if len(rows) > limit else None))

    def detail(self, identity):
        _, (manifest, context, _) = self.get(identity)
        datasets = [DatasetProvenance(dataset_id=item.dataset_id, version=item.version,
            source_label=item.source_label, license=item.license, checksum=item.checksum, crs=item.crs,
            coverage_start=item.time_coverage.start if item.time_coverage else None,
            coverage_end=item.time_coverage.end if item.time_coverage else None) for item in manifest.datasets]
        limitations = context.limitations
        result = PrototypeDetail(**self.summary(manifest).model_dump(), crs=manifest.crs,
            historical_event_id=manifest.historical_event_id, run_timestamp=manifest.run_timestamp,
            run_timestamp_unknown_reason=manifest.run_timestamp_unknown_reason,
            coverage_start=manifest.time_coverage.start, coverage_end=manifest.time_coverage.end,
            time_step_minutes=manifest.time_step_minutes, parameters=manifest.parameters,
            parameter_units=manifest.parameter_units, summary=manifest.summary, engine=context.engine,
            provenance=PublicProvenance(source_scenario_id=context.original.scenario_id,
                source_manifest_checksum=context.original.manifest_checksum, scenario_family=context.scenario_family,
                derivation_processor=context.derivation.processor, derivation_version=context.derivation.processor_version),
            timing=PublicTiming.from_context(context.timing), arrival=PublicArrival.from_context(context.arrival),
            datasets=datasets, limitations=[limitations.calibration, limitations.terrain_bathymetry,
                limitations.vertical_datum, limitations.exposure, *limitations.source_uncertainties],
            assumptions=context.assumptions, unavailable_reasons=context.unavailable_products,
            links=PrototypeLinks(self=public_url(identity), layers=public_url(identity, "/layers"),
                impact=public_url(identity, "/impact"), assumptions=public_url(identity, "/assumptions"),
                quality_report=public_url(identity, "/quality-report")))
        try:
            safe_public(result.model_dump(mode="json"))
        except ValueError as error:
            raise HTTPException(503, "The registered prototype response is unavailable.") from error
        return result

    def layers(self, identity):
        _, (manifest, _, assets) = self.get(identity)
        layers = [PrototypeLayer(asset_type=role, format=asset.format, crs=asset.crs, unit=asset.unit,
            nodata=asset.nodata, checksum=asset.checksum, coverage_start=asset.coverage_start,
            coverage_end=asset.coverage_end, url=public_url(identity, "/assets/" + role)) for role, asset in assets.items()]
        return PrototypeLayers(**self.summary(manifest).model_dump(), layers=layers)

    def impact(self, identity):
        _, (manifest, context, _) = self.get(identity)
        return PrototypeImpact(**self.summary(manifest).model_dump(), **manifest.summary.model_dump(),
                               unavailable_reasons=context.unavailable_products)

    def download(self, identity, resource):
        row, (manifest, _, assets) = self.get(identity)
        scenario, _, run = row
        if resource == "assumptions":
            uri, checksum, media, filename = scenario.assumptions_url, manifest.assumptions_checksum, "application/json", "prototype-context.json"
            policy = replace(download_policy(), max_bytes=MAX_CONTEXT_BYTES)
        elif resource == "quality-report":
            uri, checksum, media, filename = run.quality_report_uri, run.quality_report_checksum, "application/octet-stream", "prototype-quality-report.bin"
            policy = download_policy()
        else:
            if resource not in assets:
                raise HTTPException(404, "The prototype asset is unavailable.")
            asset = assets[resource]
            uri, checksum = asset.storage_uri, asset.checksum
            media = "image/tiff" if asset.format == "cog" else "application/geo+json"
            filename = resource + (".tif" if asset.format == "cog" else ".geojson")
            policy = download_policy()
        download = verified_download(self.store, uri, checksum, media_type=media, filename=filename, policy=policy)
        try:
            if resource == "quality-report":
                tail = ""
                deadline = time.monotonic() + policy.verification_seconds
                while chunk := download.handle.read(64 * 1024):
                    if time.monotonic() > deadline:
                        raise ValueError("Report review exceeded bounded verification time")
                    text = tail + chunk.decode("utf-8", errors="ignore")
                    if PRIVATE.search(text):
                        raise ValueError("Private locator in report")
                    tail = text[-256:]
                download.handle.seek(0)
            current = self.admission()
            if self.repository.get(identity, entries=current.entries) is None:
                raise HTTPException(404, "The prototype is not available.")
            return download
        except HTTPException:
            download.handle.close()
            raise
        except (ValueError, OSError) as error:
            download.handle.close()
            raise HTTPException(503, "The prototype report is unavailable.") from error


def get_prototype_service(request: Request):
    from services.api.app.db.session import SessionLocal
    from services.api.app.repositories.prototype_repository import PrototypeRepository
    from services.api.app.storage import default_store
    from sqlalchemy import text
    settings = request.app.state.prototype_settings
    with SessionLocal() as session:
        session.execute(text("SET TRANSACTION READ ONLY"))
        yield PrototypeService(PrototypeRepository(session), default_store(), settings)

"""Verified precomputed bundle ingestion; no model execution or filesystem writes."""
import hashlib
import json
from urllib.parse import unquote, urlsplit

from sqlalchemy import select

from services.api.app.db.models import (
    Scenario, ProcessingRun, ResultAsset, ImpactSummary, DatasetVersion,
    PublishedBundle, ScenarioDatasetVersion, PublicationAction,
    AssetSpatialMetadata, ScenarioSpatialMetadata,
)
from services.api.app.published_contract import PublishedScenarioManifest, resolve_reference
from services.api.app.repositories.catalog_repository import DatasetRepository, HistoricalEventRepository


def nonblank(value, field):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{field} must be a nonblank unpadded string")
    return value


def register_published_bundle(session, manifest, store, *, bundle_root_uri,
                              registered_by, trusted_approvers=(), asset_inspector=None):
    """Flush an atomic import; the caller owns the outer commit/rollback.

    Production requires an injected GIS content verifier in addition to hashes.
    Approver allowlists come from trusted configuration, never the manifest.
    """
    manifest = PublishedScenarioManifest.model_validate(manifest.model_dump() if isinstance(manifest, PublishedScenarioManifest) else manifest)
    nonblank(registered_by, "registered_by")
    if isinstance(trusted_approvers, (str, bytes)):
        raise ValueError("trusted approvers must be an explicit collection, not a string")
    for approver in trusted_approvers:
        nonblank(approver, "trusted approver")
    if manifest.status == "approved" and manifest.quality.approved_by not in trusted_approvers:
        raise ValueError("approved bundle requires an explicitly trusted approver")
    if manifest.data_mode == "production" and asset_inspector is None:
        raise ValueError("production imports require a configured GIS content verifier")
    if asset_inspector is not None and not callable(asset_inspector):
        raise ValueError("GIS content verifier must be callable")
    if asset_inspector is not None:
        from services.api.app.gis_validation import GISInspector
        if isinstance(asset_inspector, GISInspector):
            asset_inspector.reset()
    # Validate the trusted root even if all references are absolute.
    store.resolve_uri(resolve_reference(bundle_root_uri, "root-validation"))
    if session.scalar(select(Scenario.id).where(Scenario.scenario_id == manifest.scenario_id)) is not None:
        raise ValueError("scenario already exists; publish changed results under a new ID")
    if session.scalar(select(ProcessingRun.id).where(ProcessingRun.run_id == manifest.run_id)) is not None:
        raise ValueError("run already exists")

    def verified(reference, checksum):
        uri = resolve_reference(bundle_root_uri, reference)
        store.verify(uri, checksum)
        # Normalize aliases for distinctness checks and durable DB references.
        return store.resolve_uri(uri).as_uri()

    assumptions_uri = verified(manifest.assumptions_url, manifest.assumptions_checksum)
    report_uri = verified(manifest.quality.report_reference, manifest.quality.report_checksum)
    versions = []
    datasets = DatasetRepository(session)
    events = HistoricalEventRepository(session)
    event = events.get(manifest.historical_event_id) if manifest.historical_event_id else None
    if manifest.historical_event_id and (event is None or event.data_mode != manifest.data_mode):
        raise ValueError("historical event must exist with matching data mode")
    event_version_ids = {row.id for row in events.datasets(event.event_id)} if event else set()
    for item in manifest.datasets:
        parent = datasets.get(item.dataset_id)
        version = datasets.get_version(item.dataset_id, item.version)
        if parent is None or version is None or parent.data_mode != manifest.data_mode:
            raise ValueError("dataset version must be registered with matching data mode")
        uri = verified(item.source_reference, item.checksum)
        # Catalog-relative keys use the store root, not the bundle root.
        stored_uri = version.source_reference
        if not urlsplit(stored_uri).scheme:
            stored_uri = store.path_for_key(unquote(stored_uri)).as_uri()
        stored_uri = store.resolve_uri(stored_uri).as_uri()
        expected = (uri, item.source_label, item.license, item.checksum, item.crs,
                    item.time_coverage.start if item.time_coverage else None,
                    item.time_coverage.end if item.time_coverage else None, item.quality_notes)
        actual = (stored_uri, version.source_label, version.license, version.checksum,
                  version.crs, version.coverage_start, version.coverage_end, version.quality_notes)
        if actual != expected:
            raise ValueError("dataset provenance differs from its registered immutable version")
        if event and version.id not in event_version_ids:
            raise ValueError("historical event must explicitly link each input dataset version")
        versions.append(version)
    assets = []
    inspections = {}
    seen = set()
    # Raster-first inspection makes alignment/vector coverage independent of JSON order.
    for role in sorted(manifest.assets, key=lambda role: (not role.endswith("_cog"), role)):
        reference = manifest.assets[role]
        metadata = manifest.asset_metadata[role]
        uri = verified(reference, metadata.checksum)
        if uri in seen:
            raise ValueError("asset references resolve to the same object")
        seen.add(uri)
        if asset_inspector is not None:
            inspection = asset_inspector(store.resolve_uri(uri), role, metadata)
            from services.api.app.gis_validation import GISInspection
            if manifest.data_mode == "production" and not isinstance(inspection, GISInspection):
                raise ValueError("production requires structured GIS inspection results")
            if isinstance(inspection, GISInspection):
                if manifest.data_mode == "production" and inspection.synthetic:
                    raise ValueError("synthetic GIS artifacts cannot be published as production")
                inspections[role] = inspection
            store.verify(uri, metadata.checksum)
        assets.append(ResultAsset(scenario_id=manifest.scenario_id, run_id=manifest.run_id,
                                  asset_type=role, storage_uri=uri, checksum=metadata.checksum,
                                  crs=metadata.crs, format=metadata.format, unit=metadata.unit,
                                  coverage_start=metadata.time_coverage.start,
                                  coverage_end=metadata.time_coverage.end, nodata=metadata.nodata,
                                  data_mode=manifest.data_mode))
    snapshot = manifest.model_dump(mode="json")
    checksum = "sha256:" + hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    # A savepoint ensures a late DB error cannot leave a partial import even
    # when the caller catches the exception and later commits its transaction.
    with session.begin_nested():
        scenario = Scenario(scenario_id=manifest.scenario_id, scenario_type=manifest.scenario_type,
                            status="completed", publication_status=manifest.status,
                            schema_version=manifest.schema_version, data_kind=manifest.data_kind,
                            model_version=manifest.model_version, input_dataset_version=manifest.input_dataset_version,
                            crs=manifest.crs, time_step_minutes=manifest.time_step_minutes,
                            parameters=manifest.parameters.model_dump(), parameter_units=manifest.parameter_units.model_dump(),
                            coverage_start=manifest.time_coverage.start, coverage_end=manifest.time_coverage.end,
                            historical_event_id=manifest.historical_event_id, assumptions_url=assumptions_uri,
                            assumptions_checksum=manifest.assumptions_checksum, data_mode=manifest.data_mode)
        session.add(scenario)
        session.flush()
        run = ProcessingRun(scenario_id=scenario.scenario_id, run_id=manifest.run_id,
                            stage="precomputed_import", status="completed", completed_at=manifest.run_timestamp,
                            model_version=manifest.model_version, input_dataset_version=manifest.input_dataset_version,
                            run_timestamp=manifest.run_timestamp, validation_status=manifest.quality.validation_status,
                            quality_report_uri=report_uri, quality_report_checksum=manifest.quality.report_checksum,
                            approved_by=manifest.quality.approved_by, approved_at=manifest.quality.approved_at,
                            metadata_json={"origin": "published_manifest", "schema_version": manifest.schema_version})
        session.add(run)
        session.flush()
        session.add_all(assets)
        session.flush()
        if inspections:
            from geoalchemy2.shape import from_shape
            from shapely.geometry import shape
            for asset in assets:
                inspection = inspections.get(asset.asset_type)
                if inspection is not None:
                    geom = from_shape(shape(inspection.geometry), srid=4326)
                    session.add(AssetSpatialMetadata(asset_id=asset.id, geom=geom, details=inspection.details, source_checksum=asset.checksum))
                    if asset.asset_type == "extent_geojson":
                        session.add(ScenarioSpatialMetadata(scenario_id=scenario.scenario_id, source_asset_id=asset.id, geom=geom, source_checksum=asset.checksum))
        session.add(ImpactSummary(scenario_id=scenario.scenario_id, data_mode=manifest.data_mode, **manifest.summary.model_dump()))
        session.add_all(ScenarioDatasetVersion(scenario_id=scenario.scenario_id, dataset_version_id=version.id) for version in versions)
        session.add(PublicationAction(scenario_id=scenario.scenario_id, action="registered", actor=registered_by, reason=f"Imported {manifest.status} manifest"))
        row = PublishedBundle(scenario_id=scenario.scenario_id, run_id=run.run_id, bundle_root_uri=bundle_root_uri,
                              manifest_checksum=checksum, manifest_json=snapshot, registered_by=registered_by)
        session.add(row)
        session.flush()
    return row

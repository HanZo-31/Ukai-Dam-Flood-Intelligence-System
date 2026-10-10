"""Explicit owned-target integration, never imported by read-only preflight."""
import hashlib
import os
from pathlib import Path
import tempfile

from services.api.app.receiving import ReceiptError, inventory, raw_hash, relative_key, canonical_manifest_hash, regular_file
from services.api.app.storage import publish_no_replace


def owned_target(marker_path, expected_database, object_root, database_url_file=None):
    from services.api.app.prototype_settings import regular_json
    from sqlalchemy.engine import make_url
    marker = regular_json(Path(marker_path), 4096)
    expected = {"database", "project", "version", "state", "protected_database", "protected_object_root", "objects_root", "scratch_root"}
    if (set(marker) != expected or marker["state"] != "created"
            or marker["database"] != expected_database or not expected_database.startswith("ukai_b_integration_")
            or marker["database"] == marker["protected_database"]):
        raise ReceiptError("verified_isolated_target_marker_required")
    objects = Path(object_root).resolve()
    protected = Path(marker["protected_object_root"]).resolve()
    scratch = Path(marker["scratch_root"]).resolve()
    if (objects != Path(marker["objects_root"]).resolve() or not objects.is_dir()
            or objects.is_relative_to(protected) or protected.is_relative_to(objects)
            or not scratch.is_dir() or scratch.is_relative_to(protected) or protected.is_relative_to(scratch)
            or scratch.is_relative_to(objects) or objects.is_relative_to(scratch)):
        raise ReceiptError("object_root_isolation_failed")
    raw: str | None
    if database_url_file:
        raw_path = Path(database_url_file)
        if regular_file(raw_path).st_size > 8192:
            raise ReceiptError("private_configuration_size_limit")
        raw = raw_path.read_text(encoding="utf-8").strip()
    else:
        raw = os.environ.get("DATABASE_URL")
    if not raw:
        raise ReceiptError("explicit_private_target_configuration_required")
    url = make_url(raw)
    if (url.database != expected_database or url.host not in {"127.0.0.1", "localhost", "::1"}
            or url.drivername != "postgresql+psycopg" or set(url.query) - {"connect_timeout", "options"}):
        raise ReceiptError("target_database_identity_failed")
    if url.host == "localhost":
        url = url.set(host="127.0.0.1")
    url = url.update_query_dict({"options": "-c search_path=public -c statement_timeout=10000", "connect_timeout": "5"})
    from sqlalchemy import create_engine, text
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            if conn.scalar(text("SELECT current_database()")) != expected_database or conn.scalar(text("SELECT version_num FROM public.alembic_version")) != "g05b8eab1001":
                raise ReceiptError("target_schema_or_identity_failed")
    except Exception:
        engine.dispose()
        raise
    return engine, objects


def immutable_copy(source, target, expected):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if raw_hash(target) != expected:
            raise ReceiptError("immutable_staging_conflict")
        return
    temporary = None
    try:
        with source.open("rb") as original, tempfile.NamedTemporaryFile(dir=target.parent, prefix=".receiver-pending-", delete=False) as output:
            temporary = Path(output.name)
            digest = hashlib.sha256()
            for block in iter(lambda: original.read(1024 * 1024), b""):
                digest.update(block)
                output.write(block)
            output.flush()
            os.fsync(output.fileno())
        if digest.hexdigest() != expected:
            raise ReceiptError("source_changed_during_staging")
        try:
            publish_no_replace(temporary, target)
        except FileExistsError:
            if raw_hash(target) != expected:
                raise ReceiptError("concurrent_staging_conflict")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def integrate(report, manifest_key, *, marker, expected_database, object_root, delivery_id,
              registered_by, catalog=None, database_url_file=None, fixture=False):
    """Explicit DB write operation; production drafts remain hidden/unadmitted."""
    if not report["passed"] or report["evidence_kind"] != ("synthetic_fixture" if fixture else "real_receipt"):
        raise ReceiptError("preflight_must_pass_before_integration")
    from services.api.app.published_contract import PublishedScenarioManifest, resolve_reference, Identifier
    from pydantic import TypeAdapter
    TypeAdapter(Identifier).validate_python(delivery_id)
    if not isinstance(registered_by, str) or not registered_by.strip() or registered_by != registered_by.strip():
        raise ReceiptError("actual_operator_identity_required")
    root = Path(report["root"])
    entries = inventory(root)
    if raw_hash(root / "CHECKSUMS.sha256") != report["inventory_sha256"]:
        raise ReceiptError("receipt_changed_after_preflight")
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    from services.api.app.db.models import Scenario, PublishedBundle, ProcessingRun
    from services.api.app.published_registry import register_published_bundle
    from services.api.app.repositories.catalog_repository import DatasetRepository, HistoricalEventRepository
    from services.api.app.catalog_schemas import DatasetCreate, DatasetVersionCreate, HistoricalEventCreate
    from services.api.app.gis_validation import GISInspector
    from services.api.app.storage import LocalObjectStore
    from services.api.app.prototype_settings import regular_json
    manifest = PublishedScenarioManifest.model_validate(regular_json(root / manifest_key, 1024 * 1024))
    catalog_values = regular_json(Path(catalog), 1024 * 1024) if catalog else {"datasets": [], "events": []}
    if set(catalog_values) != {"datasets", "events"}:
        raise ReceiptError("input_catalog_unknown_fields")
    if catalog:
        catalog_path = Path(catalog).resolve()
        if not catalog_path.is_relative_to(root) or catalog_path.relative_to(root).as_posix() not in entries:
            raise ReceiptError("input_catalog_must_belong_to_verified_receipt")
    engine, objects = owned_target(marker, expected_database, object_root, database_url_file)
    report["database_connected"] = True
    destination = objects / "received" / delivery_id
    bundle_root = (destination / manifest_key).parent.as_uri() + "/"
    try:
        with Session(engine) as session, session.begin():
            existing = session.scalar(select(Scenario).where(Scenario.scenario_id == manifest.scenario_id))
            if existing is not None:
                saved = session.scalar(select(PublishedBundle).where(PublishedBundle.scenario_id == manifest.scenario_id))
                run = session.scalar(select(ProcessingRun).where(ProcessingRun.run_id == manifest.run_id))
                if (saved is None or run is None or saved.run_id != manifest.run_id
                        or saved.manifest_checksum != canonical_manifest_hash(manifest) or saved.bundle_root_uri != bundle_root
                        or existing.publication_status != "draft" or existing.status != "completed"
                        or run.scenario_id != manifest.scenario_id or run.status != "completed"
                        or run.validation_status != "pending" or run.approved_by is not None or run.approved_at is not None
                        or canonical_manifest_hash(PublishedScenarioManifest.model_validate(saved.manifest_json)) != canonical_manifest_hash(manifest)):
                    raise ReceiptError("existing_identity_conflict_no_upsert")
                fields = ("scenario_type", "model_version", "input_dataset_version", "data_mode", "data_kind", "crs", "time_step_minutes", "historical_event_id", "schema_version")
                if (any(getattr(existing, key) != getattr(manifest, key) for key in fields)
                        or existing.parameters != manifest.parameters.model_dump()
                        or existing.parameter_units != manifest.parameter_units.model_dump()
                        or existing.coverage_start != manifest.time_coverage.start or existing.coverage_end != manifest.time_coverage.end
                        or run.model_version != manifest.model_version or run.input_dataset_version != manifest.input_dataset_version
                        or run.run_timestamp != manifest.run_timestamp
                        or existing.assumptions_checksum != manifest.assumptions_checksum
                        or run.quality_report_checksum != manifest.quality.report_checksum):
                    raise ReceiptError("resume_scenario_or_run_metadata_conflict")
                store = LocalObjectStore(objects)
                for actual, reference in ((existing.assumptions_url, manifest.assumptions_url),
                                          (run.quality_report_uri, manifest.quality.report_reference)):
                    if actual is None or store.resolve_uri(actual) != store.resolve_uri(resolve_reference(bundle_root, reference)):
                        raise ReceiptError("resume_evidence_reference_conflict")
                from services.api.app.db.models import DatasetVersion, ScenarioDatasetVersion
                versions = session.scalars(select(DatasetVersion).join(ScenarioDatasetVersion,
                    ScenarioDatasetVersion.dataset_version_id == DatasetVersion.id).where(
                    ScenarioDatasetVersion.scenario_id == manifest.scenario_id)).all()
                mapping = {(item.dataset_id, item.version): item for item in versions}
                if set(mapping) != {(item.dataset_id, item.version) for item in manifest.datasets}:
                    raise ReceiptError("resume_dataset_link_conflict")
                for item in manifest.datasets:
                    version = mapping[(item.dataset_id, item.version)]
                    if (any(getattr(version, key) != getattr(item, key) for key in ("checksum", "license", "quality_notes", "source_label", "crs"))
                            or version.coverage_start != (item.time_coverage.start if item.time_coverage else None)
                            or version.coverage_end != (item.time_coverage.end if item.time_coverage else None)
                            or store.resolve_uri(version.source_reference) != store.resolve_uri(resolve_reference(bundle_root, item.source_reference))):
                        raise ReceiptError("resume_dataset_provenance_conflict")
                if manifest.historical_event_id:
                    events = HistoricalEventRepository(session)
                    historical = events.get(manifest.historical_event_id)
                    if (historical is None or historical.data_mode != manifest.data_mode
                            or not {item.id for item in versions}.issubset({item.id for item in events.datasets(historical.event_id)})):
                        raise ReceiptError("resume_historical_event_link_conflict")
                for key, digest in entries.items():
                    if raw_hash(destination / key) != digest:
                        raise ReceiptError("resume_staged_bytes_changed")
                from services.api.app.db.models import ResultAsset, AssetSpatialMetadata, ImpactSummary
                assets = session.scalars(select(ResultAsset).where(ResultAsset.scenario_id == manifest.scenario_id,
                                                                  ResultAsset.run_id == manifest.run_id)).all()
                if {asset.asset_type for asset in assets} != set(manifest.assets):
                    raise ReceiptError("resume_asset_set_conflict")
                inspector = GISInspector()
                for asset in sorted(assets, key=lambda item: (not item.asset_type.endswith("_cog"), item.asset_type)):
                    from services.api.app.published_contract import AssetRole
                    role: AssetRole = TypeAdapter(AssetRole).validate_python(asset.asset_type)
                    metadata = manifest.asset_metadata[role]
                    if (any(getattr(asset, key) != getattr(metadata, key) for key in ("checksum", "format", "unit", "crs", "nodata"))
                            or asset.data_mode != manifest.data_mode
                            or asset.coverage_start != metadata.time_coverage.start or asset.coverage_end != metadata.time_coverage.end):
                        raise ReceiptError("resume_asset_metadata_conflict")
                    spatial = session.scalar(select(AssetSpatialMetadata).where(AssetSpatialMetadata.asset_id == asset.id))
                    store = LocalObjectStore(objects)
                    expected = store.resolve_uri(resolve_reference(bundle_root, manifest.assets[role]))
                    if store.resolve_uri(asset.storage_uri) != expected or spatial is None or spatial.source_checksum != asset.checksum:
                        raise ReceiptError("resume_inspection_or_reference_conflict")
                    fresh = inspector(expected, asset.asset_type, metadata)
                    if spatial.details != fresh.details:
                        raise ReceiptError("resume_inspection_metadata_changed")
                    from geoalchemy2.shape import to_shape
                    from geoalchemy2.elements import WKBElement
                    from shapely.geometry import shape  # type: ignore[import-untyped]
                    if not isinstance(spatial.geom, WKBElement) or not to_shape(spatial.geom).equals_exact(shape(fresh.geometry), 1e-10):
                        raise ReceiptError("resume_inspection_geometry_changed")
                summary = session.scalar(select(ImpactSummary).where(ImpactSummary.scenario_id == manifest.scenario_id))
                if summary is None or summary.data_mode != manifest.data_mode or any(getattr(summary, key) != value for key, value in manifest.summary.model_dump().items()):
                    raise ReceiptError("resume_impact_conflict")
                result = "verified_existing_identity"
            else:
                if session.scalar(select(ProcessingRun).where(ProcessingRun.run_id == manifest.run_id)) is not None:
                    raise ReceiptError("run_identity_conflict")
                for key, digest in entries.items():
                    relative_key(key)
                    immutable_copy(root / key, destination / key, digest)
                store = LocalObjectStore(objects)
                datasets = DatasetRepository(session)
                parents = {item["dataset_id"]: DatasetCreate.model_validate(item) for item in catalog_values["datasets"]}
                if len(parents) != len(catalog_values["datasets"]):
                    raise ReceiptError("duplicate_catalog_identity")
                for item in manifest.datasets:
                    parent = datasets.get(item.dataset_id)
                    if parent is None:
                        if item.dataset_id not in parents:
                            raise ReceiptError("actual_input_catalog_parent_required")
                        parent = datasets.register(parents[item.dataset_id])
                    if parent.data_mode != manifest.data_mode:
                        raise ReceiptError("dataset_mode_conflict")
                    source = store.resolve_uri(resolve_reference(bundle_root, item.source_reference)).as_uri()
                    version = datasets.get_version(item.dataset_id, item.version)
                    values = item.model_dump() | {"source_reference": source}
                    if version is None:
                        datasets.register_version(DatasetVersionCreate.model_validate(values))
                    # Exact existing-version provenance is revalidated below by the importer.
                if manifest.historical_event_id:
                    events = HistoricalEventRepository(session)
                    event = events.get(manifest.historical_event_id)
                    supplied = {item["event_id"]: HistoricalEventCreate.model_validate(item) for item in catalog_values["events"]}
                    if event is None:
                        if manifest.historical_event_id not in supplied:
                            raise ReceiptError("actual_historical_event_required")
                        events.register(supplied[manifest.historical_event_id])
                    for item in manifest.datasets:
                        events.link_dataset(manifest.historical_event_id, item.dataset_id, item.version)
                register_published_bundle(session, manifest, store, bundle_root_uri=bundle_root,
                    registered_by=registered_by, trusted_approvers=(), asset_inspector=GISInspector())
                result = "registered_new_draft"
        report.update(operation="integrate", data_imported=result == "registered_new_draft", integration_result=result,
                      target_database=expected_database, stored_scenario_id=manifest.scenario_id,
                      stored_run_id=manifest.run_id, stored_canonical_checksum=canonical_manifest_hash(manifest),
                      staged_directory=str(destination), preview_admission_granted=False,
                      real_api_roundtrip_verified=False)
        report["source_hashes"]["receiving_db.py"] = raw_hash(Path(__file__))
        if inventory(root) != entries:
            raise ReceiptError("originals_changed_after_integration")
        return report
    finally:
        engine.dispose()

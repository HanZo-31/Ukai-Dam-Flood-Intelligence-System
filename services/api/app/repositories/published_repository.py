"""B2 approved-only data access; legacy/admin repositories remain separate."""
from sqlalchemy import select, func
from services.api.app.db.models import Scenario, ProcessingRun, PublishedBundle, ResultAsset, ImpactSummary, DatasetVersion, ScenarioDatasetVersion, PublicationAction
from services.api.app.published_registry import nonblank
from .base import Repository
from .catalog_repository import page
from .query_filters import bbox_values, time_window
from services.api.app.db.models import ScenarioSpatialMetadata, AssetSpatialMetadata


def approved_statement(data_mode):
    if data_mode not in {"demo", "production"}:
        raise ValueError("an explicit demo or production data mode is required")
    return (select(Scenario).join(PublishedBundle, PublishedBundle.scenario_id == Scenario.scenario_id)
            .join(ProcessingRun, ProcessingRun.run_id == PublishedBundle.run_id)
            .where(Scenario.publication_status == "approved", Scenario.status == "completed",
                   Scenario.data_mode == data_mode, ProcessingRun.scenario_id == Scenario.scenario_id,
                   ProcessingRun.status == "completed", ProcessingRun.validation_status == "pass",
                   ProcessingRun.approved_by.is_not(None), ProcessingRun.approved_at.is_not(None)))


def valid_extent_source(data_mode):
    return (select(ResultAsset.id).join(PublishedBundle, PublishedBundle.scenario_id == ResultAsset.scenario_id)
            .where(ResultAsset.id == ScenarioSpatialMetadata.source_asset_id,
                   ResultAsset.scenario_id == ScenarioSpatialMetadata.scenario_id,
                   ResultAsset.run_id == PublishedBundle.run_id, ResultAsset.data_mode == data_mode,
                   ResultAsset.asset_type == "extent_geojson", ResultAsset.checksum == ScenarioSpatialMetadata.source_checksum)
            .correlate(ScenarioSpatialMetadata).exists())


class PublishedScenarioRepository(Repository):
    def get(self, scenario_id, *, data_mode):
        return self.session.scalar(approved_statement(data_mode).where(Scenario.scenario_id == scenario_id))

    def list(self, *, data_mode, scenario_type=None, historical_event_id=None,
             model_version=None, dataset_id=None, dataset_version=None, data_kind=None,
             start=None, end=None, bbox=None, limit=100, offset=0):
        statement = approved_statement(data_mode).order_by(Scenario.scenario_id)
        start, end = time_window(start, end)
        if dataset_version is not None and dataset_id is None:
            raise ValueError("dataset_version requires dataset_id")
        if scenario_type is not None and scenario_type not in {"hypothetical", "historical_replay"}:
            raise ValueError("unknown scenario type")
        if data_kind is not None and data_kind not in {"demo", "observed", "simulated", "assumed"}:
            raise ValueError("unknown data kind")
        for field, value in ((Scenario.model_version, model_version), (Scenario.data_kind, data_kind)):
            if value is not None:
                statement = statement.where(field == value)
        if start is not None:
            statement = statement.where(Scenario.coverage_end >= start)
        if end is not None:
            statement = statement.where(Scenario.coverage_start <= end)
        if dataset_id is not None:
            links = select(ScenarioDatasetVersion.id).join(DatasetVersion, DatasetVersion.id == ScenarioDatasetVersion.dataset_version_id).where(ScenarioDatasetVersion.scenario_id == Scenario.scenario_id, DatasetVersion.dataset_id == dataset_id)
            if dataset_version is not None:
                links = links.where(DatasetVersion.version == dataset_version)
            statement = statement.where(links.exists())
        if bbox is not None:
            bounds = bbox_values(bbox)
            statement = statement.join(ScenarioSpatialMetadata, ScenarioSpatialMetadata.scenario_id == Scenario.scenario_id).where(valid_extent_source(data_mode), func.ST_Intersects(ScenarioSpatialMetadata.geom, func.ST_MakeEnvelope(*bounds, 4326)))
        if scenario_type is not None:
            statement = statement.where(Scenario.scenario_type == scenario_type)
        if historical_event_id is not None:
            statement = statement.where(Scenario.historical_event_id == historical_event_id)
        return self.session.scalars(page(statement, limit, offset)).all()

    def assets(self, scenario_id, *, data_mode, asset_type=None, format=None, limit=100, offset=0):
        approved = approved_statement(data_mode).where(Scenario.scenario_id == scenario_id).with_only_columns(Scenario.scenario_id).subquery()
        statement = (select(ResultAsset).join(PublishedBundle, PublishedBundle.scenario_id == ResultAsset.scenario_id)
                     .where(ResultAsset.scenario_id.in_(select(approved.c.scenario_id)), ResultAsset.run_id == PublishedBundle.run_id,
                            ResultAsset.data_mode == data_mode).order_by(ResultAsset.asset_type))
        if asset_type is not None:
            statement = statement.where(ResultAsset.asset_type == asset_type)
        if format is not None:
            statement = statement.where(ResultAsset.format == format)
        return self.session.scalars(page(statement, limit, offset)).all()

    def footprint(self, scenario_id, *, data_mode):
        approved = approved_statement(data_mode).where(Scenario.scenario_id == scenario_id).with_only_columns(Scenario.scenario_id).subquery()
        return self.session.scalar(select(func.ST_AsGeoJSON(ScenarioSpatialMetadata.geom)).where(ScenarioSpatialMetadata.scenario_id.in_(select(approved.c.scenario_id)), valid_extent_source(data_mode)))

    def spatial_assets(self, scenario_id, *, data_mode):
        approved = approved_statement(data_mode).where(Scenario.scenario_id == scenario_id).with_only_columns(Scenario.scenario_id).subquery()
        return self.session.scalars(select(AssetSpatialMetadata).join(ResultAsset, ResultAsset.id == AssetSpatialMetadata.asset_id).join(PublishedBundle, PublishedBundle.scenario_id == ResultAsset.scenario_id).where(ResultAsset.scenario_id.in_(select(approved.c.scenario_id)), ResultAsset.run_id == PublishedBundle.run_id, ResultAsset.data_mode == data_mode, AssetSpatialMetadata.source_checksum == ResultAsset.checksum).order_by(ResultAsset.asset_type)).all()

    def summary(self, scenario_id, *, data_mode):
        approved = approved_statement(data_mode).where(Scenario.scenario_id == scenario_id).with_only_columns(Scenario.scenario_id).subquery()
        return self.session.scalar(select(ImpactSummary).where(ImpactSummary.scenario_id.in_(select(approved.c.scenario_id)), ImpactSummary.data_mode == data_mode))

    def datasets(self, scenario_id, *, data_mode):
        approved = approved_statement(data_mode).where(Scenario.scenario_id == scenario_id).with_only_columns(Scenario.scenario_id).subquery()
        return self.session.scalars(select(DatasetVersion).join(ScenarioDatasetVersion, ScenarioDatasetVersion.dataset_version_id == DatasetVersion.id).where(ScenarioDatasetVersion.scenario_id.in_(select(approved.c.scenario_id))).order_by(DatasetVersion.id)).all()

    def revoke(self, scenario_id, *, actor, reason):
        """Trusted administrative call, not a B2 public API operation."""
        nonblank(actor, "actor")
        nonblank(reason, "reason")
        with self.session.begin_nested():
            row = self.session.scalar(select(Scenario).join(PublishedBundle, PublishedBundle.scenario_id == Scenario.scenario_id).where(Scenario.scenario_id == scenario_id).with_for_update(of=Scenario))
            if row is None or row.publication_status != "approved":
                raise ValueError("only an approved imported scenario may be revoked")
            row.publication_status = "revoked"
            self.session.add(PublicationAction(scenario_id=scenario_id, action="revoked", actor=actor, reason=reason))
            self.session.flush()
        return row

"""Separate pending-draft read boundary; approved_statement is never widened."""
from sqlalchemy import select, tuple_
from .base import Repository
from services.api.app.db.models import (
    Scenario, ProcessingRun, PublishedBundle, ResultAsset, AssetSpatialMetadata,
    ImpactSummary, DatasetVersion, ScenarioDatasetVersion,
)


def prototype_statement(entries):
    keys = [(item.scenario_id, item.run_id, item.manifest_checksum) for item in entries]
    return (select(Scenario, PublishedBundle, ProcessingRun)
            .join(PublishedBundle, PublishedBundle.scenario_id == Scenario.scenario_id)
            .join(ProcessingRun, ProcessingRun.run_id == PublishedBundle.run_id)
            .where(Scenario.publication_status == "draft", Scenario.status == "completed",
                   Scenario.data_mode == "production", Scenario.data_kind == "simulated",
                   ProcessingRun.scenario_id == Scenario.scenario_id,
                   ProcessingRun.status == "completed", ProcessingRun.validation_status == "pending",
                   ProcessingRun.approved_by.is_(None), ProcessingRun.approved_at.is_(None),
                   tuple_(Scenario.scenario_id, PublishedBundle.run_id, PublishedBundle.manifest_checksum).in_(keys)))


class PrototypeRepository(Repository):
    def get(self, scenario_id, *, entries):
        return self.session.execute(prototype_statement(entries).where(Scenario.scenario_id == scenario_id)).first()

    def list(self, *, entries, limit, offset):
        return self.session.execute(prototype_statement(entries).order_by(Scenario.scenario_id).limit(limit).offset(offset)).all()

    def assets(self, scenario_id, run_id):
        return self.session.execute(select(ResultAsset, AssetSpatialMetadata)
            .outerjoin(AssetSpatialMetadata, AssetSpatialMetadata.asset_id == ResultAsset.id)
            .where(ResultAsset.scenario_id == scenario_id, ResultAsset.run_id == run_id,
                   ResultAsset.data_mode == "production").order_by(ResultAsset.asset_type)).all()

    def summary(self, scenario_id):
        return self.session.scalar(select(ImpactSummary).where(ImpactSummary.scenario_id == scenario_id,
                                                             ImpactSummary.data_mode == "production"))

    def datasets(self, scenario_id):
        return self.session.scalars(select(DatasetVersion).join(ScenarioDatasetVersion,
            ScenarioDatasetVersion.dataset_version_id == DatasetVersion.id)
            .where(ScenarioDatasetVersion.scenario_id == scenario_id).order_by(DatasetVersion.dataset_id, DatasetVersion.version)).all()

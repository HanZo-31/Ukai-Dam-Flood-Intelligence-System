from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.app.db.models import Scenario, ScenarioInput
from services.api.app.repositories.base import Repository
from services.api.app.schemas import ScenarioManifest
from .catalog_repository import page


class ScenarioRepository(Repository):
    def get(self, scenario_id: str) -> Scenario | None:
        return self.session.scalar(select(Scenario).where(Scenario.scenario_id == scenario_id))

    def list(self, *, status=None, data_mode=None, scenario_type=None, model_version=None, limit=100, offset=0):
        statement = select(Scenario).order_by(Scenario.created_at.desc(), Scenario.id.desc())
        if data_mode is not None and data_mode not in {"demo", "production"}:
            raise ValueError("unknown data mode")
        for field, value in ((Scenario.status, status), (Scenario.data_mode, data_mode), (Scenario.scenario_type, scenario_type), (Scenario.model_version, model_version)):
            if value is not None:
                statement = statement.where(field == value)
        return self.session.scalars(page(statement, limit, offset)).all()

    def register(self, manifest: ScenarioManifest) -> Scenario:
        manifest = ScenarioManifest.model_validate(manifest.model_dump())
        if self.get(manifest.scenario_id):
            raise ValueError(f"scenario already exists: {manifest.scenario_id}")
        scenario = Scenario(
            scenario_id=manifest.scenario_id,
            scenario_type=manifest.scenario_type,
            status="registered",
            model_version=manifest.model_version,
            input_dataset_version=manifest.input_dataset_version,
            crs=manifest.crs,
            time_step_minutes=manifest.time_step_minutes,
            parameters=manifest.parameters,
            assumptions_url=manifest.assumptions_url,
            data_mode=manifest.data_mode,
        )
        self.session.add(scenario)
        self.session.flush()
        self.session.add_all(
            ScenarioInput(
                scenario_id=scenario.scenario_id,
                input_type=item.input_type,
                storage_uri=item.storage_uri,
                checksum=item.checksum,
                dataset_version=item.dataset_version,
            )
            for item in manifest.inputs
        )
        self.session.flush()
        return scenario

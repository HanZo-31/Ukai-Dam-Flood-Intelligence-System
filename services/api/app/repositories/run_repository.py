from datetime import datetime, timezone

from sqlalchemy import select

from services.api.app.db.models import ProcessingRun
from services.api.app.repositories.base import Repository
from .catalog_repository import page


class RunRepository(Repository):
    def list_for_scenario(self, scenario_id, *, status=None, stage=None, limit=100, offset=0):
        statement = select(ProcessingRun).where(ProcessingRun.scenario_id == scenario_id).order_by(ProcessingRun.created_at.desc(), ProcessingRun.id.desc())
        for field, value in ((ProcessingRun.status, status), (ProcessingRun.stage, stage)):
            if value is not None:
                statement = statement.where(field == value)
        return self.session.scalars(page(statement, limit, offset)).all()

    def get(self, run_id: str) -> ProcessingRun | None:
        return self.session.scalar(select(ProcessingRun).where(ProcessingRun.run_id == run_id))

    def start(self, *, scenario_id: str, run_id: str, stage: str, log_uri: str | None = None) -> ProcessingRun:
        run = ProcessingRun(
            scenario_id=scenario_id,
            run_id=run_id,
            stage=stage,
            status="running",
            started_at=datetime.now(timezone.utc),
            log_uri=log_uri,
            metadata_json={},
        )
        self.session.add(run)
        self.session.flush()
        return run

    def finish(self, run: ProcessingRun, *, status: str, metadata_json: dict | None = None) -> ProcessingRun:
        if run.status != "running":
            raise ValueError("only a running run can transition to a terminal status")
        if status not in {"completed", "failed"}:
            raise ValueError("terminal run status must be completed or failed")
        run.status = status
        run.completed_at = datetime.now(timezone.utc)
        if metadata_json is not None:
            run.metadata_json = metadata_json
        self.session.flush()
        return run

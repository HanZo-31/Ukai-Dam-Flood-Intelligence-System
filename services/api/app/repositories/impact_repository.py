from sqlalchemy import select

from services.api.app.db.models import ImpactSummary
from services.api.app.repositories.base import Repository


class ImpactRepository(Repository):
    def get(self, scenario_id: str) -> ImpactSummary | None:
        return self.session.scalar(select(ImpactSummary).where(ImpactSummary.scenario_id == scenario_id))

    def upsert(self, scenario_id: str, **values) -> ImpactSummary:
        summary = self.get(scenario_id)
        if summary is None:
            summary = ImpactSummary(scenario_id=scenario_id, **values)
            self.session.add(summary)
        else:
            for key, value in values.items():
                setattr(summary, key, value)
        self.session.flush()
        return summary

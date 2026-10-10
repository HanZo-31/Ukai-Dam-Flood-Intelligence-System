from typing import Literal
from services.api.app.published_contract import ImpactSummary


class ScenarioImpactResponse(ImpactSummary):
    """Registered measurements plus public scenario identity/provenance."""
    scenario_id: str
    model_version: str
    input_dataset_version: str
    data_mode: Literal["demo", "production"]
    data_kind: Literal["observed", "simulated", "assumed", "demo"]

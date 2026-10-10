from sqlalchemy import select

from services.api.app.db.models import ResultAsset
from services.api.app.repositories.base import Repository
from .catalog_repository import page


class AssetRepository(Repository):
    def list_for_scenario(self, scenario_id, *, asset_type=None, run_id=None, format=None, limit=100, offset=0):
        statement = select(ResultAsset).where(ResultAsset.scenario_id == scenario_id).order_by(ResultAsset.id)
        for field, value in ((ResultAsset.asset_type, asset_type), (ResultAsset.run_id, run_id), (ResultAsset.format, format)):
            if value is not None:
                statement = statement.where(field == value)
        return self.session.scalars(page(statement, limit, offset)).all()

    def add(self, **values) -> ResultAsset:
        asset = ResultAsset(**values)
        self.session.add(asset)
        self.session.flush()
        return asset

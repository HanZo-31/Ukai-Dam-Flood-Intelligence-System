"""B2 adapter from B1's approved repository to public response models."""
from collections.abc import Generator
from datetime import datetime
from urllib.parse import quote

from fastapi import HTTPException
from pydantic import ValidationError

from services.api.app.db.session import SessionLocal
from services.api.app.repositories.published_repository import PublishedScenarioRepository
from services.api.app.repositories.run_repository import RunRepository
from services.api.app.api_schemas.scenario import (
    ApprovedQuality, AssumptionsLink, DatasetProvenance, OffsetPagination,
    ScenarioDetail, ScenarioLinks, ScenarioListResponse, ScenarioSummary,
)
from services.api.app.api_schemas.layer import Layer, ScenarioLayersResponse
from services.api.app.api_schemas.impact import ScenarioImpactResponse
from services.api.app.api_schemas.export import ScenarioExportResponse
from services.api.app.published_contract import ImpactSummary, ROLE_UNITS
from services.api.app.services.asset_service import verified_download
from services.api.app.storage import LocalObjectStore, default_store

MAP_ROLES = {
    "max_depth_cog", "max_velocity_cog", "arrival_time_cog", "duration_cog",
    "hazard_cog", "extent_geojson", "exposure_geojson",
}


def resource_url(scenario_id: str, suffix: str, data_mode: str) -> str:
    base = "/api/v1/scenarios/" + quote(scenario_id, safe="")
    return base + suffix + "?data_mode=" + quote(data_mode, safe="")


def public_summary(row) -> ScenarioSummary:
    return ScenarioSummary(
        scenario_id=row.scenario_id, scenario_type=row.scenario_type,
        model_version=row.model_version, input_dataset_version=row.input_dataset_version,
        crs=row.crs, data_mode=row.data_mode, data_kind=row.data_kind,
        historical_event_id=row.historical_event_id, coverage_start=row.coverage_start,
        coverage_end=row.coverage_end,
    )


class ScenarioService:
    def __init__(self, repository: PublishedScenarioRepository, store: LocalObjectStore | None = None) -> None:
        self.repository = repository
        self.store = store if store is not None else default_store()

    def list_scenarios(self, *, data_mode: str, limit: int, offset: int,
                       scenario_type: str | None = None, historical_event_id: str | None = None,
                       model_version: str | None = None, dataset_id: str | None = None,
                       dataset_version: str | None = None, data_kind: str | None = None,
                       start: datetime | None = None, end: datetime | None = None,
                       bbox: tuple[float, float, float, float] | None = None) -> ScenarioListResponse:
        rows = self.repository.list(data_mode=data_mode, limit=limit + 1, offset=offset,
            scenario_type=scenario_type, historical_event_id=historical_event_id,
            model_version=model_version, dataset_id=dataset_id, dataset_version=dataset_version,
            data_kind=data_kind, start=start, end=end, bbox=bbox)
        has_next = len(rows) > limit
        items = [public_summary(row) for row in rows[:limit]]
        return ScenarioListResponse(items=items, pagination=OffsetPagination(
            limit=limit, offset=offset, next_offset=offset + limit if has_next else None))

    def approved_scenario(self, scenario_id: str, data_mode: str):
        row = self.repository.get(scenario_id, data_mode=data_mode)
        if row is None:
            raise HTTPException(404, "The scenario does not exist or is not published.")
        return row

    def detail(self, scenario_id: str, *, data_mode: str) -> ScenarioDetail:
        row = self.approved_scenario(scenario_id, data_mode)
        assets = self.repository.assets(scenario_id, data_mode=data_mode, limit=1000)
        summary = self.repository.summary(scenario_id, data_mode=data_mode)
        # B1 assets() ties these assets to the approved PublishedBundle.run_id.
        # Only that vetted run identity is used with B1's internal run accessor.
        run = RunRepository(self.repository.session).get(assets[0].run_id) if assets else None
        if summary is None or run is None or run.scenario_id != scenario_id or run.run_timestamp is None:
            raise HTTPException(503, "The registered scenario metadata is unavailable.")
        impact = ImpactSummary(**{name: getattr(summary, name) for name in ImpactSummary.model_fields})
        datasets = [DatasetProvenance(
            dataset_id=source.dataset_id, version=source.version,
            source_label=source.source_label, license=source.license,
            checksum=source.checksum, crs=source.crs,
            coverage_start=source.coverage_start, coverage_end=source.coverage_end,
        ) for source in self.repository.datasets(scenario_id, data_mode=data_mode)]
        return ScenarioDetail(
            **public_summary(row).model_dump(), schema_version=row.schema_version,
            time_step_minutes=row.time_step_minutes, parameters=row.parameters,
            parameter_units=row.parameter_units, summary=impact,
            run_id=run.run_id, run_timestamp=run.run_timestamp,
            quality=ApprovedQuality.model_validate(dict(validation_status=run.validation_status,
                approved_by=run.approved_by, approved_at=run.approved_at)),
            datasets=datasets,
            assumptions=AssumptionsLink(
                url=resource_url(scenario_id, "/assumptions", data_mode),
                checksum=row.assumptions_checksum,
            ),
            links=ScenarioLinks(self=resource_url(scenario_id, "", data_mode),
                                layers=resource_url(scenario_id, "/layers", data_mode)),
        )

    def layers(self, scenario_id: str, *, data_mode: str) -> ScenarioLayersResponse:
        row = self.approved_scenario(scenario_id, data_mode)
        assets = self.repository.assets(scenario_id, data_mode=data_mode, limit=1000)
        layers = [Layer(
            asset_type=asset.asset_type, format=asset.format, crs=asset.crs,
            unit=asset.unit, nodata=asset.nodata, checksum=asset.checksum,
            coverage_start=asset.coverage_start, coverage_end=asset.coverage_end,
            url=resource_url(scenario_id, "/assets/" + quote(asset.asset_type, safe=""), data_mode),
        ) for asset in assets if asset.asset_type in MAP_ROLES]
        return ScenarioLayersResponse(
            scenario_id=row.scenario_id, model_version=row.model_version,
            input_dataset_version=row.input_dataset_version,
            data_mode=row.data_mode, data_kind=row.data_kind, layers=layers,
        )

    def impact(self, scenario_id: str, *, data_mode: str) -> ScenarioImpactResponse:
        row = self.approved_scenario(scenario_id, data_mode)
        summary = self.repository.summary(scenario_id, data_mode=data_mode)
        if summary is None:
            raise HTTPException(503, "The registered impact summary is unavailable.")
        try:
            return ScenarioImpactResponse(
                scenario_id=row.scenario_id, model_version=row.model_version,
                input_dataset_version=row.input_dataset_version,
                data_mode=row.data_mode, data_kind=row.data_kind,
                **{name: getattr(summary, name) for name in ImpactSummary.model_fields},
            )
        except ValidationError as error:
            raise HTTPException(503, "The registered impact summary is unavailable.") from error

    def export(self, scenario_id: str, *, format: str, data_mode: str) -> ScenarioExportResponse:
        row = self.approved_scenario(scenario_id, data_mode)
        role = {"geojson": "export_geojson", "kml": "export_kml"}.get(format)
        if role is None:
            raise HTTPException(422, "Invalid export format.")
        assets = self.repository.assets(scenario_id, data_mode=data_mode, asset_type=role, limit=1)
        if not assets:
            raise HTTPException(404, "The requested export does not exist or is not published.")
        asset = assets[0]
        if asset.format != format:
            raise HTTPException(503, "The registered export metadata is unavailable.")
        result = ScenarioExportResponse.model_validate(dict(
            scenario_id=row.scenario_id, model_version=row.model_version,
            input_dataset_version=row.input_dataset_version, data_mode=row.data_mode,
            data_kind=row.data_kind, asset_type=role, format=format,
            crs=asset.crs, unit=asset.unit, checksum=asset.checksum,
            coverage_start=asset.coverage_start, coverage_end=asset.coverage_end,
            download_url=resource_url(scenario_id, "/assets/" + role, data_mode),
        ))
        # Discovery is not an availability lease. Delivery rechecks approval
        # and integrity, including if the object changes after this request.
        media = "application/geo+json" if format == "geojson" else "application/vnd.google-earth.kml+xml"
        download = verified_download(self.store, asset.storage_uri, asset.checksum,
                                     media_type=media, filename=role + "." + format)
        download.handle.close()
        return result

    def asset_download(self, scenario_id: str, asset_type: str, *, data_mode: str):
        self.approved_scenario(scenario_id, data_mode)
        assets = self.repository.assets(scenario_id, data_mode=data_mode, asset_type=asset_type, limit=1)
        if not assets:
            raise HTTPException(404, "The asset does not exist or is not published.")
        asset = assets[0]
        formats = {"cog": ("image/tiff", ".tif"),
                   "geojson": ("application/geo+json", ".geojson"),
                   "kml": ("application/vnd.google-earth.kml+xml", ".kml")}
        expected_format = "cog" if asset_type.endswith("_cog") else "geojson" if asset_type.endswith("_geojson") else "kml"
        if asset.format not in formats or asset.format != expected_format or asset.unit != ROLE_UNITS.get(asset_type):
            raise HTTPException(503, "The registered artifact format is unavailable.")
        media_type, extension = formats[asset.format]
        return verified_download(self.store, asset.storage_uri, asset.checksum,
                                 media_type=media_type, filename=asset_type + extension)

    def assumptions_download(self, scenario_id: str, *, data_mode: str):
        row = self.approved_scenario(scenario_id, data_mode)
        return verified_download(self.store, row.assumptions_url, row.assumptions_checksum,
                                 media_type="text/plain", filename="assumptions.txt")


def get_scenario_service() -> Generator[ScenarioService, None, None]:
    session = SessionLocal()
    try:
        yield ScenarioService(PublishedScenarioRepository(session))
    finally:
        session.close()

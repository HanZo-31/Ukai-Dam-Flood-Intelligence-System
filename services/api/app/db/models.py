from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Scenario(Base):
    __tablename__ = "scenarios"
    __table_args__ = (
        CheckConstraint("publication_status IS NULL OR publication_status IN ('draft', 'approved', 'rejected', 'revoked')", name="ck_scenario_publication_status"),
        CheckConstraint("(coverage_start IS NULL AND coverage_end IS NULL) OR (coverage_start IS NOT NULL AND coverage_end IS NOT NULL AND coverage_end >= coverage_start)", name="ck_scenario_coverage"),
    )
    publication_status: Mapped[str | None] = mapped_column(String(20), index=True)
    schema_version: Mapped[str | None] = mapped_column(String(20))
    data_kind: Mapped[str | None] = mapped_column(String(20))
    parameter_units: Mapped[dict | None] = mapped_column(JSONB)
    coverage_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    coverage_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    historical_event_id: Mapped[str | None] = mapped_column(String(150), ForeignKey("historical_events.event_id", name="fk_scenario_historical_event", ondelete="RESTRICT"), index=True)
    assumptions_checksum: Mapped[str | None] = mapped_column(String(71))

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    scenario_id: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        nullable=False,
        index=True,
    )

    scenario_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    model_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    input_dataset_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    crs: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    time_step_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    parameters: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    assumptions_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    data_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="demo",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

class ResultAsset(Base):
    __tablename__ = "result_assets"
    __table_args__ = (
        UniqueConstraint("run_id", "asset_type", name="uq_run_asset_role"),
        CheckConstraint("(coverage_start IS NULL AND coverage_end IS NULL) OR (coverage_start IS NOT NULL AND coverage_end IS NOT NULL AND coverage_end >= coverage_start)", name="ck_asset_coverage"),
        CheckConstraint("nodata IS NULL OR nodata NOT IN ('NaN'::float8, 'Infinity'::float8, '-Infinity'::float8)", name="ck_asset_nodata"),
    )
    run_id: Mapped[str | None] = mapped_column(String(150), ForeignKey("processing_runs.run_id", name="fk_asset_run", ondelete="RESTRICT"), index=True)
    format: Mapped[str | None] = mapped_column(String(20))
    unit: Mapped[str | None] = mapped_column(Text)
    coverage_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    coverage_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    nodata: Mapped[float | None] = mapped_column(Float)

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    scenario_id: Mapped[str] = mapped_column(
        String(150),
        ForeignKey("scenarios.scenario_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    asset_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    storage_uri: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    crs: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    checksum: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    data_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="demo",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ImpactSummary(Base):
    __tablename__ = "impact_summaries"
    __table_args__ = (
        CheckConstraint("roads_affected_km IS NULL OR (roads_affected_km >= 0 AND roads_affected_km NOT IN ('NaN'::float8, 'Infinity'::float8, '-Infinity'::float8))", name="ck_impact_roads"),
        CheckConstraint("critical_facilities_exposed IS NULL OR critical_facilities_exposed >= 0", name="ck_impact_facilities"),
    )
    roads_affected_km: Mapped[float | None] = mapped_column(Float)
    critical_facilities_exposed: Mapped[int | None] = mapped_column(Integer)

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    scenario_id: Mapped[str] = mapped_column(
        String(150),
        ForeignKey("scenarios.scenario_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    max_depth_m: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    flooded_area_km2: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    population_exposed: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    buildings_exposed: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    data_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="demo",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class StatusReading(Base):
    __tablename__ = "status_readings"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    reading_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    reservoir_level_m: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    inflow_m3s: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    release_m3s: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    data_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="demo",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ScenarioInput(Base):
    """Immutable input reference captured when a scenario is registered."""

    __tablename__ = "scenario_inputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[str] = mapped_column(
        String(150), ForeignKey("scenarios.scenario_id", ondelete="CASCADE"), nullable=False, index=True
    )
    input_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ProcessingRun(Base):
    """Execution audit trail; B2 can use this to locate a scenario's outputs."""

    __tablename__ = "processing_runs"
    __table_args__ = (
        UniqueConstraint("run_id", name="processing_runs_run_id_key"),
        CheckConstraint("validation_status IS NULL OR validation_status IN ('pending', 'pass', 'fail')", name="ck_run_validation"),
        CheckConstraint("(approved_by IS NULL AND approved_at IS NULL) OR (approved_by IS NOT NULL AND length(btrim(approved_by)) > 0 AND approved_at IS NOT NULL AND validation_status IS NOT DISTINCT FROM 'pass' AND run_timestamp IS NOT NULL AND approved_at >= run_timestamp)", name="ck_run_approval"),
    )
    model_version: Mapped[str | None] = mapped_column(String(100))
    input_dataset_version: Mapped[str | None] = mapped_column(String(100))
    run_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    validation_status: Mapped[str | None] = mapped_column(String(20))
    quality_report_uri: Mapped[str | None] = mapped_column(Text)
    quality_report_checksum: Mapped[str | None] = mapped_column(String(71))
    approved_by: Mapped[str | None] = mapped_column(Text)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[str] = mapped_column(
        String(150), ForeignKey("scenarios.scenario_id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_id: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, index=True)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    log_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


# Register the catalog tables on the same metadata used by Alembic and backups.
from .catalog_models import Dataset, DatasetVersion, HistoricalEvent, HistoricalEventDataset, ValidationMetric  # noqa: E402,F401
from .publication_models import PublishedBundle, ScenarioDatasetVersion, PublicationAction  # noqa: E402,F401
from .spatial_models import AssetSpatialMetadata, ScenarioSpatialMetadata  # noqa: E402,F401

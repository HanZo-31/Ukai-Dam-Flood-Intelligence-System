"""B1 catalog entities. Foreign keys retain provenance instead of cascading it away."""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class CatalogRow:
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Dataset(CatalogRow, Base):
    __tablename__ = "datasets"
    __table_args__ = (CheckConstraint("data_mode IN ('demo', 'production')", name="ck_dataset_mode"),)
    dataset_id: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    data_mode: Mapped[str] = mapped_column(String(20), nullable=False)


class DatasetVersion(CatalogRow, Base):
    __tablename__ = "dataset_versions"
    __table_args__ = (
        UniqueConstraint("dataset_id", "version", name="uq_dataset_version"),
        CheckConstraint("source_label IN ('observed', 'simulated', 'assumed', 'demo')", name="ck_version_source"),
        CheckConstraint("checksum ~ '^sha256:[0-9a-f]{64}$'", name="ck_version_checksum"),
        CheckConstraint("(coverage_start IS NULL AND coverage_end IS NULL) OR (coverage_start IS NOT NULL AND coverage_end IS NOT NULL AND coverage_end >= coverage_start)", name="ck_version_coverage"),
    )
    dataset_id: Mapped[str] = mapped_column(String(150), ForeignKey("datasets.dataset_id", ondelete="RESTRICT"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    source_reference: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_label: Mapped[str] = mapped_column(String(20), nullable=False)
    license: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str] = mapped_column(String(71), nullable=False)
    crs: Mapped[str | None] = mapped_column(String(50))
    coverage_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    coverage_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quality_notes: Mapped[str] = mapped_column(Text, nullable=False)
    units: Mapped[dict] = mapped_column(JSONB, nullable=False)


class HistoricalEvent(CatalogRow, Base):
    __tablename__ = "historical_events"
    __table_args__ = (
        CheckConstraint("coverage_end >= coverage_start", name="ck_event_coverage"),
        CheckConstraint("data_mode IN ('demo', 'production')", name="ck_event_mode"),
    )
    event_id: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    coverage_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    coverage_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_coverage: Mapped[str] = mapped_column(Text, nullable=False)
    quality_notes: Mapped[str] = mapped_column(Text, nullable=False)
    source_urls: Mapped[list] = mapped_column(JSONB, nullable=False)
    data_mode: Mapped[str] = mapped_column(String(20), nullable=False)


class HistoricalEventDataset(CatalogRow, Base):
    __tablename__ = "historical_event_datasets"
    __table_args__ = (UniqueConstraint("event_id", "dataset_version_id", name="uq_event_dataset_version"),)
    event_id: Mapped[str] = mapped_column(String(150), ForeignKey("historical_events.event_id", ondelete="RESTRICT"), nullable=False, index=True)
    dataset_version_id: Mapped[int] = mapped_column(Integer, ForeignKey("dataset_versions.id", ondelete="RESTRICT"), nullable=False, index=True)


class ValidationMetric(CatalogRow, Base):
    __tablename__ = "validation_metrics"
    __table_args__ = (
        ForeignKeyConstraint(["event_id", "dataset_version_id"], ["historical_event_datasets.event_id", "historical_event_datasets.dataset_version_id"], name="fk_metric_event_dataset", ondelete="RESTRICT"),
        CheckConstraint("metric_name IN ('rmse', 'mae', 'peak_stage_error', 'timing_error', 'iou', 'flood_area_agreement')", name="ck_metric_name"),
        CheckConstraint("value NOT IN ('NaN'::float8, 'Infinity'::float8, '-Infinity'::float8)", name="ck_metric_finite"),
        CheckConstraint("metric_name NOT IN ('rmse', 'mae') OR value >= 0", name="ck_metric_nonnegative"),
        CheckConstraint("metric_name NOT IN ('iou', 'flood_area_agreement') OR (value BETWEEN 0 AND 1 AND unit = 'fraction')", name="ck_metric_fraction"),
        CheckConstraint("sample_count IS NULL OR sample_count > 0", name="ck_metric_samples"),
        CheckConstraint("report_checksum ~ '^sha256:[0-9a-f]{64}$'", name="ck_metric_checksum"),
    )
    metric_id: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    event_id: Mapped[str] = mapped_column(String(150), ForeignKey("historical_events.event_id", ondelete="RESTRICT"), nullable=False, index=True)
    dataset_version_id: Mapped[int] = mapped_column(Integer, ForeignKey("dataset_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    run_id: Mapped[str | None] = mapped_column(String(150), ForeignKey("processing_runs.run_id", ondelete="RESTRICT"), index=True)
    station_id: Mapped[str | None] = mapped_column(String(150), index=True)
    metric_name: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(Text, nullable=False)
    sample_count: Mapped[int | None] = mapped_column(Integer)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    calculation_config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    report_reference: Mapped[str] = mapped_column(Text, nullable=False)
    report_checksum: Mapped[str] = mapped_column(String(71), nullable=False)

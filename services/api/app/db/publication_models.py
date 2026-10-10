"""Verified imported snapshots and their publication audit trail."""
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class PublishedBundle(Base):
    __tablename__ = "published_bundles"
    __table_args__ = (CheckConstraint("manifest_checksum ~ '^sha256:[0-9a-f]{64}$'", name="ck_bundle_checksum"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[str] = mapped_column(String(150), ForeignKey("scenarios.scenario_id", ondelete="RESTRICT"), nullable=False, unique=True)
    run_id: Mapped[str] = mapped_column(String(150), ForeignKey("processing_runs.run_id", ondelete="RESTRICT"), nullable=False, unique=True)
    bundle_root_uri: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_checksum: Mapped[str] = mapped_column(String(71), nullable=False)
    manifest_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    registered_by: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ScenarioDatasetVersion(Base):
    __tablename__ = "scenario_dataset_versions"
    __table_args__ = (UniqueConstraint("scenario_id", "dataset_version_id", name="uq_scenario_dataset_version"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[str] = mapped_column(String(150), ForeignKey("scenarios.scenario_id", ondelete="RESTRICT"), nullable=False, index=True)
    dataset_version_id: Mapped[int] = mapped_column(Integer, ForeignKey("dataset_versions.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PublicationAction(Base):
    __tablename__ = "publication_actions"
    __table_args__ = (CheckConstraint("action IN ('registered', 'revoked')", name="ck_publication_action"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[str] = mapped_column(String(150), ForeignKey("scenarios.scenario_id", ondelete="RESTRICT"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    actor: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

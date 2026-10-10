"""Small spatial metadata only; raster bytes stay in immutable object storage."""
from datetime import datetime
from geoalchemy2 import Geometry
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class AssetSpatialMetadata(Base):
    __tablename__ = "asset_spatial_metadata"
    __table_args__ = (
        CheckConstraint("ST_IsValid(geom) AND NOT ST_IsEmpty(geom)", name="ck_asset_spatial_valid"),
        Index("ix_asset_spatial_geom", "geom", postgresql_using="gist"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("result_assets.id", ondelete="RESTRICT"), nullable=False, unique=True)
    geom: Mapped[object] = mapped_column(Geometry("MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source_checksum: Mapped[str] = mapped_column(String(71), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ScenarioSpatialMetadata(Base):
    __tablename__ = "scenario_spatial_metadata"
    __table_args__ = (
        CheckConstraint("ST_IsValid(geom) AND NOT ST_IsEmpty(geom)", name="ck_scenario_spatial_valid"),
        Index("ix_scenario_spatial_geom", "geom", postgresql_using="gist"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[str] = mapped_column(String(150), ForeignKey("scenarios.scenario_id", ondelete="RESTRICT"), nullable=False, unique=True)
    source_asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("result_assets.id", ondelete="RESTRICT"), nullable=False, unique=True)
    geom: Mapped[object] = mapped_column(Geometry("MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False)
    source_checksum: Mapped[str] = mapped_column(String(71), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

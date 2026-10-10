"""Add indexed verified asset bounds and scenario extents.

Revision ID: g05b8eab1001
Revises: f04b5e7b1001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry

revision = "g05b8eab1001"
down_revision = "f04b5e7b1001"
branch_labels = None
depends_on = None


def upgrade():
    for table, owner, target, check in (
        ("asset_spatial_metadata", "asset_id", "result_assets.id", "ck_asset_spatial_valid"),
        ("scenario_spatial_metadata", "scenario_id", "scenarios.scenario_id", "ck_scenario_spatial_valid"),
    ):
        columns = [
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(owner, sa.Integer() if owner == "asset_id" else sa.String(150), sa.ForeignKey(target, ondelete="RESTRICT"), nullable=False, unique=True),
            sa.Column("geom", Geometry("MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False),
            sa.Column("source_checksum", sa.String(71), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("ST_IsValid(geom) AND NOT ST_IsEmpty(geom)", name=check),
        ]
        if owner == "asset_id":
            columns.append(sa.Column("details", JSONB(), nullable=False))
        else:
            columns.append(sa.Column("source_asset_id", sa.Integer(), sa.ForeignKey("result_assets.id", ondelete="RESTRICT"), nullable=False, unique=True))
        op.create_table(table, *columns)
        op.create_index("ix_asset_spatial_geom" if owner == "asset_id" else "ix_scenario_spatial_geom", table, ["geom"], postgresql_using="gist")


def downgrade():
    op.drop_table("scenario_spatial_metadata")
    op.drop_table("asset_spatial_metadata")

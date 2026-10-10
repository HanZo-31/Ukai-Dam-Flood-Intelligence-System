"""add immutable scenario inputs and processing-run audit records

Revision ID: c01b8f01b101
Revises: b52235f9108d
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c01b8f01b101"
down_revision = "b52235f9108d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scenario_inputs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scenario_id", sa.String(length=150), nullable=False),
        sa.Column("input_type", sa.String(length=100), nullable=False),
        sa.Column("storage_uri", sa.Text(), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("dataset_version", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.scenario_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scenario_inputs_scenario_id", "scenario_inputs", ["scenario_id"])
    op.create_table(
        "processing_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scenario_id", sa.String(length=150), nullable=False),
        sa.Column("run_id", sa.String(length=100), nullable=False),
        sa.Column("stage", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("log_uri", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.scenario_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index("ix_processing_runs_scenario_id", "processing_runs", ["scenario_id"])
    op.create_index("ix_processing_runs_run_id", "processing_runs", ["run_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_processing_runs_run_id", table_name="processing_runs")
    op.drop_index("ix_processing_runs_scenario_id", table_name="processing_runs")
    op.drop_table("processing_runs")
    op.drop_index("ix_scenario_inputs_scenario_id", table_name="scenario_inputs")
    op.drop_table("scenario_inputs")

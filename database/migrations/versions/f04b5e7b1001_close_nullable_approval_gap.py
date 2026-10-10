"""Close nullable approval-state gap without changing an applied migration.

Revision ID: f04b5e7b1001
Revises: e03b5e7b1001
"""
from alembic import op

revision = "f04b5e7b1001"
down_revision = "e03b5e7b1001"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_run_approval", "processing_runs", type_="check")
    op.create_check_constraint(
        "ck_run_approval", "processing_runs",
        "(approved_by IS NULL AND approved_at IS NULL) OR "
        "(approved_by IS NOT NULL AND length(btrim(approved_by)) > 0 "
        "AND approved_at IS NOT NULL AND validation_status IS NOT DISTINCT FROM 'pass' "
        "AND run_timestamp IS NOT NULL AND approved_at >= run_timestamp)",
    )


def downgrade():
    op.drop_constraint("ck_run_approval", "processing_runs", type_="check")
    op.create_check_constraint(
        "ck_run_approval", "processing_runs",
        "approved_at IS NULL OR (approved_by IS NOT NULL AND validation_status = 'pass' "
        "AND run_timestamp IS NOT NULL AND approved_at >= run_timestamp)",
    )

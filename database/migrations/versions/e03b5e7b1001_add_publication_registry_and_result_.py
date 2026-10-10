"""add publication registry and result metadata

Revision ID: e03b5e7b1001
Revises: d02c3e4b1001
Create Date: 2026-10-05 01:05:59.561130

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e03b5e7b1001'
down_revision: Union[str, Sequence[str], None] = 'd02c3e4b1001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Only nullable metadata, new catalog tables and an expanded run identifier.
    op.alter_column('processing_runs', 'run_id', existing_type=sa.String(100), type_=sa.String(150), existing_nullable=False)
    op.alter_column('validation_metrics', 'run_id', existing_type=sa.String(100), type_=sa.String(150), existing_nullable=True)
    op.create_table('publication_actions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('scenario_id', sa.String(length=150), nullable=False),
    sa.Column('action', sa.String(length=20), nullable=False),
    sa.Column('actor', sa.Text(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("action IN ('registered', 'revoked')", name='ck_publication_action'),
    sa.ForeignKeyConstraint(['scenario_id'], ['scenarios.scenario_id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_publication_actions_scenario_id'), 'publication_actions', ['scenario_id'], unique=False)
    op.create_table('scenario_dataset_versions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('scenario_id', sa.String(length=150), nullable=False),
    sa.Column('dataset_version_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['dataset_version_id'], ['dataset_versions.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['scenario_id'], ['scenarios.scenario_id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('scenario_id', 'dataset_version_id', name='uq_scenario_dataset_version')
    )
    op.create_index(op.f('ix_scenario_dataset_versions_dataset_version_id'), 'scenario_dataset_versions', ['dataset_version_id'], unique=False)
    op.create_index(op.f('ix_scenario_dataset_versions_scenario_id'), 'scenario_dataset_versions', ['scenario_id'], unique=False)
    op.create_table('published_bundles',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('scenario_id', sa.String(length=150), nullable=False),
    sa.Column('run_id', sa.String(length=150), nullable=False),
    sa.Column('bundle_root_uri', sa.Text(), nullable=False),
    sa.Column('manifest_checksum', sa.String(length=71), nullable=False),
    sa.Column('manifest_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('registered_by', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("manifest_checksum ~ '^sha256:[0-9a-f]{64}$'", name='ck_bundle_checksum'),
    sa.ForeignKeyConstraint(['run_id'], ['processing_runs.run_id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['scenario_id'], ['scenarios.scenario_id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('run_id'),
    sa.UniqueConstraint('scenario_id')
    )
    op.add_column('impact_summaries', sa.Column('roads_affected_km', sa.Float(), nullable=True))
    op.add_column('impact_summaries', sa.Column('critical_facilities_exposed', sa.Integer(), nullable=True))
    op.add_column('processing_runs', sa.Column('model_version', sa.String(length=100), nullable=True))
    op.add_column('processing_runs', sa.Column('input_dataset_version', sa.String(length=100), nullable=True))
    op.add_column('processing_runs', sa.Column('run_timestamp', sa.DateTime(timezone=True), nullable=True))
    op.add_column('processing_runs', sa.Column('validation_status', sa.String(length=20), nullable=True))
    op.add_column('processing_runs', sa.Column('quality_report_uri', sa.Text(), nullable=True))
    op.add_column('processing_runs', sa.Column('quality_report_checksum', sa.String(length=71), nullable=True))
    op.add_column('processing_runs', sa.Column('approved_by', sa.Text(), nullable=True))
    op.add_column('processing_runs', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('result_assets', sa.Column('run_id', sa.String(length=150), nullable=True))
    op.add_column('result_assets', sa.Column('format', sa.String(length=20), nullable=True))
    op.add_column('result_assets', sa.Column('unit', sa.Text(), nullable=True))
    op.add_column('result_assets', sa.Column('coverage_start', sa.DateTime(timezone=True), nullable=True))
    op.add_column('result_assets', sa.Column('coverage_end', sa.DateTime(timezone=True), nullable=True))
    op.add_column('result_assets', sa.Column('nodata', sa.Float(), nullable=True))
    op.create_index(op.f('ix_result_assets_run_id'), 'result_assets', ['run_id'], unique=False)
    op.create_unique_constraint('uq_run_asset_role', 'result_assets', ['run_id', 'asset_type'])
    op.create_foreign_key('fk_asset_run', 'result_assets', 'processing_runs', ['run_id'], ['run_id'], ondelete='RESTRICT')
    op.add_column('scenarios', sa.Column('publication_status', sa.String(length=20), nullable=True))
    op.add_column('scenarios', sa.Column('schema_version', sa.String(length=20), nullable=True))
    op.add_column('scenarios', sa.Column('data_kind', sa.String(length=20), nullable=True))
    op.add_column('scenarios', sa.Column('parameter_units', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('scenarios', sa.Column('coverage_start', sa.DateTime(timezone=True), nullable=True))
    op.add_column('scenarios', sa.Column('coverage_end', sa.DateTime(timezone=True), nullable=True))
    op.add_column('scenarios', sa.Column('historical_event_id', sa.String(length=150), nullable=True))
    op.add_column('scenarios', sa.Column('assumptions_checksum', sa.String(length=71), nullable=True))
    op.create_index(op.f('ix_scenarios_historical_event_id'), 'scenarios', ['historical_event_id'], unique=False)
    op.create_index(op.f('ix_scenarios_publication_status'), 'scenarios', ['publication_status'], unique=False)
    op.create_foreign_key('fk_scenario_historical_event', 'scenarios', 'historical_events', ['historical_event_id'], ['event_id'], ondelete='RESTRICT')
    op.create_check_constraint('ck_scenario_publication_status', 'scenarios', "publication_status IS NULL OR publication_status IN ('draft', 'approved', 'rejected', 'revoked')")
    op.create_check_constraint('ck_scenario_coverage', 'scenarios', '(coverage_start IS NULL AND coverage_end IS NULL) OR (coverage_start IS NOT NULL AND coverage_end IS NOT NULL AND coverage_end >= coverage_start)')
    op.create_check_constraint('ck_asset_coverage', 'result_assets', '(coverage_start IS NULL AND coverage_end IS NULL) OR (coverage_start IS NOT NULL AND coverage_end IS NOT NULL AND coverage_end >= coverage_start)')
    op.create_check_constraint('ck_asset_nodata', 'result_assets', "nodata IS NULL OR nodata NOT IN ('NaN'::float8, 'Infinity'::float8, '-Infinity'::float8)")
    op.create_check_constraint('ck_impact_roads', 'impact_summaries', "roads_affected_km IS NULL OR (roads_affected_km >= 0 AND roads_affected_km NOT IN ('NaN'::float8, 'Infinity'::float8, '-Infinity'::float8))")
    op.create_check_constraint('ck_impact_facilities', 'impact_summaries', 'critical_facilities_exposed IS NULL OR critical_facilities_exposed >= 0')
    op.create_check_constraint('ck_run_validation', 'processing_runs', "validation_status IS NULL OR validation_status IN ('pending', 'pass', 'fail')")
    op.create_check_constraint('ck_run_approval', 'processing_runs', "approved_at IS NULL OR (approved_by IS NOT NULL AND validation_status = 'pass' AND run_timestamp IS NOT NULL AND approved_at >= run_timestamp)")
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # Never silently truncate newer IDs when reverting the expanded identifier.
    if op.get_bind().execute(sa.text('SELECT EXISTS (SELECT 1 FROM processing_runs WHERE length(run_id) > 100 UNION ALL SELECT 1 FROM validation_metrics WHERE length(run_id) > 100)')).scalar():
        raise RuntimeError('Cannot downgrade with run identifiers longer than 100 characters')
    for table, name in (
        ('scenarios', 'ck_scenario_publication_status'), ('scenarios', 'ck_scenario_coverage'),
        ('result_assets', 'ck_asset_coverage'), ('result_assets', 'ck_asset_nodata'),
        ('impact_summaries', 'ck_impact_roads'), ('impact_summaries', 'ck_impact_facilities'),
        ('processing_runs', 'ck_run_validation'), ('processing_runs', 'ck_run_approval'),
    ):
        op.drop_constraint(name, table, type_='check')
    op.drop_constraint('fk_scenario_historical_event', 'scenarios', type_='foreignkey')
    op.drop_index(op.f('ix_scenarios_publication_status'), table_name='scenarios')
    op.drop_index(op.f('ix_scenarios_historical_event_id'), table_name='scenarios')
    op.drop_column('scenarios', 'assumptions_checksum')
    op.drop_column('scenarios', 'historical_event_id')
    op.drop_column('scenarios', 'coverage_end')
    op.drop_column('scenarios', 'coverage_start')
    op.drop_column('scenarios', 'parameter_units')
    op.drop_column('scenarios', 'data_kind')
    op.drop_column('scenarios', 'schema_version')
    op.drop_column('scenarios', 'publication_status')
    op.drop_constraint('fk_asset_run', 'result_assets', type_='foreignkey')
    op.drop_constraint('uq_run_asset_role', 'result_assets', type_='unique')
    op.drop_index(op.f('ix_result_assets_run_id'), table_name='result_assets')
    op.drop_column('result_assets', 'nodata')
    op.drop_column('result_assets', 'coverage_end')
    op.drop_column('result_assets', 'coverage_start')
    op.drop_column('result_assets', 'unit')
    op.drop_column('result_assets', 'format')
    op.drop_column('result_assets', 'run_id')
    op.drop_column('processing_runs', 'approved_at')
    op.drop_column('processing_runs', 'approved_by')
    op.drop_column('processing_runs', 'quality_report_checksum')
    op.drop_column('processing_runs', 'quality_report_uri')
    op.drop_column('processing_runs', 'validation_status')
    op.drop_column('processing_runs', 'run_timestamp')
    op.drop_column('processing_runs', 'input_dataset_version')
    op.drop_column('processing_runs', 'model_version')
    op.drop_column('impact_summaries', 'critical_facilities_exposed')
    op.drop_column('impact_summaries', 'roads_affected_km')
    op.drop_table('published_bundles')
    op.drop_index(op.f('ix_scenario_dataset_versions_scenario_id'), table_name='scenario_dataset_versions')
    op.drop_index(op.f('ix_scenario_dataset_versions_dataset_version_id'), table_name='scenario_dataset_versions')
    op.drop_table('scenario_dataset_versions')
    op.drop_index(op.f('ix_publication_actions_scenario_id'), table_name='publication_actions')
    op.drop_table('publication_actions')
    op.alter_column('validation_metrics', 'run_id', existing_type=sa.String(150), type_=sa.String(100), existing_nullable=True)
    op.alter_column('processing_runs', 'run_id', existing_type=sa.String(150), type_=sa.String(100), existing_nullable=False)
    # ### end Alembic commands ###

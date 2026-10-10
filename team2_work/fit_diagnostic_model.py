"""Fit an experimental spatial regression; original plan's ML demo gate stays closed."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import time
from zoneinfo import ZoneInfo

import numpy as np
import rasterio


def read(root, role):
    manifest = json.loads((root / 'prototype-manifest.json').read_text())
    path = root / manifest['assets'][role]
    with path.open('rb') as handle:
        if 'sha256:' + hashlib.file_digest(handle, 'sha256').hexdigest() != manifest['asset_metadata'][role]['checksum']:
            raise ValueError('Source hash mismatch')
    with rasterio.open(path) as dataset:
        values = dataset.read(1, masked=True)
        return values.data.astype(np.float64), ~np.ma.getmaskarray(values) & np.isfinite(values.data), manifest


def errors(predicted, actual):
    residual = predicted - actual
    return {'mae': float(np.abs(residual).mean()), 'rmse': float(np.sqrt(np.square(residual).mean())),
            'signed_bias': float(residual.mean()), 'p95_absolute_error': float(np.percentile(np.abs(residual), 95))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text())
    if (not audit['passed'] or not audit['all_registered_raster_grids_equal']
            or not audit['hypothetical_geometry_identical'] or not audit['hypothetical_terrain_identical']
            or any(audit['non_identity_hypothetical_plan_differences'].values())
            or max(audit['hypothetical_hydrograph_shape']['shape_max_absolute_differences'].values()) > 0.0001):
        raise ValueError('Scenario compatibility prerequisite failed')
    if args.output.exists():
        raise ValueError('Use a fresh diagnostic delivery')
    args.output.mkdir(parents=True)
    clock = time.perf_counter()
    report = {'started_at': datetime.now(ZoneInfo('Asia/Calcutta')).isoformat(),
        'model': 'spatial_log_linear_regression', 'model_version': '0.1.0-diagnostic',
        'experiment_kind': 'ML approximation diagnostic; not hydraulic simulation',
        'fit_scenarios': ['h01', 'h03'], 'holdout_scenario': 'h02',
        'historical_2006_used_for_training': False, 'scenario_level_holdout': True,
        'hyperparameters_tuned_on_holdout': False, 'extra_scenario_runs': 0,
        'scientifically_validated': False, 'calibration_status': 'uncalibrated',
        'two_disjoint_intermediate_holdouts_available': False,
        'original_plan_surrogate_gate_passed': False, 'enable_new_condition_ml_in_demo': False,
        'planned_fallback': 'stored HEC-RAS reference exploration with actual returned peak clearly displayed',
        'reason': 'Only three comparable hypothetical runs and one intermediate holdout; original plan requires at least two disjoint intermediate holdouts.',
        'roles': {}, 'lineage': audit['scenarios'],
        'prediction_domain_rule': 'Only cells valid at both endpoint training scenarios; invalid cells are unknown, not observed dry zeros.'}
    coefficients = {}
    q = np.asarray([15000., 30000.])
    feature = np.log(q / 20000.)
    design = np.stack([np.ones(2), feature], axis=1)
    query_feature = np.log(20000. / 20000.)
    for role, unit, transformation in [('max_depth_cog', 'm', 'log1p'),
                                      ('arrival_time_cog', 'min', 'identity')]:
        first, mask_first, _ = read(args.source / 'receipts/h01', role)
        last, mask_last, _ = read(args.source / 'receipts/h03', role)
        domain = mask_first & mask_last
        rows, columns = np.nonzero(domain)
        y = np.stack([first[domain], last[domain]])
        response = np.log1p(y) if transformation == 'log1p' else y
        fitted = np.linalg.solve(design, response)
        predicted = fitted[0] + fitted[1] * query_feature
        if transformation == 'log1p':
            predicted = np.expm1(predicted)
        actual, mask_actual, _ = read(args.source / 'part_a', role)
        diagnostic_mask = mask_actual[domain]
        truth = actual[domain][diagnostic_mask]
        ml = predicted[diagnostic_mask]
        # Explicit numerical interpolation comparator, not labelled ML.
        baseline = (first[domain] + (last[domain] - first[domain]) / 3)[diagnostic_mask]
        report['roles'][role] = {'unit': unit, 'output_transform': transformation,
            'fit_physical_scenario_count': 2, 'held_out_physical_scenario_count': 1,
            'fit_cells': int(domain.sum()), 'evaluation_both_valid_cells': int(diagnostic_mask.sum()),
            'held_out_valid_cells': int(mask_actual.sum()),
            'held_out_valid_cells_not_predicted': int((mask_actual & ~domain).sum()),
            'coverage_fraction_of_held_out_valid': float(diagnostic_mask.sum() / mask_actual.sum()),
            'negative_prediction_cells': int((predicted < 0).sum()),
            'ml_diagnostic': errors(ml, truth), 'linear_interpolation_baseline': errors(baseline, truth),
            'mask_condition': 'held-out valid AND both training scenarios valid',
            'extent_iou': None, 'flooded_area_prediction': None,
            'unavailable_reason': 'The fit domain cannot infer flood expansion into endpoint nodata cells; no flood footprint prediction is asserted.'}
        coefficients[role + '_intercept'] = fitted[0].astype(np.float32)
        coefficients[role + '_slope'] = fitted[1].astype(np.float32)
        coefficients[role + '_row'] = rows.astype(np.int32)
        coefficients[role + '_column'] = columns.astype(np.int32)
    artifact = args.output / 'diagnostic-model.npz'
    np.savez_compressed(artifact, **coefficients)
    loaded = np.load(artifact, allow_pickle=False)
    report['artifact_reload_verified'] = all(np.array_equal(loaded[key], value) for key, value in coefficients.items())
    loaded.close()
    report.update(elapsed_training_and_diagnostic_seconds=time.perf_counter() - clock,
        finished_at=datetime.now(ZoneInfo('Asia/Calcutta')).isoformat(),
        evidence_complete=True, diagnostic_passed=report['artifact_reload_verified'],
        source_script_checksum='sha256:' + hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        audit_checksum='sha256:' + hashlib.sha256(args.audit.read_bytes()).hexdigest(),
        artifact_checksum='sha256:' + hashlib.sha256(artifact.read_bytes()).hexdigest())
    (args.output / 'evaluation.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('roles', 'elapsed_training_and_diagnostic_seconds',
        'artifact_reload_verified', 'original_plan_surrogate_gate_passed', 'enable_new_condition_ml_in_demo')}, indent=2))


if __name__ == '__main__':
    main()

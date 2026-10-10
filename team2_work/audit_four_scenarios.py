"""Read-only audit of exactly four supplied scenarios; no database or simulation."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

import numpy as np
import rasterio


def sha(path):
    with path.open('rb') as handle:
        return 'sha256:' + hashlib.file_digest(handle, 'sha256').hexdigest()


def hydrograph(path):
    lines = path.read_text(encoding='utf-8-sig').splitlines()
    indices = [i for i, line in enumerate(lines) if line.startswith('Flow Hydrograph=')]
    if len(indices) != 1:
        raise ValueError('Expected exactly one supplied flow hydrograph')
    index = indices[0]
    count = int(lines[index].split('=', 1)[1])
    values = []
    for line in lines[index + 1:]:
        if len(values) >= count:
            break
        if '=' in line:
            raise ValueError('Incomplete hydrograph values')
        values.extend(float(value) for value in re.findall(r'-?\d+(?:\.\d+)?', line))
    if len(values) != count:
        raise ValueError('Hydrograph sample count differs')
    return np.asarray(values, dtype=np.float64)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Choose a fresh evidence file')
    roots = {'h01': args.source / 'receipts/h01', 'h02': args.source / 'part_a',
             'h03': args.source / 'receipts/h03', '2006': args.source / 'receipts/2006'}
    report = {'started_at': datetime.now(ZoneInfo('Asia/Calcutta')).isoformat(),
              'source': str(args.source.resolve()), 'scenario_count': 4,
              'extra_scenarios_generated': 0, 'database_used': False,
              'python': sys.version.split()[0], 'numpy': np.__version__,
              'rasterio': rasterio.__version__, 'scenarios': {}, 'passed': False}
    arrays, flow, plans, bindings = {}, {}, {}, {}
    for name, root in roots.items():
        manifest_path = root / 'prototype-manifest.json'
        context_path = root / 'prototype-context.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        context = json.loads(context_path.read_text(encoding='utf-8'))
        record = {'scenario_id': manifest['scenario_id'], 'run_id': manifest['run_id'],
            'root': str(root.resolve()), 'manifest_checksum': sha(manifest_path),
            'schema_version': manifest['schema_version'], 'context_checksum': sha(context_path),
            'peak_release_m3s': manifest['parameters']['peak_release_m3s'],
            'forcing_kind': context['forcing']['kind'], 'scenario_family': context['scenario_family'],
            'coverage': manifest['time_coverage'], 'assets': {}, 'input_checksums': {},
            'reported_summary': manifest['summary'], 'unknowns': context['limitations']}
        if sha(context_path) != manifest['assumptions_checksum']:
            raise ValueError('Context checksum differs: ' + name)
        for source in manifest['datasets']:
            path = root / source['source_reference']
            checksum = sha(path)
            if checksum != source['checksum']:
                raise ValueError('Input checksum differs: ' + name)
            key = Path(source['source_reference']).stem.split('.')[0]
            record['input_checksums'][key] = checksum
            if path.suffix.startswith('.u'):
                flow[name] = hydrograph(path)
                record['forcing_samples'] = int(flow[name].size)
                record['forcing_min_m3s'] = float(flow[name].min())
                record['forcing_max_m3s'] = float(flow[name].max())
                if flow[name].max() != record['peak_release_m3s']:
                    raise ValueError('Manifest peak differs from input: ' + name)
            elif path.suffix.startswith('.p'):
                plans[name] = dict(line.split('=', 1) for line in path.read_text().splitlines() if '=' in line)
        for role, relative in manifest['assets'].items():
            path = root / relative
            metadata = manifest['asset_metadata'][role]
            if sha(path) != metadata['checksum']:
                raise ValueError('Asset checksum differs: ' + name + '/' + role)
            if not role.endswith('_cog'):
                record['assets'][role] = {'checksum_verified': True, 'bytes': path.stat().st_size}
                continue
            with rasterio.open(path) as dataset:
                values = dataset.read(1, masked=True)
                valid = ~np.ma.getmaskarray(values) & np.isfinite(values.data)
                grid = (dataset.crs.to_string(), tuple(dataset.transform), dataset.width, dataset.height)
                bindings[(name, role)] = grid
                arrays[(name, role)] = (values.data, valid)
                pixel_area = abs(dataset.transform.a * dataset.transform.e - dataset.transform.b * dataset.transform.d)
                sample_positions = np.flatnonzero(valid)
                chosen = sample_positions[np.linspace(0, len(sample_positions) - 1, 3, dtype=int)]
                samples = []
                for position in chosen:
                    row, col = divmod(int(position), dataset.width)
                    x, y = dataset.xy(row, col)
                    samples.append({'row': row, 'column': col, 'x': x, 'y': y, 'value': float(values.data[row, col])})
                stats = {'checksum_verified': True, 'checksum': metadata['checksum'],
                    'crs': dataset.crs.to_string(), 'transform': list(dataset.transform),
                    'width': dataset.width, 'height': dataset.height, 'nodata': dataset.nodata,
                    'unit': dataset.units[0], 'valid_cells': int(valid.sum()),
                    'min': float(values.data[valid].min()), 'max': float(values.data[valid].max()),
                    'negative_valid_cells': int((values.data[valid] < 0).sum()),
                    'pixel_area_m2': pixel_area, 'samples': samples}
                if role == 'max_depth_cog':
                    stats['wet_area_km2_depth_gt_0_1'] = float((valid & (values.data > 0.1)).sum() * pixel_area / 1e6)
                record['assets'][role] = stats
        report['scenarios'][name] = record
    hypothetical = ['h01', 'h02', 'h03']
    ignored = {'Plan Title', 'Short Identifier', 'Flow File', 'Simulation Date', 'Current Plan', 'Plan File'}
    base_plan = plans['h01']
    report['plan_field_differences'] = {
        name: {key: {'h01': base_plan.get(key), name: plans[name].get(key)}
               for key in sorted(set(base_plan) | set(plans[name]))
               if base_plan.get(key) != plans[name].get(key)} for name in ('h02', 'h03', '2006')}
    report['non_identity_hypothetical_plan_differences'] = {
        name: {key: value for key, value in report['plan_field_differences'][name].items() if key not in ignored}
        for name in ('h02', 'h03')}
    shapes = {name: (flow[name] - flow[name][0]) / (flow[name].max() - flow[name][0]) for name in hypothetical}
    report['hypothetical_hydrograph_shape'] = {
        'base_flow_m3s': {name: float(flow[name][0]) for name in hypothetical},
        'same_sample_count': len({len(flow[name]) for name in hypothetical}) == 1,
        'shape_max_absolute_differences': {name: float(np.max(np.abs(shapes[name] - shapes['h01']))) for name in ('h02', 'h03')},
        'definition': 'q(t)=500+(peak-500)*shape(t); input values have integer rounding'}
    report['all_registered_raster_grids_equal'] = len(set(bindings.values())) == 1
    report['hypothetical_terrain_identical'] = len({report['scenarios'][name]['input_checksums']['terrain'] for name in hypothetical}) == 1
    report['hypothetical_geometry_identical'] = len({report['scenarios'][name]['input_checksums']['geometry'] for name in hypothetical}) == 1
    report['held_out_design'] = {'fit_scenarios': ['h01', 'h03'], 'holdout_scenario': 'h02',
        'historical_2006': 'separate reconstructed hydrograph and coverage; not an extra peak-only training sample',
        'independent_physical_runs': 3, 'holdout_count': 1,
        'limitation': 'One middle-scenario diagnostic; no two disjoint intermediate holdouts are available. Original surrogate acceptance gate cannot pass.'}
    for role in ('max_depth_cog', 'arrival_time_cog', 'max_velocity_cog'):
        common = np.logical_and.reduce([arrays[(name, role)][1] for name in hypothetical])
        union = np.logical_or.reduce([arrays[(name, role)][1] for name in hypothetical])
        train_common = arrays[('h01', role)][1] & arrays[('h03', role)][1]
        report.setdefault('hypothetical_masks', {})[role] = {'all_three_valid_cells': int(common.sum()),
            'any_valid_cells': int(union.sum()), 'train_both_valid_cells': int(train_common.sum()),
            'h02_valid_outside_train_common': int((arrays[('h02', role)][1] & ~train_common).sum()),
            'rule': 'Invalid raster cells remain unknown; absence of valid data is not an observed zero.'}
    report.update(passed=True, finished_at=datetime.now(ZoneInfo('Asia/Calcutta')).isoformat(),
                  source_script_checksum=sha(Path(__file__)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key != 'scenarios'}, indent=2))


if __name__ == '__main__':
    main()

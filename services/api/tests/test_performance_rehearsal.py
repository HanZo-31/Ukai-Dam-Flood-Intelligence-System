"""Fail-closed target evaluation; no live load or DB in unit tests."""
import copy
import json
from pathlib import Path

import pytest
from scripts.b2_performance_probe import evaluate, json_routes, percentiles, read_profile

ROOT=Path(__file__).resolve().parents[3]
PROFILE=ROOT/'docs/contracts/b2-performance-targets.local.json'


def valid_evidence():
    profile=read_profile(PROFILE)
    phases=[]
    for name in ('json','full','head','range','mixed'):
        minimum={r[0]:profile['json_min_samples_per_route'] for r in json_routes('fixture')} if name in {'json','mixed'} else {}
        if name!='json': minimum['full' if name=='mixed' else name]=profile['artifact_min_samples']
        duration=profile['mixed_duration_seconds'] if name=='mixed' else profile['json_duration_seconds'] if name=='json' else profile['artifact_duration_seconds']
        phases.append({'name':name,'minimum_samples':minimum,'minimum_duration_seconds':duration,'elapsed_seconds':duration+1,
            'json_clients':profile['json_concurrency'] if name in {'json','mixed'} else 0,
            'artifact_clients':0 if name=='json' else profile['artifact_concurrency'],
            'workloads':{label:{'samples':count,'p95_ms':100,'unexpected_errors':0,
                'status_counts':{str(206 if label=='range' else 200):count}} for label,count in minimum.items()},
            'resources':{'complete':True,'sampled_max_memory_bytes':100000000,
                'cgroup_peak_since_container_start_bytes':100000000,'sampled_min_scratch_free_bytes':100000000,
                'oom_delta':0,'oom_kill_delta':0}})
    recovery={'scratch_recovered':True,'health_ready':True,'sampler_stopped':True,'oom_delta':0,'oom_kill_delta':0}
    return profile,phases,2*1024**3,recovery


def test_nearest_rank_small_sample_percentiles_are_explicit():
    result=percentiles([float(v) for v in range(1,101)])
    assert result=={'samples':100,'p50_ms':50.0,'p95_ms':95.0,'p99_ms':99.0,'max_ms':100.0}


@pytest.mark.parametrize('values',[[],[float('nan')],[-1],[float('inf')]])
def test_invalid_percentile_samples_rejected(values):
    with pytest.raises(ValueError): percentiles(values)


def test_provisional_local_acceptance_is_not_team_a_acceptance():
    result=evaluate(*valid_evidence())
    assert result['local_targets_met'] and result['local_provisional_acceptance']
    assert not result['team_a_final_performance_accepted']


def test_proposed_targets_cannot_be_called_accepted():
    evidence=valid_evidence(); evidence[0]['approval']['status']='proposed'
    result=evaluate(*evidence)
    assert result['local_targets_met'] and not result['local_provisional_acceptance']


@pytest.mark.parametrize('mutation',['missing_phase','duplicate_phase','duration','samples','p95','errors',
    'missing_route','changed_minimum','concurrency','resource_gaps','memory','kernel_peak','scratch','oom',
    'overall_oom','not_ready','not_recovered','sampler_running','status'])
def test_incomplete_or_failed_measurements_cannot_pass(mutation):
    profile,phases,memory,recovery=valid_evidence()
    phase=phases[0]; row=phase['workloads']['health']; resources=phase['resources']
    if mutation=='missing_phase': phases.pop()
    elif mutation=='duplicate_phase': phases[-1]=copy.deepcopy(phases[0])
    elif mutation=='duration': phase['elapsed_seconds']=1
    elif mutation=='samples': row['samples']=1
    elif mutation=='p95': row['p95_ms']=501
    elif mutation=='errors': row['unexpected_errors']=1
    elif mutation=='missing_route': phase['workloads'].pop('catalogue')
    elif mutation=='changed_minimum': phase['minimum_samples']['health']=1
    elif mutation=='concurrency': phase['json_clients']=1
    elif mutation=='resource_gaps': resources['complete']=False
    elif mutation=='memory': resources['sampled_max_memory_bytes']=memory
    elif mutation=='kernel_peak': resources['cgroup_peak_since_container_start_bytes']=memory
    elif mutation=='scratch': resources['sampled_min_scratch_free_bytes']=0
    elif mutation=='oom': resources['oom_kill_delta']=1
    elif mutation=='overall_oom': recovery['oom_delta']=1
    elif mutation=='not_ready': recovery['health_ready']=False
    elif mutation=='not_recovered': recovery['scratch_recovered']=False
    elif mutation=='sampler_running': recovery['sampler_stopped']=False
    elif mutation=='status': row['status_counts']={'503':row['samples']}
    result=evaluate(profile,phases,memory,recovery)
    assert not result['local_targets_met'] and result['failures']


@pytest.mark.parametrize('field,value',[('artifact_concurrency',3),('json_concurrency',0),
    ('json_duration_seconds',0),('http_timeout_seconds',1000),('json_concurrency',True),
    ('catalogue_extra_scenarios',501),('max_phase_seconds',60)])
def test_unsafe_profile_bounds_rejected(tmp_path,field,value):
    profile=json.loads(PROFILE.read_text()); profile[field]=value
    path=tmp_path/'targets.json'; path.write_text(json.dumps(profile))
    with pytest.raises(ValueError): read_profile(path)


def test_profile_cannot_invent_final_team_a_approval(tmp_path):
    profile=json.loads(PROFILE.read_text()); profile['approval']['team_a_final_sla_approved']=True
    path=tmp_path/'targets.json'; path.write_text(json.dumps(profile))
    with pytest.raises(ValueError): read_profile(path)

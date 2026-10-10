"""Verified original native solver adapter, isolated child and derivative packaging."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
import rasterio
from rasterio.transform import from_origin

from .compute import Produced, PREFIX, digest, strict_json, safe_file
from .packaging import write_derivative, extent_from_depth
from .process_ownership import own_child

ROOT=Path(__file__).resolve().parents[1]

class NativeProvider:
    synthetic=False

    def __init__(self,source,root=ROOT,timeout_seconds=1800,scratch_bytes=256*1024**2):
        self.source=Path(source).resolve();self.root=Path(root).resolve()
        self.timeout_seconds=timeout_seconds;self.scratch_bytes=scratch_bytes
        self.config=strict_json(self.root/'rapid_engine/native_configuration.json')
        self.identity='sha256:'+hashlib.sha256(json.dumps(self.config,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        self.runtime_checked={}

    def verify(self):
        for relative,expected in self.config['bound_files'].items():
            kind,name=relative.split(':',1)
            root=self.source if kind=='base' else self.root
            if digest(safe_file(root,name))!=expected:raise ValueError('Bound native/input/runtime file changed')
        readiness=strict_json(self.root/'rapid_engine/native_readiness.json')
        if not readiness['accepted_numerical_runtime'] or readiness['configuration_checksum']!=self.identity:
            raise ValueError('Native readiness evidence mismatch')
        installed=strict_json(self.root/'solver_env/installed_checksums.json')
        for relative,expected in installed.items():
            path=safe_file(self.root,relative);stat=path.stat();stamp=(stat.st_size,stat.st_mtime_ns)
            if self.runtime_checked.get(relative)!=stamp:
                if digest(path)!=expected:raise ValueError('Installed dependency changed')
                self.runtime_checked[relative]=stamp
        return {'configuration_id':self.config['configuration_id'],'configuration_checksum':self.identity,
                'available_roles':['max_depth_cog','arrival_time_cog','max_velocity_cog','extent_geojson']}

    def compute(self,request,folder,cancel):
        self.verify();started=time.perf_counter()
        env=os.environ.copy();env['OMP_NUM_THREADS']='2';env['PYTHONDONTWRITEBYTECODE']='1'
        # Explicit source/state arguments, no request-supplied executable or filesystem path.
        command=[sys.executable,'-B',str(self.root/'rapid_engine/solver_worker.py'),'--source',str(self.source),
            '--output',str(folder/'native'),'--peak',str(request['peak_release_m3s'])]
        with (folder/'worker.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=env)
            ownership=None
            try:
                ownership=own_child(process)
                while process.poll() is None:
                    if cancel.wait(.1):raise InterruptedError()
                    if time.perf_counter()-started>self.timeout_seconds:raise TimeoutError('Native timeout')
                    if sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())>self.scratch_bytes:
                        raise ValueError('Native scratch budget exceeded')
                if process.returncode:raise ValueError('Native worker failed')
            finally:
                if process.poll() is None:process.terminate()
                process.wait(timeout=10)
                if ownership is not None:ownership.close()
        self.verify()
        report=strict_json(folder/'native/report.json')
        if (not report['passed'] or not report['genuine_full_scenario'] or report['probe_only']
                or report['peak_release_m3s']!=request['peak_release_m3s'] or report['scientifically_validated']):
            raise ValueError('Native result identity/gate failed')
        return self.package(request,folder,report,started)

    def package(self,request,folder,report,started):
        package_started=time.perf_counter();folder=Path(folder)
        native=safe_file(folder,'native/native-results.npz');diagnostic=safe_file(folder,'native/numerical-diagnostics.json')
        if digest(native)!='sha256:'+report['native_result_sha256']:raise ValueError('Native result changed')
        reference=self.source/'part_a/assets/max_depth.tif';manifest=strict_json(self.source/'part_a/prototype-manifest.json')
        files={};assets={};reasons={role:None for role in ['max_depth_cog','arrival_time_cog','max_velocity_cog','extent_geojson']}
        with np.load(native,allow_pickle=False) as bundle:
            mask=bundle['mask'].astype(bool);xs=bundle['xs'];ys=bundle['ys']
            if mask.shape!=(len(ys),len(xs)) or not np.allclose(np.diff(xs),100) or not np.allclose(np.diff(ys),100):
                raise ValueError('Native geometry mismatch')
            affine=from_origin(float(xs[0])-50,float(ys[-1])+50,100,100)
            for role,key,name,unit in [('max_depth_cog','hmax','max_depth.tif','m'),('arrival_time_cog','arr','arrival_time.tif','min'),
                ('max_velocity_cog','vmax','max_velocity.tif','m/s')]:
                array=bundle[key];valid=mask&(array>=0) if key=='arr' else mask
                if not valid.any():
                    if key!='arr':raise ValueError('Required native product missing')
                    assets[role]=None;reasons[role]='No native cell reached the 0.1 m arrival threshold.';continue
                write_derivative(np.flipud(array),np.flipud(valid),affine,'EPSG:32643',reference,folder/name,arrival_seconds=key=='arr')
                files[role]=name
                assets[role]={'url':PREFIX+'/jobs/'+request['request_id']+'/assets/'+role,'sha256':digest(folder/name),
                    'bytes':(folder/name).stat().st_size,'unit':unit}
        extent_from_depth(folder/'max_depth.tif',folder/'extent.geojson');files['extent_geojson']='extent.geojson'
        assets['extent_geojson']={'url':PREFIX+'/jobs/'+request['request_id']+'/assets/extent_geojson',
            'sha256':digest(folder/'extent.geojson'),'bytes':(folder/'extent.geojson').stat().st_size,'unit':'geographic_coordinates'}
        with rasterio.open(reference) as ds:
            grid={'crs':'EPSG:32643','width':ds.width,'height':ds.height,'transform':list(ds.transform)[:6],'nodata':-9999,
                'mapping':'nearest_neighbour_with_validity_mask','target_reference_scenario_id':manifest['scenario_id']}
        execution_hash=hashlib.sha256((request['request_id']+self.identity+report['native_result_sha256']).encode()).hexdigest()[:16]
        peak=format(request['peak_release_m3s'],'.12g').replace('.','p')
        elapsed=time.perf_counter()-started;pack=time.perf_counter()-package_started
        result={k:request[k] for k in ['schema_version','input_family','configuration_id','configuration_checksum','request_id']}
        result.update(job_id=request['request_id'],scenario_id='ukai-fast-q'+peak+'-'+execution_hash,
            run_id='ukai-fast-run-'+execution_hash,requested_peak_release_m3s=request['peak_release_m3s'],
            actual_peak_release_m3s=request['peak_release_m3s'],engine='experimental_fast_solver',
            engine_version='li2d-original-dll-'+self.config['original_dll_hash'][-12:],computed=True,cache_hit=False,
            scientifically_validated=False,calibration_status='uncalibrated',
            input_checksums={name:value for name,value in self.config['bound_files'].items() if name.startswith('base:')},
            warnings=['experimental_simulation','uncalibrated','not_observed_flood_truth','native_100m_grid_resampled_not_29m_hydraulics',
                'manning_n_fitted_to_unvalidated_hecras_h02','assumed_hydrograph_not_reservoir_routing'],
            limitations=['No channel bathymetry; vertical datum unresolved.','No exposure data or evacuation/optimal release recommendation.',
                'Agreement with stored HEC-RAS is not observational validation.','Velocity is maximum face-normal component, not HEC-RAS speed magnitude.',
                'Comparing this new release with a different HEC-RAS release changes both forcing and engine; differences do not isolate release effect.',
                'Input licensing and producing-run historical timezone remain unverified.'],
            timings={'prepare_seconds':report['prepare_seconds'],'solver_seconds':report['solver_seconds'],
                'package_check_seconds':pack,'availability_seconds':max(0,elapsed-report['prepare_seconds']-report['solver_seconds']-pack),
                'request_to_assets_seconds':elapsed,'scope':'request_to_checked_asset_availability_not_browser_ready'},
            numerical_diagnostics_checksum=digest(diagnostic),native_results_checksum=digest(native),
            arrival_definition={'threshold_m':0.1,'origin':'elapsed_simulation_start','native_unit':'s',
                'comparison_transform':'ceil(native_seconds/3600)*60','definition_compatible':True,'unavailable_reason':reasons['arrival_time_cog']},
            velocity_definition='Maximum absolute face-normal flux divided by face depth over the run; not velocity-vector magnitude.',
            derived_grid=grid,assets=assets,unavailable_reasons=reasons)
        return Produced(result,files,'native/native-results.npz','native/numerical-diagnostics.json')

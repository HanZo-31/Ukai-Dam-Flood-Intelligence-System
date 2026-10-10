"""Isolated original-driver worker; numerical source/DLL are never rewritten."""
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
ENV=ROOT/'solver_env'
sys.path.insert(0,str(ENV/'site-packages'))
import numpy as np
import rasterio
import tifffile
import scipy
import cv2

HANDLES=[]

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def driver():
    HANDLES.append(os.add_dll_directory(str(ENV/'native')))
    path=ROOT/'native_received_v01/fast_solver/driver.py'
    spec=importlib.util.spec_from_file_location('received_driver',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.B=str(ROOT/'solver_inputs_v01')+os.sep
    return module

def prepare(source):
    import shutil
    root=ROOT/'solver_inputs_v01'
    mapping={'base_model/Ukai_Lower_Tapi_A2.g01':source/'part_a/inputs/geometry.g01',
        'terrain/Ukai_Lower_Tapi_A2_Terrain.ukai_to_surat_dem_utm43_working.tif':source/'part_a/inputs/terrain.tif',
        'base_model/Ukai_Lower_Tapi_A2.u04':source/'receipts/h01/inputs/forcing.u04',
        'base_model/Ukai_Lower_Tapi_A2.u05':source/'part_a/inputs/forcing.u05',
        'base_model/Ukai_Lower_Tapi_A2.u06':source/'receipts/h03/inputs/forcing.u06'}
    inventory={}
    for relative,original in mapping.items():
        target=root/relative;target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and sha(target)!=sha(original):raise ValueError('Inputs changed since preparation')
        if not target.exists():shutil.copyfile(original,target)
        inventory[relative]={'sha256':'sha256:'+sha(target),'original_path':original.relative_to(source).as_posix()}
    return inventory

def build_checked(module):
    grid=module.build()
    terrain=ROOT/'solver_inputs_v01/terrain/Ukai_Lower_Tapi_A2_Terrain.ukai_to_surat_dem_utm43_working.tif'
    original=tifffile.imread(terrain)
    with rasterio.open(terrain) as ds:
        if not np.array_equal(original,ds.read(1)):raise ValueError('Reader parity failed')
        if str(ds.crs)!='EPSG:32643' or abs(ds.transform.c-260653.128487587)>1e-6 or abs(ds.transform.f-2369001.58195343)>1e-6:
            raise ValueError('Driver terrain tiepoint mismatch')
    if not np.isfinite(grid['z'][grid['m']]).all() or not grid['m'].any():raise ValueError('Invalid built terrain')
    shape=(module.hydrograph('u05')-500)/(20000-500)
    if len(shape)!=115 or not np.isfinite(shape).all() or (shape<0).any() or shape.max()!=1:raise ValueError('Forcing definition mismatch')
    for name,peak in [('u04',15000),('u06',30000)]:
        other=(module.hydrograph(name)-500)/(peak-500)
        if other.shape!=shape.shape or np.max(np.abs(other-shape))>1e-4:raise ValueError('Hydrograph family mismatch')
    return grid,shape

def check_outputs(result,grid,seconds):
    mask=grid['m'];depth=result['hmax'];velocity=result['vmax'];arrival=result['arr'];stats=result['stats']
    if result['n_in']<=0 or result['n_out']<=0:raise ValueError('Missing hydraulic boundary cells')
    if any(field.shape!=mask.shape for field in [depth,velocity,arrival]):raise ValueError('Native shape mismatch')
    if not np.isfinite(depth[mask]).all() or not np.isfinite(velocity[mask]).all() or (depth[mask]<0).any() or (velocity[mask]<0).any():
        raise ValueError('Nonfinite/negative physical output')
    arrived=mask&(arrival>=0)
    if not np.isfinite(arrival[mask]).all() or (arrival[arrived]>seconds+1e-6).any() or (arrival[mask]<-1).any():raise ValueError('Invalid arrival')
    if stats.shape!=(5,) or not np.isfinite(stats).all() or abs(stats[0]-seconds)>1e-6 or stats[4]<=0:raise ValueError('Incomplete native run')
    residual=float(stats[1]-stats[2]-stats[3]);relative=abs(residual)/max(abs(float(stats[1])),1)
    # Strict arithmetic conservation gate for this implementation, not scientific calibration.
    if relative>1e-6:raise ValueError('Numerical volume-accounting gate failed')
    return dict(steps=int(stats[4]),simulated_seconds=float(stats[0]),mass_in_m3=float(stats[1]),mass_out_m3=float(stats[2]),
        mass_stored_m3=float(stats[3]),mass_residual_m3=residual,mass_relative_residual=relative,
        numeric_conservation_gate=1e-6,numerical_only_not_scientific_validation=True,
        inflow_cells=result['n_in'],outflow_cells=result['n_out'],valid_native_cells=int(mask.sum()),
        wet_native_cells=int((mask&(depth>0.1)).sum()),max_depth_m=float(depth[mask].max()),
        max_face_normal_velocity_m_s=float(velocity[mask].max()),valid_arrival_cells=int(arrived.sum()))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--peak',type=float,default=25000);parser.add_argument('--probe',action='store_true')
    args=parser.parse_args()
    if not 15000<=args.peak<=30000 or not np.isfinite(args.peak):raise ValueError('Bounded finite release required')
    args.output.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter();inputs=prepare(args.source.resolve());module=driver();grid,shape=build_checked(module)
    prepared=time.perf_counter()-start
    hyd=500+(args.peak-500)*shape;duration=60 if args.probe else (len(hyd)-1)*3600
    # All parameters match the received evaluated n0.025 family. No tuning on new results.
    result=module.run(grid,hyd,duration/3600,n=0.025,alpha=0.7,dtmax=30,theta=0.9,fr=1,s_out=0.0005,hth=0.1)
    diagnostics=check_outputs(result,grid,duration)
    native=args.output/'native-results.npz'
    np.savez_compressed(native,hmax=result['hmax'],vmax=result['vmax'],arr=result['arr'],stats=result['stats'],
        mask=grid['m'],z=grid['z'],xs=grid['xs'],ys=grid['ys'],hydrograph=hyd)
    report={'checked_at':datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(),'passed':True,'probe_only':args.probe,
        'genuine_full_scenario':not args.probe,'peak_release_m3s':args.peak,'hydrograph_samples':len(hyd),
        'hydrograph_dt_seconds':3600,'model_duration_seconds':duration,'prepare_seconds':prepared,'solver_seconds':result['sec'],
        'worker_total_seconds':time.perf_counter()-start,'original_driver_unmodified':True,
        'driver_sha256':sha(ROOT/'native_received_v01/fast_solver/driver.py'),
        'original_dll_sha256':sha(ROOT/'native_received_v01/fast_solver/li2d.dll'),
        'native_result_sha256':sha(native),'input_inventory':inputs,'native_grid':{'width':grid['nx'],'height':grid['ny'],'dx_m':100},
        'versions':{'numpy':np.__version__,'scipy':scipy.__version__,'tifffile':tifffile.__version__,'opencv':cv2.__version__},
        'diagnostics':diagnostics,'scientifically_validated':False,'calibration_status':'uncalibrated'}
    (args.output/'numerical-diagnostics.json').write_text(json.dumps(diagnostics,indent=2),encoding='utf-8')
    (args.output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()

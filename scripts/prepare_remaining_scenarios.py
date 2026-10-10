"""Build the remaining real drafts from preserved Team A files; run no simulations."""
import copy
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

import numpy as np
import rasterio
from rasterio.features import shapes
from rasterio.shutil import copy as cog_copy
from rasterio.windows import Window
from pyproj import Transformer
from shapely.geometry import shape, mapping
from shapely.ops import unary_union, transform

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.api.app.published_contract import PublishedScenarioManifest
from services.api.app.prototype_context import PrototypeContext, validate_bound_context
from services.api.app.receiving import preflight, write_evidence

A = Path(r'C:\Ukai\Ukai')
MODEL = A/'ukai-flood-intelligence/hydraulic/hecras/base_model'
TERRAIN = next((A/'ukai-flood-intelligence/hydraulic/hecras/terrain').glob('*working.tif'))
CASES = [('h01','ukai-hyp-h01-release15000-v1','p03','u04'),
         ('h03','ukai-hyp-h03-release30000-v1','p05','u06'),
         ('2006','ukai-2006-historical-v2','p06','u07')]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def put(root, reference, value):
    p = root/reference
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def date(text):
    from datetime import datetime
    return datetime.strptime(text,'%d%b%Y,%H%M').strftime('%Y-%m-%dT%H:%M:%SZ')


def inventory(root):
    files = sorted(p for p in root.rglob('*') if p.is_file() and p.name not in {'FILE_INVENTORY.csv','CHECKSUMS.sha256'})
    with (root/'FILE_INVENTORY.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream)
        writer.writerow(['path','size_bytes','sha256'])
        for p in files:
            writer.writerow([p.relative_to(root).as_posix(),p.stat().st_size,sha(p)])
    files.append(root/'FILE_INVENTORY.csv')
    (root/'CHECKSUMS.sha256').write_text(''.join(f'{sha(p)}  {p.relative_to(root).as_posix()}\n' for p in sorted(files)),encoding='utf-8')


def prepare(code, original_id, plan_ext, flow_ext):
    out = ROOT/'receipts'/code
    if out.exists():
        raise ValueError('A fresh receipt folder is required: '+code)
    source=A/'part_a_handoff/v0.1/scenarios'/original_id
    shutil.copytree(source,out/'original')
    old=json.loads((source/'scenario_manifest.json').read_text())
    plan=MODEL/('Ukai_Lower_Tapi_A2.'+plan_ext)
    flow=MODEL/('Ukai_Lower_Tapi_A2.'+flow_ext)
    text=plan.read_text()
    assert re.search(r'^Flow File='+flow_ext+r'\s*$',text,re.M)
    assert re.search(r'^Geom File=g01\s*$',text,re.M)
    match=re.search(r'^Simulation Date=(\d+\w+\d+,\d+),(\d+\w+\d+,\d+)\s*$',text,re.M)
    assert match
    coverage={'start':date(match[1]),'end':date(match[2])}
    output_interval=re.search(r'^Output Interval=(\d+)MIN\s*$',text,re.M)
    computation=re.search(r'^Computation Interval=(\d+)SEC\s*$',text,re.M)
    assert output_interval and computation and 'Mapping Interval=1HOUR' in text
    for p in (out/'assets',out/'inputs',out/'evidence',out/'reports'):
        p.mkdir(parents=True,exist_ok=True)
    identifier=original_id.rsplit('-v',1)[0]+'-combined-v1'
    run_id=identifier+'-run'
    baseline={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
    inputs={'plan':plan,'forcing':flow,'geometry':MODEL/'Ukai_Lower_Tapi_A2.g01','terrain':TERRAIN}
    dataset_list=[]
    for role,p in inputs.items():
        ref='inputs/'+role+p.suffix
        shutil.copyfile(p,out/ref)
        digest=sha(p)
        dataset_list.append({'dataset_id':'ukai-'+code+'-'+role,'version':'sha256-'+digest[:16],
            'source_reference':ref,'source_label':'assumed','license':'UNKNOWN: no licence evidence supplied; no permission or redistribution licence asserted.',
            'checksum':'sha256:'+digest,'crs':'EPSG:32643' if role in {'terrain','geometry'} else None,
            'time_coverage':coverage if role=='forcing' else None,
            'quality_notes':'Existing Part A input, preserved by checksum. Content-addressed snapshot assigned locally. Forcing is assumed or reconstructed; no verified observation or licence is asserted.'})
    snapshot=hashlib.sha256(json.dumps({d['dataset_id']:d['checksum'] for d in dataset_list},sort_keys=True).encode()).hexdigest()[:16]
    manifest=copy.deepcopy(json.loads((ROOT/'part_a/prototype-manifest.json').read_text()))
    manifest.update(scenario_id=identifier,run_id=run_id,scenario_type=old['scenario_type'] if code=='2006' else 'hypothetical',
        model_version='ukai-'+code+'-model-snapshot-'+snapshot,input_dataset_version='ukai-'+code+'-input-snapshot-'+snapshot,
        time_coverage=coverage,time_step_minutes=int(output_interval[1]),datasets=dataset_list,
        historical_event_id=None,run_timestamp=None,
        run_timestamp_unknown_reason='Producing HEC-RAS timezone is not attested in supplied files. No UTC producing-run instant is asserted.',
        parameters={k:float(v) if v is not None else None for k,v in old['parameters'].items()})
    context=copy.deepcopy(json.loads((ROOT/'part_a/prototype-context.json').read_text()))
    for key in ('scenario_id','run_id','model_version','input_dataset_version','time_coverage'):
        context[key]=manifest[key]
    context['scenario_family']=original_id.rsplit('-v',1)[0]
    context['engine']['build']='Input plan Program Version 7.01; producing executable build was not byte-attested.'
    context['engine']['source_checksum_unavailable_reason']='Producing executable bytes were not attested; proprietary engine source is unavailable.'
    originals={p.relative_to(out).as_posix():'sha256:'+sha(p) for p in (out/'original/assets').iterdir() if p.is_file()}
    context['original'].update(scenario_id=original_id,scenario_type=old['scenario_type'],manifest_checksum='sha256:'+sha(out/'original/scenario_manifest.json'),asset_checksums=originals)
    forcing=next(d for d in dataset_list if d['dataset_id'].endswith('-forcing'))
    context['forcing'].update(kind='reconstructed_historical' if code=='2006' else 'hypothetical_assumption',
        description=('Existing reconstructed 2006 release hydrograph; primary release-volume source and timezone unverified; hourly interpolation is assumed.' if code=='2006' else f'Existing {flow_ext} hypothetical release hydrograph, peak {old["parameters"]["peak_release_m3s"]} m3/s; no observed dam telemetry.'),
        datasets=[{k:forcing[k] for k in ('dataset_id','version')}],provenance_references=['inputs/forcing.'+flow_ext,'evidence/timing.json'])
    context['arrival'].update(reference_timestamp=coverage['start'],original_checksum=originals['original/assets/arrival_time.tif'])
    context['timing'].update(result_output_interval_minutes=int(output_interval[1]),computation_step_seconds=float(computation[1]),
        coverage_clock_kind='model_clock',timezone_convention='Nominal UTC index assigned to model-clock dates for relative-time interoperability. Actual historical and producing-run timezones remain unverified.',
        evidence_references=['inputs/plan.'+plan_ext,'evidence/timing.json'])
    context['assumptions'][-1]='Nominal UTC model-clock dates are indices for relative timing; no verified historical UTC event time is asserted.'
    if code=='2006':
        context['limitations']['source_uncertainties'].append('Historical forcing reconstructed from unverified twelve-hourly release volumes; no observed event catalog or calibration asserted.')
    context['preserved_wse']['checksum']=originals['original/assets/max_wse.tif']
    context['derivation'].update(processor='Combined local raster packager',processor_version='2026.10.08-v1',
        source_scenario_id=original_id,derivative_scenario_id=identifier,derivative_run_id=run_id)
    context['derivation']['operations'][1]['parameters_and_method']='Coordinate-derived integer window, no resampling; original valid arrival cells retained. Exact offsets and values are rechecked by receiver.'
    depth_source=source/'assets/max_depth.tif'
    with rasterio.open(depth_source) as depth:
        grid=depth.profile.copy()
        depth_values=depth.read(1)
        wet=(depth_values!=depth.nodata)&(depth_values>0.1)
        area=float(wet.sum()*abs(depth.transform.a*depth.transform.e)/1e6)
        maximum=float(depth_values[depth_values!=depth.nodata].max())
        context['derivation']['operations'][3]['parameters_and_method']='Pixel-edge extent from unchanged depth raster, depth greater than 0.1 m, 4-connected components, all holes preserved, full-precision WGS84 transform.'
        metadata={}
        for role,name,unit in [('max_depth_cog','max_depth','m'),('max_velocity_cog','max_velocity','m/s'),('arrival_time_cog','arrival_time','min')]:
            with rasterio.open(source/('assets/'+name+'.tif')) as src:
                if name=='arrival_time':
                    col=(depth.transform.c-src.transform.c)/src.transform.a
                    row=(depth.transform.f-src.transform.f)/src.transform.e
                    assert abs(col-round(col))<1e-6 and abs(row-round(row))<1e-6
                    values=src.read(1,window=Window(round(col),round(row),depth.width,depth.height))
                    assert int((values!=src.nodata).sum())==int((src.read(1)!=src.nodata).sum())
                    values[values!=src.nodata]*=60
                else:
                    assert src.transform==depth.transform and src.shape==depth.shape
                    values=src.read(1)
                tmp=ROOT/'scratch'/f'{code}-{name}-temporary.tif'
                profile={k:v for k,v in grid.items() if k not in {'blockxsize','blockysize','tiled','compress','interleave'}}
                profile.update(driver='GTiff',dtype=values.dtype,nodata=src.nodata,count=1)
                with rasterio.open(tmp,'w',**profile) as target:
                    target.write(values,1)
                    target.set_band_unit(1,unit)
                    target.update_tags(coverage_start=coverage['start'],coverage_end=coverage['end'],coverage_clock_kind='model_clock',timezone_convention='nominal_utc_model_index_not_verified_event_time')
                result=out/('assets/'+name+'.tif')
                cog_copy(tmp,result,driver='COG',compress='DEFLATE',blocksize=256,overview_resampling='nearest')
                tmp.unlink()
                with rasterio.open(result) as final:
                    assert np.array_equal(final.read(1),values)
                metadata[role]={'checksum':'sha256:'+sha(result),'format':'cog','crs':'EPSG:32643','unit':unit,'time_coverage':coverage,'nodata':float(src.nodata)}
        native=unary_union([shape(g) for g,v in shapes(wet.astype('uint8'),mask=wet,transform=depth.transform) if v])
        geom=transform(Transformer.from_crs(depth.crs,4326,always_xy=True).transform,native)
    put(out,'assets/extent.geojson',{'type':'FeatureCollection','features':[{'type':'Feature','properties':{'scenario_id':identifier,'run_id':run_id,'threshold_m':0.1},'geometry':mapping(geom)}]})
    metadata['extent_geojson']={'checksum':'sha256:'+sha(out/'assets/extent.geojson'),'format':'geojson','crs':'EPSG:4326','unit':'1','time_coverage':coverage,'nodata':None}
    manifest['asset_metadata']=metadata
    manifest['summary'].update(max_depth_m=maximum,flooded_area_km2=area)
    put(out,'evidence/timing.json',{'plan':plan_ext,'flow':flow_ext,'source_simulation_date':match[0].strip(),'coverage':coverage,'clock_kind':'nominal_model_clock','historical_timezone_verified':False})
    put(out,'evidence/input_release.json',{'source_hashes':{d['source_reference']:d['checksum'] for d in dataset_list},'source_status':'existing assumed/reconstructed model inputs'})
    put(out,'reports/quality.json',{'stage':'combined local draft preparation','scientific_validation_status':'not_validated','import_status':'pending_receiver_verification',
        'source_unchanged':all(sha(source/key)==digest for key,digest in baseline.items()),'base_raster_values_and_masks_preserved':True,
        'arrival_conversion':'valid cells times 60; nodata retained','extent':'full-precision pixel edges, depth greater than 0.1 m',
        'unknowns':['producing-run timezone','input licences','vertical datum','observation-based calibration','exposure'],
        'no_simulations_run':True})
    put(out,'reports/pixel-edge-extent-evidence.json',{'schema_version':'1.0.0','method':'raster_pixel_edges','threshold_m':0.1,'comparison':'greater_than',
        'scenario_id':identifier,'run_id':run_id,'depth_checksum':metadata['max_depth_cog']['checksum'],'extent_checksum':metadata['extent_geojson']['checksum']})
    put(out,'prototype-context.json',context)
    manifest['assumptions_checksum']='sha256:'+sha(out/'prototype-context.json')
    manifest['quality']['report_checksum']='sha256:'+sha(out/'reports/quality.json')
    put(out,'prototype-manifest.json',manifest)
    put(out,'input-catalog.json',{'datasets':[{'dataset_id':d['dataset_id'],'name':d['dataset_id'],'description':d['quality_notes'],'data_mode':'production'} for d in dataset_list],'events':[]})
    parsed=PublishedScenarioManifest.model_validate(manifest)
    validate_bound_context(PrototypeContext.model_validate(context),parsed)
    inventory(out)
    report=preflight(out,'prototype-manifest.json')
    write_evidence(report,ROOT/'evidence'/('preflight-'+code))
    print(code+': '+('all preflight checks passed' if report['passed'] else 'preflight failed'),flush=True)
    assert report['passed']


if __name__=='__main__':
    for case in CASES:
        prepare(*case)

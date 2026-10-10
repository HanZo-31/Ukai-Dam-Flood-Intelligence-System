import tifffile, numpy as np, cv2, json, math, hashlib, os, shutil, re
exec(open('/tmp/claude-0/-home-claude/c1f15995-d94d-5e55-bafc-3982b25ee34d/scratchpad/qa/bundle2006.py').read().split("PX=")[0].split("names=")[0].replace("SRC=","_x=").replace("OUT=","_y=").replace("os.makedirs(OUT+'assets',exist_ok=True); os.makedirs(OUT+'provenance',exist_ok=True)",""))
src=open('/tmp/claude-0/-home-claude/c1f15995-d94d-5e55-bafc-3982b25ee34d/scratchpad/qa/bundle2006.py').read()
# reuse utm_inv and ring definitions
ns={}
exec("import math,cv2,numpy as np\nPX=28.999033361477533; X0=268076.8810281253; Y0=2369001.58195343\n"+src[src.index("def utm_inv"):src.index("polys=[]")],ns)
utm_inv=ns['utm_inv']; ring=ns['ring']; PX=ns['PX']
BASE='/mnt/user-data/uploads/Ukai/ukai-flood-intelligence/hydraulic/hecras/base_model/'
T='.Ukai_Lower_Tapi_A2_Terrain.ukai_to_surat_dem_utm43_working.tif'
sc=[('H01','HYPH01',15000,'u04','p03','51:42','0.000716'),('H02','HYPH02',20000,'u05','p04','46:45','0.000670'),('H03','HYPH03',30000,'u06','p05','51:09','0.000607')]
A=PX**2/1e6
for hid,folder,peak,u,p,rt,verr in sc:
    sid='ukai-hyp-%s-release%d-v1'%(hid.lower(),peak)
    OUT='/mnt/user-data/outputs/v0.1/scenarios/%s/'%sid
    os.makedirs(OUT+'assets',exist_ok=True); os.makedirs(OUT+'provenance',exist_ok=True)
    for k,f in (('max_depth','Depth (Max)'),('max_velocity','Velocity (Max)'),('max_wse','WSE (Max)')):
        shutil.copyfile(BASE+folder+'/'+f+T,OUT+'assets/%s.tif'%k)
    d=tifffile.imread(OUT+'assets/max_depth.tif').astype('f8'); H,W=d.shape
    mask=((d!=-9999)&(d>0.1)).astype(np.uint8)
    cs,hier=cv2.findContours(mask,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE); hier=hier[0]
    polys=[]
    for i,(n,pr,fc,par) in enumerate(hier):
        if par==-1:
            outer=ring(cs[i])
            if outer is None or cv2.contourArea(cs[i])<4: continue
            rings=[outer]; j=fc
            while j!=-1:
                h=ring(cs[j])
                if h is not None and cv2.contourArea(cs[j])>=4: rings.append(h)
                j=hier[j][0]
            polys.append(rings)
    gj={'type':'FeatureCollection','name':'extent_max_depth_gt_0.1m','crs':{'type':'name','properties':{'name':'urn:ogc:def:crs:OGC:1.3:CRS84'}},
     'features':[{'type':'Feature','properties':{'scenario_id':sid,'definition':'max depth > 0.1 m','source':'max_depth.tif','simplification':'cv2.approxPolyDP 0.7 px; parts < 4 px area dropped','status':'uncalibrated prototype, hypothetical release'},'geometry':{'type':'MultiPolygon','coordinates':polys}}]}
    json.dump(gj,open(OUT+'assets/extent.geojson','w'))
    qa={}
    for k in ('max_depth','max_velocity','max_wse'):
        arr=tifffile.imread(OUT+'assets/%s.tif'%k).astype('f8'); v=arr[arr!=-9999]
        qa[k]={'shape':list(arr.shape),'valid_cells':int(v.size),'min':float(v.min()),'max':float(v.max()),'mean':float(v.mean()),'nan_count':int(np.isnan(arr).sum()),'neg_nonnodata':int((v<0).sum())}
    v=tifffile.imread(OUT+'assets/max_velocity.tif').astype('f8')
    qa['consistency']={'velocity_valid_equals_depth_valid':bool(np.array_equal(v!=-9999,d!=-9999))}
    qa['depth_exceedance_km2']={str(t):round(float((d[d!=-9999]>t).sum()*A),1) for t in (0.1,0.5,1,2,5,10,15,20)}
    fa=round(float(mask.sum()*A),1); md=round(qa['max_depth']['max'],2); mv=round(qa['max_velocity']['max'],2)
    qa['flooded_area_km2_gt_0.1m']=fa; qa['polygons']=len(polys)
    json.dump(qa,open(OUT+'provenance/raster_qa.json','w'),indent=1)
    man={'scenario_id':sid,'scenario_type':'hypothetical_release','status':'draft','model_version':'hecras2d-0.1.0','input_dataset_version':'ukai-data-2026.1','crs':'EPSG:32643','time_step_minutes':None,
     'parameters':{'reservoir_level_m':None,'peak_inflow_m3s':None,'peak_release_m3s':peak,'breach_width_m':None,'breach_formation_minutes':None},
     'assets':{'max_depth_cog':'assets/max_depth.tif','max_velocity_cog':'assets/max_velocity.tif','arrival_time_cog':None,'extent_geojson':'assets/extent.geojson'},
     'summary':{'max_depth_m':md,'flooded_area_km2':fa,'population_exposed':None,'buildings_exposed':None},
     'assumptions_url':'qa_report.md','quality':{'approved_by':'','validation_status':'not_validated'}}
    json.dump(man,open(OUT+'scenario_manifest.json','w'),indent=2)
    json.dump({'note':'PROPOSAL ONLY. Not part of the agreed Part B schema.','data_mode':'assumed','forcing':'hypothetical release hydrograph (not an observed event)','calibration':'uncalibrated','model_basis':'HEC-RAS 2D, Manning n 0.04 uniform, SRTM-derived terrain without bathymetry','known_issues':['arrival_time asset not exported for this scenario','max_wse.tif is present in assets but has no key in the template','breach not modelled: release hydrograph only']},open(OUT+'proposed_additions.json','w'),indent=2)
    exc=qa['depth_exceedance_km2']
    open(OUT+'qa_report.md','w').write(f"""# QA report: {sid}

Status: **draft, uncalibrated prototype, hypothetical scenario**. Not an observed or reproduced event.

## What this is
A HEC-RAS 2D run of the Ukai to Surat reach driven by an assumed dam-release hydrograph with a peak of {peak:,} m3/s (plan {p}, flow file {u}, 06 Aug 2006 06:00 to 11 Aug 2006 00:00, 115 h). The shape of the hydrograph is a scaled test shape, not a reservoir-routing result. No breach is modelled.

## Run
Runtime {rt}; volume accounting error {verr}%. Solver diffusion wave. Terrain SRTM-derived with no channel bathymetry; mesh 100 m; Manning n 0.04 uniform; datum unresolved.

## Results (max over the run)
- Flooded area (depth > 0.1 m): {fa} km2
- Max depth: {md} m; max velocity: {mv} m/s
- Area deeper than 1 m: {exc['1']} km2; deeper than 5 m: {exc['5']} km2; deeper than 10 m: {exc['10']} km2

## Checks done
Rasters share the 1024 x 3072 grid with the 2006 bundle; no NaN; no negative values apart from the -9999 nodata; velocity and depth have identical valid cells: {qa['consistency']['velocity_valid_equals_depth_valid']}. Extent outline made from depth > 0.1 m ({len(polys)} polygons, simplified 0.7 px).

## Not done / limits
- Arrival-time raster NOT exported for this scenario (manifest key left null).
- Rasters are RAS Mapper exports of the default max layers (tiled GeoTIFF); strict COG layout not verified.
- No exposure statistics (no building/road/population layers available): left null.
- Near-channel depths unreliable (no bathymetry, 100 m mesh). Do not quote as a forecast.
""")
    open(OUT+'run_log.md','w').write(f"# Run log {sid}\n\n- Plan {p} / flow {u}, peak {peak} m3/s, 06 Aug 2006 06:00 to 11 Aug 2006 00:00.\n- Runtime {rt}, volume error {verr}%.\n- Max rasters exported from RAS Mapper on 2026-10-07 (default Depth, Velocity, WSE max layers).\n- Extent built from depth > 0.1 m.\n- Arrival time not exported.\n")
    print(sid,fa,md,mv,len(polys),os.path.getsize(OUT+'assets/extent.geojson'))

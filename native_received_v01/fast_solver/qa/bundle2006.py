import tifffile, numpy as np, cv2, json, math, hashlib, os, shutil
SRC='/mnt/user-data/uploads/Ukai/ukai-flood-intelligence/hydraulic/hecras/base_model/OBS2006/'
OUT='/mnt/user-data/outputs/v0.1/scenarios/ukai-2006-historical-v1/'
os.makedirs(OUT+'assets',exist_ok=True); os.makedirs(OUT+'provenance',exist_ok=True)
names={'max_depth':'max_depth.Ukai_Lower_Tapi_A2_Terrain.ukai_to_surat_dem_utm43_working.tif',
'max_velocity':'max_velocity.Ukai_Lower_Tapi_A2_Terrain.ukai_to_surat_dem_utm43_working.tif',
'max_wse':'max_wse.Ukai_Lower_Tapi_A2_Terrain.ukai_to_surat_dem_utm43_working.tif',
'arrival_time':'Arrival Time (0.1m hrs).Ukai_Lower_Tapi_A2_Terrain.ukai_to_surat_dem_utm43_working.tif'}
for k,v in names.items(): shutil.copyfile(SRC+v,OUT+'assets/%s.tif'%k)
PX=28.999033361477533; X0=268076.8810281253; Y0=2369001.58195343+0  # tiepoint y is top
d=tifffile.imread(OUT+'assets/max_depth.tif').astype('f8'); H,W=d.shape
a=tifffile.imread(OUT+'assets/arrival_time.tif').astype('f8')
mask=((d!=-9999)&(d>0.1)).astype(np.uint8)
cs,hier=cv2.findContours(mask,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
def utm_inv(E,N):
    a_=6378137.0; f=1/298.257223563; k0=0.9996; e2=f*(2-f); ep2=e2/(1-e2)
    x=E-500000.0; M=N/k0; mu=M/(a_*(1-e2/4-3*e2**2/64-5*e2**3/256))
    e1=(1-math.sqrt(1-e2))/(1+math.sqrt(1-e2))
    p=mu+(3*e1/2-27*e1**3/32)*math.sin(2*mu)+(21*e1**2/16-55*e1**4/32)*math.sin(4*mu)+(151*e1**3/96)*math.sin(6*mu)+(1097*e1**4/512)*math.sin(8*mu)
    s=math.sin(p);c=math.cos(p);t=math.tan(p)
    N1=a_/math.sqrt(1-e2*s*s);T1=t*t;C1=ep2*c*c;R1=a_*(1-e2)/(1-e2*s*s)**1.5;D=x/(N1*k0)
    lat=p-(N1*t/R1)*(D*D/2-(5+3*T1+10*C1-4*C1*C1-9*ep2)*D**4/24+(61+90*T1+298*C1+45*T1*T1-252*ep2-3*C1*C1)*D**6/720)
    lon=math.radians(75)+(D-(1+2*T1+C1)*D**3/6+(5-2*C1+28*T1-3*C1*C1+8*ep2+24*T1*T1)*D**5/120)/c
    return math.degrees(lon),math.degrees(lat)
def ring(cnt):
    pts=cv2.approxPolyDP(cnt,0.7,True).reshape(-1,2)
    if len(pts)<3: return None
    r=[list(utm_inv(X0+(x+0.5)*PX,Y0-(y+0.5)*PX)) for x,y in pts]; r.append(r[0]); return r
polys=[]; 
hier=hier[0]
for i,(n,p,fc,par) in enumerate(hier):
    if par==-1:
        outer=ring(cs[i]); 
        if outer is None or cv2.contourArea(cs[i])<4: continue
        rings=[outer]; j=fc
        while j!=-1:
            h=ring(cs[j]); 
            if h is not None and cv2.contourArea(cs[j])>=4: rings.append(h)
            j=hier[j][0]
        polys.append(rings)
gj={'type':'FeatureCollection','name':'extent_max_depth_gt_0.1m','crs':{'type':'name','properties':{'name':'urn:ogc:def:crs:OGC:1.3:CRS84'}},
 'features':[{'type':'Feature','properties':{'scenario_id':'ukai-2006-historical-v1','definition':'max depth > 0.1 m','source':'max_depth.tif','simplification':'cv2.approxPolyDP 0.7 px; parts < 4 px area dropped','status':'uncalibrated prototype'},
 'geometry':{'type':'MultiPolygon','coordinates':polys}}]}
json.dump(gj,open(OUT+'assets/extent.geojson','w'))
A=PX**2/1e6
print('polys',len(polys),'wet km2 %.1f'%(mask.sum()*A),'geojson bytes',os.path.getsize(OUT+'assets/extent.geojson'))
# sanity: lon/lat of first point and dam-side/corner
print(utm_inv(X0,Y0),utm_inv(X0+W*PX,Y0-H*PX))
# QA
qa={}
for k in names:
    arr=tifffile.imread(OUT+'assets/%s.tif'%k).astype('f8'); v=arr[arr!=-9999]
    qa[k]={'shape':list(arr.shape),'valid_cells':int(v.size),'min':float(v.min()),'max':float(v.max()),'mean':float(v.mean()),'nan_count':int(np.isnan(arr).sum()),'neg_nonnodata':int((v<0).sum())}
av=a[a!=-9999]; qa['arrival_time']['integer_valued']=bool(np.all(av==np.round(av)))
# consistency: arrival-time wet cells vs depth wet cells (align: arrival offset cols 256)
ao=a[0:H,256:256+W]
dv=(d!=-9999)&(d>0.1); av2=(ao!=-9999)
qa['consistency']={'depth_wet_gt0.1_cells':int(dv.sum()),'arrival_valid_cells_in_depth_window':int(av2.sum()),'depth_wet_without_arrival':int((dv&~av2).sum()),'arrival_without_depth_wet':int((av2&~dv).sum())}
v=tifffile.imread(OUT+'assets/max_velocity.tif').astype('f8'); 
qa['consistency']['velocity_valid_vs_depth_valid_equal']=bool(np.array_equal(v!=-9999,d!=-9999))
qa['depth_exceedance_km2']={str(t):round(float((d[d!=-9999]>t).sum()*A),1) for t in (0.1,0.5,1,2,5,10,15,20)}
qa['flooded_area_km2_gt_0.1m']=round(float(mask.sum()*A),1)
json.dump(qa,open(OUT+'provenance/raster_qa.json','w'),indent=1)
print(json.dumps(qa,indent=1))

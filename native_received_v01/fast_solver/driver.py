import numpy as np, tifffile, ctypes, re, time, cv2, sys, json
from scipy import ndimage as ndi
import os
HERE=os.path.dirname(os.path.abspath(__file__))
ROOT=os.path.abspath(os.path.join(HERE,'..','..'))   # folder that holds part_a_handoff and ukai-flood-intelligence
B=os.path.join(ROOT,'ukai-flood-intelligence','hydraulic','hecras')+os.sep
SCEN=os.path.join(ROOT,'part_a_handoff','v0.1','scenarios')+os.sep
if os.name=='nt':
    for _d in (r'C:\msys64\ucrt64\bin',):
        if os.path.isdir(_d): os.add_dll_directory(_d)   # lets li2d.dll find libgomp
lib=ctypes.CDLL(os.path.join(HERE,'li2d.dll' if os.name=='nt' else 'li2d.so'))
DX=100.0
def perimeter():
    L=open(B+'base_model/Ukai_Lower_Tapi_A2.g01').read().split('\n')
    k=[i for i,l in enumerate(L) if l.startswith('Storage Area Surface Line=')][0]
    n=int(L[k].split('=')[1]); pts=[]
    for l in L[k+1:k+1+n]:
        a=l.split(); pts.append((float(a[0]),float(a[1])))
    return np.array(pts)
def hydrograph(u):
    L=open(B+'base_model/Ukai_Lower_Tapi_A2.'+u).read().split('\n')
    k=[i for i,l in enumerate(L) if l.startswith('Flow Hydrograph=')][0]
    n=int(L[k].split('=')[1]); v=[]
    for l in L[k+1:]:
        if not re.match(r'^[\s\d.\-eE+]+$',l) or not l.strip(): break
        v+= [float(l[i:i+8]) for i in range(0,len(l.rstrip()),8)]
    assert len(v)==n,(len(v),n); return np.array(v)
def build():
    P=perimeter()
    x0=np.floor(P[:,0].min()/DX)*DX+DX/2; x1=P[:,0].max(); y0=np.floor(P[:,1].min()/DX)*DX+DX/2+34.3-50 ; y1=P[:,1].max()
    xs=np.arange(x0,x1+DX,DX); ys=np.arange(y0,y1+DX,DX); nx,ny=len(xs),len(ys)
    X,Y=np.meshgrid(xs,ys)
    # mask by polygon via cv2 on grid indices
    poly=np.stack([(P[:,0]-xs[0])/DX,(P[:,1]-ys[0])/DX],1)
    m=np.zeros((ny,nx),np.uint8); cv2.fillPoly(m,[np.round(poly).astype(np.int32)],1)
    # DEM
    t=tifffile.imread(B+'terrain/Ukai_Lower_Tapi_A2_Terrain.ukai_to_surat_dem_utm43_working.tif').astype('f8')
    PX=28.99903336147746; DX0=260653.128487587; DY0=2369001.58195343
    valid=(t>-1000).astype('f8'); tt=np.where(t>-1000,t,0)
    k=3; s=ndi.uniform_filter(tt,k)*k*k; c=ndi.uniform_filter(valid,k)*k*k
    f=np.where(c>0,s/np.maximum(c,1e-9),np.nan)
    cols=(X-DX0)/PX-0.5; rows=(DY0-Y)/PX-0.5
    z=ndi.map_coordinates(np.nan_to_num(f,nan=-9999),[rows,cols],order=1,mode='nearest')
    m=m.astype(bool)&(z>-1000)
    return dict(xs=xs,ys=ys,X=X,Y=Y,m=m,z=z,nx=nx,ny=ny)
def run(G,hyd,t_end_h,n=0.04,alpha=0.7,dtmax=30.0,theta=0.9,fr=1.0,s_out=0.0005,hth=0.1):
    nx,ny,m,z=G['nx'],G['ny'],G['m'],G['z']; X,Y=G['X'],G['Y']
    inflow=np.flatnonzero((m&(X>=353300-DX)&(Y>=2349000-DX/2)&(Y<=2353000+DX/2)).ravel()).astype(np.int32)
    out=np.flatnonzero((m&(X<=268500+DX)&(Y>=2343818-DX/2)&(Y<=2354817+DX/2)).ravel()).astype(np.int32)
    N=nx*ny; hm=np.zeros(N); vm=np.zeros(N); ar=np.zeros(N); st=np.zeros(5)
    zz=np.ascontiguousarray(z.ravel()); mk=np.ascontiguousarray(m.ravel().astype(np.uint8)); hy=np.ascontiguousarray(hyd)
    P=lambda a:a.ctypes.data_as(ctypes.c_void_p)
    lib.run.restype=ctypes.c_int
    lib.run.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_double]+[ctypes.c_void_p]*2+[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_double,ctypes.c_double]+[ctypes.c_double]*6+[ctypes.c_double]+[ctypes.c_void_p]*4
    t0=time.time()
    lib.run(nx,ny,DX,P(zz),P(mk),P(inflow),len(inflow),P(out),len(out),P(hy),len(hy),3600.0,t_end_h*3600.0,n,alpha,dtmax,theta,fr,s_out,hth,P(hm),P(vm),P(ar),P(st))
    el=time.time()-t0
    return dict(hmax=hm.reshape(ny,nx),vmax=vm.reshape(ny,nx),arr=ar.reshape(ny,nx),stats=st,sec=el,n_in=len(inflow),n_out=len(out))
if __name__=='__main__':
    t0=time.time(); G=build(); print('grid',G['nx'],G['ny'],'cells in mask',int(G['m'].sum()),'build s',round(time.time()-t0,1))
    print('z range in mask',G['z'][G['m']].min(),G['z'][G['m']].max())
    h=hydrograph('u07'); print('hyd',len(h),h.max())
    r=run(G,h,float(sys.argv[1]) if len(sys.argv)>1 else 2)
    print('sec',round(r['sec'],1),'steps',r['stats'][4],'in/out/stored',r['stats'][1:4],'n_in',r['n_in'],'n_out',r['n_out'])
    print('max depth',r['hmax'].max(),'wet km2',(r['hmax']>0.1).sum()*DX*DX/1e6)

import sys, os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from driver import *
A=28.999033361477533**2/1e6
PX=28.99903336147746; DX0=260653.128487587; DY0=2369001.58195343
def to_hecras_grid(G,field,H=1024,W=3072,col_off=256):
    # sample solver field at pixel centres of the HEC-RAS export raster (rows from DEM top, cols offset by 256)
    r=np.arange(H)[:,None]; c=np.arange(W)[None,:]+col_off
    Xp=DX0+(c+0.5)*PX; Yp=DY0-(r+0.5)*PX
    Xp,Yp=np.broadcast_arrays(Xp,Yp)
    i=np.round((Xp-G['xs'][0])/DX).astype(int); j=np.round((Yp-G['ys'][0])/DX).astype(int)
    ok=(i>=0)&(i<G['nx'])&(j>=0)&(j<G['ny'])
    out=np.zeros((H,W)); out[ok]=field[j[ok],i[ok]]
    return out
def hec(path):
    a=tifffile.imread(path).astype('f8'); a[a==-9999]=0; a[a<0]=0; return a
def metrics(p,t):
    wp=p>0.1; wt=t>0.1; inter=(wp&wt).sum(); union=(wp|wt).sum()
    e=(p-t)[wt]
    return dict(true_km2=round(float(wt.sum()*A),1),pred_km2=round(float(wp.sum()*A),1),area_err_pct=round(float((wp.sum()-wt.sum())/wt.sum()*100),1),IoU=round(float(inter/union),3),
      depth_bias_m=round(float(e.mean()),2),depth_MAE_m=round(float(np.abs(e).mean()),2),depth_RMSE_m=round(float(np.sqrt((e**2).mean())),2),
      pct_within_1m=round(float((np.abs(e)<=1).mean()*100),1),pct_within_2m=round(float((np.abs(e)<=2).mean()*100),1))
if __name__=='__main__':
    G=build(); h=hydrograph('u07')
    r=run(G,h,138.0)
    np.savez_compressed('res_obs2006.npz',hmax=r['hmax'],vmax=r['vmax'],arr=r['arr'],stats=r['stats'],sec=r['sec'])
    print('RUN sec',round(r['sec'],1),'steps',r['stats'][4],'mass in/out/stored',r['stats'][1:4])
    O=SCEN+'ukai-2006-historical-v2/assets/'
    pd=to_hecras_grid(G,r['hmax']); td=hec(O+'max_depth.tif')
    print(metrics(pd,td))
    pv=to_hecras_grid(G,r['vmax']); tv=hec(O+'max_velocity.tif')
    print('vmax solver',round(float(pv.max()),2),'hec',round(float(tv.max()),2),'mean on common wet',round(float(pv[(pd>0.1)&(td>0.1)].mean()),2),round(float(tv[(pd>0.1)&(td>0.1)].mean()),2))
    np.save('obs2006_depth.npy',pd)

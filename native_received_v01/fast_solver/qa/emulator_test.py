import tifffile, numpy as np, time, json
A=28.999033361477533**2/1e6
O='/mnt/user-data/outputs/v0.1/scenarios/'
runs={15000:O+'ukai-hyp-h01-release15000-v1/assets/max_depth.tif',20000:O+'ukai-hyp-h02-release20000-v1/assets/max_depth.tif',
      25648:O+'ukai-2006-historical-v2/assets/max_depth.tif',30000:O+'ukai-hyp-h03-release30000-v1/assets/max_depth.tif'}
D={}
for q,p in runs.items():
    a=tifffile.imread(p).astype('f4'); a[a==-9999]=0; a[a<0]=0; D[q]=a
Q=sorted(D); shape=D[Q[0]].shape
def pred(qs,q,mode):
    qs=sorted(qs); lo=[x for x in qs if x<=q]; hi=[x for x in qs if x>=q]
    if lo and hi:
        a,b=lo[-1],hi[0]
        if a==b: return D[a]
    elif not lo: a,b=qs[0],qs[1]
    else: a,b=qs[-2],qs[-1]
    t=(np.log(q/a)/np.log(b/a)) if mode=='logQ' else (q-a)/(b-a)
    out=D[a]*(1-t)+D[b]*t
    return np.maximum(out,0)
def metrics(p,t):
    wp=p>0.1; wt=t>0.1
    inter=(wp&wt).sum(); union=(wp|wt).sum()
    tw=t[wt]; 
    err=(p-t)[wt|wp]
    return dict(true_km2=round(float(wt.sum()*A),1),pred_km2=round(float(wp.sum()*A),1),area_err_pct=round(float((wp.sum()-wt.sum())/wt.sum()*100),1),
      IoU=round(float(inter/union),3),depth_MAE_m=round(float(np.abs(err).mean()),2),depth_RMSE_m=round(float(np.sqrt((err**2).mean())),2),
      depth_MAE_on_true_wet_m=round(float(np.abs((p-t)[wt]).mean()),2),pct_wet_cells_within_1m=round(float((np.abs((p-t)[wt])<=1).mean()*100),1))
res={}
for tq in Q:
    others=[q for q in Q if q!=tq]
    for mode in ('linear','logQ'):
        t0=time.time(); p=pred(others,tq,mode); dt=time.time()-t0
        m=metrics(p,D[tq]); m['seconds']=round(dt,3)
        kind='interpolation' if min(others)<tq<max(others) else 'extrapolation'
        res[f'{tq}_{mode}']=dict(kind=kind,**m)
        print(tq,mode,kind,m)
json.dump(res,open('/tmp/claude-0/-home-claude/c1f15995-d94d-5e55-bafc-3982b25ee34d/scratchpad/qa/emulator_results.json','w'),indent=1)

print('--- area-matched cutoff variant ---')
area={q:float((D[q]>0.1).sum()*A) for q in Q}
def pred_matched(qs,q):
    p=pred(qs,q,'logQ')
    qs=sorted(qs); lo=[x for x in qs if x<=q]; hi=[x for x in qs if x>=q]
    if lo and hi: a,b=lo[-1],hi[0]
    elif not lo: a,b=qs[0],qs[1]
    else: a,b=qs[-2],qs[-1]
    t=np.log(q/a)/np.log(b/a); tgt=area[a]*(1-t)+area[b]*t   # km2
    vals=np.sort(p[p>0].ravel())[::-1]; n=int(round(tgt/A))
    c=vals[min(n,len(vals)-1)]
    c=max(c,0.1)
    p2=np.where(p>=c,p,0); return p2,c,tgt
res2={}
for tq in Q:
    others=[q for q in Q if q!=tq]
    t0=time.time(); p,c,tgt=pred_matched(others,tq); dt=time.time()-t0
    m=metrics(p,D[tq]); m['cutoff_m']=round(float(c),3); m['target_km2']=round(tgt,1); m['seconds']=round(dt,3)
    kind='interpolation' if min(others)<tq<max(others) else 'extrapolation'
    res2[str(tq)]=dict(kind=kind,**m); print(tq,kind,m)
json.dump(dict(basic=res,area_matched=res2),open('/tmp/claude-0/-home-claude/c1f15995-d94d-5e55-bafc-3982b25ee34d/scratchpad/qa/emulator_results.json','w'),indent=1)

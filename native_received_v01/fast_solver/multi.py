import sys, os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from compare import *
import json
NN=float(sys.argv[1]) if len(sys.argv)>1 else 0.025   # Manning n for the solver (0.025 = best fit to HEC-RAS on H02)
TAG='n%g'%NN
G=build(); out={}
cases=[('OBS2006','u07','ukai-2006-historical-v2'),('H01','u04','ukai-hyp-h01-release15000-v1'),('H02','u05','ukai-hyp-h02-release20000-v1'),('H03','u06','ukai-hyp-h03-release30000-v1')]
for name,u,sid in cases:
    h=hydrograph(u); r=run(G,h,float(len(h)-1),n=NN)
    np.savez_compressed('res_%s_%s.npz'%(name,TAG),hmax=r['hmax'],vmax=r['vmax'],arr=r['arr'],stats=r['stats'],sec=r['sec'])
    O=SCEN+sid+'/assets/'
    pd=to_hecras_grid(G,r['hmax']); td=hec(O+'max_depth.tif')
    m=metrics(pd,td); m['sec']=round(r['sec'],1); m['peak']=float(h.max()); m['hours']=len(h)-1; m['mass_in']=r['stats'][1]; m['mass_stored']=r['stats'][3]
    out[name]=m; print(name,m,flush=True)
json.dump(out,open('multi_results_%s.json'%TAG,'w'),indent=1)

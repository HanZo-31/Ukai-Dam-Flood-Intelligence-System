import sys, os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from compare import *
G=build(); h=hydrograph('u05'); O=SCEN+'ukai-hyp-h02-release20000-v1/assets/'; td=hec(O+'max_depth.tif')
for n in [float(a) for a in sys.argv[1:]]:
    r=run(G,h,float(len(h)-1),n=n); m=metrics(to_hecras_grid(G,r['hmax']),td); m['sec']=round(r['sec'],1); print('n',n,m,flush=True)

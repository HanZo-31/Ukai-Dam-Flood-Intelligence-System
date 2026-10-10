/* Synthetic native-code smoke only: uses received solver unchanged.
 * This is not a Ukai scenario, pipeline adapter, or scientific validation.
 */
#include <stdio.h>
#include <math.h>
#include "../native_received_v01/fast_solver/li2d.c"

int main(void) {
    enum { NX=16, NY=16, CELLS=NX*NY };
    double terrain[CELLS], depth[CELLS], velocity[CELLS], arrival[CELLS], stats[5];
    unsigned char mask[CELLS];
    int inflow[1]={15}, outflow[1]={240};
    double hydrograph[2]={500.0,500.0};
    int i;
    for(i=0;i<CELLS;i++){terrain[i]=0.0;mask[i]=1;}
    int steps=run(NX,NY,100.0,terrain,mask,inflow,1,outflow,1,hydrograph,2,
        3600.0,600.0,0.025,0.7,30.0,0.9,1.0,0.0005,0.1,depth,velocity,arrival,stats);
    if(steps<=0 || !isfinite(stats[3]) || fabs(stats[0]-600.0)>1e-9)return 2;
    for(i=0;i<CELLS;i++){
        if(!isfinite(depth[i]) || depth[i]<0.0 || !isfinite(velocity[i]) || velocity[i]<0.0)return 3;
        if(arrival[i]!=-1 && (!isfinite(arrival[i]) || arrival[i]<0 || arrival[i]>600.0))return 4;
    }
    double residual=stats[1]-stats[2]-stats[3];
    if(fabs(residual)>1e-6*stats[1])return 5;
    printf("{\"synthetic_only\":true,\"steps\":%d,\"simulated_seconds\":%.17g,\"mass_in_m3\":%.17g,\"mass_out_m3\":%.17g,\"mass_stored_m3\":%.17g,\"residual_m3\":%.17g}\n",
        steps,stats[0],stats[1],stats[2],stats[3],residual);
    return 0;
}

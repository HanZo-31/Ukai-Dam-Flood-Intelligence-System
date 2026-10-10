// Local-inertial 2D shallow water (Bates et al. 2010) on a regular grid. OpenMP. Not for hand-over yet.
#include <math.h>
#include <string.h>
#include <stdlib.h>
#include <omp.h>
#define G 9.80665
static inline double mx(double a,double b){return a>b?a:b;}
static inline double mn(double a,double b){return a<b?a:b;}
// returns number of steps; out_stats: [0]=t_end,[1]=mass_in,[2]=mass_out,[3]=mass_stored,[4]=nsteps
int run(int nx,int ny,double dx,const double*z,const unsigned char*mask,
        const int*inflow_idx,int n_in,const int*out_idx,int n_out,
        const double*hyd,int nhyd,double hyd_dt,double t_end,
        double n_man,double alpha,double dtmax,double theta,double fr_lim,double s_out,
        double hthresh,double*hmax_out,double*vmax_out,double*arr_out,double*stats)
{
  size_t N=(size_t)nx*ny;
  double*h=calloc(N,8),*qx=calloc(N,8),*qy=calloc(N,8),*qxn=calloc(N,8),*qyn=calloc(N,8);
  for(size_t k=0;k<N;k++){hmax_out[k]=0;vmax_out[k]=0;arr_out[k]=-1;}
  double t=0,min_in=0,mout=0; long step=0; double dt=1.0; double n2=n_man*n_man;
  const double hmin=1e-3;
  while(t<t_end){
    if(step%10==0){
      double hm=0.01;
      #pragma omp parallel for reduction(max:hm)
      for(size_t k=0;k<N;k++) if(mask[k]&&h[k]>hm) hm=h[k];
      dt=alpha*dx/sqrt(G*hm); if(dt>dtmax)dt=dtmax;
    }
    if(t+dt>t_end) dt=t_end-t;
    // fluxes
    #pragma omp parallel for
    for(int j=0;j<ny;j++){
      for(int i=0;i<nx;i++){
        size_t k=(size_t)j*nx+i;
        double qa=0,qb=0;
        if(mask[k]){
          if(i+1<nx&&mask[k+1]){
            double ei=z[k]+h[k],ej=z[k+1]+h[k+1];
            double hf=mx(ei,ej)-mx(z[k],z[k+1]);
            if(hf>hmin){
              double ql=(i>0&&mask[k-1])?qx[k-1]:qx[k], qr=(i+2<nx&&mask[k+1])?qx[k+1]:qx[k];
              double qm=theta*qx[k]+0.5*(1-theta)*(ql+qr);
              qa=(qm-G*hf*dt*(ej-ei)/dx)/(1+G*dt*n2*fabs(qx[k])/pow(hf,7.0/3.0));
              double c=fr_lim*sqrt(G*hf); if(fabs(qa)>c*hf) qa=copysign(c*hf,qa);
              { double lim_p=h[k]*dx/(4*dt), lim_m=h[k+1]*dx/(4*dt); if(qa>lim_p)qa=lim_p; if(qa<-lim_m)qa=-lim_m; }
            }
          }
          if(j+1<ny&&mask[k+nx]){
            double ei=z[k]+h[k],ej=z[k+nx]+h[k+nx];
            double hf=mx(ei,ej)-mx(z[k],z[k+nx]);
            if(hf>hmin){
              double ql=(j>0&&mask[k-nx])?qy[k-nx]:qy[k], qr=(j+2<ny&&mask[k+nx])?qy[k+nx]:qy[k];
              double qm=theta*qy[k]+0.5*(1-theta)*(ql+qr);
              qb=(qm-G*hf*dt*(ej-ei)/dx)/(1+G*dt*n2*fabs(qy[k])/pow(hf,7.0/3.0));
              double c=fr_lim*sqrt(G*hf); if(fabs(qb)>c*hf) qb=copysign(c*hf,qb);
              { double lim_p=h[k]*dx/(4*dt), lim_m=h[k+nx]*dx/(4*dt); if(qb>lim_p)qb=lim_p; if(qb<-lim_m)qb=-lim_m; }
            }
          }
        }
        qxn[k]=qa; qyn[k]=qb;
      }
    }
    double*tp=qx;qx=qxn;qxn=tp; tp=qy;qy=qyn;qyn=tp;
    // depth update
    #pragma omp parallel for
    for(int j=0;j<ny;j++){
      for(int i=0;i<nx;i++){
        size_t k=(size_t)j*nx+i; if(!mask[k]) continue;
        double div=(i>0?qx[k-1]:0)-qx[k]+(j>0?qy[k-nx]:0)-qy[k];
        double hn=h[k]+dt*div/dx; if(hn<0)hn=0; h[k]=hn;
      }
    }
    // inflow
    double qin;{ double ft=t/hyd_dt; int i0=(int)ft; if(i0>=nhyd-1){qin=hyd[nhyd-1];} else {double f=ft-i0; qin=hyd[i0]*(1-f)+hyd[i0+1]*f;} }
    double vin=qin*dt; for(int a=0;a<n_in;a++){ h[inflow_idx[a]]+=vin/n_in/(dx*dx); }
    min_in+=vin;
    // outflow (normal depth)
    double vo=0;
    for(int a=0;a<n_out;a++){ size_t k=out_idx[a]; double hh=h[k]; if(hh>hmin){ double q=pow(hh,5.0/3.0)*sqrt(s_out)/n_man; double v=q*dx*dt; if(v>hh*dx*dx)v=hh*dx*dx; h[k]-=v/(dx*dx); vo+=v; } }
    mout+=vo;
    t+=dt; step++;
    // stats
    #pragma omp parallel for
    for(int j=0;j<ny;j++) for(int i=0;i<nx;i++){
      size_t k=(size_t)j*nx+i; if(!mask[k]) continue;
      if(h[k]>hmax_out[k]) hmax_out[k]=h[k];
      if(arr_out[k]<0 && h[k]>hthresh) arr_out[k]=t;
      double v=0; double a1=0;
      if(i>0){double hf=mx(z[k]+h[k],z[k-1]+h[k-1])-mx(z[k],z[k-1]); if(hf>0.05) a1=fabs(qx[k-1])/hf; v=mx(v,a1);}
      {double hf=mx(z[k]+h[k],(i+1<nx?z[k+1]+h[k+1]:-1e9))-mx(z[k],(i+1<nx?z[k+1]:1e9)); if(hf>0.05) v=mx(v,fabs(qx[k])/hf);}
      if(j>0){double hf=mx(z[k]+h[k],z[k-nx]+h[k-nx])-mx(z[k],z[k-nx]); if(hf>0.05) v=mx(v,fabs(qy[k-nx])/hf);}
      {double hf=mx(z[k]+h[k],(j+1<ny?z[k+nx]+h[k+nx]:-1e9))-mx(z[k],(j+1<ny?z[k+nx]:1e9)); if(hf>0.05) v=mx(v,fabs(qy[k])/hf);}
      if(v>vmax_out[k]) vmax_out[k]=v;
    }
  }
  double stored=0; for(size_t k=0;k<N;k++) if(mask[k]) stored+=h[k]*dx*dx;
  stats[0]=t;stats[1]=min_in;stats[2]=mout;stats[3]=stored;stats[4]=step;
  free(h);free(qx);free(qy);free(qxn);free(qyn);
  return (int)step;
}

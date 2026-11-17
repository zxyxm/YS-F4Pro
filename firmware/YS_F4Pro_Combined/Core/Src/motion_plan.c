#include "motion_plan.h"
#include <math.h>
#define PPR ((float)MOTOR_PULSES_PER_REV)
int plan_move(MotionPlan *p,uint32_t n,float rpm,float acc,float dec,uint8_t curve)
{
 if(n==0 || n>32000 || !isfinite(rpm)||!isfinite(acc)||!isfinite(dec)||rpm<1||rpm>200||acc<1||acc>400||dec<1||dec>400||curve>1) return 0;
 *p=(MotionPlan){0}; p->steps=n;p->a=acc*PPR/60;p->d=dec*PPR/60;p->v=rpm*PPR/60;p->curve=curve;
 if(curve==1) {
  /* Quintic position: s=10u^3-15u^4+6u^5. Peak ds/du=1.875;
     peak |d2s/du2|=10/sqrt(3). Both acceleration limits respected. */
  p->total=fmaxf(1.875f*n/p->v,sqrtf(5.773503f*n/fminf(p->a,p->d)));
 } else {
  p->v=fminf(p->v,sqrtf(2.0f*n*p->a*p->d/(p->a+p->d)));
  p->ta=p->v/p->a;p->da=p->v*p->v/(2*p->a);
  float dd=p->v*p->v/(2*p->d);
  p->dc=fmaxf(0,(float)n-p->da-dd);p->tc=p->dc/p->v;
  p->total=p->ta+p->tc+p->v/p->d;
 }
 return p->total<=120.0f;
}
void plan_stop(MotionPlan *p,uint32_t n,float v)
{
 *p=(MotionPlan){0};p->steps=n;p->v=v;p->d=v*v/(2.0f*n);p->total=2.0f*n/v;p->curve=2;
}
uint32_t plan_time_us(const MotionPlan *p,uint32_t k,float *velocity)
{
 float t=0,v=0;
 if(k>=p->steps){t=p->total;v=0;}
 else if(p->curve==1){
  float lo=0,hi=1,x=(float)k/p->steps;
  for(int i=0;i<25;i++) {float u=(lo+hi)*0.5f;float s=u*u*u*(10+u*(-15+6*u));if(s<x)lo=u;else hi=u;}
  float u=(lo+hi)*0.5f;t=u*p->total;v=p->steps/p->total*30*u*u*(1-u)*(1-u);
 } else if(p->curve==2){
  v=sqrtf(fmaxf(0,p->v*p->v-2*p->d*k));t=2.0f*k/(p->v+v);
 } else if(k<p->da){t=sqrtf(2.0f*k/p->a);v=p->a*t;}
 else if(k<p->da+p->dc){t=p->ta+(k-p->da)/p->v;v=p->v;}
 else {float remaining=p->steps-k;v=sqrtf(2*p->d*remaining);t=p->total-v/p->d;}
 if(velocity)*velocity=v;
 return (uint32_t)(t*1000000.0f+0.5f);
}

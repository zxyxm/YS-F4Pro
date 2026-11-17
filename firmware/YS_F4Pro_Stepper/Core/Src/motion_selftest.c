#include "motion_plan.h"
#include <math.h>
/* Runs only calculations; never touches GPIO or a timer. Check absolute-time
 * quantisation, first/last intervals and timer pulse-width margin. */
uint32_t motion_selftest(void)
{
 const uint32_t distances[]={1,2,3200,32000};
 for(uint8_t curve=0;curve<2;curve++){
  for(uint32_t c=0;c<4;c++){
   MotionPlan p;uint32_t previous=0;
   if(!plan_move(&p,distances[c],200,400,400,curve))return 10+curve;
   for(uint32_t k=1;k<=p.steps;k++){
    float v;uint32_t now=plan_time_us(&p,k,&v);
    if(now<=previous||now-previous<=48||!isfinite(v)||v<0||v>MOTOR_PULSES_PER_REV*200.0f/60+0.1f)return 20+curve;
    previous=now;
   }
   if(fabsf(previous*0.000001f-p.total)>0.00002f)return 30+curve;
  }
 }
 MotionPlan p;
 if(plan_move(&p,0,30,30,30,0)||plan_move(&p,32001,30,30,30,0)||plan_move(&p,1,201,30,30,0)||plan_move(&p,1,30,0,30,0)||plan_move(&p,1,NAN,30,30,0))return 40;
 plan_stop(&p,1000,1600);uint32_t previous=0;
 for(uint32_t k=1;k<=p.steps;k++){
  float v;uint32_t now=plan_time_us(&p,k,&v);
  if(now<=previous||v<0||v>1600)return 50;
  previous=now;
 }
 return 0;
}

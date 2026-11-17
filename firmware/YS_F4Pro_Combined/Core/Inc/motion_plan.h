#ifndef MOTION_PLAN_H
#define MOTION_PLAN_H
#include <stdint.h>
#define MOTOR_PULSES_PER_REV 3200U
typedef struct {
 uint32_t steps;
 float a,d,v,ta,tc,total,da,dc;
 uint8_t curve; /* 0: trapezoid, 1: symmetric quintic position, 2: stop */
} MotionPlan;
int plan_move(MotionPlan *p,uint32_t steps,float rpm,float accel,float decel,uint8_t curve);
void plan_stop(MotionPlan *p,uint32_t steps,float velocity);
uint32_t plan_time_us(const MotionPlan *p,uint32_t step,float *velocity);
#endif

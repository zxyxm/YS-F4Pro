#include "stm32f4xx_hal.h"
#include "motion_plan.h"
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
#include <stdlib.h>
#include <errno.h>

#define AXIS_COUNT 4U
#define PULSE_US 40U
#define RX_CAP 1024U
TIM_HandleTypeDef htim8;
UART_HandleTypeDef huart1;
typedef struct {
 volatile uint32_t active,fault,emitted,target,done_counter,isr_max_cycles;
 volatile int32_t position;
 volatile float velocity;
 volatile uint8_t stop_requested;
 uint8_t speed_mode;
 uint32_t period_us;
 float speed_target,speed_accel;
 uint8_t phase,direction;
 uint32_t wait_remaining,segment_step,previous_us;
 uint16_t compare_tick;
 float next_velocity;
 MotionPlan plan;
} Axis;
Axis axes[AXIS_COUNT];
typedef struct { uint32_t steps,rpm,accel,decel,curve,revision; } AxisParams;
AxisParams axis_params[4]={{MOTOR_PULSES_PER_REV,30,30,30,0,0},{MOTOR_PULSES_PER_REV,30,30,30,0,0},{MOTOR_PULSES_PER_REV,30,30,30,0,0},{MOTOR_PULSES_PER_REV,30,30,30,0,0}};
volatile uint32_t g_uptime_ms,g_motion_selftest_result=0xffffffffU,g_link_timeout;
#ifdef MOTION_ENGINE_TEST
volatile uint32_t g_engine_test_result=0xffffffffU,g_test_stop_position;
#endif
static uint8_t ready,rx_byte;
static volatile uint16_t rx_head,rx_tail;
static volatile uint8_t rx_overflow;
static char rx_ring[RX_CAP];
static uint32_t watchdog_ms,last_command_ms;
static GPIO_TypeDef *const dir_ports[4]={GPIOD,GPIOD,GPIOF,GPIOC};
static const uint16_t dir_pins[4]={GPIO_PIN_3,GPIO_PIN_11,GPIO_PIN_1,GPIO_PIN_8};
extern uint32_t motion_selftest(void);
static void send_text(const char *s){HAL_UART_Transmit(&huart1,(const uint8_t *)s,(uint16_t)strlen(s),100);}
void Fault_Stop(void){
 if(RCC->APB2ENR&RCC_APB2ENR_TIM8EN){TIM8->BDTR&=~TIM_BDTR_MOE;TIM8->CR1&=~TIM_CR1_CEN;TIM8->DIER=0;}
 for(unsigned i=0;i<AXIS_COUNT;i++){axes[i].active=0;axes[i].fault=99;}
}
void Error_Handler(void){Fault_Stop();__disable_irq();while(1){}}
void SysTick_Handler(void){HAL_IncTick();}
void TIM8_CC_IRQHandler(void){HAL_TIM_IRQHandler(&htim8);}
void USART1_IRQHandler(void){HAL_UART_IRQHandler(&huart1);}
static void clock_init(void)
{
 RCC_OscInitTypeDef o={0};RCC_ClkInitTypeDef c={0};
 __HAL_RCC_PWR_CLK_ENABLE();__HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);
 o.OscillatorType=RCC_OSCILLATORTYPE_HSE;o.HSEState=RCC_HSE_ON;o.PLL.PLLState=RCC_PLL_ON;
 o.PLL.PLLSource=RCC_PLLSOURCE_HSE;o.PLL.PLLM=8;o.PLL.PLLN=336;o.PLL.PLLP=RCC_PLLP_DIV2;o.PLL.PLLQ=7;
 if(HAL_RCC_OscConfig(&o)!=HAL_OK)Error_Handler();
 c.ClockType=RCC_CLOCKTYPE_SYSCLK|RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
 c.SYSCLKSource=RCC_SYSCLKSOURCE_PLLCLK;c.AHBCLKDivider=RCC_SYSCLK_DIV1;c.APB1CLKDivider=RCC_HCLK_DIV4;c.APB2CLKDivider=RCC_HCLK_DIV2;
 if(HAL_RCC_ClockConfig(&c,FLASH_LATENCY_5)!=HAL_OK)Error_Handler();
}

static void oc_mode(unsigned i,uint32_t mode){
 volatile uint32_t *reg=i<2?&TIM8->CCMR1:&TIM8->CCMR2;
 unsigned shift=(i&1U)*8U;
 MODIFY_REG(*reg,TIM_CCMR1_OC1M<<shift,mode<<shift);
}
static void hardware_init(void){
 __HAL_RCC_GPIOD_CLK_ENABLE();__HAL_RCC_GPIOE_CLK_ENABLE();__HAL_RCC_GPIOF_CLK_ENABLE();
 __HAL_RCC_GPIOH_CLK_ENABLE();__HAL_RCC_GPIOI_CLK_ENABLE();__HAL_RCC_GPIOB_CLK_ENABLE();__HAL_RCC_GPIOC_CLK_ENABLE();
 GPIO_InitTypeDef g={0};g.Mode=GPIO_MODE_OUTPUT_PP;g.Speed=GPIO_SPEED_FREQ_HIGH;
 HAL_GPIO_WritePin(GPIOD,GPIO_PIN_3|GPIO_PIN_7|GPIO_PIN_11,GPIO_PIN_RESET);
 g.Pin=GPIO_PIN_3|GPIO_PIN_7|GPIO_PIN_11;HAL_GPIO_Init(GPIOD,&g);
 HAL_GPIO_WritePin(GPIOF,GPIO_PIN_1|GPIO_PIN_2|GPIO_PIN_11,GPIO_PIN_RESET);
 g.Pin=GPIO_PIN_1|GPIO_PIN_2|GPIO_PIN_11;HAL_GPIO_Init(GPIOF,&g);
 HAL_GPIO_WritePin(GPIOC,GPIO_PIN_8,GPIO_PIN_RESET);g.Pin=GPIO_PIN_8;HAL_GPIO_Init(GPIOC,&g);
 HAL_GPIO_WritePin(GPIOH,GPIO_PIN_7,GPIO_PIN_RESET);HAL_GPIO_WritePin(GPIOH,GPIO_PIN_9,GPIO_PIN_SET);
 g.Pin=GPIO_PIN_7|GPIO_PIN_9;HAL_GPIO_Init(GPIOH,&g);
 HAL_GPIO_WritePin(GPIOI,GPIO_PIN_2|GPIO_PIN_5|GPIO_PIN_6|GPIO_PIN_7,GPIO_PIN_RESET);
 g.Pin=GPIO_PIN_2|GPIO_PIN_5|GPIO_PIN_6|GPIO_PIN_7;HAL_GPIO_Init(GPIOI,&g);
 g.Pin=GPIO_PIN_0|GPIO_PIN_1|GPIO_PIN_2|GPIO_PIN_3;g.Mode=GPIO_MODE_INPUT;g.Pull=GPIO_PULLUP;HAL_GPIO_Init(GPIOE,&g);
 __HAL_RCC_USART1_CLK_ENABLE();g.Pin=GPIO_PIN_6|GPIO_PIN_7;g.Mode=GPIO_MODE_AF_PP;g.Alternate=GPIO_AF7_USART1;g.Pull=GPIO_PULLUP;HAL_GPIO_Init(GPIOB,&g);
 huart1.Instance=USART1;huart1.Init.BaudRate=115200;huart1.Init.WordLength=UART_WORDLENGTH_8B;huart1.Init.StopBits=UART_STOPBITS_1;
 huart1.Init.Parity=UART_PARITY_NONE;huart1.Init.Mode=UART_MODE_TX_RX;huart1.Init.HwFlowCtl=UART_HWCONTROL_NONE;huart1.Init.OverSampling=UART_OVERSAMPLING_16;
 if(HAL_UART_Init(&huart1)!=HAL_OK)Error_Handler();
 HAL_NVIC_SetPriority(USART1_IRQn,3,0);HAL_NVIC_EnableIRQ(USART1_IRQn);
 __HAL_RCC_TIM8_CLK_ENABLE();htim8.Instance=TIM8;htim8.Init.Prescaler=167;htim8.Init.CounterMode=TIM_COUNTERMODE_UP;
 htim8.Init.Period=65535;htim8.Init.ClockDivision=TIM_CLOCKDIVISION_DIV1;htim8.Init.RepetitionCounter=0;
 if(HAL_TIM_OC_Init(&htim8)!=HAL_OK)Error_Handler();
 TIM_OC_InitTypeDef oc={0};oc.OCMode=TIM_OCMODE_FORCED_INACTIVE;oc.OCPolarity=TIM_OCPOLARITY_HIGH;oc.OCIdleState=TIM_OCIDLESTATE_RESET;
 for(unsigned i=0;i<4;i++)if(HAL_TIM_OC_ConfigChannel(&htim8,&oc,i*4U)!=HAL_OK)Error_Handler();
 SET_BIT(TIM8->BDTR,TIM_BDTR_OSSI);
 /* Test firmware deliberately keeps all PUL pins as GPIO outputs LOW.
    Only internal timer IRQs run; the motor drivers receive no pulses. */
#ifndef MOTION_ENGINE_TEST
 g.Pin=GPIO_PIN_2|GPIO_PIN_5|GPIO_PIN_6|GPIO_PIN_7;g.Mode=GPIO_MODE_AF_PP;g.Pull=GPIO_NOPULL;g.Alternate=GPIO_AF3_TIM8;HAL_GPIO_Init(GPIOI,&g);
#endif
 HAL_NVIC_SetPriority(TIM8_CC_IRQn,0,0);HAL_NVIC_EnableIRQ(TIM8_CC_IRQn);
 CoreDebug->DEMCR|=CoreDebug_DEMCR_TRCENA_Msk;DWT->CYCCNT=0;DWT->CTRL|=DWT_CTRL_CYCCNTENA_Msk;
 __HAL_DBGMCU_FREEZE_TIM8();ready=1;
 if(HAL_UART_Receive_IT(&huart1,&rx_byte,1)!=HAL_OK)Error_Handler();
}
static void finish(unsigned i,uint32_t fault){
 Axis *a=&axes[i];
 /* HAL stops CEN/MOE only if ALL four channels are disabled. */
 HAL_TIM_OC_Stop_IT(&htim8,i*4U);oc_mode(i,TIM_OCMODE_FORCED_INACTIVE);
 __HAL_TIM_CLEAR_FLAG(&htim8,TIM_FLAG_CC1<<i);
 a->velocity=0;a->fault=fault;a->stop_requested=0;__DMB();a->active=0;a->done_counter++;
}
static void schedule(unsigned i,uint32_t delay,uint32_t mode){
 Axis *a=&axes[i];uint32_t elapsed=(uint16_t)((uint16_t)TIM8->CNT-a->compare_tick);
 if(delay<8 || elapsed+4>=delay){finish(i,1);return;}
 oc_mode(i,mode);a->compare_tick=(uint16_t)(a->compare_tick+delay);
 __HAL_TIM_SET_COMPARE(&htim8,i*4U,a->compare_tick);
}
static void schedule_wait(unsigned i){
 Axis *a=&axes[i];uint32_t chunk=a->wait_remaining>60000?60000:a->wait_remaining;a->wait_remaining-=chunk;
 schedule(i,chunk,a->wait_remaining?TIM_OCMODE_TIMING:TIM_OCMODE_TOGGLE);
}
static int move_start(unsigned i,int32_t steps,uint32_t rpm,uint32_t acc,uint32_t dec,uint8_t curve){
 if(i>=AXIS_COUNT)return 0;
 Axis *a=&axes[i];
 if(a->active||a->fault||!ready)return 0;
 int64_t goal=(int64_t)a->position+steps;uint32_t n=steps<0?(uint32_t)(-(int64_t)steps):(uint32_t)steps;
 MotionPlan proposed;
 if(goal<INT32_MIN||goal>INT32_MAX||!plan_move(&proposed,n,(float)rpm,(float)acc,(float)dec,curve))return 0;
 a->direction=steps<0;HAL_GPIO_WritePin(dir_ports[i],dir_pins[i],a->direction?GPIO_PIN_SET:GPIO_PIN_RESET);
 HAL_Delay(1);
 /* Compute expensive planning outside critical section; existing axes keep running. */
 float v;uint32_t first=plan_time_us(&proposed,1,&v);
 __disable_irq();a->plan=proposed;a->emitted=0;a->target=n;a->velocity=0;a->segment_step=0;a->phase=0;a->stop_requested=0;a->speed_mode=0;a->period_us=first;
 a->next_velocity=v;a->previous_us=first;a->wait_remaining=first;
 HAL_TIM_OC_Stop_IT(&htim8,i*4U);oc_mode(i,TIM_OCMODE_FORCED_INACTIVE);
 /* Shared free-running counter: NEVER reset CNT when starting another axis. */
 a->compare_tick=(uint16_t)TIM8->CNT;__HAL_TIM_CLEAR_FLAG(&htim8,TIM_FLAG_CC1<<i);a->active=1;
 schedule_wait(i);
 if(a->active&&HAL_TIM_OC_Start_IT(&htim8,i*4U)!=HAL_OK)finish(i,2);
 __enable_irq();return a->active!=0;
}
/* Continuous trapezoidal speed ramp. Each interval uses local pulse-distance
   integration, avoiding floating-point absolute timestamps on long runs. */
static int speed_start(unsigned i,int direction,uint32_t rpm,uint32_t acc,uint32_t dec){
 if(i>=4||!ready||axes[i].active||axes[i].fault)return 0;
 if(rpm<1||rpm>200||acc<1||acc>400||dec<1||dec>400)return 0;
 Axis *a=&axes[i];
 a->direction=direction<0;HAL_GPIO_WritePin(dir_ports[i],dir_pins[i],a->direction?GPIO_PIN_SET:GPIO_PIN_RESET);HAL_Delay(1);
 __disable_irq();
 a->emitted=0;a->target=UINT32_MAX;a->velocity=0;a->segment_step=0;a->phase=0;a->stop_requested=0;a->speed_mode=1;
 a->speed_target=rpm*(float)MOTOR_PULSES_PER_REV/60;a->speed_accel=acc*(float)MOTOR_PULSES_PER_REV/60;
 a->plan.d=dec*(float)MOTOR_PULSES_PER_REV/60;
 a->next_velocity=fminf(a->speed_target,sqrtf(2*a->speed_accel));
 a->period_us=(uint32_t)(2000000.0f/a->next_velocity+0.5f);a->wait_remaining=a->period_us;
 HAL_TIM_OC_Stop_IT(&htim8,i*4U);oc_mode(i,TIM_OCMODE_FORCED_INACTIVE);
 a->compare_tick=(uint16_t)TIM8->CNT;__HAL_TIM_CLEAR_FLAG(&htim8,TIM_FLAG_CC1<<i);a->active=1;
 schedule_wait(i);if(a->active&&HAL_TIM_OC_Start_IT(&htim8,i*4U)!=HAL_OK)finish(i,2);
 __enable_irq();return a->active!=0;
}
void HAL_TIM_OC_DelayElapsedCallback(TIM_HandleTypeDef *h){
 if(h->Instance!=TIM8)return;
 unsigned i;for(i=0;i<4;i++)if(h->Channel==(HAL_TIM_ACTIVE_CHANNEL_1<<i))break;
 if(i==4||!axes[i].active)return;
 Axis *a=&axes[i];uint32_t begin=DWT->CYCCNT;
 if(a->phase==0){
  if(a->wait_remaining)schedule_wait(i);
  else{a->emitted++;a->segment_step++;a->position+=a->direction?-1:1;a->velocity=a->next_velocity;a->phase=1;schedule(i,PULSE_US,TIM_OCMODE_TOGGLE);}
 }else{
  if(a->emitted>=a->target)finish(i,0);
  else{
   if(a->speed_mode){
    int64_t room=a->direction?(int64_t)a->position-INT32_MIN:(int64_t)INT32_MAX-a->position;
    if(room<=(int64_t)ceilf(a->velocity*a->velocity/(2*a->plan.d))+2)a->stop_requested=1;
   }
   if(a->stop_requested){
    a->stop_requested=0;uint32_t n=(uint32_t)ceilf(a->velocity*a->velocity/(2*a->plan.d));
    uint32_t remaining=a->target-a->emitted;if(n<1)n=1;if(n>remaining)n=remaining;
    if(a->velocity<1){finish(i,0);return;}
    float v=a->velocity;plan_stop(&a->plan,n,v);a->target=a->emitted+n;a->segment_step=0;a->previous_us=0;a->speed_mode=0;
   }
   uint32_t interval;
   if(a->speed_mode){
    a->next_velocity=fminf(a->speed_target,sqrtf(a->velocity*a->velocity+2*a->speed_accel));
    interval=(uint32_t)(2000000.0f/(a->velocity+a->next_velocity)+0.5f);
   }else{
    uint32_t next=plan_time_us(&a->plan,a->segment_step+1,&a->next_velocity);
    interval=next-a->previous_us;a->previous_us=next;
   }
   a->period_us=interval;a->phase=0;
   if(interval<=PULSE_US+8)finish(i,3);else{a->wait_remaining=interval-PULSE_US;schedule_wait(i);}
  }
 }
 uint32_t cycles=DWT->CYCCNT-begin;if(cycles>a->isr_max_cycles)a->isr_max_cycles=cycles;
}
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *h)
{
 if(h->Instance!=USART1)return;
 uint16_t next=(rx_head+1)&(RX_CAP-1);
 if(next==rx_tail)rx_overflow=1;else{rx_ring[rx_head]=(char)rx_byte;__DMB();rx_head=next;}
 HAL_UART_Receive_IT(&huart1,&rx_byte,1);
}
void HAL_UART_ErrorCallback(UART_HandleTypeDef *h)
{
 if(h->Instance==USART1){rx_overflow=1;HAL_UART_AbortReceive_IT(h);HAL_UART_Receive_IT(h,&rx_byte,1);}
}

static void status(unsigned i){
 char out[220];uint32_t active,fault,n,total,done,period,speed;int32_t pos;float v;
 __disable_irq();Axis *a=&axes[i];active=a->active;fault=a->fault;n=a->emitted;total=a->target;pos=a->position;v=a->velocity;done=a->done_counter;period=a->period_us;speed=a->speed_mode;__enable_irq();
 snprintf(out,sizeof(out),"STATE %u %s POS=%ld PULSES=%lu/%lu RPM_MILLI=%lu FAULT=%lu DONE=%lu T=%lu MODE=%s PUL_HZ_MILLI=%lu\r\n",i+1,active?"RUNNING":"IDLE",(long)pos,(unsigned long)n,(unsigned long)total,(unsigned long)(v*60000/MOTOR_PULSES_PER_REV),(unsigned long)fault,(unsigned long)done,(unsigned long)HAL_GetTick(),speed?"SPEED":"POSITION",(unsigned long)(active&&period?1000000000UL/period:0));send_text(out);
}
static void ack(const char *action,unsigned i){char out[48];snprintf(out,sizeof(out),"OK %s %u\r\n",action,i+1);send_text(out);}
static void reject(const char *reason,unsigned i){char out[48];snprintf(out,sizeof(out),"ERR %s %u\r\n",reason,i+1);send_text(out);}
static int number(const char *text,long *value){char *end;errno=0;*value=strtol(text,&end,10);return errno!=ERANGE&&end!=text&&!*end;}
static void request_stop_all(void){for(unsigned i=0;i<4;i++)axes[i].stop_requested=1;}
static void parameters(unsigned i){
 AxisParams *p=&axis_params[i];char out[150];
 snprintf(out,sizeof(out),"PARAM %u STEPS=%lu RPM=%lu ACC=%lu DEC=%lu CURVE=%s REV=%lu\r\n",i+1,(unsigned long)p->steps,(unsigned long)p->rpm,(unsigned long)p->accel,(unsigned long)p->decel,p->curve?"S":"TRAP",(unsigned long)p->revision);send_text(out);
}
static void command(char *line){
 char *t[9],*save=NULL;unsigned count=0;
 for(char *p=strtok_r(line," \t",&save);p&&count<9;p=strtok_r(NULL," \t",&save))t[count++]=p;
 if(!count)return;
 if(count==1&&!strcmp(t[0],"HELLO")){send_text("HELLO YS_F4Pro AXES=4 PROTO=4 PARAMS=1 PPR=3200 RPM_MAX=200 ACC_MAX=400 STEPS_MAX=32000 SPEED=1\r\n");return;}
 if(count==1&&!strcmp(t[0],"PING")){send_text("OK PING\r\n");return;}
 if(count==1&&!strcmp(t[0],"HELP")){send_text("SET axis steps rpm accel decel TRAP|S; GET axis; RUN axis direction; STATUS [axis]; STOP axis|ALL; CLEAR axis; ZERO axis; WATCHDOG 0|1500\r\n");return;}
 if(!strcmp(t[0],"WATCHDOG")&&count==2){long ms;if(!number(t[1],&ms)||(ms!=0&&ms!=1500)){send_text("ERR WATCHDOG\r\n");return;}watchdog_ms=(uint32_t)ms;g_link_timeout=0;send_text("OK WATCHDOG\r\n");return;}
 if(count==1&&!strcmp(t[0],"STATUS")){for(unsigned i=0;i<4;i++)status(i);return;}
 if(count==2&&!strcmp(t[0],"STOP")&&!strcmp(t[1],"ALL")){request_stop_all();send_text("OK STOP ALL\r\n");return;}
 unsigned i=0;long axis=1;
 if(!strcmp(t[0],"GET")||!strcmp(t[0],"SET")||!strcmp(t[0],"RUN")||!strcmp(t[0],"SPEED")){
  if(count<2||!number(t[1],&axis)||axis<1||axis>4){send_text("ERR AXIS\r\n");return;}i=(unsigned)(axis-1);
  if(!strcmp(t[0],"GET")&&count==2){parameters(i);return;}
  if(axes[i].active){reject("BUSY",i);return;}
  if(!strcmp(t[0],"SPEED")&&count==6){
   long direction,rpm,acc,dec;
   if(!number(t[2],&direction)||(direction!=1&&direction!=-1)||!number(t[3],&rpm)||!number(t[4],&acc)||!number(t[5],&dec)||rpm<1||rpm>200||acc<1||acc>400||dec<1||dec>400){reject("RANGE",i);return;}
   int64_t room=direction<0?(int64_t)axes[i].position-INT32_MIN:(int64_t)INT32_MAX-axes[i].position;
   if(room<=(int64_t)ceilf((rpm*(float)MOTOR_PULSES_PER_REV/60)*(rpm*(float)MOTOR_PULSES_PER_REV/60)/(2*dec*(float)MOTOR_PULSES_PER_REV/60))+4){reject("POSITION_LIMIT",i);return;}
   if(speed_start(i,(int)direction,(uint32_t)rpm,(uint32_t)acc,(uint32_t)dec))ack("SPEED",i);else reject("RANGE_OR_FAULT",i);return;
  }
  if(!strcmp(t[0],"SET")&&count==7){
   long v[4];for(unsigned j=0;j<4;j++)if(!number(t[j+2],&v[j])){reject("NUMBER",i);return;}
   if(v[0]<1||v[0]>32000||v[1]<1||v[1]>200||v[2]<1||v[2]>400||v[3]<1||v[3]>400){reject("RANGE",i);return;}
   if(strcmp(t[6],"TRAP")&&strcmp(t[6],"S")){reject("CURVE",i);return;}
   uint8_t curve=!strcmp(t[6],"S");MotionPlan check;
   if(!plan_move(&check,(uint32_t)v[0],(float)v[1],(float)v[2],(float)v[3],curve)){reject("RANGE",i);return;}
   AxisParams *p=&axis_params[i];p->steps=v[0];p->rpm=v[1];p->accel=v[2];p->decel=v[3];p->curve=curve;p->revision++;
   ack("SET",i);parameters(i);return;
  }
  if(!strcmp(t[0],"RUN")&&count==3){
   long direction;if(!number(t[2],&direction)||(direction!=1&&direction!=-1)){reject("DIRECTION",i);return;}
   AxisParams *p=&axis_params[i];
   if(move_start(i,(int32_t)p->steps*(int32_t)direction,p->rpm,p->accel,p->decel,p->curve))ack("RUN",i);else reject("RANGE_OR_FAULT",i);
   return;
  }
  send_text("ERR COMMAND\r\n");return;
 }
 /* Legacy single-axis MOVE/STOP/ZERO/CLEAR remains on axis 1. */
 if(!strcmp(t[0],"MOVE")){
  unsigned start=count==6?1:2;
  if(count!=6&&count!=7){send_text("ERR COMMAND\r\n");return;}
  if(count==7&&(!number(t[1],&axis)||axis<1||axis>4)){send_text("ERR AXIS\r\n");return;}i=(unsigned)(axis-1);
  long v[4];for(unsigned j=0;j<4;j++)if(!number(t[start+j],&v[j])){reject("NUMBER",i);return;}
  if(v[1]<1||v[1]>200||v[2]<1||v[2]>400||v[3]<1||v[3]>400){reject("RANGE",i);return;}
  char *curve=t[start+4];if(strcmp(curve,"TRAP")&&strcmp(curve,"S")){reject("CURVE",i);return;}
  if(axes[i].active){reject("BUSY",i);return;}
  if(move_start(i,(int32_t)v[0],(uint32_t)v[1],(uint32_t)v[2],(uint32_t)v[3],!strcmp(curve,"S")))ack("MOVE",i);else reject("RANGE_OR_FAULT",i);
  return;
 }
 if(count==2){if(!number(t[1],&axis)||axis<1||axis>4){send_text("ERR AXIS\r\n");return;}i=(unsigned)(axis-1);}
 else if(count!=1){send_text("ERR COMMAND\r\n");return;}
 if(!strcmp(t[0],"STATUS")){status(i);return;}
 if(!strcmp(t[0],"STOP")){axes[i].stop_requested=1;ack("STOP",i);return;}
 if(!strcmp(t[0],"CLEAR")||!strcmp(t[0],"ZERO")){
  if(axes[i].active){reject("BUSY",i);return;}
  if(!strcmp(t[0],"CLEAR"))axes[i].fault=0;else axes[i].position=0;ack(t[0],i);return;
 }
 send_text("ERR COMMAND\r\n");
}
static void serial_poll(void){
 static char line[112];static unsigned len;static uint8_t discard;
 /* Discard the entire buffered burst on overflow: no partial MOVE can execute. */
 if(rx_overflow){__disable_irq();rx_tail=rx_head;rx_overflow=0;__enable_irq();discard=1;len=0;}
 while(rx_tail!=rx_head){char c=rx_ring[rx_tail];rx_tail=(rx_tail+1)&(RX_CAP-1);
  if(c=='\r')continue;
  if(c=='\n'){if(discard)send_text("ERR LINE\r\n");else if(len){line[len]=0;last_command_ms=HAL_GetTick();g_link_timeout=0;command(line);}len=0;discard=0;}
  else if(!discard){if(c<32||c>126||len>=sizeof(line)-1){discard=1;len=0;}else line[len++]=c;}
 }
}
static void keys_poll(void)
{
 static uint8_t initialized,stable,last;static uint32_t changed;
 uint8_t sample=(uint8_t)(GPIOE->IDR&15);uint32_t now=HAL_GetTick();
 if(!initialized){initialized=1;stable=last=sample;changed=now;return;}
 if(sample!=last){last=sample;changed=now;}
 if(sample!=stable && now-changed>=30){uint8_t pressed=stable&~sample;stable=sample;
  if(pressed&2){axes[0].stop_requested=1;return;} /* KEY2 takes priority. */
  if(pressed&1){if(move_start(0,MOTOR_PULSES_PER_REV,30,30,30,0))send_text("OK KEY1 TRAP FORWARD\r\n");}
  else if(pressed&4){if(move_start(0,-(int32_t)MOTOR_PULSES_PER_REV,30,30,30,0))send_text("OK KEY3 TRAP REVERSE\r\n");}
  else if(pressed&8){if(move_start(0,MOTOR_PULSES_PER_REV,30,30,30,1))send_text("OK KEY4 S FORWARD\r\n");}
 }
}

#ifdef MOTION_ENGINE_TEST
static uint32_t engine_test(void){
 uint32_t mask=(3U<<4)|(3U<<10)|(3U<<12)|(3U<<14);
 uint32_t expected=(1U<<4)|(1U<<10)|(1U<<12)|(1U<<14);
 if((GPIOI->MODER&mask)!=expected || (GPIOI->ODR&(GPIO_PIN_2|GPIO_PIN_5|GPIO_PIN_6|GPIO_PIN_7)))return 100;
 for(unsigned i=0;i<4;i++)if(!move_start(i,i==2?-3200:3200,60,120,120,i==3))return 110+i;
 HAL_Delay(100);axes[1].stop_requested=1;HAL_Delay(400);
 if(axes[1].active||!axes[0].active||!axes[2].active||!axes[3].active)return 120;
 for(unsigned i=0;i<4;i++)if(axes[i].fault)return 130+i;
 g_test_stop_position=(uint32_t)axes[1].position;
 if(!move_start(1,-1600,60,120,120,1))return 140;
 uint32_t start=HAL_GetTick();
 while(axes[0].active||axes[1].active||axes[2].active||axes[3].active){if(HAL_GetTick()-start>6000)return 150;}
 for(unsigned i=0;i<4;i++)if(axes[i].fault)return 160+i;
 if(axes[0].position!=3200||axes[2].position!=-3200||axes[3].position!=3200||axes[1].position!=(int32_t)g_test_stop_position-1600)return 170;
 if(axes[1].done_counter!=2||axes[0].done_counter!=1||axes[2].done_counter!=1||axes[3].done_counter!=1)return 180;
 if(TIM8->CR1&TIM_CR1_CEN)return 190;
 for(unsigned i=0;i<4;i++)if(!speed_start(i,i&1?-1:1,200,400,400))return 200+i;
 HAL_Delay(800);
 for(unsigned i=0;i<4;i++)if(!axes[i].active||axes[i].fault||fabsf(axes[i].velocity-10666.667f)>0.1f||axes[i].period_us<93||axes[i].period_us>94)return 210+i;
 request_stop_all();HAL_Delay(700);
 for(unsigned i=0;i<4;i++)if(axes[i].active||axes[i].fault)return 220+i;
 if(GPIOI->ODR&(GPIO_PIN_2|GPIO_PIN_5|GPIO_PIN_6|GPIO_PIN_7))return 230;
 for(unsigned i=0;i<4;i++)if(!move_start(i,32000,200,400,400,i&1))return 240+i;
 start=HAL_GetTick();
 while(axes[0].active||axes[1].active||axes[2].active||axes[3].active){if(HAL_GetTick()-start>8000)return 250;}
 for(unsigned i=0;i<4;i++)if(axes[i].fault||axes[i].emitted!=32000)return 260+i;
 return 0;
}
#endif
int main(void){
 HAL_Init();clock_init();g_motion_selftest_result=motion_selftest();if(g_motion_selftest_result)Error_Handler();hardware_init();
 send_text("YS-F4Pro HAL STEPPER v4 AXES=4 PROTO=4 PARAMS_RAM NO_AUTOSTART\r\n");
#ifdef MOTION_ENGINE_TEST
 g_engine_test_result=engine_test();
 if(g_engine_test_result)Fault_Stop();
 while(1){g_uptime_ms=HAL_GetTick();}
#endif
 uint32_t blink=HAL_GetTick(),done[4]={0};last_command_ms=HAL_GetTick();
 while(1){
  g_uptime_ms=HAL_GetTick();serial_poll();keys_poll();
  if(watchdog_ms&&!g_link_timeout&&HAL_GetTick()-last_command_ms>watchdog_ms){request_stop_all();g_link_timeout=1;}
  for(unsigned i=0;i<4;i++)if(axes[i].done_counter!=done[i]){done[i]=axes[i].done_counter;status(i);}
  if(HAL_GetTick()-blink>=500){blink=HAL_GetTick();HAL_GPIO_TogglePin(GPIOH,GPIO_PIN_9);}
 }
}

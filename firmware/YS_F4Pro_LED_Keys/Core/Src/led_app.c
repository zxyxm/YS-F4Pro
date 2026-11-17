#include "main.h"
#include "bsp_led.h"
#include "led_app.h"
#include <string.h>
#include <stdlib.h>
#include <errno.h>

volatile uint8_t g_led_index, g_paused, g_manual;
volatile int8_t g_direction=1;
volatile uint32_t g_interval_ms=300, g_key_events;
volatile uint32_t g_cycles, g_flow_steps;
static uint32_t last_step;

uint8_t LED_App_Mask(void){
    return ((GPIOH->ODR&GPIO_PIN_9)?1:0)|((GPIOE->ODR&GPIO_PIN_5)?2:0)|((GPIOE->ODR&GPIO_PIN_6)?4:0);
}
static void mask_set(uint8_t mask){
    HAL_GPIO_WritePin(GPIOH,GPIO_PIN_9,(mask&1)?GPIO_PIN_SET:GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOE,GPIO_PIN_5,(mask&2)?GPIO_PIN_SET:GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOE,GPIO_PIN_6,(mask&4)?GPIO_PIN_SET:GPIO_PIN_RESET);
}
void LED_App_Init(void){
    g_led_index=0;g_paused=0;g_manual=0;g_direction=1;g_interval_ms=300;
    g_cycles=0;g_flow_steps=0;
    LED_Show(0);last_step=HAL_GetTick();
}
static void restart(void){
    g_led_index=0;g_flow_steps=0;g_manual=0;g_paused=0;
    LED_Show(0);last_step=HAL_GetTick();
}
void LED_App_Tick(void){
    uint32_t now=HAL_GetTick();
    if(!g_manual&&!g_paused&&(uint32_t)(now-last_step)>=g_interval_ms){
        last_step=now;
        /* Three complete lamp dwell intervals constitute one cycle. */
        if(g_flow_steps<UINT32_MAX)g_flow_steps++;
        if(g_cycles&&g_flow_steps>=g_cycles*3U){g_paused=1;mask_set(0);return;}
        g_led_index=g_direction>0?(g_led_index+1U)%3U:(g_led_index+2U)%3U;LED_Show(g_led_index);
    }
}
void LED_App_Keys(uint8_t keys){
    if(!keys)return;
    g_key_events++;
    if(keys&16){LED_App_Init();return;}
    if(keys&1){if(g_manual||!LED_App_Mask()||(g_cycles&&g_flow_steps>=g_cycles*3U)){restart();}else g_paused^=1;}
    if(keys&2)g_direction=-g_direction;
    if((keys&4)&&g_interval_ms>100)g_interval_ms=g_interval_ms>200?g_interval_ms-100:100;
    if((keys&8)&&g_interval_ms<1000)g_interval_ms=g_interval_ms<900?g_interval_ms+100:1000;
    last_step=HAL_GetTick();
}
static int number(const char *s,long *v){char *end;errno=0;*v=strtol(s,&end,10);return errno!=ERANGE&&end!=s&&!*end;}
int LED_App_Command(char *line){
    char *t[6],*save=NULL;unsigned n=0;
    for(char *p=strtok_r(line," \t",&save);p&&n<6;p=strtok_r(NULL," \t",&save))t[n++]=p;
    if(n==1&&!strcmp(t[0],"RESET")){LED_App_Init();return 1;}
    if(n==3&&!strcmp(t[0],"LED")){
        long led;if(!number(t[1],&led)||led<1||led>3)return 0;
        if(strcmp(t[2],"ON")&&strcmp(t[2],"OFF"))return 0;
        uint8_t mask=LED_App_Mask();g_manual=1;g_paused=1;
        if(!strcmp(t[2],"ON"))mask|=1U<<(led-1);else mask&=~(1U<<(led-1));
        mask_set(mask);return 1;
    }
    if(n==2&&!strcmp(t[0],"ALL")&&(!strcmp(t[1],"ON")||!strcmp(t[1],"OFF"))){g_manual=1;g_paused=1;mask_set(!strcmp(t[1],"ON")?7:0);return 1;}
    if(n>=2&&!strcmp(t[0],"FLOW")){
        if(n==2&&!strcmp(t[1],"RESTART")){restart();return 1;}
        if(n==2&&!strcmp(t[1],"STOP")){g_manual=0;g_paused=1;g_flow_steps=0;g_led_index=0;mask_set(0);return 1;}
        if(n==5&&!strcmp(t[1],"CONFIG")){
            long ms,dir,cycles;
            if(!number(t[2],&ms)||ms<50||ms>60000||!number(t[3],&dir)||(dir!=1&&dir!=-1)||!number(t[4],&cycles)||cycles<0||cycles>9999)return 0;
            g_interval_ms=(uint32_t)ms;g_direction=(int8_t)dir;g_cycles=(uint32_t)cycles;
            /* Applying settings leaves the outputs unchanged and pauses the run. */
            g_paused=1;g_flow_steps=0;last_step=HAL_GetTick();return 1;
        }
        if(n==2&&(!strcmp(t[1],"START")||!strcmp(t[1],"PAUSE"))){
            if(!strcmp(t[1],"START")&&(g_manual||(g_cycles&&g_flow_steps>=g_cycles*3U)||!LED_App_Mask())){restart();return 1;}
            if(g_manual)LED_Show(g_led_index);
            g_manual=0;g_paused=!strcmp(t[1],"PAUSE");last_step=HAL_GetTick();return 1;
        }
        long value;
        if(n==3&&number(t[2],&value)){
            if(!strcmp(t[1],"DIR")&&(value==1||value==-1)){g_direction=(int8_t)value;return 1;}
            if(!strcmp(t[1],"MS")&&value>=50&&value<=60000){g_interval_ms=(uint32_t)value;last_step=HAL_GetTick();return 1;}
        }
    }
    return 0;
}

#ifndef LED_APP_H
#define LED_APP_H
#include <stdint.h>
extern volatile uint8_t g_led_index, g_paused, g_manual;
extern volatile int8_t g_direction;
extern volatile uint32_t g_interval_ms, g_key_events;
extern volatile uint32_t g_cycles, g_flow_steps;
void LED_App_Init(void);
void LED_App_Tick(void);
void LED_App_Keys(uint8_t keys);
int LED_App_Command(char *line);
uint8_t LED_App_Mask(void);
#endif

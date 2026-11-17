#ifndef BSP_LED_H
#define BSP_LED_H
#include <stdint.h>
/* LED index: 0=PH9, 1=PE5, 2=PE6. HIGH turns the LED on. */
void LED_AllOff(void);
void LED_AllOn(void);
void LED_Show(uint8_t index);
#endif

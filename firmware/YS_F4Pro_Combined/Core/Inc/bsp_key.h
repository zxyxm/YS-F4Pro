#ifndef BSP_KEY_H
#define BSP_KEY_H
#include <stdint.h>
void Keys_Init(void);
/* Debounced press events, bits 0..4 = KEY1..KEY5; held keys do not repeat. */
uint8_t Keys_Poll(void);
#endif

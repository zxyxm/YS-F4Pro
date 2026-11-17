#include "main.h"
#include "bsp_key.h"

#define DEBOUNCE_MS 25U
static uint8_t stable[5];
static uint8_t candidate[5];
static uint32_t changed_at[5];

void Keys_Init(void)
{
    uint32_t now = HAL_GetTick();
    for (uint8_t i = 0; i < 5; i++) {
        /* A button already held during power-up must be released first. */
        stable[i] = candidate[i] = (GPIOE->IDR >> i) & 1U;
        changed_at[i] = now;
    }
}

uint8_t Keys_Poll(void)
{
    uint8_t events = 0;
    uint32_t now = HAL_GetTick();
    for (uint8_t i = 0; i < 5; i++) {
        uint8_t sample = (GPIOE->IDR >> i) & 1U;
        if (sample != candidate[i]) {
            candidate[i] = sample;
            changed_at[i] = now;
        }
        if (candidate[i] != stable[i] && (uint32_t)(now - changed_at[i]) >= DEBOUNCE_MS) {
            stable[i] = candidate[i];
            if (stable[i] == 0) {
                events |= (uint8_t)(1U << i);
            }
        }
    }
    return events;
}

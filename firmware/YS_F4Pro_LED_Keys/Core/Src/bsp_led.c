#include "main.h"
#include "bsp_led.h"

void LED_AllOff(void)
{
    HAL_GPIO_WritePin(GPIOH, GPIO_PIN_9, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOE, GPIO_PIN_5 | GPIO_PIN_6, GPIO_PIN_RESET);
}

void LED_AllOn(void)
{
    HAL_GPIO_WritePin(GPIOH, GPIO_PIN_9, GPIO_PIN_SET);
    HAL_GPIO_WritePin(GPIOE, GPIO_PIN_5 | GPIO_PIN_6, GPIO_PIN_SET);
}

void LED_Show(uint8_t index)
{
    LED_AllOff();
    if (index == 0) {
        HAL_GPIO_WritePin(GPIOH, GPIO_PIN_9, GPIO_PIN_SET);
    } else if (index == 1) {
        HAL_GPIO_WritePin(GPIOE, GPIO_PIN_5, GPIO_PIN_SET);
    } else if (index == 2) {
        HAL_GPIO_WritePin(GPIOE, GPIO_PIN_6, GPIO_PIN_SET);
    }
}

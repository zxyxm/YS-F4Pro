#include <stdint.h>
extern uint32_t _sidata,_sdata,_edata,_sbss,_ebss,_estack;
extern void SystemInit(void); extern int main(void);
extern void Error_Handler(void);
void Default_Handler(void) { Error_Handler(); while(1) {} }
void Reset_Handler(void) {
 uint32_t *s=&_sidata; for(uint32_t *d=&_sdata;d<&_edata;) *d++=*s++;
 for(uint32_t *d=&_sbss;d<&_ebss;) *d++=0;
 SystemInit(); main(); while(1) {}
}
extern void SysTick_Handler(void);
void WWDG_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void PVD_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void TAMP_STAMP_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void RTC_WKUP_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void FLASH_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void RCC_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void EXTI0_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void EXTI1_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void EXTI2_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void EXTI3_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void EXTI4_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void DMA1_Stream0_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void DMA1_Stream1_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void DMA1_Stream2_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void DMA1_Stream3_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void DMA1_Stream4_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void DMA1_Stream5_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void DMA1_Stream6_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void ADC_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void CAN1_TX_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void CAN1_RX0_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void CAN1_RX1_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void CAN1_SCE_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void EXTI9_5_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void TIM1_BRK_TIM9_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void TIM1_UP_TIM10_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void TIM1_TRG_COM_TIM11_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void TIM1_CC_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void TIM2_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void TIM3_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void TIM4_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void I2C1_EV_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void I2C1_ER_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void I2C2_EV_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void I2C2_ER_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void SPI1_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void SPI2_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void USART1_IRQHandler(void);
void USART2_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void USART3_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void EXTI15_10_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void RTC_Alarm_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void OTG_FS_WKUP_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void TIM8_BRK_TIM12_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void TIM8_UP_TIM13_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void TIM8_TRG_COM_TIM14_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void TIM8_CC_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void DMA1_Stream7_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void FSMC_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void SDIO_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void TIM5_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void SPI3_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void UART4_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void UART5_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void TIM6_DAC_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void TIM7_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void DMA2_Stream0_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void DMA2_Stream1_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void DMA2_Stream2_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void DMA2_Stream3_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void DMA2_Stream4_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void ETH_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void ETH_WKUP_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void CAN2_TX_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void CAN2_RX0_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void CAN2_RX1_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void CAN2_SCE_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void OTG_FS_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void DMA2_Stream5_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void DMA2_Stream6_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void DMA2_Stream7_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void USART6_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void I2C3_EV_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void I2C3_ER_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void OTG_HS_EP1_OUT_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void OTG_HS_EP1_IN_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void OTG_HS_WKUP_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void OTG_HS_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void DCMI_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void RNG_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
void FPU_IRQHandler(void) __attribute__((weak,alias("Default_Handler")));
__attribute__((section(".isr_vector"),used)) const uintptr_t vectors[98] = {
[0]=(uintptr_t)&_estack,[1]=(uintptr_t)Reset_Handler,
[2]=(uintptr_t)Default_Handler,
[3]=(uintptr_t)Default_Handler,
[4]=(uintptr_t)Default_Handler,
[5]=(uintptr_t)Default_Handler,
[6]=(uintptr_t)Default_Handler,
[11]=(uintptr_t)Default_Handler,
[12]=(uintptr_t)Default_Handler,
[14]=(uintptr_t)Default_Handler,
[15]=(uintptr_t)SysTick_Handler,
[16]=(uintptr_t)WWDG_IRQHandler,
[17]=(uintptr_t)PVD_IRQHandler,
[18]=(uintptr_t)TAMP_STAMP_IRQHandler,
[19]=(uintptr_t)RTC_WKUP_IRQHandler,
[20]=(uintptr_t)FLASH_IRQHandler,
[21]=(uintptr_t)RCC_IRQHandler,
[22]=(uintptr_t)EXTI0_IRQHandler,
[23]=(uintptr_t)EXTI1_IRQHandler,
[24]=(uintptr_t)EXTI2_IRQHandler,
[25]=(uintptr_t)EXTI3_IRQHandler,
[26]=(uintptr_t)EXTI4_IRQHandler,
[27]=(uintptr_t)DMA1_Stream0_IRQHandler,
[28]=(uintptr_t)DMA1_Stream1_IRQHandler,
[29]=(uintptr_t)DMA1_Stream2_IRQHandler,
[30]=(uintptr_t)DMA1_Stream3_IRQHandler,
[31]=(uintptr_t)DMA1_Stream4_IRQHandler,
[32]=(uintptr_t)DMA1_Stream5_IRQHandler,
[33]=(uintptr_t)DMA1_Stream6_IRQHandler,
[34]=(uintptr_t)ADC_IRQHandler,
[35]=(uintptr_t)CAN1_TX_IRQHandler,
[36]=(uintptr_t)CAN1_RX0_IRQHandler,
[37]=(uintptr_t)CAN1_RX1_IRQHandler,
[38]=(uintptr_t)CAN1_SCE_IRQHandler,
[39]=(uintptr_t)EXTI9_5_IRQHandler,
[40]=(uintptr_t)TIM1_BRK_TIM9_IRQHandler,
[41]=(uintptr_t)TIM1_UP_TIM10_IRQHandler,
[42]=(uintptr_t)TIM1_TRG_COM_TIM11_IRQHandler,
[43]=(uintptr_t)TIM1_CC_IRQHandler,
[44]=(uintptr_t)TIM2_IRQHandler,
[45]=(uintptr_t)TIM3_IRQHandler,
[46]=(uintptr_t)TIM4_IRQHandler,
[47]=(uintptr_t)I2C1_EV_IRQHandler,
[48]=(uintptr_t)I2C1_ER_IRQHandler,
[49]=(uintptr_t)I2C2_EV_IRQHandler,
[50]=(uintptr_t)I2C2_ER_IRQHandler,
[51]=(uintptr_t)SPI1_IRQHandler,
[52]=(uintptr_t)SPI2_IRQHandler,
[53]=(uintptr_t)USART1_IRQHandler,
[54]=(uintptr_t)USART2_IRQHandler,
[55]=(uintptr_t)USART3_IRQHandler,
[56]=(uintptr_t)EXTI15_10_IRQHandler,
[57]=(uintptr_t)RTC_Alarm_IRQHandler,
[58]=(uintptr_t)OTG_FS_WKUP_IRQHandler,
[59]=(uintptr_t)TIM8_BRK_TIM12_IRQHandler,
[60]=(uintptr_t)TIM8_UP_TIM13_IRQHandler,
[61]=(uintptr_t)TIM8_TRG_COM_TIM14_IRQHandler,
[62]=(uintptr_t)TIM8_CC_IRQHandler,
[63]=(uintptr_t)DMA1_Stream7_IRQHandler,
[64]=(uintptr_t)FSMC_IRQHandler,
[65]=(uintptr_t)SDIO_IRQHandler,
[66]=(uintptr_t)TIM5_IRQHandler,
[67]=(uintptr_t)SPI3_IRQHandler,
[68]=(uintptr_t)UART4_IRQHandler,
[69]=(uintptr_t)UART5_IRQHandler,
[70]=(uintptr_t)TIM6_DAC_IRQHandler,
[71]=(uintptr_t)TIM7_IRQHandler,
[72]=(uintptr_t)DMA2_Stream0_IRQHandler,
[73]=(uintptr_t)DMA2_Stream1_IRQHandler,
[74]=(uintptr_t)DMA2_Stream2_IRQHandler,
[75]=(uintptr_t)DMA2_Stream3_IRQHandler,
[76]=(uintptr_t)DMA2_Stream4_IRQHandler,
[77]=(uintptr_t)ETH_IRQHandler,
[78]=(uintptr_t)ETH_WKUP_IRQHandler,
[79]=(uintptr_t)CAN2_TX_IRQHandler,
[80]=(uintptr_t)CAN2_RX0_IRQHandler,
[81]=(uintptr_t)CAN2_RX1_IRQHandler,
[82]=(uintptr_t)CAN2_SCE_IRQHandler,
[83]=(uintptr_t)OTG_FS_IRQHandler,
[84]=(uintptr_t)DMA2_Stream5_IRQHandler,
[85]=(uintptr_t)DMA2_Stream6_IRQHandler,
[86]=(uintptr_t)DMA2_Stream7_IRQHandler,
[87]=(uintptr_t)USART6_IRQHandler,
[88]=(uintptr_t)I2C3_EV_IRQHandler,
[89]=(uintptr_t)I2C3_ER_IRQHandler,
[90]=(uintptr_t)OTG_HS_EP1_OUT_IRQHandler,
[91]=(uintptr_t)OTG_HS_EP1_IN_IRQHandler,
[92]=(uintptr_t)OTG_HS_WKUP_IRQHandler,
[93]=(uintptr_t)OTG_HS_IRQHandler,
[94]=(uintptr_t)DCMI_IRQHandler,
[96]=(uintptr_t)RNG_IRQHandler,
[97]=(uintptr_t)FPU_IRQHandler,
};

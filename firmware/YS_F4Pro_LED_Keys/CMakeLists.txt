cmake_minimum_required(VERSION 3.22)
project(YS_F4Pro_LED_Keys C)
set(CMAKE_C_STANDARD 11)
set(HAL_DIR Drivers/STM32F4xx_HAL_Driver)
set(HAL_SOURCES
    ${HAL_DIR}/Src/stm32f4xx_hal_uart.c
    ${HAL_DIR}/Src/stm32f4xx_hal_dma.c
    ${HAL_DIR}/Src/stm32f4xx_hal.c
    ${HAL_DIR}/Src/stm32f4xx_hal_cortex.c
    ${HAL_DIR}/Src/stm32f4xx_hal_gpio.c
    ${HAL_DIR}/Src/stm32f4xx_hal_rcc.c
    ${HAL_DIR}/Src/stm32f4xx_hal_rcc_ex.c
    ${HAL_DIR}/Src/stm32f4xx_hal_flash.c
    ${HAL_DIR}/Src/stm32f4xx_hal_flash_ex.c
    ${HAL_DIR}/Src/stm32f4xx_hal_pwr.c
    ${HAL_DIR}/Src/stm32f4xx_hal_pwr_ex.c)
add_executable(${PROJECT_NAME}.elf
    Core/Src/main.c Core/Src/gpio.c Core/Src/bsp_led.c Core/Src/bsp_key.c
    Core/Src/led_app.c Core/Src/led_serial.c
    Core/Src/stm32f4xx_it.c Core/Src/stm32f4xx_hal_msp.c
    Core/Src/startup.c Core/Src/system_stm32f4xx.c ${HAL_SOURCES})
target_include_directories(${PROJECT_NAME}.elf PRIVATE Core/Inc ${HAL_DIR}/Inc Drivers/CMSIS/Include Drivers/CMSIS/Device/ST/STM32F4xx/Include)
target_compile_definitions(${PROJECT_NAME}.elf PRIVATE USE_HAL_DRIVER STM32F407xx HSE_VALUE=8000000U)
target_compile_options(${PROJECT_NAME}.elf PRIVATE -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard -Og -g3 -ffunction-sections -fdata-sections -Wall -Wextra)
target_link_options(${PROJECT_NAME}.elf PRIVATE -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard -T${CMAKE_CURRENT_SOURCE_DIR}/STM32F407IG_FLASH.ld -nostartfiles --specs=nano.specs --specs=nosys.specs -Wl,--gc-sections -Wl,-Map=${PROJECT_NAME}.map -Wl,--print-memory-usage)
add_custom_command(TARGET ${PROJECT_NAME}.elf POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:${PROJECT_NAME}.elf> ${PROJECT_NAME}.hex
    COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:${PROJECT_NAME}.elf> ${PROJECT_NAME}.bin
    COMMAND ${CMAKE_SIZE} $<TARGET_FILE:${PROJECT_NAME}.elf>)

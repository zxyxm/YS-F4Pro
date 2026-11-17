# YS-F4Pro 流水灯与按键 HAL 例程

已增加 USART1（PB6/PB7、115200 8N1）串口控制，配套[LED 上位机说明](../../led_controller/README.md)。应用状态和按键动作现位于 led_app.c，串口收发位于 led_serial.c，支持上位机单灯开关、流水控制和状态读取。

适用：YS-F4Pro / STM32F407IGT6，外部晶振 8MHz，系统时钟 168MHz。创建日期：2026-11-14。

这是独立的 HAL + GCC/CMake 工程，包含所需 HAL/CMSIS 文件，不依赖电机工程源码。没有 CubeMX `.ioc` 或 Keil `.uvprojx`。目录采用 Core/Inc、Core/Src、Drivers 的常见组织方式。

## 功能

上电 LED1 亮，默认每 300ms 按 LED1 → LED2 → LED3 → LED1 循环，每次只点亮一个灯。

串口可设置每灯 50～60000ms、正反方向、0～9999 圈（0 为无限），有限循环结束后全部熄灭。三个灯各亮一个间隔算一圈。支持暂停/继续、从 LED1 重新开始、停止清零并熄灭，以及配置和完成圈数读取。计数在 STM32 内执行，不依赖上位机保持连接；掉电不保存设置。详细操作与报文见上位机说明。

| 按键 | 功能 |
|---|---|
| KEY1 | 暂停/继续流水灯，暂停时保持当前灯 |
| KEY2 | 切换流水方向 |
| KEY3 | 加快，每次减少 100ms，最小 100ms |
| KEY4 | 减慢，每次增加 100ms，最大 1000ms |
| KEY5 | 恢复默认：LED1、正向、300ms、继续运行 |

按键使用 25ms 独立软件去抖，只在按下时产生一次事件，长按不重复；上电已经按住的按键需释放后再按。多键同时按下时，KEY5 优先恢复默认。

主循环使用 HAL_GetTick() 时间差调度，没有阻塞等待流水间隔的 HAL_Delay()，等待下一个灯时仍能扫描按键。使用无符号时间差处理毫秒计数回绕。

## 引脚

依据开发板原理图和配套 LED/KEY 定义：

| 功能 | 引脚 | 有效电平 |
|---|---|---|
| LED1 | PH9 | 高电平亮 |
| LED2 | PE5 | 高电平亮 |
| LED3 | PE6 | 高电平亮 |
| KEY1～KEY5 | PE0～PE4 | 按下为低电平，输入上拉 |

只使用板载器件，无须外接灯或按键。例程不配置电机 PUL/DIR/EN，不含电机运动功能。

## 代码阅读顺序

```text
Core/Src/main.c                   初始化、流水灯状态和按键功能
Core/Src/gpio.c                   LED 与按键 GPIO 配置
Core/Src/bsp_led.c                点亮指定灯、全部开关
Core/Src/bsp_key.c                25ms 去抖和按下事件
Core/Src/stm32f4xx_it.c           SysTick 中断，累计系统毫秒数
Core/Src/stm32f4xx_hal_msp.c      HAL 基础底层初始化
Core/Src/startup.c                向量表及复位启动
Core/Src/system_stm32f4xx.c       ST 系统初始化
Core/Inc/stm32f4xx_hal_conf.h     启用所需 HAL 模块
```

主程序流程：HAL_Init → SystemClock_Config → MX_GPIO_Init → Keys_Init → 点亮 LED1 → 循环扫描按键并按时间切灯。

## 编译与调试

在 VS Code 中**单独打开本文件夹**，这样会使用本工程自己的 `.vscode` 配置，不会下载电机工程产物：

```powershell
code firmware/YS_F4Pro_LED_Keys
```

Ctrl+Shift+B 仅编译。F5 通过硬石 CMSIS-DAP 下载并调试，停在 main，继续运行后开始流水灯。

也可以从仓库根目录执行：

```powershell
# 只编译
powershell -NoProfile -ExecutionPolicy Bypass -File firmware/YS_F4Pro_LED_Keys/build.ps1

# 编译并刷写，执行这条会替换板上现有电机固件
powershell -NoProfile -ExecutionPolicy Bypass -File firmware/YS_F4Pro_LED_Keys/build.ps1 -Flash
```

编译产物在 build/Debug：YS_F4Pro_LED_Keys.elf、.hex、.bin、.map。工具使用此前安装的 `%LOCALAPPDATA%/STM32Tools`。

在 Watch 中查看 g_led_index、g_paused、g_direction、g_interval_ms、g_key_events，可观察按键对状态的影响。

2026-11-14 已按用户要求备份原 Flash 并刷入 LED 串口控制固件，Flash 校验通过，COM6 LED 控制及 GUI 状态读取测试通过。电机工程源码未修改，板上程序已替换为本 LED 例程；实体按键尚未由软件自动实测。

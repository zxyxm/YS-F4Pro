# LED 上下位机开发笔记

整理日期：2026-11-17。

## 硬件与连接

开发板 YS-F4Pro，STM32F407IGT6，8MHz 外部晶振、168MHz 系统时钟。LED1/2/3 对应 PH9/PE5/PE6，高电平点亮。KEY1～KEY5 为 PE0～PE4，低电平按下，软件去抖 25ms。

硬石 CMSIS-DAP 通过 SWD 下载调试；开发板 USB2 串口连接电脑，JP2 两路跳帽接通。USART1 使用 PB6 TX、PB7 RX，115200、8N1。电脑上的 COM 编号以设备管理器为准，历史联调使用 COM6。

## 项目分工与阅读顺序

上位机独立放在 [led_controller](../led_controller/)：`app.py` 负责界面，`link.py` 用后台线程收发串口、握手和轮询状态，`device.py` 校验状态并实现离线模拟，`tests` 保存测试。

下位机独立放在 [firmware/YS_F4Pro_LED_Keys](../firmware/YS_F4Pro_LED_Keys/)：先读 `Core/Src/main.c` 初始化和主循环，再读 `led_app.c` 的灯光状态机、`led_serial.c` 的串口收发和命令解析、`bsp_key.c` 的按键去抖。`Drivers` 为 HAL/CMSIS；`cmake`、链接脚本和启动代码服务于 GCC 构建。

这是 HAL + GCC/CMake 工程，采用常见 Core/Inc、Core/Src、Drivers 布局，但没有 CubeMX `.ioc` 和 Keil `.uvprojx`，不能视为可直接用 CubeMX 重新生成的工程。

## 程序如何运行

HAL_Init → 时钟配置 → GPIO 和按键初始化 → LED 应用初始化 → USART1 初始化 → 主循环反复处理串口、按键和流水计时。

主循环以 HAL_GetTick 的无符号时间差判断灯光切换，无阻塞流水延时。串口中断将字节存入环形缓冲，主循环解析完整的一行。流水计时和圈数由下位机负责，电脑关闭后照常运行。

上位机连接后先发送 HELLO，仅接受 LED 固件身份，然后周期读取 STATUS；界面显示来自板上 GPIO 输出寄存器，不是光学反馈。反馈过期时禁用操作并显示未知。

## 操作与循环定义

上电默认：正向、每灯 300ms、无限循环。从 LED1 开始，正向顺序 1→2→3，反向 1→3→2；三个灯各保持一个间隔算一圈。设置范围：每灯 50～60000ms，循环 0～9999 次，0 表示无限。

填写间隔、方向和循环次数 → 写入设置 → 重新开始。写入设置会暂停并清零圈数，保持当前输出；重新开始从 LED1 计数。暂停保持灯光和圈数，继续时当前灯重新计时一个完整间隔。有限循环完成后自动熄灭。

停止并熄灭会清零计数；单灯控制进入手动模式；恢复默认重新启用 300ms 无限流水。参数只保存 RAM，复位/断电后恢复默认。

KEY1 暂停或继续，手动/完成/熄灭状态下重新启动；KEY2 切方向；KEY3 加快；KEY4 在低于 1000ms 时减慢；KEY5 恢复默认。串口可以设置比实体按键更宽的间隔范围。

## 串口报文速查

ASCII 文本，一行一条，LF 或 CRLF 结尾。

```text
HELLO
STATUS
LED 1 ON
LED 3 OFF
ALL ON
ALL OFF
FLOW CONFIG 300 1 5
FLOW RESTART
FLOW PAUSE
FLOW START
FLOW STOP
RESET
```

CONFIG 参数依次为间隔、方向（1/-1）、循环次数；全部合法才应用。成功返回 OK 和状态，错误命令返回 ERR COMMAND。完整协议见[上位机说明](../led_controller/README.md)。

```text
HELLO YS_F4Pro_LED PROTO=1
LEDSTATE MODE=FLOW RUN=1 DIR=1 MS=300 MASK=1 KEYS=0 CYCLES=5 DONE=0
```

MASK 的低三位对应三灯，CYCLES 是目标圈数，DONE 是已完成圈数。上位机兼容旧版缺少循环字段的状态，此时禁用新增设置按钮。

## 编译、打包与验证记录

源码构建命令见[仓库首页](../README.md)。上位机依赖 pyserial 和 Tkinter，打包额外需要 PyInstaller；下位机依赖 Arm GCC、CMake、Ninja，下载依赖 OpenOCD 和 CMSIS-DAP。

2026-11-14：通过固件编译、DAP 下载校验、5 项单元测试、界面测试以及 COM6 实测，覆盖单灯/全部控制、有限/无限循环、自动熄灭、暂停/继续、重新开始、非法配置拒绝、真实界面参数读写。结束恢复默认流水。实体按键未自动实测。

源码、说明和第三方许可提交 Git；build、EXE、Python 缓存、设备日志和原始 Flash 备份保留本地。电机工程及原始开发板资料属于其他工作内容，本次 LED 提交不包含它们。

# LED 与流水灯桌面上位机

配套固件：`firmware/YS_F4Pro_LED_Keys`。固件新增 USART1 串口，原有五个实体按键保留。

双击仓库根目录“启动LED上位机.cmd”，或运行 `output/led_controller/YSF4Pro_LED_Controller.exe`。没有硬件时点击“离线演示”，不会打开串口。

## 功能

- LED1～LED3 分别点亮/熄灭、全部点亮/熄灭。
- 三列等宽显示 LED1 / PH9、LED2 / PE5、LED3 / PE6，最小窗口也可操作三个灯。
- 流水启动/暂停、重新开始、停止并熄灭、正反向、50～60000ms 每灯间隔、0～9999 次循环、恢复默认。
- 状态读取、ASCII 命令输入及收发记录。

## 流水灯设置操作

1. 连接 LED 固件后，填写每灯点亮间隔（整数毫秒），选择正向或反向，填写循环次数。
2. 循环次数 0 表示无限循环；正向 LED1 → LED2 → LED3，反向 LED1 → LED3 → LED2。三个灯各保持一个间隔算一圈，例如 300ms、5 圈约运行 4.5 秒。
3. 点击“写入设置”，下位机接收设置并暂停，当前灯光保持不变；点击“重新开始”从 LED1 和第 0 圈运行。输入框是待写入值，下方“板上设置”与完成圈数来自实际串口反馈。
4. “暂停”保持灯光和圈数，“启动/继续”接着运行；恢复时当前灯重新计时一个完整间隔。手动模式、已停止或已完成时启动会从 LED1 重新计数。
5. 达到指定圈数自动熄灭三个灯；“停止并熄灭”立即熄灭并清零计数。“重新开始”保留设置重新计数。“读取设置”把板上值填回输入框，不会修改灯光。

循环由 STM32 执行，关闭上位机或断开串口后仍继续。设置只在 RAM 保存，断电、复位或“恢复默认”后回到正向、300ms、无限循环。KEY5 同样恢复默认；KEY1 在循环完成后重新开始。

旧版 LED 固件仍可连接和控制单灯，未返回 CYCLES/DONE 时新增按钮禁用，需要通过 DAP 下载本目录配套固件。

单灯或全部开关命令进入手动模式，避免流水覆盖设置。“启动/继续”恢复流水。实体 KEY1 在手动模式下恢复流水，在流水模式下暂停/继续；KEY2 改方向，KEY3/KEY4 调速，KEY5 恢复默认。

LED 状态来自 GPIO 输出寄存器，不是光学反馈。未连接或状态过期时显示“未知”。关闭上位机后，板子保持当前工作方式，流水不会因断开串口而停止。

## 连接

先停止机械运动，再决定是否下载 LED 固件。下载会替换板上现有电机程序，2026-11-14 已按用户要求刷入 LED 固件并通过校验，原程序已备份。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File firmware/YS_F4Pro_LED_Keys/build.ps1 -Flash
```

电脑连接 USB2 串口口，JP2 两路跳帽接通，选择实际 COM 口连接。通信为 115200、8N1；DAP 用于下载，不代替串口。

上位机只接受 LED 固件握手，不能连接电机固件。串口被其他程序占用时，需先关闭占用程序。

## 协议

ASCII，一行一条，末尾 LF 或 CRLF。正常连接只发送握手和查询，不自动修改灯光。

```text
HELLO
STATUS
LED 1 ON
LED 2 OFF
ALL ON
ALL OFF
FLOW START
FLOW PAUSE
FLOW DIR 1
FLOW DIR -1
FLOW MS 300
FLOW CONFIG 300 1 5
FLOW RESTART
FLOW STOP
RESET
```

FLOW MS 接受 50～60000 整数；FLOW CONFIG 的三个参数为间隔、方向（1/-1）、循环次数（0～9999），全部校验通过才应用，并暂停、清零计数。FLOW RESTART 按当前配置从 LED1 重新运行，FLOW STOP 停止、清零并熄灭。RESET 恢复应用默认状态，不复位 MCU。

```text
HELLO YS_F4Pro_LED PROTO=1
OK
LEDSTATE MODE=FLOW RUN=1 DIR=1 MS=300 MASK=1 KEYS=0 CYCLES=5 DONE=0
```

MASK 位 0～2 分别代表 LED1～LED3；KEYS 为按键事件批次计数。CYCLES 为目标圈数，DONE 为已完成整圈数。手动模式 RUN=0，流水暂停 MODE=FLOW、RUN=0。有限循环完成后 MODE=FLOW、RUN=0、MASK=0、DONE=CYCLES。新增字段沿用 PROTO=1，上位机兼容旧版六字段状态。

## 源码与验证

app.py：界面；link.py：后台串口与握手；device.py：解析及离线模拟；tests/：测试。

```powershell
python -m pip install -r led_controller/requirements.txt
python led_controller/app.py --demo
python led_controller/app.py --port COM4
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build-led-controller.ps1
```

在 led_controller 目录执行 `python -m unittest discover -s tests -v` 和 `python tests/gui_smoke.py`。

LED 固件已编译，桌面程序经过离线协议与界面测试；2026-11-14 已通过 COM6 单灯/全部开关、流水启停、方向/间隔及无效命令拒绝测试，恢复默认 300ms 流水灯；真实 GUI 握手及状态读取也已通过。

同日新增循环设置版本已通过 DAP 下载校验、5 项单元测试、界面布局与离线操作测试，以及 COM6 有限/无限循环、停止/暂停/重新开始、非法配置拒绝和真实界面参数读写测试。测试后恢复 300ms 正向无限循环。实体按键仍需人工按下验证。

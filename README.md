# YS-F4Pro LED 串口控制例程

STM32F407IGT6 开发板上的三灯流水灯、实体按键和 Python 桌面串口控制。本次整理版本为 2026-11-17，代码对应此前已下载验证的 LED 固件。

## 两个源码文件夹

| 文件夹 | 内容 |
| --- | --- |
| [led_controller](led_controller/) | 上位机：Python / Tkinter / pyserial，含离线演示、协议解析和测试 |
| [firmware/YS_F4Pro_LED_Keys](firmware/YS_F4Pro_LED_Keys/) | 下位机：STM32 HAL、Arm GCC、CMake、CMSIS-DAP 下载配置，含 HAL/CMSIS 依赖及许可 |

[开发笔记](docs/LED上下位机开发笔记.md) · [上位机操作及串口协议](led_controller/README.md) · [下位机结构与按键说明](firmware/YS_F4Pro_LED_Keys/README.md)

## 启动上位机

在仓库根目录执行（Python 3，含 Tkinter）：

```powershell
python -m pip install -r led_controller/requirements.txt
python led_controller/app.py --demo
# 接上 USB2 串口后，替换为实际 COM 口
python led_controller/app.py --port COM6
```

如需 Windows 单文件程序，安装 PyInstaller 后执行 `powershell -ExecutionPolicy Bypass -File scripts/build-led-controller.ps1`。输出位于 `output/led_controller`，之后可双击根目录 `启动LED上位机.cmd`。仓库保存源码，EXE、构建缓存和 Flash 备份不提交。

## 编译下位机

将 Arm GNU Toolchain、CMake、Ninja 加入 PATH，在仓库根目录执行：

```powershell
cmake -S firmware/YS_F4Pro_LED_Keys -B firmware/YS_F4Pro_LED_Keys/build/Debug -G Ninja -DCMAKE_TOOLCHAIN_FILE=cmake/gcc-arm-none-eabi.cmake -DCMAKE_BUILD_TYPE=Debug
cmake --build firmware/YS_F4Pro_LED_Keys/build/Debug
```

本机已安装工具时也可使用下位机目录的 `build.ps1`。它依赖本机 `%LOCALAPPDATA%/STM32Tools/manifest.json`；移到另一台电脑时需配置工具路径。下位机 `.vscode/settings.json` 是本机路径配置，其他电脑使用前需修改。

通过 DAP 下载会替换板上现有程序，LED 固件不控制步进电机。USB2 串口用于上位机通信，DAP 用于下载，两者作用不同。

## 测试

```powershell
cd led_controller
python -m unittest discover -s tests -v
python tests/gui_smoke.py
# 硬件测试会实际切换灯光，结束恢复默认流水
python tests/hardware_serial.py COM6
```

2026-11-14 已完成 DAP 下载校验和 COM6 实测。2026-11-17 整理源码时重跑软件测试与固件编译；历史硬件测试不代表每台设备都已验证。实体按键需人工按下验证。

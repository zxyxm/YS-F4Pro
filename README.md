# YS-F4Pro 电机 + LED 控制

当前推荐：**v5 合并版**，一个上位机、一个串口连接、一套固件，同时控制四轴电机和三灯流水。每转 3200 脉冲，最高 200 rpm，加减速度上限 400 rpm/s。

| 当前源码 | 内容 |
| --- | --- |
| [combined_controller](combined_controller/) | 统一 Python/Tkinter 上位机：电机与 LED 页签、共享串口、离线演示、测试 |
| [firmware/YS_F4Pro_Combined](firmware/YS_F4Pro_Combined/) | 合并 HAL 固件：四轴位置/速度模式、PUL 频率、LED 流水及按键 |

[合并版使用与开发笔记](docs/电机LED合并版使用与开发笔记.md)

```powershell
# 源码运行（Python 3，需包含 Tkinter）
python -m pip install -r combined_controller/requirements.txt
python combined_controller/app.py --demo
python combined_controller/app.py --port COM4

# 本机 STM32Tools 工具链：编译、下载合并固件
powershell -ExecutionPolicy Bypass -File firmware/YS_F4Pro_Combined/build.ps1 -Flash

# 打包 Windows EXE，需另外安装 PyInstaller
powershell -ExecutionPolicy Bypass -File scripts/build-combined-controller.ps1
```

打包后双击“启动电机LED上位机.cmd”。COM 编号按设备管理器选择。根目录 VS Code Ctrl+Shift+B / F5 目标为合并工程，本机工具路径需按其他电脑安装位置调整。

切换页签不会停止运动。实体按键仅控制 LED，电机通过上位机操作；KEY2 不再是电机停止键。LED1 不再被心跳覆盖。关闭上位机会请求电机减速停止，LED 保持状态。LED 恢复默认不会复位或停止电机。

合并版已于 2026-11-17 通过 20 项单元测试、界面测试、PUL 保持低电平的四轴高负载板内测试、正式固件下载校验和 COM4 电机参数/LED 操作隔离验证。未启动实际电机，带载最高速度及实体按键需人工验证。光电配置尚未实现真实限位或回原点保护。

历史独立例程保留在 `upper_controller` + `firmware/YS_F4Pro_Stepper`（电机 v4），及 `led_controller` + `firmware/YS_F4Pro_LED_Keys`（LED v1），它们有各自协议和启动脚本。合并版请使用上面的当前入口。EXE、build、缓存和原始 Flash 备份留在本地。

---

# 历史 LED 独立例程说明

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

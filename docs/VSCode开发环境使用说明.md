# 本机 VS Code STM32 开发环境

2026-11-17 更新：仓库根目录 `.vscode` 默认构建/调试目标已改为 `firmware/YS_F4Pro_Combined` 电机+LED v5 合并固件。Ctrl+Shift+B 编译，F5 下载并停在 main，继续运行后可串口连接。[合并版说明](电机LED合并版使用与开发笔记.md)。下文独立电机/CubeMX 流程作为历史和新建项目参考。

配置日期：2026-11-12。对象：YS-F4Pro / STM32F407IGT6 / 硬石 CMSIS-DAP。

后续状态：已建立 `firmware/YS_F4Pro_Stepper` HAL/CMake 工程，并通过 DAP 刷入开发板。可直接使用 Ctrl+Shift+B 或 F5。此工程由已有 ST HAL/CMSIS 建立，没有 `.ioc`；以下“生成工程”保留为未来新建 CubeMX 工程的步骤，不应覆盖当前目录。实际操作和验证记录见[固件说明](../firmware/YS_F4Pro_Stepper/README.md)。

## 软件分工

- CubeMX：配置芯片、时钟、引脚，生成 HAL CMake 工程。
- VS Code C/C++：编辑及代码提示。
- Arm GCC：编译 Cortex-M4 固件。
- CMake + Ninja：配置和执行构建。
- Cortex-Debug + OpenOCD：通过 CMSIS-DAP 下载和断点调试。

不需要 Keil 或 IAR。本次采用独立工具链与 Cortex-Debug，未叠加安装 ST 官方集成扩展，避免同时出现多套构建入口。

## 工具位置

工具安装在 `%LOCALAPPDATA%/STM32Tools`，版本与下载来源记录在其中的 `manifest.json`。VS Code 工作区已设置编译器、调试器及终端 PATH，未修改其他项目的用户全局配置。

`scripts/stm32-env.ps1` 会为当前 PowerShell 会话加载工具；普通外部终端如要调用这些工具，可先在仓库根目录执行：

```powershell
. ./scripts/stm32-env.ps1
arm-none-eabi-gcc --version
cmake --version
ninja --version
openocd --version
```

## 生成工程

在 CubeMX 中选择 STM32F407IGT6，配置 HAL，并设置：

```text
Project Name: YS_F4Pro_Stepper
Toolchain / IDE: CMake
```

最终工程必须位于仓库的 `firmware/YS_F4Pro_Stepper`，其中直接包含 `CMakeLists.txt`、`.ioc`、`Core`、`Drivers`、`cmake/gcc-arm-none-eabi.cmake`。CubeMX 是否自动增加项目名子目录取决于界面选项，以生成后的实际目录为准。

当前已有可编译 HAL 固件。若另行生成 CubeMX 工程，请先使用其他目录并检查差异。不要从本仓库的 tmp 目录选择 CMake 工程；其中含解压参考例程的库文件。

详细引脚与时钟参考[入门教程](从ARM开始的HAL步进电机入门教程.md)和[开发笔记](步进电机开发笔记.md)。首次保持电机动力断电，不启动 PWM。

## 打开、构建和调试

1. 在 VS Code 打开整个 `YS-F4Pro` 仓库，载入本目录的 `.vscode` 配置。
2. 如提示工作区信任，确认这是你自己的仓库后再启用任务。环境配置不会绕过信任机制。
3. 新建终端，使工作区工具 PATH 生效。
4. 按 `Ctrl+Shift+B`，运行默认的 `STM32: Build`，会先配置再编译。
5. 成功后，产物应为 `firmware/YS_F4Pro_Stepper/build/Debug/YS_F4Pro_Stepper.elf`。
6. 连接 DAP 的 SWDIO、SWCLK、GND；按说明连接参考电压，确认目标板正常供电。
7. 在“运行和调试”中选择 `STM32F407 - HardStone DAP (OpenOCD)`，按 F5。

F5 使用 launch 模式，会构建并下载固件，然后运行到 main。只在准备好目标板后执行。不要在接着运行中的电机时随意打断点。

OpenOCD 使用 `interface/cmsis-dap.cfg` 和 `target/stm32f4x.cfg`，初始 SWD 速率 1000kHz。若连接不稳定，可在 `.vscode/launch.json` 中降低 `adapter speed`。

## 常见情况

- 提示 Generate the CubeMX CMake project：先完成 CubeMX 生成，确认目录没有多嵌套一层。
- 找不到 ELF：确认项目名为 `YS_F4Pro_Stepper`，且编译成功；若改项目名，也要同步修改 launch.json。
- 提示找不到 CMSIS-DAP：检查 USB 数据线、设备管理器和实际仿真器固件，不能靠安装 ST-Link 驱动解决。
- CMake 选错工具链：使用这里的 STM32 构建任务，或选择 Arm GCC；不要使用桌面 MSVC。
- 代码红线：先成功配置/编译，以生成 compile_commands.json，再刷新 C/C++；使用工作区指定的数据库。
- CubeMX 安装：本次只配置编译调试环境，CubeMX 本体的安装与固件包下载状态需单独确认。

## 验证范围

本次已完成：

| 检查 | 结果 |
|---|---|
| Arm GCC | 15.2.1，运行正常 |
| Arm GDB | 16.3.90，运行正常 |
| CMake | 4.4.5，配置成功 |
| Ninja | 1.13.2，构建成功 |
| OpenOCD | xPack 0.12.0-7，CMSIS-DAP/STM32F4 配置加载成功 |
| Cortex-Debug | 1.12.1，四个依赖扩展已安装 |
| Cortex-M4 测试 | 成功交叉编译和链接，ELF 为 ARM32、hard-float ABI |
| 固件格式转换 | HEX、BIN 生成成功 |
| 包校验 | GCC、OpenOCD、CMake 对照发布方 SHA-256 校验通过；Ninja 记录本地 SHA-256 |

测试程序仅用于验证工具链，不含板卡启动和完整 HAL 初始化，不用于烧录。本次没有在目标板下载程序，也没有验证电机转动。未检测到名称含 CMSIS-DAP 的已接入设备；这不能替代实际连接检查。

## 官方参考

- [Cortex-Debug 配置属性](https://github.com/Marus/cortex-debug/blob/master/debug_attributes.md)
- [xPack OpenOCD](https://github.com/xpack-dev-tools/openocd-xpack)
- [xPack Arm GCC](https://github.com/xpack-dev-tools/arm-none-eabi-gcc-xpack)
- [CMake](https://github.com/Kitware/CMake)
- [Ninja](https://github.com/ninja-build/ninja)

## 用户提供的阅读参考

[基于 VS Code 搭建通用 ARM 微控制器开发平台](https://blog.csdn.net/u013441358/article/details/124133648)。该文主要展示 Makefile 工程及 Cortex-Debug 的配置思路；本项目使用 CubeMX 生成的 CMake 工程，因此任务命令有所不同。调试器配置针对硬石 CMSIS-DAP，不照搬文中的 ST-Link 或 J-Link 接口。具体工具参数以官方文档和本机验证为准。

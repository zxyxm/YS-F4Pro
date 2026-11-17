# YS-F4Pro 电机 + LED 合并 HAL 固件 v5

当前推荐固件，与 `combined_controller` 上位机配套。四轴位置/连续速度和三灯流水共存；STM32F407IGT6、HSE 8MHz、系统 168MHz。板端使用单个 USART1（PB6/PB7，115200 8N1）和 TIM8 四路 PUL，LED/按键在主循环运行。

3200 脉冲/转，速度 1～200 rpm，加减速度 1～400 rpm/s；定位位移 1～32000 脉冲。默认电机参数 3200/30/30/30，上电不自动运动。PUL 高电平 40μs，编译优化 -O2，保留调试符号。

LED1 PH9、LED2 PE5、LED3 PE6，高电平亮。KEY1～KEY5 为 PE0～PE4，25ms 去抖。KEY1 暂停/继续 LED，KEY2 换流水方向，KEY3 加快，KEY4 减慢，KEY5 恢复 LED 默认。旧电机例程的按键启动功能在合并版中取消，避免误触发运动。LED1 不再作为电机心跳灯。

当前完整[使用与开发笔记](../../docs/电机LED合并版使用与开发笔记.md)。本工程为独立 HAL + GCC/CMake 工程，没有 CubeMX `.ioc`，第三方许可保留在 Drivers。

```powershell
# 在仓库根目录执行；使用本机 STM32Tools/manifest.json
powershell -ExecutionPolicy Bypass -File firmware/YS_F4Pro_Combined/build.ps1
powershell -ExecutionPolicy Bypass -File firmware/YS_F4Pro_Combined/build.ps1 -Flash
```

其他电脑将 Arm GCC、CMake、Ninja、OpenOCD 加入 PATH 后可用常规 CMake 构建：

```powershell
cmake -S firmware/YS_F4Pro_Combined -B firmware/YS_F4Pro_Combined/build/Debug -G Ninja -DCMAKE_TOOLCHAIN_FILE=cmake/gcc-arm-none-eabi.cmake -DCMAKE_BUILD_TYPE=Debug
cmake --build firmware/YS_F4Pro_Combined/build/Debug
```

`MOTION_ENGINE_TEST=ON` 是专门的板内测试固件：全部 PUL 脚保持 GPIO 低电平，测试内部定时器及 LED 并发，结束后不进入普通串口控制循环。它不能用于实际控制，测试后需重新下载默认 OFF 的正式固件。2026-11-17 两项测试结果均为 0，正式版已通过下载校验和 COM4 联调。未做真实电机带载高转速测试。

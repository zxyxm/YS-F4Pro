# 电机 + LED 统一上位机（v5）

一个窗口、一个串口线程，连接 `firmware/YS_F4Pro_Combined` 合并固件。支持四轴位置/连续速度控制、3200 脉冲/转、200 rpm 和 400 rpm/s 上限，以及三灯独立开关和有限/无限流水。[操作与协议笔记](../docs/电机LED合并版使用与开发笔记.md)。

```powershell
python -m pip install -r combined_controller/requirements.txt
python combined_controller/app.py --demo
python combined_controller/app.py --port COM4
```

Windows EXE：安装 PyInstaller 后执行 `powershell -ExecutionPolicy Bypass -File scripts/build-combined-controller.ps1`，输出 `output/combined_controller/YSF4Pro_Combined.exe`。然后可双击根目录“启动电机LED上位机.cmd”。

顶部共用连接栏和全部轴停止按钮；“四轴电机”和“LED 与流水灯”页签切换不停止设备。LED 操作不会发送电机启动命令，关闭窗口会请求所有电机减速停止，LED 保持当前模式。频率来自定时器周期，不是驱动器端子实测。光电输入仍是本机规划配置，未实现真实限位保护或回原点。

协议只接受 PROTO=5、LED=1 的合并固件。旧 LED 单独上位机、旧电机上位机用于各自独立固件；使用合并版后不要再同时打开旧程序抢占串口。

源码：`app.py` 为组合入口，`motor_app.py` 为电机界面，`led_panel.py` 为 LED 界面；`transport.py` 为唯一串口线程；`protocol.py` 与 `led_device.py` 分别解析状态；`demo.py` 为组合离线设备；`axis_config.py` 保存本机细分配置，沿用原电机上位机配置位置。

```powershell
cd combined_controller
python -m unittest discover -s tests -v
python tests/gui_smoke.py
# 下项会切换 LED、临时写入并恢复电机 RAM 参数，不启动电机
python tests/hardware_shared.py COM4
```

"""YS-F4Pro four-axis desktop controller (Tk + pySerial)."""
import argparse
from collections import deque
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import os
from pathlib import Path
import queue
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import serial.tools.list_ports
from protocol import Profile, PPR
from transport import ControllerLink
from axis_config import Calibration, PPR_OPTIONS, SENSOR_ROLES, defaults, load_calibrations, save_calibrations, to_wire, physical_text, raw_commands

BG, WHITE, INK, MUTED, BLUE = "#f1f5f9", "#ffffff", "#14263d", "#64748b", "#2563eb"
COLORS = ["#2563eb", "#0891b2", "#7c3aed", "#db6b18"]


class Chart(tk.Canvas):
    def __init__(self, parent, **kw):
        super().__init__(parent, background=WHITE, highlightthickness=0, height=182, **kw)
        self.points, self.maximum, self.span, self.color = [], 60, 1, BLUE
        self.empty_message = "尚未收到状态数据"
        self.bind("<Configure>", lambda _: self.draw())

    def update_plot(self, points, span, maximum=60, color=BLUE, message=None):
        self.points, self.span, self.maximum, self.color = points, max(span, 0.1), max(maximum, 1), color
        if message is not None:
            self.empty_message = message
        self.draw()

    def draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 50:
            return
        left, top, right, bottom = 44, 14, w-14, h-29
        for i in range(5):
            y = bottom-(bottom-top)*i/4
            self.create_line(left, y, right, y, fill="#e6edf5")
            self.create_text(left-7, y, text=f"{self.maximum*i/4:.0f}", anchor="e", fill=MUTED, font=("Segoe UI", 8))
        for i in range(5):
            x = left+(right-left)*i/4
            self.create_text(x, bottom+14, text=f"{self.span*i/4:.1f}s", fill=MUTED, font=("Segoe UI", 8))
        self.create_text(left, 3, text="rpm", anchor="nw", fill=MUTED, font=("Segoe UI", 8))
        points = []
        for x, y in self.points:
            points.extend((left+(right-left)*max(0, min(x/self.span, 1)), bottom-(bottom-top)*max(0, min(y/self.maximum, 1))))
        if len(points) >= 4:
            self.create_line(*points, fill=self.color, width=2)
        elif not points:
            self.create_text((left+right)/2, (top+bottom)/2, text=self.empty_message, width=max(100, right-left-20), fill=MUTED, font=("Microsoft YaHei UI", 10))


class App:
    def __init__(self, root, demo=False, settings_path=None):
        self.root = root
        self.root.title("YS-F4Pro · 电机与 LED 控制台")
        self.root.geometry("1240x900")
        self.root.minsize(1100, 840)
        self.root.configure(background=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.events = queue.Queue()
        self.link = None
        self.connected = False
        self.is_demo = False
        self.axis = 1
        self.states = {}
        self.updated = {}
        self.pending = {}
        self.board_params = {}
        self.parameter_pending = {}
        self.histories = {i: deque(maxlen=240) for i in range(1, 5)}
        self.settings = {}
        self.motion_modes = {i:tk.StringVar(value='位置模式') for i in range(1,5)}
        self.controls = []
        self.log_lines = deque(maxlen=1000)
        self.closing = False
        self.config_file = settings_path
        self.config_error = None
        try:
            self.calibrations = load_calibrations(settings_path)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.calibrations = defaults()
            self.config_error = str(exc)
        self.driver_confirmed = {i: cfg.ppr == PPR for i, cfg in self.calibrations.items()}
        self._styles()
        self._build()
        self.refresh_ports()
        self.select_axis(1)
        if self.config_error:
            self.connection_note.set("本机配置读取失败，已使用默认 3200："+self.config_error)
        self.root.after(50, self.tick)
        if demo:
            self.root.after(200, lambda: self.connect(True))

    def _styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=WHITE)
        style.configure("TLabel", background=WHITE, foreground=INK, font=("Microsoft YaHei UI", 10))
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 16, "bold"))
        style.configure("TButton", font=("Microsoft YaHei UI", 10), padding=(12, 8))
        style.configure("Primary.TButton", background=BLUE, foreground=WHITE)
        style.map("Primary.TButton", background=[("active", "#1d4ed8"), ("disabled", "#b5c5df")], foreground=[("disabled", "#f8fafc")])
        style.configure("Stop.TButton", background="#fff1f2", foreground="#b42332")
        style.configure("TEntry", padding=6, font=("Segoe UI", 11))
        style.configure("TCombobox", padding=5, font=("Microsoft YaHei UI", 10))
        for i in range(1, 5):
            vals = {"distance": str(PPR), "unit": "脉冲", "rpm": "30", "accel": "30", "decel": "30", "curve": "梯形加减速"}
            self.settings[i] = {k: tk.StringVar(value=v) for k, v in vals.items()}
            for v in self.settings[i].values():
                v.trace_add("write", lambda *_: self.preview())

    def _build(self):
        header = tk.Frame(self.root, bg="#14263d", height=78)
        header.pack(fill="x")
        tk.Label(header, text="YS-F4Pro", fg=WHITE, bg="#14263d", font=("Segoe UI", 23, "bold")).pack(side="left", padx=(24, 12), pady=16)
        tk.Label(header, text="四轴电机 + 三灯控制", fg="#cbd5e1", bg="#14263d", font=("Microsoft YaHei UI", 12)).pack(side="left")
        self.banner = tk.Label(header, text="未连接", fg="#fbbf24", bg="#14263d", font=("Microsoft YaHei UI", 11))
        self.banner.pack(side="right", padx=24)
        connection = ttk.Frame(self.root, padding=(18, 10))
        connection.pack(fill="x")
        ttk.Label(connection, text="串口", background=BG).pack(side="left")
        self.port_var = tk.StringVar()
        self.ports = ttk.Combobox(connection, textvariable=self.port_var, width=13, state="readonly")
        self.ports.pack(side="left", padx=8)
        self.refresh_btn = ttk.Button(connection, text="刷新", command=self.refresh_ports)
        self.refresh_btn.pack(side="left")
        self.connect_btn = ttk.Button(connection, text="连接设备", command=lambda: self.connect(False))
        self.connect_btn.pack(side="left", padx=8)
        self.demo_btn = ttk.Button(connection, text="离线演示", command=lambda: self.connect(True))
        self.demo_btn.pack(side="left")
        ttk.Label(connection, text="115200 · 8N1  |  USB2 串口", background=BG, foreground=MUTED).pack(side="left", padx=14)
        self.stop_all_btn = ttk.Button(connection, text="全部轴减速停止", style="Stop.TButton", command=lambda: self.send("STOP ALL"))
        self.stop_all_btn.pack(side="right")
        self.connection_note = tk.StringVar(value="连接开发板 USB2 串口；DAP 用于下载程序，不代替串口数据线。")
        ttk.Label(self.root, textvariable=self.connection_note, background=BG, foreground=MUTED).pack(fill="x", padx=20, pady=(0, 8))
        self.main_tabs=ttk.Notebook(self.root)
        self.main_tabs.pack(fill='both',expand=True)
        motor_tab=ttk.Frame(self.main_tabs);self.led_tab=ttk.Frame(self.main_tabs)
        self.main_tabs.add(motor_tab,text='四轴电机')
        self.main_tabs.add(self.led_tab,text='LED 与流水灯')
        body = ttk.Frame(motor_tab, padding=(18, 0))
        body.pack(fill="both", expand=True)
        sidebar = ttk.Frame(body, width=205)
        sidebar.pack(side="left", fill="y", padx=(0, 14))
        self.cards = {}
        for i in range(1, 5):
            frame = tk.Frame(sidebar, bg=WHITE, highlightbackground="#dce4ee", highlightthickness=1, padx=16, pady=12, cursor="hand2")
            frame.pack(fill="x", pady=(0, 10))
            title = tk.Label(frame, text=f"轴 {i}  /  CN{15+i}", bg=WHITE, fg=INK, anchor="w", font=("Microsoft YaHei UI", 13, "bold"))
            title.pack(fill="x")
            state = tk.Label(frame, text="离线", bg=WHITE, fg=MUTED, anchor="w", font=("Microsoft YaHei UI", 10))
            state.pack(fill="x", pady=(7, 3))
            position = tk.Label(frame, text="位置 —", bg=WHITE, fg=MUTED, anchor="w", font=("Microsoft YaHei UI", 9))
            position.pack(fill="x")
            for widget in (frame, title, state, position):
                widget.bind("<Button-1>", lambda _, n=i: self.select_axis(n))
            self.cards[i] = (frame, title, state, position)
        ttk.Label(sidebar, text="各轴可分别启动与停止\n切换轴不会停止其他轴\n\n细分按每轴设置换算\n未读取编码器实际位置", background=BG, foreground=MUTED, justify="left").pack(anchor="w", pady=4)
        main = ttk.Frame(body)
        main.pack(side="left", fill="both", expand=True)
        panel = ttk.Frame(main, style="Card.TFrame", padding=18)
        panel.pack(fill="x")
        self.axis_title = ttk.Label(panel, text="轴 1", style="Title.TLabel")
        self.axis_title.grid(row=0, column=0, columnspan=2, sticky="w")
        self.mode_box=ttk.Combobox(panel,values=['位置模式','速度模式'],state='readonly',width=12)
        self.mode_box.grid(row=0,column=2,columnspan=2,sticky='w')
        self.mode_box.bind('<<ComboboxSelected>>',lambda _:self.preview())
        self.axis_status = ttk.Label(panel, text="等待连接", style="Muted.TLabel")
        self.axis_status.grid(row=0, column=4, columnspan=2, sticky="e")
        self.form = {}
        fields = [("distance", "相对位移", "entry"), ("unit", "位移单位", "unit"), ("rpm", "目标速度 / rpm", "entry"), ("accel", "加速度 / rpm/s", "entry"), ("decel", "减速度 / rpm/s", "entry"), ("curve", "速度曲线", "curve")]
        for index, (key, label, kind) in enumerate(fields):
            col = index % 3 * 2
            row = 1 + index // 3 * 2
            ttk.Label(panel, text=label, style="Muted.TLabel").grid(row=row, column=col, columnspan=2, sticky="w", pady=(14, 4))
            if kind == "entry":
                widget = ttk.Entry(panel, width=14)
            else:
                widget = ttk.Combobox(panel, state="readonly", width=16, values=["脉冲", "转"] if kind == "unit" else ["梯形加减速", "S 型平滑定位"])
            widget.grid(row=row+1, column=col, columnspan=2, sticky="ew", padx=(0, 14 if col < 4 else 0))
            self.form[key] = widget
        for col in (0, 2, 4):
            panel.columnconfigure(col, weight=1)
        parameter_actions = ttk.Frame(panel, style="Card.TFrame")
        parameter_actions.grid(row=5, column=0, columnspan=6, sticky="ew", pady=(14, 0))
        self.write_btn = ttk.Button(parameter_actions, text="写入参数", command=self.write_parameters)
        self.write_btn.pack(side="left")
        self.read_btn = ttk.Button(parameter_actions, text="读取参数", command=self.read_parameters)
        self.read_btn.pack(side="left", padx=8)
        self.parameter_status = tk.StringVar(value="板端 RAM 参数 · 断电恢复默认")
        ttk.Label(parameter_actions, textvariable=self.parameter_status, foreground=MUTED, wraplength=480).pack(side="left", padx=4)
        actions = ttk.Frame(panel, style="Card.TFrame")
        actions.grid(row=6, column=0, columnspan=6, sticky="ew", pady=(12, 0))
        self.forward = ttk.Button(actions, text="正向启动", style="Primary.TButton", command=lambda: self.move(1))
        self.forward.pack(side="left")
        self.reverse = ttk.Button(actions, text="反向启动", style="Primary.TButton", command=lambda: self.move(-1))
        self.reverse.pack(side="left", padx=8)
        self.stop_btn = ttk.Button(actions, text="本轴减速停止", style="Stop.TButton", command=lambda: self.send(f"STOP {self.axis}"))
        self.stop_btn.pack(side="left")
        self.zero_btn = ttk.Button(actions, text="软件置零", command=lambda: self.send(f"ZERO {self.axis}"))
        self.zero_btn.pack(side="right")
        self.clear_btn = ttk.Button(actions, text="清软件故障", command=lambda: self.send(f"CLEAR {self.axis}"))
        self.clear_btn.pack(side="right", padx=8)
        self.metrics = tk.StringVar(value="指令位置 —    指令速度 —    已发脉冲 —")
        ttk.Label(panel, textvariable=self.metrics).grid(row=7, column=0, columnspan=6, sticky="w", pady=(14, 0))
        self.validation = tk.StringVar()
        ttk.Label(panel, textvariable=self.validation, foreground=MUTED, wraplength=780).grid(row=8, column=0, columnspan=6, sticky="w", pady=(6, 0))
        self.tabs = ttk.Notebook(main)
        self.tabs.pack(fill="both", expand=True, pady=(12, 0))
        curve_tab, config_tab, terminal_tab = (ttk.Frame(self.tabs) for _ in range(3))
        self.tabs.add(curve_tab, text="速度曲线")
        self.tabs.add(config_tab, text="细分与光电开关")
        self.tabs.add(terminal_tab, text="串口报文 / 收发记录")
        self.build_configuration(config_tab)
        charts = ttk.Frame(curve_tab)
        charts.pack(fill="both", expand=True, pady=6)
        charts.columnconfigure(0, weight=1)
        charts.columnconfigure(1, weight=1)
        for column, title in enumerate(("下一次移动 · 规划曲线预览", "指令速度 · 最近 30 秒")):
            card = ttk.Frame(charts, style="Card.TFrame", padding=(12, 10))
            card.grid(row=0, column=column, sticky="nsew", padx=(0, 6) if column == 0 else (6, 0))
            ttk.Label(card, text=title).pack(anchor="w")
            chart = Chart(card)
            chart.pack(fill="both", expand=True)
            if column == 0:
                self.preview_chart = chart
            else:
                self.history_chart = chart
        raw_panel = ttk.Frame(terminal_tab, style="Card.TFrame", padding=(12, 8))
        raw_panel.pack(fill="x")
        ttk.Label(raw_panel, text="ASCII 报文 · 一行一条，自动追加 LF · 原始报文不做细分换算", style="Muted.TLabel").pack(anchor="w")
        self.raw_text = tk.Text(raw_panel, height=3, font=("Consolas", 10), wrap="none", relief="solid", borderwidth=1)
        self.raw_text.pack(fill="x", pady=6)
        raw_actions = ttk.Frame(raw_panel, style="Card.TFrame")
        raw_actions.pack(fill="x")
        self.raw_send = ttk.Button(raw_actions, text="发送报文", command=self.send_raw)
        self.raw_send.pack(side="left")
        ttk.Button(raw_actions, text="填入本轴 GET", command=lambda: self.fill_raw(f"GET {self.axis}")).pack(side="left", padx=8)
        ttk.Button(raw_actions, text="填入本轴 SET", command=self.fill_parameter_command).pack(side="left", padx=(0, 8))
        ttk.Button(raw_actions, text="填入 STATUS", command=lambda: self.fill_raw("STATUS")).pack(side="left")
        self.show_poll = tk.BooleanVar(value=False)
        ttk.Checkbutton(raw_actions, text="显示轮询报文", variable=self.show_poll).pack(side="right")
        ttk.Label(raw_panel, text="RUN / MOVE 会启动运动；本功能直接发送下位机原始命令。", foreground="#a65d16").pack(anchor="w", pady=(5, 0))
        logs = ttk.Frame(terminal_tab, style="Card.TFrame", padding=(12, 8))
        logs.pack(fill="both", expand=True)
        ttk.Label(logs, text="通信记录", style="Muted.TLabel").pack(side="top", anchor="w")
        self.log = tk.Text(logs, height=5, wrap="none", font=("Consolas", 9), bg=WHITE, fg=MUTED, relief="flat", state="disabled")
        self.log.pack(fill="both", expand=True)
        bottom = ttk.Frame(self.root, padding=(18, 7))
        bottom.pack(fill="x")
        ttk.Label(bottom, text="普通软件停止，非安全急停。S 型为对称五次多项式定位曲线。", background=BG, foreground=MUTED, font=("Microsoft YaHei UI", 9)).pack(side="left")
        ttk.Button(bottom, text="导出通信记录", command=self.export_log).pack(side="right")

    def build_configuration(self, parent):
        panel = ttk.Frame(parent, style="Card.TFrame", padding=14)
        panel.pack(fill="both", expand=True)
        row = ttk.Frame(panel, style="Card.TFrame")
        row.pack(fill="x")
        ttk.Label(row, text="每转指令脉冲数").pack(side="left")
        self.ppr_draft = tk.StringVar(value=str(PPR))
        self.ppr_box = ttk.Combobox(row, textvariable=self.ppr_draft, values=PPR_OPTIONS, width=10, state="readonly")
        self.ppr_box.pack(side="left", padx=8)
        self.confirm_draft = tk.BooleanVar(value=True)
        self.ppr_box.bind("<<ComboboxSelected>>", lambda _: self.confirm_draft.set(False))
        ttk.Checkbutton(row, text="驱动器已手动设为同值", variable=self.confirm_draft).pack(side="left")
        self.apply_config_btn = ttk.Button(row, text="应用本轴配置", command=self.apply_configuration)
        self.apply_config_btn.pack(side="right")
        self.calibration_note = tk.StringVar()
        ttk.Label(panel, textvariable=self.calibration_note, style="Muted.TLabel", wraplength=800).pack(fill="x", pady=(8, 12))
        grid = ttk.Frame(panel, style="Card.TFrame")
        grid.pack(fill="x")
        for column, title in enumerate(("光电开关", "计划输入映射", "触发有效电平", "当前状态")):
            ttk.Label(grid, text=title, style="Muted.TLabel").grid(row=0, column=column, sticky="w", padx=(0, 18), pady=(0, 6))
        self.sensor_inputs, self.sensor_levels, self.sensor_labels = [], [], []
        for index, role in enumerate(SENSOR_ROLES):
            ttk.Label(grid, text=role).grid(row=index+1, column=0, sticky="w", pady=4)
            source, level = tk.StringVar(), tk.StringVar()
            ttk.Combobox(grid, textvariable=source, values=[f"IN{i}" for i in range(1, 13)], state="readonly", width=10).grid(row=index+1, column=1, sticky="w", padx=(0, 18))
            ttk.Combobox(grid, textvariable=level, values=["低电平", "高电平"], state="readonly", width=10).grid(row=index+1, column=2, sticky="w", padx=(0, 18))
            label = ttk.Label(grid, text="未知 · 当前报文不含输入状态", foreground=MUTED)
            label.grid(row=index+1, column=3, sticky="w")
            self.sensor_inputs.append(source)
            self.sensor_levels.append(level)
            self.sensor_labels.append(label)
        ttk.Label(panel, text="当前仅保存光电开关配置，不向下位机写入映射；尚不具备光电限位保护或自动回原点功能。", foreground="#a65d16", wraplength=800).pack(fill="x", pady=(12, 0))

    def apply_configuration(self):
        state = self.states.get(self.axis)
        if self.connected and (not state or state.running or time.monotonic()-self.updated.get(self.axis, 0)>1):
            self.connection_note.set("请等待本轴停止且状态有效后更改细分配置")
            return
        if self.axis in self.pending or self.axis in self.parameter_pending:
            self.connection_note.set("请等待当前命令完成")
            return
        try:
            cfg = Calibration(int(self.ppr_draft.get()), tuple(v.get() for v in self.sensor_inputs), tuple(v.get() for v in self.sensor_levels))
            cfg.validate()
            if not self.confirm_draft.get():
                raise ValueError("请先手动设置驱动器细分，并勾选驱动器已设为同值")
            values = dict(self.calibrations)
            values[self.axis] = cfg
            save_calibrations(values, self.config_file)
            self.calibrations = values
            self.driver_confirmed[self.axis] = True
            self.preview()
            self.connection_note.set(f"轴 {self.axis} 本机配置已保存：{cfg.ppr} 脉冲/转。请重新写入运动参数；光电状态仍未知。")
            self.update_calibration_note()
        except (ValueError, OSError) as exc:
            self.connection_note.set(str(exc))

    def update_calibration_note(self):
        ppr = self.calibrations[self.axis].ppr
        self.calibration_note.set(f"当前轴：{ppr} 脉冲/转；下位机原报文参考值仍为 {PPR}。实际速度范围 {physical_text(1,ppr)}～{physical_text(200,ppr)} rpm，加减速度 {physical_text(1,ppr)}～{physical_text(400,ppr)} rpm/s。不会远程修改驱动器。")

    def fill_raw(self, command):
        self.raw_text.delete("1.0", "end")
        self.raw_text.insert("1.0", command)

    def fill_parameter_command(self):
        try:
            self.fill_raw(self.profile().set_command(self.axis))
        except ValueError as exc:
            self.connection_note.set(str(exc))

    def send_raw(self):
        try:
            commands = raw_commands(self.raw_text.get("1.0", "end-1c"))
            if not self.connected or not self.link:
                raise ValueError("请先连接设备或离线演示")
            if self.link.commands.qsize()+len(commands)>32:
                raise ValueError("发送队列已满，请稍后重试")
            for command in commands:
                self.link.send(command)
            self.connection_note.set(f"已排队发送 {len(commands)} 条原始 ASCII 报文；请查看接收回复")
        except (ValueError, RuntimeError) as exc:
            self.connection_note.set(str(exc))

    def refresh_ports(self):
        ports = list(serial.tools.list_ports.comports())
        self.ports["values"] = [p.device for p in ports]
        if self.port_var.get() not in self.ports["values"]:
            self.port_var.set(ports[0].device if ports else "")
        if not ports and not self.connected:
            self.connection_note.set("尚未检测到串口。可以先打开离线演示，查看四轴操作与曲线。")

    def connect(self, demo):
        if self.link and self.link.is_alive():
            self.connection_note.set("正在断开并请求所有轴减速停止…")
            self.link.close()
            return
        if not demo and not self.port_var.get():
            messagebox.showinfo("没有串口", "请连接开发板 USB2 数据线并刷新串口，或使用离线演示。")
            return
        self.states.clear()
        self.updated.clear()
        self.pending.clear()
        self.board_params.clear()
        self.parameter_pending.clear()
        for history in self.histories.values():
            history.clear()
        self.connected, self.is_demo = False, demo
        self.banner.configure(text="离线演示启动中" if demo else "正在握手…", fg="#fbbf24")
        self.link = ControllerLink(self.events, self.port_var.get(), demo)
        self.link.start()

    def send(self, command):
        try:
            if not self.connected or not self.link:
                raise RuntimeError("请先连接设备或打开离线演示")
            self.link.send(command)
            return True
        except (RuntimeError, ValueError) as exc:
            self.connection_note.set(str(exc))
            return False

    def profile(self):
        values = self.settings[self.axis]
        ppr = self.calibrations[self.axis].ppr
        try:
            speed=self.motion_modes[self.axis].get()=='速度模式'
            distance = Decimal(PPR if speed else values["distance"].get())
            if not distance.is_finite() or distance <= 0 or distance > 32000:
                raise ValueError("请输入有效的正位移")
            if not speed and values["unit"].get() == "转":
                distance *= ppr
                pulses = int(distance.to_integral_value(rounding=ROUND_HALF_UP))
            else:
                if distance != distance.to_integral_value():
                    raise ValueError("脉冲数必须为整数")
                pulses = int(distance)
            rpm, acc, dec = (to_wire(values[k].get(), ppr) for k in ("rpm", "accel", "decel"))
            if not 1 <= rpm <= 200 or not 1 <= acc <= 400 or not 1 <= dec <= 400:
                raise ValueError(f"当前细分实际速度须为 {physical_text(1,ppr)}～{physical_text(200,ppr)} rpm，加减速度须为 {physical_text(1,ppr)}～{physical_text(400,ppr)} rpm/s")
            profile = Profile(pulses, rpm, acc, dec, "S" if not speed and values["curve"].get().startswith("S") else "TRAP")
            profile.validate()
            return profile
        except (InvalidOperation, ValueError, OverflowError) as exc:
            raise ValueError(str(exc) if isinstance(exc, ValueError) and str(exc) and not str(exc).startswith("invalid literal") else "请输入有效数值") from exc

    def preview(self):
        if not hasattr(self, "preview_chart"):
            return
        try:
            p = self.profile()
            ppr = self.calibrations[self.axis].ppr
            factor = PPR/ppr
            if self.motion_modes[self.axis].get()=='速度模式':
                ramp=p.rpm/p.accel;span=ramp+3
                self.preview_chart.update_plot([(0,0),(ramp,p.rpm*factor),(span,p.rpm*factor)],span,200*factor,COLORS[self.axis-1])
                self.validation.set(f'连续运行，梯形升降速 · 设定 {p.rpm*factor:g} rpm ≈ {p.rpm*PPR/60:g} Hz · STOP 减速停止；位移和 S 曲线不参与')
                return
            points = [(p.duration*i/120, p.sample(p.duration*i/120)[1]*factor) for i in range(121)]
            self.preview_chart.update_plot(points, p.duration, 200*factor, COLORS[self.axis-1])
            self.validation.set(f"{p.pulses} 脉冲 ≈ {p.pulses/ppr:g} 转  ·  规划时长 {p.duration:.2f}s  ·  驱动器须匹配 {ppr} 脉冲/转")
        except ValueError as exc:
            self.preview_chart.update_plot([], 1, message="参数无效，无法生成预览\n"+str(exc))
            self.validation.set(str(exc))

    def read_parameters(self, axis=None):
        axis = self.axis if axis is None else axis
        if axis in self.parameter_pending:
            return
        if self.send(f"GET {axis}"):
            self.parameter_pending[axis] = {"kind": "read", "sent": time.monotonic()}

    def write_parameters(self):
        state = self.states.get(self.axis)
        if not state or state.running or self.axis in self.parameter_pending or self.axis in self.pending:
            self.connection_note.set("请等待本轴空闲及前一条命令完成")
            return
        try:
            p = self.profile()
            command = p.set_command(self.axis)
        except ValueError as exc:
            self.validation.set(str(exc))
            return
        if self.send(command):
            self.parameter_pending[self.axis] = {"kind": "write", "profile": p, "sent": time.monotonic()}

    def parameters_match(self):
        try:
            return self.driver_confirmed[self.axis] and self.axis in self.board_params and self.profile() == self.board_params[self.axis].profile
        except ValueError:
            return False

    def select_axis(self, axis):
        self.axis = axis
        self.mode_box.configure(textvariable=self.motion_modes[axis])
        self.axis_title.configure(text=f"轴 {axis}  ·  CN{15+axis}")
        for key, widget in self.form.items():
            widget.configure(textvariable=self.settings[axis][key])
        cfg = self.calibrations[axis]
        self.ppr_draft.set(str(cfg.ppr))
        self.confirm_draft.set(self.driver_confirmed[axis])
        for index in range(3):
            self.sensor_inputs[index].set(cfg.inputs[index])
            self.sensor_levels[index].set(cfg.active_levels[index])
        self.update_calibration_note()
        for i, (frame, title, status, position) in self.cards.items():
            color = "#eaf1ff" if i == axis else WHITE
            frame.configure(bg=color, highlightbackground=COLORS[i-1] if i == axis else "#dce4ee")
            for widget in (title, status, position):
                widget.configure(bg=color)
        self.preview()

    def move(self, direction):
        state = self.states.get(self.axis)
        if not state or time.monotonic()-self.updated.get(self.axis, 0) > 1 or state.running or state.fault or self.axis in self.pending:
            self.connection_note.set("本轴未就绪、状态已过期、正在运行或有软件故障")
            return
        try:
            self.profile().validate()
        except ValueError as exc:
            self.validation.set(str(exc))
            return
        speed=self.motion_modes[self.axis].get()=='速度模式'
        if not (self.driver_confirmed[self.axis] if speed else self.parameters_match()) or self.axis in self.parameter_pending:
            self.connection_note.set("参数未同步：请先写入参数，或读取板端参数后启动")
            return
        p=self.profile()
        command = f"SPEED {self.axis} {direction} {p.rpm} {p.accel} {p.decel}" if speed else f"RUN {self.axis} {direction}"
        if self.send(command):
            self.pending[self.axis] = {"sent": time.monotonic(), "acked": False}

    def append_log(self, text):
        text = f"{time.strftime('%H:%M:%S')}  {text}"
        self.log_lines.append(text)
        self.log.configure(state="normal")
        self.log.insert("end", text+"\n")
        if int(self.log.index("end-1c").split(".")[0]) > 400:
            self.log.delete("1.0", "101.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def handle_event(self, kind, data):
        if kind == "ready":
            self.connected, self.is_demo = True, data
            self.banner.configure(text="离线演示 · 不连接硬件" if data else f"已连接 {self.port_var.get()} · 电机+LED v5", fg="#fbbf24" if data else "#6ee7b7")
            self.connection_note.set("演示数据：可以切换轴并独立启动；不会向任何串口发送命令。" if data else "四轴握手成功；通信中断超过 1.5 秒，下位机请求所有轴减速停止。")
            for axis in range(1, 5):
                self.read_parameters(axis)
        elif kind == "parameters":
            operation = self.parameter_pending.pop(data.axis, None)
            self.board_params[data.axis] = data
            if operation and operation["kind"] == "read":
                p = data.profile
                ppr = self.calibrations[data.axis].ppr
                values = {"distance": str(p.pulses), "unit": "脉冲", "rpm": physical_text(p.rpm,ppr), "accel": physical_text(p.accel,ppr), "decel": physical_text(p.decel,ppr), "curve": "S 型平滑定位" if p.curve == "S" else "梯形加减速"}
                for key, value in values.items():
                    self.settings[data.axis][key].set(value)
                self.connection_note.set(f"轴 {data.axis} 参数已从下位机读取（RAM，断电恢复默认）")
            elif operation and operation["kind"] == "write":
                if data.profile == operation["profile"]:
                    self.connection_note.set(f"轴 {data.axis} 参数写入成功，板端回读一致（RAM，断电恢复默认）")
                else:
                    self.connection_note.set(f"轴 {data.axis} 回读参数与写入值不同，请重新读取确认")
        elif kind == "state":
            self.states[data.axis] = data
            self.updated[data.axis] = time.monotonic()
            self.histories[data.axis].append((time.monotonic(), data.rpm))
            pending = self.pending.get(data.axis)
            if pending and (pending["acked"] or data.running):
                self.pending.pop(data.axis, None)
        elif kind == "sent":
            self.append_log("→ "+data)
        elif kind == "tx_status":
            if self.show_poll.get():
                self.append_log("→ "+data)
        elif kind == "line":
            if not data.startswith(("STATE ","LEDSTATE ")) or self.show_poll.get():
                self.append_log("← "+data)
            if data.startswith(("OK MOVE ", "OK RUN ","OK SPEED ")):
                try:
                    pending = self.pending.get(int(data.split()[-1]))
                    if pending:
                        pending["acked"] = True
                except ValueError:
                    pass
            if data.startswith("ERR "):
                self.connection_note.set("设备拒绝命令："+data)
                try:
                    self.pending.pop(int(data.split()[-1]), None)
                    self.parameter_pending.pop(int(data.split()[-1]), None)
                except ValueError:
                    pass
        elif kind == "error":
            self.connection_note.set(data)
            self.append_log("错误："+data)
        elif kind == "closed":
            self.connected = False
            self.pending.clear()
            self.parameter_pending.clear()
            self.banner.configure(text="未连接", fg="#fbbf24")
            self.append_log("连接已关闭")

    def tick(self):
        for _ in range(150):
            try:
                self.handle_event(*self.events.get_nowait())
            except queue.Empty:
                break
        now = time.monotonic()
        for axis, operation in list(self.parameter_pending.items()):
            if now-operation["sent"] > 2:
                self.parameter_pending.pop(axis)
                self.board_params.pop(axis, None)
                self.connection_note.set(f"轴 {axis} 参数操作未收到确认，请重新读取，当前禁止启动")
        for i, (_, _, label, position) in self.cards.items():
            state = self.states.get(i)
            fresh = self.connected and now-self.updated.get(i, 0) <= 1
            text, color = "离线" if not self.connected else "等待状态", MUTED
            if state and fresh:
                text, color = (f"软件故障 {state.fault}", "#b42332") if state.fault else (("运行中", COLORS[i-1]) if state.running else ("空闲", "#15803d"))
            elif state and self.connected:
                text = "状态过期"
            if i in self.pending:
                text, color = "等待启动反馈", COLORS[i-1]
            label.configure(text=text, fg=color)
            factor = PPR/self.calibrations[i].ppr
            position.configure(text=f"{state.position:+d} 脉冲  ·  {state.rpm*factor:.1f} rpm" if state else "位置 —")
        state = self.states.get(self.axis)
        fresh = self.connected and now-self.updated.get(self.axis, 0) <= 1
        idle = fresh and state is not None and not state.running and not state.fault and self.axis not in self.pending
        synchronized = self.parameters_match()
        speed=self.motion_modes[self.axis].get()=='速度模式'
        if speed:
            try:self.profile();synchronized=self.driver_confirmed[self.axis]
            except ValueError:synchronized=False
        operation = self.parameter_pending.get(self.axis)
        self.write_btn.configure(state="normal" if idle and not operation and not speed else "disabled")
        self.read_btn.configure(state="normal" if self.connected and not operation else "disabled")
        self.raw_send.configure(state="normal" if self.connected else "disabled")
        self.apply_config_btn.configure(state="normal" if not operation and self.axis not in self.pending and (not self.connected or (fresh and state and not state.running)) else "disabled")
        for key, widget in self.form.items():
            widget.configure(state="disabled" if operation or (speed and key in ('distance','unit','curve')) else ("readonly" if key in ("unit", "curve") else "normal"))
        self.mode_box.configure(state='readonly' if idle or not self.connected else 'disabled')
        if operation:
            self.parameter_status.set("正在写入并等待回读…" if operation["kind"] == "write" else "正在读取板端参数…")
        elif not self.connected:
            self.parameter_status.set("板端 RAM 参数 · 连接后自动读取 · 断电恢复默认")
        elif speed:
            self.parameter_status.set('速度模式：启动时发送速度/加减速度，持续至 STOP；不使用定位位移')
        elif synchronized:
            self.parameter_status.set(f"已同步板端参数 · RAM · REV {self.board_params[self.axis].revision}")
        else:
            self.parameter_status.set("参数未同步，请先写入；或读取板端参数覆盖输入框")
        for button in (self.forward, self.reverse):
            button.configure(state="normal" if idle and synchronized and not operation and not self.closing else "disabled")
        self.stop_btn.configure(state="normal" if self.connected else "disabled")
        self.stop_all_btn.configure(state="normal" if self.connected else "disabled")
        self.zero_btn.configure(state="normal" if fresh and state and not state.running else "disabled")
        self.clear_btn.configure(state="normal" if fresh and state and not state.running else "disabled")
        self.axis_status.configure(text=self.cards[self.axis][2].cget("text"))
        if state:
            suffix = "（状态已过期）" if not fresh else ""
            ppr = self.calibrations[self.axis].ppr
            target='连续' if state.mode=='SPEED' else str(state.target)
            self.metrics.set(f"位置 {state.position:+d} 脉冲    速度 {state.rpm*PPR/ppr:.2f} rpm    已发 {state.emitted}/{target}    PUL {state.pul_hz:.2f} Hz（定时器）{suffix}")
        factor = PPR/self.calibrations[self.axis].ppr
        history = [(t-(now-30), v*factor) for t, v in self.histories[self.axis] if t >= now-30]
        self.history_chart.update_plot(history if fresh else [], 30, 200*factor, COLORS[self.axis-1], message="状态已过期" if self.connected and state else "未连接设备，暂无实时数据")
        alive = self.link is not None and self.link.is_alive()
        self.connect_btn.configure(text="断开连接" if alive else "连接设备")
        self.demo_btn.configure(state="disabled" if alive else "normal")
        self.ports.configure(state="disabled" if alive else "readonly")
        self.refresh_btn.configure(state="disabled" if alive else "normal")
        if self.closing and not alive:
            self.root.destroy()
            return
        self.root.after(80, self.tick)

    def export_log(self):
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("文本记录", "*.txt")], initialfile="四轴通信记录.txt")
        if filename:
            try:
                Path(filename).write_text("\n".join(self.log_lines)+"\n", encoding="utf-8")
            except OSError as exc:
                messagebox.showerror("保存失败", str(exc))

    def close(self):
        self.closing = True
        if self.link:
            self.link.close()
        self.connection_note.set("关闭前请求全部轴减速停止…")


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--demo", action="store_true", help="Open explicit offline simulation")
    mode.add_argument("--port", help="Connect to a specified serial port without starting motion")
    args = parser.parse_args()
    if os.name == "nt":
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    root = tk.Tk()
    controller = App(root, args.demo)
    if args.port:
        controller.port_var.set(args.port)
        root.after(200, lambda: controller.connect(False))
    root.mainloop()


if __name__ == "__main__":
    main()

"""LED view using the shared motor/LED link; never opens a serial port."""
import time
import tkinter as tk
from tkinter import ttk


class LedPanel:
    def __init__(self,parent,send):
        self.send=send;self.state=None;self.updated=0;self.pending_read=False;self.initial=True
        self.controls=[];self.canvases=[]
        frame=ttk.Frame(parent,padding=20);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='三灯独立控制与流水灯',font=('Microsoft YaHei UI',18,'bold')).pack(anchor='w')
        ttk.Label(frame,text='与电机共用一个串口；切换页签不会停止运动。实体 KEY1～KEY5 仅控制 LED。').pack(anchor='w',pady=10)
        cards=ttk.Frame(frame);cards.pack(fill='x',pady=12)
        for i,pin in enumerate(('PH9','PE5','PE6'),1):
            cards.columnconfigure(i-1,weight=1,uniform='leds')
            card=ttk.LabelFrame(cards,text=f'LED{i} / {pin}',padding=12)
            card.grid(row=0,column=i-1,sticky='nsew',padx=5)
            canvas=tk.Canvas(card,width=120,height=90,highlightthickness=0,bg='white');canvas.pack(fill='x')
            self.canvases.append(canvas)
            row=ttk.Frame(card);row.pack(fill='x')
            self.button(row,'点亮',f'LED {i} ON');self.button(row,'熄灭',f'LED {i} OFF')
        row=ttk.Frame(frame);row.pack(fill='x',pady=8)
        for label,cmd in [('全部点亮','ALL ON'),('全部熄灭','ALL OFF'),('恢复 LED 默认','LEDRESET')]:self.button(row,label,cmd)
        flow=ttk.LabelFrame(frame,text='流水灯设置',padding=16);flow.pack(fill='x',pady=14)
        row=ttk.Frame(flow);row.pack(fill='x')
        self.interval=tk.StringVar(value='300');self.direction=tk.StringVar(value='正向');self.cycles=tk.StringVar(value='0')
        ttk.Label(row,text='每灯间隔 / ms').pack(side='left')
        ttk.Spinbox(row,from_=50,to=60000,increment=50,textvariable=self.interval,width=8).pack(side='left',padx=8)
        ttk.Combobox(row,textvariable=self.direction,values=['正向','反向'],width=7,state='readonly').pack(side='left',padx=8)
        ttk.Label(row,text='循环次数').pack(side='left')
        ttk.Spinbox(row,from_=0,to=9999,textvariable=self.cycles,width=7).pack(side='left',padx=8)
        self.button(row,'写入设置',self.write);self.button(row,'读取设置',self.read)
        ttk.Label(flow,text='0 次表示无限；三个灯各亮一次算一圈。写入后暂停，点击“重新开始”从 LED1 运行。').pack(anchor='w',pady=12)
        row=ttk.Frame(flow);row.pack(fill='x')
        for label,cmd in [('启动/继续','FLOW START'),('暂停','FLOW PAUSE'),('重新开始','FLOW RESTART'),('停止并熄灭','FLOW STOP')]:self.button(row,label,cmd)
        self.status=tk.StringVar(value='等待 LED 状态')
        ttk.Label(frame,textvariable=self.status).pack(anchor='w',pady=12)
        self.note=tk.StringVar(value='灯光操作不修改电机参数；LED 恢复默认不复位芯片，不停止电机。')
        ttk.Label(frame,textvariable=self.note,wraplength=950).pack(anchor='w')

    def button(self,parent,title,command):
        callback=command if callable(command) else lambda:self.send(command)
        b=ttk.Button(parent,text=title,command=callback);b.pack(side='left',padx=4)
        self.controls.append(b)

    def receive(self,state):
        self.state=state;self.updated=time.monotonic()
        if self.initial or self.pending_read:
            self.interval.set(str(state['MS']));self.direction.set('正向' if state['DIR']==1 else '反向')
            self.cycles.set(str(state['CYCLES']));self.initial=self.pending_read=False

    def write(self):
        try:
            ms,cycles=int(self.interval.get()),int(self.cycles.get())
            if not 50<=ms<=60000 or not 0<=cycles<=9999:raise ValueError()
        except ValueError:self.note.set('间隔应为 50～60000 的整数，循环次数为 0～9999 的整数。');return
        if self.send(f"FLOW CONFIG {ms} {1 if self.direction.get()=='正向' else -1} {cycles}"):
            self.note.set('已发送设置，板上实际值见状态；点击重新开始运行。')

    def read(self):
        self.pending_read=True;self.send('LEDSTATUS')

    def refresh(self,connected):
        fresh=connected and self.state is not None and time.monotonic()-self.updated<1
        for b in self.controls:b.configure(state='normal' if fresh else 'disabled')
        for i,c in enumerate(self.canvases):
            c.delete('all');x=max(40,c.winfo_width()/2);on=fresh and self.state['MASK']&(1<<i)
            c.create_oval(x-23,8,x+23,54,fill=('#22c55e' if on else '#cbd5e1') if fresh else '#94a3b8',outline='')
            c.create_text(x,73,text=('亮' if on else '灭') if fresh else '未知')
        if fresh:
            s=self.state;mode='手动' if s['MODE']=='MANUAL' else ('流水运行' if s['RUN'] else '流水暂停/完成')
            target=str(s['CYCLES']) if s['CYCLES'] else '无限'
            self.status.set(f"板上状态：{mode} · {s['MS']}ms / 灯 · {'正向' if s['DIR']==1 else '反向'} · 已完成 {s['DONE']} / {target} 圈 · 按键事件 {s['KEYS']}")
        else:self.status.set('未连接或 LED 状态已过期；灯光显示为未知')

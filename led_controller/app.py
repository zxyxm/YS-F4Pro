import argparse
import queue
import time
import tkinter as tk
from tkinter import ttk
import serial.tools.list_ports
from link import Link


class App:
    def __init__(self, root, demo=False, port=None):
        self.root, self.events = root, queue.Queue()
        self.link, self.state = None, None
        self.ready, self.last_update, self.closing = False, 0, False
        root.title('YS-F4Pro · LED 与流水灯控制台')
        root.geometry('900x760');root.minsize(850,720)
        root.protocol('WM_DELETE_WINDOW', self.close)
        style=ttk.Style();style.theme_use('clam')
        style.configure('TButton',padding=(12,7),font=('Microsoft YaHei UI',10))
        style.configure('TLabel',font=('Microsoft YaHei UI',10))
        frame=ttk.Frame(root,padding=18);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='YS-F4Pro  LED 控制',font=('Microsoft YaHei UI',20,'bold')).pack(anchor='w')
        self.note=tk.StringVar(value='请连接 USB2 串口；首次需先下载流水灯串口版固件。')
        ttk.Label(frame,textvariable=self.note,wraplength=790).pack(anchor='w',pady=(8,12))
        row=ttk.Frame(frame);row.pack(fill='x')
        self.port=tk.StringVar(value=port or '')
        self.ports=ttk.Combobox(row,textvariable=self.port,width=12,state='readonly');self.ports.pack(side='left')
        ttk.Button(row,text='刷新',command=self.refresh).pack(side='left',padx=6)
        self.connect_btn=ttk.Button(row,text='连接',command=lambda:self.connect(False));self.connect_btn.pack(side='left')
        self.demo_btn=ttk.Button(row,text='离线演示',command=lambda:self.connect(True));self.demo_btn.pack(side='left',padx=6)
        ttk.Label(row,text='115200 · 8N1').pack(side='right')
        cards=ttk.Frame(frame);cards.pack(fill='x',pady=16)
        self.canvases,self.controls=[],[]
        for i,pin in enumerate(('PH9','PE5','PE6'),1):
            cards.columnconfigure(i-1,weight=1,uniform='led_cards')
            card=ttk.LabelFrame(cards,text=f'LED{i} / {pin}',padding=10)
            card.grid(row=0,column=i-1,sticky='nsew',padx=4)
            canvas=tk.Canvas(card,width=120,height=76,highlightthickness=0);canvas.pack(fill='x')
            self.canvases.append(canvas)
            buttons=ttk.Frame(card);buttons.pack(fill='x')
            for action,title in [('ON','点亮'),('OFF','熄灭')]:
                button=ttk.Button(buttons,text=title,width=5,command=lambda n=i,a=action:self.send(f'LED {n} {a}'));button.pack(side='left',expand=True);self.controls.append(button)
        row=ttk.Frame(frame);row.pack(fill='x')
        for title,command in [('全部点亮','ALL ON'),('全部熄灭','ALL OFF'),('恢复默认','RESET')]:
            button=ttk.Button(row,text=title,command=lambda c=command:self.send(c));button.pack(side='left',padx=4);self.controls.append(button)
        flow=ttk.LabelFrame(frame,text='流水灯',padding=12);flow.pack(fill='x',pady=12)
        settings=ttk.Frame(flow);settings.pack(fill='x',pady=(0,8))
        self.interval=tk.StringVar(value='300');self.direction=tk.StringVar(value='正向');self.cycles=tk.StringVar(value='0')
        ttk.Label(settings,text='每灯间隔 / ms').pack(side='left')
        ttk.Spinbox(settings,from_=50,to=60000,increment=50,textvariable=self.interval,width=7).pack(side='left',padx=5)
        ttk.Combobox(settings,textvariable=self.direction,values=['正向','反向'],width=6,state='readonly').pack(side='left',padx=5)
        ttk.Label(settings,text='循环次数').pack(side='left')
        ttk.Spinbox(settings,from_=0,to=9999,textvariable=self.cycles,width=6).pack(side='left',padx=5)
        self.extended_controls=[]
        for title,action in [('写入设置',self.write_flow),('读取设置',self.read_flow)]:
            button=ttk.Button(settings,text=title,command=action);button.pack(side='left',padx=3)
            self.controls.append(button);self.extended_controls.append(button)
        ttk.Label(flow,text='0 次 = 无限循环；一圈为三个灯各亮一次；写入后暂停，点击重新开始运行。').pack(anchor='w',pady=(0,8))
        actions=ttk.Frame(flow);actions.pack(fill='x')
        for title,command in [('启动/继续','FLOW START'),('暂停','FLOW PAUSE'),('正向','FLOW DIR 1'),('反向','FLOW DIR -1')]:
            button=ttk.Button(actions,text=title,width=7,command=lambda c=command:self.send(c));button.pack(side='left',padx=3);self.controls.append(button)
        for title,command in [('重新开始','FLOW RESTART'),('停止并熄灭','FLOW STOP')]:
            button=ttk.Button(actions,text=title,command=lambda c=command:self.send(c));button.pack(side='left',padx=3)
            self.controls.append(button);self.extended_controls.append(button)
        self.flow_info=tk.StringVar(value='等待下位机流水灯设置')
        ttk.Label(flow,textvariable=self.flow_info).pack(anchor='w',pady=(8,0))
        self.pending_read=False;self.initial_read=True
        self.status=tk.StringVar(value='尚未收到状态')
        ttk.Label(frame,textvariable=self.status).pack(anchor='w',pady=(0,8))
        raw=ttk.Frame(frame);raw.pack(fill='x')
        self.command=tk.StringVar(value='STATUS')
        ttk.Entry(raw,textvariable=self.command).pack(side='left',fill='x',expand=True)
        button=ttk.Button(raw,text='发送报文',command=lambda:self.send(self.command.get().strip()));button.pack(side='left',padx=5);self.controls.append(button)
        self.log=tk.Text(frame,height=7,font=('Consolas',9),state='disabled');self.log.pack(fill='both',expand=True,pady=(8,0))
        self.refresh()
        if port:self.port.set(port)
        root.after(50,self.tick)
        if demo or port:root.after(150,lambda:self.connect(demo))

    def refresh(self):
        values=[p.device for p in serial.tools.list_ports.comports()];self.ports['values']=values
        if not self.port.get() and values:self.port.set(values[0])

    def connect(self,demo):
        if self.link and self.link.is_alive():self.link.close();return
        if not demo and not self.port.get():self.note.set('未发现串口，可以先用离线演示。');return
        self.ready=False;self.state=None;self.last_update=0
        self.initial_read=True
        self.link=Link(self.events,self.port.get(),demo);self.link.start();self.note.set('正在握手…')

    def send(self,command):
        try:
            if not self.link or not self.ready:raise ValueError('请先连接 LED 固件或离线演示')
            self.link.send(command)
        except ValueError as exc:self.note.set(str(exc))

    def write_flow(self):
        try:
            ms,cycles=int(self.interval.get()),int(self.cycles.get())
            if not 50<=ms<=60000 or not 0<=cycles<=9999:raise ValueError()
        except ValueError:
            self.note.set('间隔请输入 50～60000 的整数，循环次数请输入 0～9999 的整数。');return
        self.send(f"FLOW CONFIG {ms} {1 if self.direction.get()=='正向' else -1} {cycles}")

    def read_flow(self):
        self.pending_read=True;self.send('STATUS')

    def add_log(self,text):
        self.log.configure(state='normal');self.log.insert('end',time.strftime('%H:%M:%S')+' '+text+'\n')
        if int(self.log.index('end-1c').split('.')[0])>250:self.log.delete('1.0','51.0')
        self.log.see('end');self.log.configure(state='disabled')

    def tick(self):
        for _ in range(100):
            try:kind,data=self.events.get_nowait()
            except queue.Empty:break
            if kind=='ready':self.ready=True;self.note.set('离线演示 · 不连接硬件' if data else f'已连接 {self.port.get()} · LED 固件')
            elif kind=='state':
                self.state=data;self.last_update=time.monotonic()
                if self.pending_read or self.initial_read:
                    self.interval.set(str(data['MS']));self.direction.set('正向' if data['DIR']==1 else '反向')
                    self.cycles.set(str(data.get('CYCLES',0)));self.pending_read=False;self.initial_read=False
            elif kind=='tx':self.add_log('→ '+data)
            elif kind=='rx' and not data.startswith('LEDSTATE '):self.add_log('← '+data)
            elif kind=='error':self.note.set(data);self.add_log('错误：'+data)
            elif kind=='closed':self.ready=False
        fresh=self.ready and time.monotonic()-self.last_update<1
        for button in self.controls:button.configure(state='normal' if fresh else 'disabled')
        for button in self.extended_controls:button.configure(state='normal' if fresh and 'CYCLES' in (self.state or {}) else 'disabled')
        if fresh and 'CYCLES' in (self.state or {}):
            s=self.state;limit=s['CYCLES'];done=s['DONE']
            progress=f"{done} / {limit} 圈" if limit else f"{done} 圈（无限循环）"
            result=' · 已完成并熄灭' if s['MODE']=='FLOW' and limit and done>=limit and not s['MASK'] else ''
            self.flow_info.set(f"板上设置：{s['MS']}ms / 灯 · {'正向' if s['DIR']==1 else '反向'} · 已完成 {progress}{result}")
        else:self.flow_info.set('需要升级 LED 固件才能使用循环设置' if fresh else '等待下位机流水灯设置')
        for i,canvas in enumerate(self.canvases):
            canvas.delete('all');x=max(40,canvas.winfo_width()/2)
            on=fresh and self.state and self.state['MASK']&(1<<i)
            canvas.create_oval(x-22,7,x+22,51,fill=('#22c55e' if on else '#cbd5e1') if fresh else '#94a3b8',outline='')
            canvas.create_text(x,65,text=('亮' if on else '灭') if fresh else '未知')
        if fresh and self.state:
            s=self.state;mode='手动' if s['MODE']=='MANUAL' else ('流水运行' if s['RUN'] else '流水暂停')
            self.status.set(f"模式：{mode}   方向：{'正向' if s['DIR']==1 else '反向'}   间隔：{s['MS']}ms   按键事件：{s['KEYS']}")
        else:self.status.set('未连接或状态已过期；LED 显示不代表板上实际状态')
        alive=self.link and self.link.is_alive()
        self.connect_btn.configure(text='断开' if alive else '连接');self.demo_btn.configure(state='disabled' if alive else 'normal')
        self.ports.configure(state='disabled' if alive else 'readonly')
        if self.closing and not alive:self.root.destroy();return
        self.root.after(60,self.tick)

    def close(self):
        self.closing=True
        if self.link:self.link.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group();group.add_argument('--demo',action='store_true');group.add_argument('--port');args=parser.parse_args()
    root=tk.Tk();App(root,args.demo,args.port);root.mainloop()

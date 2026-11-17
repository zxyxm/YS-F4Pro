"""One window and one serial worker for the combined firmware."""
import argparse
import os
import tkinter as tk
from motor_app import App as MotorApp
from led_panel import LedPanel


class App(MotorApp):
    def _build(self):
        super()._build()
        self.led=LedPanel(self.led_tab,self.send)

    def handle_event(self,kind,data):
        if kind=='led_state':self.led.receive(data)
        else:
            if kind in ('ready','closed'):self.led.initial=True
            super().handle_event(kind,data)

    def tick(self):
        # Base tick consumes all events before rendering motor state.
        super().tick()
        if not self.closing:self.led.refresh(self.connected)


def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group()
    group.add_argument('--demo',action='store_true');group.add_argument('--port');args=parser.parse_args()
    if os.name=='nt':
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    root=tk.Tk();app=App(root,demo=args.demo)
    if args.port:app.port_var.set(args.port);root.after(200,lambda:app.connect(False))
    root.mainloop()


if __name__=='__main__':main()

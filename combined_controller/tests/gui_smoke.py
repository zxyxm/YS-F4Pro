import sys,time,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from app import App

with tempfile.TemporaryDirectory() as folder:
    root=tk.Tk();a=App(root,demo=True,settings_path=Path(folder)/'settings.json')
    def wait(condition):
        end=time.monotonic()+4
        while time.monotonic()<end:
            root.update();time.sleep(.01)
            if condition():return
        raise AssertionError(a.connection_note.get())
    try:
        wait(lambda:a.connected and len(a.states)==4 and len(a.board_params)==4 and a.led.state is not None)
        a.motion_modes[1].set('速度模式');a.settings[1]['rpm'].set('200')
        a.settings[1]['accel'].set('400');a.settings[1]['decel'].set('400');a.move(1)
        wait(lambda:a.states[1].running and a.states[1].rpm>=199)
        a.main_tabs.select(a.led_tab);root.update()
        a.send('ALL OFF');wait(lambda:a.led.state['MASK']==0)
        a.send('LED 3 ON');wait(lambda:a.led.state['MASK']==4)
        assert a.states[1].running
        a.led.interval.set('100');a.led.direction.set('反向');a.led.cycles.set('2');a.led.write()
        wait(lambda:a.led.state['CYCLES']==2 and a.led.state['DIR']==-1)
        a.send('FLOW RESTART');wait(lambda:a.led.state['DONE']==2 and a.led.state['MASK']==0)
        assert a.states[1].running
        a.led.interval.set('999');a.led.read();wait(lambda:a.led.interval.get()=='100')
        for size in ('1240x900','1100x840'):
            root.geometry(size);root.update()
            for w in a.led.controls+a.led.canvases:
                assert w.winfo_ismapped()
                assert w.winfo_rootx()+w.winfo_width()<=root.winfo_rootx()+root.winfo_width()
                assert w.winfo_rooty()+w.winfo_height()<=root.winfo_rooty()+root.winfo_height()
        a.main_tabs.select(0);a.send('STOP ALL');wait(lambda:not a.states[1].running)
        a.send('LEDRESET');wait(lambda:a.led.state['MS']==300 and a.led.state['CYCLES']==0)
        a.close();wait(lambda:not a.link.is_alive())
    finally:
        if a.link and a.link.is_alive():a.link.close();a.link.join(2)
        try:root.destroy()
        except tk.TclError:pass
print('Combined GUI: shared connection, tabs, concurrent motor/LED, all 3 LEDs, finite loop, read/write, layouts and close passed')

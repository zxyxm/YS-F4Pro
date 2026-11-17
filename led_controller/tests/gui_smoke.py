import sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from app import App
root=tk.Tk();root.withdraw();a=App(root,demo=True)
def wait(condition):
    deadline=time.monotonic()+2
    while time.monotonic()<deadline:
        root.update();time.sleep(.01)
        if condition():return
    raise AssertionError(a.note.get())
wait(lambda:a.ready and a.state is not None)
root.deiconify()
for width,height in [(900,760),(850,720)]:
    root.geometry(f'{width}x{height}');root.update()
    for widget in a.canvases+a.controls[:6]:
        assert widget.winfo_ismapped()
        assert widget.winfo_rootx()>=root.winfo_rootx()
        assert widget.winfo_rootx()+widget.winfo_width()<=root.winfo_rootx()+root.winfo_width()
    assert max(c.winfo_width() for c in a.canvases)-min(c.winfo_width() for c in a.canvases)<=1
    for widget in a.controls:
        assert widget.winfo_ismapped()
        assert widget.winfo_rootx()+widget.winfo_width()<=root.winfo_rootx()+root.winfo_width()
        assert widget.winfo_rooty()+widget.winfo_height()<=root.winfo_rooty()+root.winfo_height()
root.withdraw()
a.interval.set('50');a.cycles.set('2');a.direction.set('反向');a.write_flow()
wait(lambda:a.state['MS']==50 and a.state['CYCLES']==2 and a.state['DIR']==-1)
a.send('FLOW RESTART');wait(lambda:a.state['DONE']==2 and a.state['RUN']==0)
assert a.state['MASK']==0
a.interval.set('999');a.read_flow();wait(lambda:a.interval.get()=='50')
a.send('ALL OFF');wait(lambda:a.state['MASK']==0)
a.send('LED 3 ON');wait(lambda:a.state['MASK']==4)
a.send('FLOW MS 100');a.send('FLOW DIR -1');a.send('FLOW START')
wait(lambda:a.state['RUN']==1 and a.state['MS']==100 and a.state['DIR']==-1)
a.send('FLOW PAUSE');wait(lambda:a.state['RUN']==0)
a.send('RESET');wait(lambda:a.state['MS']==300 and a.state['DIR']==1)
a.close();wait(lambda:not a.link.is_alive())
try:root.destroy()
except tk.TclError:pass
print('LED GUI: handshake, manual, flow, interval/direction, pause/reset and close passed')

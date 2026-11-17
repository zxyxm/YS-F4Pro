import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk,time
import tempfile
from app import App
temporary = tempfile.TemporaryDirectory()
root=tk.Tk();app=App(root,demo=True,settings_path=Path(temporary.name)/'settings.json')
def advance(seconds):
 deadline=time.monotonic()+seconds
 while time.monotonic()<deadline:root.update();time.sleep(.01)
advance(.8)
assert app.connected and app.is_demo and len(app.states)==4 and len(app.board_params)==4
app.settings[1]['accel'].set('401');app.preview();assert '参数无效' in app.preview_chart.empty_message
app.move(1);assert not app.pending
app.read_parameters();advance(.3);assert app.settings[1]['accel'].get()=='30'
app.settings[1]['distance'].set('16000');app.write_parameters();advance(.3);assert app.parameters_match();app.move(1);advance(.1)
app.select_axis(2);assert app.settings[2]['distance'].get()=='3200'
app.settings[2]['distance'].set('16000');app.write_parameters();advance(.3);app.move(-1);advance(.4)
assert app.states[1].running and app.states[2].running
assert app.states[1].position>0 and app.states[2].position<0
app.send('STOP 1');advance(.5)
assert app.states[2].running
app.select_axis(4);app.settings[4]['curve'].set('S 型平滑定位');app.settings[4]['distance'].set('16000');app.write_parameters();advance(.3);app.move(1);advance(.3)
assert app.states[4].running
app.send('STOP ALL');advance(1.7)
app.select_axis(1)
app.ppr_draft.set('6400');app.confirm_draft.set(False);app.apply_configuration()
assert app.calibrations[1].ppr==3200
app.confirm_draft.set(True);app.apply_configuration()
assert app.calibrations[1].ppr==6400 and app.calibrations[2].ppr==3200
app.settings[1]['unit'].set('转');app.settings[1]['distance'].set('1')
for key in ('rpm','accel','decel'):app.settings[1][key].set('15')
assert app.profile().pulses==6400 and app.profile().rpm==30
app.write_parameters();advance(.3);assert app.parameters_match()
assert all('未知' in label.cget('text') for label in app.sensor_labels)
before={i:(s.position,s.emitted,s.done) for i,s in app.states.items()}
app.fill_raw('GET 1\nSTATUS');app.send_raw();advance(.3)
assert any('→ GET 1' in line for line in app.log_lines)
assert before=={i:(s.position,s.emitted,s.done) for i,s in app.states.items()}
app.motion_modes[1].set('速度模式');app.preview();app.move(-1);advance(1.5)
assert app.states[1].running and app.states[1].mode=='SPEED'
assert abs(app.states[1].pul_hz-1600)<1
app.send('STOP 1');advance(1.6);assert not app.states[1].running
root.update()
for tab in range(3):
 app.tabs.select(tab);root.update()
 for w in [app.forward,app.reverse,app.stop_btn,app.write_btn,app.read_btn,app.tabs]:
  assert w.winfo_rooty()+w.winfo_height() <= root.winfo_rooty()+root.winfo_height(),str(w)
assert root.winfo_width()>=1060
app.close();advance(.4)
temporary.cleanup()
print('GUI smoke: motion, per-axis calibration, exact wire scaling, unknown sensors, raw command sending, tabs and close OK')

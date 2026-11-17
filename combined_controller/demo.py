"""Explicit offline simulator. This module never opens a serial port."""
import math
import time
from dataclasses import dataclass
from protocol import Profile, PPR
from led_device import Demo as LedDemo

HELLO = f"HELLO YS_F4Pro AXES=4 PROTO=5 PARAMS=1 PPR={PPR} RPM_MAX=200 ACC_MAX=400 STEPS_MAX=32000 SPEED=1 LED=1"


@dataclass
class SimAxis:
    position: int = 0
    emitted: int = 0
    target: int = 0
    done: int = 0
    direction: int = 1
    start_position: int = 0
    started: float = 0
    profile: Profile | None = None
    stop_velocity: float = 0
    stop_decel: float = 0
    stop_duration: float = 0
    stopping: bool = False
    stop_base: int = 0
    speed_mode: bool = False

    def update(self, now):
        if self.profile is None:
            return 0.0
        elapsed = now - self.started
        if self.stopping:
            t = min(elapsed, self.stop_duration)
            pos = self.stop_base+min(self.target-self.stop_base, self.stop_velocity*t-self.stop_decel*t*t/2)
            rpm = max(0, self.stop_velocity-self.stop_decel*t)*60/PPR
            duration = self.stop_duration
        elif self.speed_mode:
            p=self.profile;acc=p.accel*PPR/60;v=p.rpm*PPR/60;ramp=v/acc
            pos=acc*elapsed*elapsed/2 if elapsed<ramp else v*(elapsed-ramp/2)
            rpm=min(p.rpm,p.accel*elapsed);duration=float('inf')
        else:
            pos, rpm = self.profile.sample(elapsed)
            duration = self.profile.duration
        self.emitted = max(0, min(self.target, int(pos + 1e-6)))
        self.position = self.start_position + self.direction*self.emitted
        if elapsed >= duration:
            self.emitted = self.target
            self.position = self.start_position+self.direction*self.target
            self.profile = None
            self.done += 1
            rpm = 0
        return rpm

    def stop(self, now):
        rpm = self.update(now)
        if self.profile is None or self.stopping:
            return
        velocity = rpm*PPR/60
        if velocity < 1:
            self.profile = None
            self.done += 1
            return
        remaining = self.target-self.emitted
        count = min(remaining, max(1, math.ceil(velocity*velocity/(2*self.profile.decel*PPR/60))))
        self.stop_base = self.emitted
        self.target = self.emitted+count
        self.stop_velocity = velocity
        self.stop_decel = velocity*velocity/(2*count)
        self.stop_duration = 2*count/velocity
        self.started = now
        self.stopping = True


class DemoDevice:
    def __init__(self):
        self.led = LedDemo()
        self.axes = [SimAxis() for _ in range(4)]
        self.created = time.monotonic()
        self.parameters = [Profile() for _ in range(4)]
        self.revisions = [0]*4

    def parameter_line(self, axis):
        p = self.parameters[axis-1]
        return f"PARAM {axis} STEPS={p.pulses} RPM={p.rpm} ACC={p.accel} DEC={p.decel} CURVE={p.curve} REV={self.revisions[axis-1]}"

    def handle(self, line):
        if line=="LEDSTATUS":return self.led.handle("STATUS")
        if line=="LEDRESET":return self.led.handle("RESET")
        if line.startswith(("LED ","FLOW ","ALL ")):return self.led.handle(line)
        now = time.monotonic()
        t = line.split()
        for axis in self.axes:
            axis.update(now)
        if t == ["HELLO"]:
            return [HELLO]
        if t == ["STATUS"]:
            lines = []
            for i, a in enumerate(self.axes, 1):
                rpm = a.update(now)
                lines.append(f"STATE {i} {'RUNNING' if a.profile else 'IDLE'} POS={a.position} PULSES={a.emitted}/{a.target} RPM_MILLI={round(rpm*1000)} FAULT=0 DONE={a.done} T={int((now-self.created)*1000)} MODE={'SPEED' if a.speed_mode and not a.stopping else 'POSITION'} PUL_HZ_MILLI={round(rpm*PPR/60*1000)}")
            return lines+self.led.handle("STATUS")
        if t[:1] == ["WATCHDOG"]:
            return ["OK WATCHDOG"]
        if t == ["STOP", "ALL"]:
            for a in self.axes:
                a.stop(now)
            return ["OK STOP ALL"]
        try:
            axis_id = int(t[1])
            if not 1 <= axis_id <= 4:
                raise ValueError()
            a = self.axes[axis_id-1]
            if t[0]=='SPEED' and len(t)==6:
                if a.profile:return [f'ERR BUSY {axis_id}']
                direction,rpm,acc,dec=map(int,t[2:])
                if direction not in (-1,1):raise ValueError()
                p=Profile(PPR,rpm,acc,dec);p.validate()
                a.profile,a.direction=p,direction
                a.start_position,a.emitted,a.target=a.position,0,2**32-1
                a.started,a.stopping,a.speed_mode=now,False,True
                return [f'OK SPEED {axis_id}']
            if t[0] == "GET" and len(t) == 2:
                return [self.parameter_line(axis_id)]
            if t[0] == "SET" and len(t) == 7:
                if a.profile:
                    return [f"ERR BUSY {axis_id}"]
                p = Profile(*(int(v) for v in t[2:6]), t[6])
                p.validate()
                self.parameters[axis_id-1] = p
                self.revisions[axis_id-1] += 1
                return [f"OK SET {axis_id}", self.parameter_line(axis_id)]
            if t[0] == "RUN" and len(t) == 3:
                direction = int(t[2])
                if direction not in (-1, 1):
                    raise ValueError()
                p = self.parameters[axis_id-1]
                response = self.handle(p.command(axis_id, direction))
                return [x.replace("OK MOVE", "OK RUN") for x in response]
            if t[0] == "MOVE" and len(t) == 7:
                if a.profile:
                    return [f"ERR BUSY {axis_id}"]
                steps, rpm, acc, dec = map(int, t[2:6])
                p = Profile(abs(steps), rpm, acc, dec, t[6])
                p.validate()
                a.profile, a.direction = p, 1 if steps > 0 else -1
                a.start_position, a.emitted, a.target = a.position, 0, abs(steps)
                a.started, a.stopping, a.speed_mode = now, False, False
            elif t[0] == "STOP" and len(t) == 2:
                a.stop(now)
            elif t[0] in ("ZERO", "CLEAR") and len(t) == 2:
                if a.profile:
                    return [f"ERR BUSY {axis_id}"]
                if t[0] == "ZERO":
                    a.position = 0
            else:
                raise ValueError()
            return [f"OK {t[0]} {axis_id}"]
        except (ValueError, IndexError):
            return ["ERR COMMAND"]

"""Protocol v3 and bounded motion previews, independent of the GUI."""
from dataclasses import dataclass
import math

PPR = 3200


@dataclass(frozen=True)
class AxisState:
    axis: int
    running: bool
    position: int
    emitted: int
    target: int
    rpm: float
    fault: int
    done: int
    tick: int
    mode: str = 'POSITION'
    pul_hz: float = 0.0


def parse_state(line: str) -> AxisState | None:
    parts = line.split()
    if not parts or parts[0] != "STATE":
        return None
    if len(parts) not in (9,11) or parts[2] not in ("IDLE", "RUNNING"):
        raise ValueError("Invalid STATE frame")
    axis = int(parts[1])
    fields = dict(item.split("=", 1) for item in parts[3:])
    if len(fields) != len(parts)-3 or set(fields) not in ({"POS", "PULSES", "RPM_MILLI", "FAULT", "DONE", "T"},{"POS", "PULSES", "RPM_MILLI", "FAULT", "DONE", "T", "MODE", "PUL_HZ_MILLI"}):
        raise ValueError("Invalid STATE fields")
    return _state(axis, parts[2], fields)


def _state(axis, state, fields):
    emitted, target = (int(v) for v in fields["PULSES"].split("/"))
    position, rpm, fault, done, tick = (int(fields[k]) for k in ("POS", "RPM_MILLI", "FAULT", "DONE", "T"))
    if not 1 <= axis <= 4 or not -(2**31) <= position < 2**31:
        raise ValueError("Invalid axis/position")
    if not 0 <= emitted <= target <= 2**32-1 or not 0 <= rpm <= 200001 or not 0 <= fault <= 99:
        raise ValueError("Invalid motion status")
    if not 0 <= done < 2**32 or not 0 <= tick < 2**32:
        raise ValueError("Invalid counters")
    mode=fields.get('MODE','POSITION');hz=int(fields.get('PUL_HZ_MILLI','0'))
    if mode not in ('POSITION','SPEED') or not 0<=hz<=12000000:raise ValueError('Invalid pulse telemetry')
    return AxisState(axis, state == "RUNNING", position, emitted, target, rpm / 1000, fault, done, tick,mode,hz/1000)


def compatible_hello(line: str) -> bool:
    parts = line.split()
    if parts[:2] != ["HELLO", "YS_F4Pro"]:
        return False
    try:
        fields = dict(item.split("=", 1) for item in parts[2:])
        return all(fields.get(k) == v for k, v in {"PROTO": "4", "PARAMS": "1", "AXES": "4", "PPR": str(PPR), "RPM_MAX": "200", "ACC_MAX":"400", "STEPS_MAX": "32000", "SPEED":"1"}.items())
    except ValueError:
        return False


@dataclass(frozen=True)
class Profile:
    pulses: int = PPR
    rpm: int = 30
    accel: int = 30
    decel: int = 30
    curve: str = "TRAP"

    def validate(self):
        if not 1 <= self.pulses <= 32000 or not 1 <= self.rpm <= 200:
            raise ValueError("位移须为 1～32000 脉冲，速度须为 1～200 rpm")
        if not 1 <= self.accel <= 400 or not 1 <= self.decel <= 400:
            raise ValueError("加速度、减速度须为 1～400 rpm/s")
        if self.curve not in ("TRAP", "S"):
            raise ValueError("不支持的曲线类型")
        if self.duration > 120:
            raise ValueError("本次运动时长超过固件的 120 秒上限")

    @property
    def parameters(self):
        a, d, v = self.accel * PPR / 60, self.decel * PPR / 60, self.rpm * PPR / 60
        v = min(v, math.sqrt(2 * self.pulses * a * d / (a + d)))
        ta, td = v / a, v / d
        tc = max(0, (self.pulses - v*v/(2*a) - v*v/(2*d)) / v)
        return a, d, v, ta, tc, td

    @property
    def duration(self):
        if self.curve == "S":
            return max(1.875 * self.pulses / (self.rpm * PPR / 60), math.sqrt(5.773503 * self.pulses / (min(self.accel, self.decel) * PPR / 60)))
        return sum(self.parameters[3:])

    def sample(self, seconds):
        """Continuous command position (pulses), velocity (rpm)."""
        t = max(0, min(seconds, self.duration))
        if self.curve == "S":
            u = t / self.duration
            return self.pulses * (10*u**3 - 15*u**4 + 6*u**5), self.pulses/self.duration*30*u*u*(1-u)**2*60/PPR
        a, d, v, ta, tc, td = self.parameters
        if t < ta:
            pos, speed = a*t*t/2, a*t
        elif t < ta + tc:
            pos, speed = a*ta*ta/2 + v*(t-ta), v
        else:
            remaining = max(0, ta+tc+td-t)
            pos, speed = self.pulses-d*remaining*remaining/2, d*remaining
        return pos, speed*60/PPR

    def command(self, axis, direction=1):
        self.validate()
        if axis not in range(1, 5) or direction not in (-1, 1):
            raise ValueError("Invalid axis/direction")
        return f"MOVE {axis} {direction*self.pulses} {self.rpm} {self.accel} {self.decel} {self.curve}"

    def set_command(self, axis):
        self.validate()
        if axis not in range(1, 5):
            raise ValueError("Invalid axis")
        return f"SET {axis} {self.pulses} {self.rpm} {self.accel} {self.decel} {self.curve}"


@dataclass(frozen=True)
class AxisParameters:
    axis: int
    profile: Profile
    revision: int


def parse_parameters(line):
    parts = line.split()
    if not parts or parts[0] != "PARAM":
        return None
    if len(parts) != 8:
        raise ValueError("Invalid PARAM frame")
    axis = int(parts[1])
    fields = dict(item.split("=", 1) for item in parts[2:])
    if not 1 <= axis <= 4 or set(fields) != {"STEPS", "RPM", "ACC", "DEC", "CURVE", "REV"}:
        raise ValueError("Invalid PARAM fields")
    profile = Profile(*(int(fields[k]) for k in ("STEPS", "RPM", "ACC", "DEC")), fields["CURVE"])
    profile.validate()
    revision = int(fields["REV"])
    if not 0 <= revision < 2**32:
        raise ValueError("Invalid parameter revision")
    return AxisParameters(axis, profile, revision)

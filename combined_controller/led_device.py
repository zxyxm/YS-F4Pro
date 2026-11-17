"""LED protocol parsing and offline model; no hardware dependencies."""
import time

HELLO = "HELLO YS_F4Pro_LED PROTO=1"


def parse_state(line):
    parts = line.split()
    if len(parts) not in (7, 9) or parts[0] != "LEDSTATE":
        raise ValueError("Invalid LED status")
    d = dict(x.split("=", 1) for x in parts[1:])
    if len(d) != len(parts)-1:
        raise ValueError('Duplicate LED fields')
    if set(d) not in ({"MODE", "RUN", "DIR", "MS", "MASK", "KEYS"},
                       {"MODE", "RUN", "DIR", "MS", "MASK", "KEYS", "CYCLES", "DONE"}):
        raise ValueError("Invalid LED fields")
    result = {k: int(v) if k != "MODE" else v for k, v in d.items()}
    if result['MODE'] not in ('FLOW', 'MANUAL') or result['RUN'] not in (0, 1) or result['DIR'] not in (-1, 1):
        raise ValueError("Invalid LED mode")
    if not 50 <= result['MS'] <= 60000 or not 0 <= result['MASK'] <= 7 or not 0 <= result['KEYS'] < 2**32:
        raise ValueError("Invalid LED values")
    if 'CYCLES' in result and (not 0 <= result['CYCLES'] <= 9999 or not 0 <= result['DONE'] <= (2**32-1)//3):
        raise ValueError('Invalid cycle values')
    return result


class Demo:
    def __init__(self):
        self.reset()

    def reset(self):
        self.state = dict(MODE='FLOW', RUN=1, DIR=1, MS=300, MASK=1, KEYS=0, CYCLES=0, DONE=0)
        self.index = 0
        self.steps = 0
        self.last = time.monotonic()

    def handle(self, command):
        s = self.state
        now = time.monotonic()
        if s['MODE'] == 'FLOW' and s['RUN']:
            steps = int((now-self.last)/(s['MS']/1000))
            if steps:
                if s['CYCLES']:
                    steps = min(steps, s['CYCLES']*3-self.steps)
                self.steps = min(2**32-1, self.steps+steps)
                self.index = (self.index + steps*s['DIR']) % 3
                self.last += steps*s['MS']/1000
                s['DONE'] = self.steps//3
                s['MASK'] = 1 << self.index
                if s['CYCLES'] and self.steps >= s['CYCLES']*3:
                    s.update(RUN=0, MASK=0)
        if command == 'HELLO':
            return [HELLO]
        if command == 'STATUS':
            return ['LEDSTATE '+' '.join(f'{k}={v}' for k, v in s.items())]
        t = command.split()
        try:
            if t == ['RESET']:
                self.reset()
            elif len(t) == 3 and t[0] == 'LED' and t[2] in ('ON', 'OFF') and 1 <= int(t[1]) <= 3:
                bit = 1 << (int(t[1])-1)
                s.update(MODE='MANUAL', RUN=0)
                s['MASK'] = (s['MASK'] | bit) if t[2] == 'ON' else (s['MASK'] & ~bit)
            elif len(t) == 2 and t[0] == 'ALL' and t[1] in ('ON', 'OFF'):
                s.update(MODE='MANUAL', RUN=0, MASK=7 if t[1] == 'ON' else 0)
            elif t[:1] == ['FLOW']:
                if len(t) == 2 and t[1] in ('RESTART', 'STOP'):
                    self.index = self.steps = 0
                    s.update(MODE='FLOW', RUN=int(t[1]=='RESTART'), MASK=1 if t[1]=='RESTART' else 0, DONE=0)
                elif len(t) == 5 and t[1] == 'CONFIG':
                    ms, direction, cycles = map(int, t[2:])
                    if not 50 <= ms <= 60000 or direction not in (-1, 1) or not 0 <= cycles <= 9999:
                        raise ValueError()
                    self.steps = 0
                    s.update(MS=ms, DIR=direction, CYCLES=cycles, DONE=0, RUN=0)
                elif len(t) == 2 and t[1] in ('START', 'PAUSE'):
                    if t[1] == 'START' and (s['MODE'] == 'MANUAL' or not s['MASK'] or (s['CYCLES'] and self.steps >= s['CYCLES']*3)):
                        self.index = self.steps = 0
                        s.update(MASK=1, DONE=0)
                    elif s['MODE'] == 'MANUAL':
                        s['MASK'] = 1 << self.index
                    s.update(MODE='FLOW', RUN=int(t[1] == 'START'))
                elif len(t) == 3 and t[1] == 'DIR' and int(t[2]) in (-1, 1):
                    s['DIR'] = int(t[2])
                elif len(t) == 3 and t[1] == 'MS' and 50 <= int(t[2]) <= 60000:
                    s['MS'] = int(t[2])
                else:
                    raise ValueError()
                self.last = now
            else:
                raise ValueError()
            return ['OK'] + self.handle('STATUS')
        except (ValueError, IndexError):
            return ['ERR COMMAND']

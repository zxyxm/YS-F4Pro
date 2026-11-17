"""COM-port integration test: changes LEDs and RAM parameters; never starts a motor."""
import sys,time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import serial
from protocol import compatible_hello,parse_parameters,parse_state
from led_device import parse_state as led_state


def run(name):
    log=[]
    with serial.Serial(name,115200,timeout=.03,write_timeout=.5) as port:
        def query(cmd,prefix):
            log.append('TX '+cmd);port.write((cmd+'\n').encode('ascii'));end=time.monotonic()+3
            while time.monotonic()<end:
                line=port.readline().decode('ascii').strip()
                if line:log.append('RX '+line)
                if line.startswith(prefix):return line
            raise AssertionError(cmd)
        def led(cmd):return led_state(query(cmd,'LEDSTATE '))
        assert compatible_hello(query('HELLO','HELLO '))
        originals=[parse_parameters(query(f'GET {i}',f'PARAM {i} ')) for i in range(1,5)]
        baseline=[parse_state(query(f'STATUS {i}',f'STATE {i} ')) for i in range(1,5)]
        assert all(not s.running and not s.fault for s in baseline)
        try:
            assert led('ALL OFF')['MASK']==0
            for i in range(1,4):
                assert led(f'LED {i} ON')['MASK']==1<<(i-1)
                assert led(f'LED {i} OFF')['MASK']==0
            assert led('ALL ON')['MASK']==7
            query('STOP ALL','OK STOP ALL')
            assert led('LEDSTATUS')['MASK']==7
            s=led('FLOW CONFIG 50 -1 2');assert s['MS']==50 and s['CYCLES']==2 and s['RUN']==0
            led('FLOW RESTART');time.sleep(.4)
            s=led('LEDSTATUS');assert (s['DONE'],s['MASK'],s['RUN'])==(2,0,0)
            query('FLOW CONFIG 49 1 1','ERR LED COMMAND')
            for i,p in enumerate(originals,1):
                assert parse_parameters(query(f'GET {i}',f'PARAM {i} '))==p
                got=parse_parameters(query(f'SET {i} 32000 200 400 400 TRAP',f'PARAM {i} '))
                assert got.profile.rpm==200 and got.profile.accel==400
                assert led('LEDSTATUS')['DONE']==2
            for i,old in enumerate(baseline,1):
                s=parse_state(query(f'STATUS {i}',f'STATE {i} '))
                assert not s.running and not s.fault and s.pul_hz==0
                assert (s.position,s.emitted,s.done)==(old.position,old.emitted,old.done)
        finally:
            for i,p in enumerate(originals,1):query(p.profile.set_command(i),f'PARAM {i} ')
            s=led('LEDRESET');assert s['RUN']==1 and s['MS']==300 and s['CYCLES']==0
    path=Path(__file__).resolve().parents[2]/'backups/combined-v5-shared-serial-20261117.json'
    path.write_text(json.dumps(dict(port=name,result='passed',motor_start_commands_sent=False,log=log),indent=2),encoding='utf-8')
    print('Combined hardware: v5 handshake, 3 LED outputs, finite flow, motor/LED isolation, 200/400 parameter roundtrip passed; motor positions unchanged; defaults restored')


if __name__=='__main__':run(sys.argv[1])

"""Manual hardware test: turns LEDs on/off and restores default flow."""
import sys,time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import serial
from device import HELLO,parse_state

def run(name):
    log=[]
    with serial.Serial(name,115200,timeout=.03,write_timeout=.5) as port:
        buffer=b''
        def query(command,predicate):
            nonlocal buffer
            port.write((command+'\n').encode('ascii'));log.append('TX '+command)
            deadline=time.monotonic()+3
            while time.monotonic()<deadline:
                buffer+=port.read(port.in_waiting or 1)
                while b'\n' in buffer:
                    line,buffer=buffer.split(b'\n',1);text=line.rstrip(b'\r').decode('ascii');log.append('RX '+text)
                    if predicate(text):return text
            raise AssertionError('Timeout: '+command+' '+repr(log[-6:]))
        def control(command):return parse_state(query(command,lambda t:t.startswith('LEDSTATE ')))
        query('HELLO',lambda t:t==HELLO)
        try:
            assert control('ALL OFF')['MASK']==0
            for i in range(1,4):
                assert control(f'LED {i} ON')['MASK']==1<<(i-1)
                assert control(f'LED {i} OFF')['MASK']==0
            assert control('ALL ON')['MASK']==7
            assert control('FLOW MS 100')['MS']==100
            assert control('FLOW DIR -1')['DIR']==-1
            s=control('FLOW START');assert s['MODE']=='FLOW' and s['RUN']==1
            time.sleep(.15)
            s=control('FLOW PAUSE');assert s['RUN']==0
            time.sleep(.15);assert control('STATUS')['MASK']==s['MASK']
            query('FLOW MS 49',lambda t:t=='ERR COMMAND')
            assert control('STATUS')['MS']==100
            s=control('FLOW CONFIG 100 -1 2');assert s['CYCLES']==2 and s['RUN']==0
            s=control('FLOW RESTART');assert s['DONE']==0 and s['MASK']==1
            time.sleep(.7)
            s=control('STATUS');assert (s['DONE'],s['RUN'],s['MASK'])==(2,0,0)
            time.sleep(.2);assert control('STATUS')['DONE']==2
            s=control('FLOW START');assert s['RUN']==1 and s['DONE']==0
            s=control('FLOW STOP');assert s['RUN']==0 and s['MASK']==0 and s['DONE']==0
            s=control('FLOW CONFIG 50 1 0');assert s['CYCLES']==0
            control('FLOW RESTART');time.sleep(.4)
            s=control('STATUS');assert s['RUN']==1 and s['DONE']>=2
            s=control('FLOW PAUSE');time.sleep(.2);assert control('STATUS')['DONE']==s['DONE']
            query('FLOW CONFIG 100 1 10000',lambda t:t=='ERR COMMAND')
            assert control('STATUS')['CYCLES']==0
        finally:
            s=control('RESET');assert s['MODE']=='FLOW' and s['RUN']==1 and s['MS']==300 and s['DIR']==1
    path=Path(__file__).resolve().parents[2]/'backups'/f'led-serial-{name.lower()}-20261114.json'
    path.write_text(json.dumps({'port':name,'result':'passed','final_state':'default_flow_300ms','log':log},ensure_ascii=False,indent=2),encoding='utf-8')
    print('LED hardware serial passed: individual/all outputs, flow start/pause/direction/interval, invalid command rejection; default flow restored.')

if __name__=='__main__':run(sys.argv[1])

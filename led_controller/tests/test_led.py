import queue
import time
import unittest
from unittest.mock import patch
from device import Demo, HELLO, parse_state
from link import Link

class LEDTests(unittest.TestCase):
    @patch('device.time.monotonic')
    def test_finite_cycles_pause_restart_and_infinite(self,clock):
        clock.return_value=0;d=Demo()
        d.handle('FLOW CONFIG 100 -1 2');d.handle('FLOW RESTART')
        clock.return_value=.101;self.assertEqual(parse_state(d.handle('STATUS')[0])['MASK'],4)
        clock.return_value=.201;self.assertEqual(parse_state(d.handle('STATUS')[0])['MASK'],2)
        clock.return_value=.301;self.assertEqual(parse_state(d.handle('STATUS')[0])['DONE'],1)
        d.handle('FLOW PAUSE');clock.return_value=5
        self.assertEqual(parse_state(d.handle('STATUS')[0])['DONE'],1)
        d.handle('FLOW START');clock.return_value=5.301
        s=parse_state(d.handle('STATUS')[0]);self.assertEqual((s['DONE'],s['RUN'],s['MASK']),(2,0,0))
        d.handle('FLOW START');s=parse_state(d.handle('STATUS')[0]);self.assertEqual((s['DONE'],s['MASK'],s['RUN']),(0,1,1))
        d.handle('FLOW STOP');self.assertEqual(parse_state(d.handle('STATUS')[0])['MASK'],0)
        d.handle('FLOW CONFIG 50 1 0');d.handle('FLOW RESTART');clock.return_value=15.302
        s=parse_state(d.handle('STATUS')[0]);self.assertEqual(s['RUN'],1);self.assertGreater(s['DONE'],0)
        d.handle('FLOW PAUSE');before=d.handle('STATUS')
        for cmd in ('FLOW CONFIG 49 1 2','FLOW CONFIG 100 0 2','FLOW CONFIG 100 1 -1','FLOW CONFIG 100 1 10000','FLOW CONFIG 100 1 2 EXTRA'):
            self.assertEqual(d.handle(cmd),['ERR COMMAND']);self.assertEqual(d.handle('STATUS'),before)

    def test_manual_and_flow(self):
        d=Demo();self.assertEqual(d.handle('HELLO'),[HELLO])
        d.handle('ALL OFF');d.handle('LED 2 ON');s=parse_state(d.handle('STATUS')[0])
        self.assertEqual((s['MASK'],s['MODE'],s['RUN']),(2,'MANUAL',0))
        d.handle('ALL ON');self.assertEqual(parse_state(d.handle('STATUS')[0])['MASK'],7)
        d.handle('FLOW DIR -1');d.handle('FLOW MS 100');d.handle('FLOW START')
        s=parse_state(d.handle('STATUS')[0]);self.assertEqual((s['RUN'],s['DIR'],s['MS']),(1,-1,100))
        d.handle('FLOW PAUSE');self.assertEqual(parse_state(d.handle('STATUS')[0])['RUN'],0)
        d.handle('RESET');s=parse_state(d.handle('STATUS')[0]);self.assertEqual((s['MS'],s['DIR']),(300,1))

    def test_invalid_commands(self):
        d=Demo();d.handle('FLOW PAUSE');before=d.handle('STATUS')
        for command in ('LED 0 ON','LED 4 ON','FLOW MS 49','FLOW MS 60001','FLOW DIR 0','MOVE 1 1600 30 30 30 TRAP'):
            self.assertEqual(d.handle(command),['ERR COMMAND']);self.assertEqual(d.handle('STATUS'),before)
        with self.assertRaises(ValueError):parse_state('LEDSTATE MODE=FLOW RUN=1 DIR=1 MS=300 MASK=8 KEYS=0')

    def test_demo_worker(self):
        events=queue.Queue()
        with patch('link.serial.serial_for_url',side_effect=AssertionError('Serial opened')) as opener:
            link=Link(events,demo=True);link.start();deadline=time.monotonic()+2
            while not link.ready and time.monotonic()<deadline:time.sleep(.01)
            self.assertTrue(link.ready);link.send('ALL OFF');time.sleep(.1);link.close();link.join(1)
            self.assertFalse(link.is_alive());opener.assert_not_called()
        self.assertTrue(any(k=='state' for k,_ in list(events.queue)))

    def test_motor_firmware_identity_never_enables_control(self):
        class WrongDevice:
            def __init__(self):self.commands=[]
            def handle(self,command):
                self.commands.append(command)
                return ['HELLO YS_F4Pro AXES=4 PROTO=3 PPR=1600']
        events=queue.Queue();link=Link(events,demo=True);wrong=WrongDevice();link.demo=wrong
        link.start();link.join(4)
        self.assertFalse(link.is_alive());self.assertFalse(link.ready)
        self.assertTrue(wrong.commands);self.assertEqual(set(wrong.commands),{'HELLO'})
        self.assertTrue(any(k=='error' for k,_ in list(events.queue)))

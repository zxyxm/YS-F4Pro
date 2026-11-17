import queue
import time
import unittest
from unittest.mock import patch
from demo import DemoDevice,HELLO
from protocol import compatible_hello,parse_state
from led_device import parse_state as led_state
from transport import ControllerLink


class CombinedTests(unittest.TestCase):
    def test_identity_rejects_both_standalone_firmwares(self):
        self.assertTrue(compatible_hello(HELLO))
        self.assertFalse(compatible_hello(HELLO.replace('PROTO=5','PROTO=4')))
        self.assertFalse(compatible_hello(HELLO.replace(' LED=1','')))
        self.assertFalse(compatible_hello('HELLO YS_F4Pro_LED PROTO=1'))

    @patch('demo.time.monotonic')
    @patch('led_device.time.monotonic')
    def test_led_commands_isolated_from_continuous_motor(self,led_clock,motor_clock):
        led_clock.return_value=motor_clock.return_value=0
        d=DemoDevice();d.handle('SPEED 2 -1 200 400 400')
        motor_clock.return_value=led_clock.return_value=1
        d.handle('ALL ON');d.handle('LED 2 OFF')
        self.assertEqual(led_state(d.handle('LEDSTATUS')[0])['MASK'],5)
        s=parse_state(d.handle('STATUS')[1]);self.assertTrue(s.running);self.assertEqual(s.rpm,200)
        position=s.position;d.handle('LEDRESET')
        self.assertEqual(parse_state(d.handle('STATUS')[1]).position,position)
        self.assertTrue(parse_state(d.handle('STATUS')[1]).running)
        self.assertEqual(len(d.handle('STATUS')),5)
        d.handle('STOP ALL');motor_clock.return_value=led_clock.return_value=2
        self.assertFalse(parse_state(d.handle('STATUS')[1]).running)
        self.assertEqual(led_state(d.handle('LEDSTATUS')[0])['RUN'],1)

    @patch('led_device.time.monotonic')
    def test_finite_led_cycle_and_config(self,clock):
        clock.return_value=0;d=DemoDevice()
        d.handle('FLOW CONFIG 100 -1 2');d.handle('FLOW RESTART')
        clock.return_value=.701
        s=led_state(d.handle('LEDSTATUS')[0]);self.assertEqual((s['RUN'],s['DONE'],s['MASK']),(0,2,0))
        self.assertTrue(all(not parse_state(x).running for x in d.handle('STATUS')[:4]))

    def test_shared_worker_routes_led_and_motor_without_serial(self):
        events=queue.Queue()
        with patch('transport.serial.serial_for_url',side_effect=AssertionError('opened hardware')) as opened:
            link=ControllerLink(events,demo=True);link.start()
            try:
                end=time.monotonic()+2
                while time.monotonic()<end:
                    kinds={k for k,_ in list(events.queue)}
                    if {'state','led_state','ready'}<=kinds:break
                    time.sleep(.01)
                self.assertTrue({'state','led_state','ready'}<=kinds)
                link.send('ALL OFF');time.sleep(.1)
            finally:link.close();link.join(2)
            opened.assert_not_called();self.assertFalse(link.is_alive())

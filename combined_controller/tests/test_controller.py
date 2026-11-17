import queue
import socket
import threading
import time
import unittest
from unittest.mock import patch
from protocol import Profile, parse_state, compatible_hello, parse_parameters, PPR
from demo import DemoDevice, HELLO
from transport import ControllerLink


class ProtocolTests(unittest.TestCase):
    def test_status_routes_axis_and_signed_position(self):
        state = parse_state("STATE 4 RUNNING POS=-420 PULSES=120/3200 RPM_MILLI=30250 FAULT=0 DONE=2 T=1000")
        self.assertEqual((state.axis, state.position, state.rpm, state.done), (4, -420, 30.25, 2))
        for line in ["STATE 5 IDLE POS=0 PULSES=0/0 RPM_MILLI=0 FAULT=0 DONE=0 T=1", "STATE 1 IDLE POS=0 PULSES=2/1 RPM_MILLI=0 FAULT=0 DONE=0 T=1", "STATE 1 BOGUS"]:
            with self.assertRaises(ValueError):
                parse_state(line)

    def test_old_firmware_rejected(self):
        self.assertFalse(compatible_hello("YS-F4Pro HAL STEPPER v1 READY"))
        self.assertFalse(compatible_hello(HELLO.replace("AXES=4", "AXES=1")))
        self.assertTrue(compatible_hello(HELLO))
        self.assertFalse(compatible_hello(HELLO.replace("PROTO=5", "PROTO=4")))
        self.assertFalse(compatible_hello(HELLO.replace("PPR=3200", "PPR=1600")))

    def test_3200_pulses_is_one_revolution_and_correct_rpm(self):
        self.assertEqual(PPR, 3200)
        self.assertEqual(Profile().pulses, 3200)
        p = Profile(3200, 30, 30, 30)
        self.assertAlmostEqual(p.duration, 3.0)
        self.assertAlmostEqual(p.sample(1.5)[1], 30)
        self.assertAlmostEqual(p.sample(p.duration)[0]/PPR, 1)

    def test_parameter_readback_and_invalid_acceleration(self):
        p = parse_parameters("PARAM 3 STEPS=1600 RPM=20 ACC=40 DEC=50 CURVE=S REV=7")
        self.assertEqual(p.profile, Profile(1600, 20, 40, 50, "S"))
        self.assertEqual((p.axis, p.revision), (3, 7))
        with self.assertRaises(ValueError):
            parse_parameters("PARAM 1 STEPS=3200 RPM=30 ACC=401 DEC=401 CURVE=TRAP REV=0")
        self.assertEqual(p.profile.set_command(3), "SET 3 1600 20 40 50 S")

    def test_profile_bounds_and_short_move(self):
        for curve in ("TRAP", "S"):
            for n in (1, 3200, 32000):
                p = Profile(n, 200, 400, 400, curve)
                p.validate()
                start, end = p.sample(0), p.sample(p.duration)
                self.assertAlmostEqual(start[0], 0)
                self.assertAlmostEqual(end[0], n)
                self.assertAlmostEqual(end[1], 0)
                values = [p.sample(p.duration*i/500) for i in range(501)]
                self.assertTrue(all(a[0] <= b[0]+1e-7 for a, b in zip(values, values[1:])))
                self.assertLessEqual(max(x[1] for x in values), 200.0001)
        for p in [Profile(0), Profile(32001), Profile(rpm=201), Profile(accel=0), Profile(32000, 1)]:
            with self.assertRaises(ValueError):
                p.validate()

    def test_switching_axis_does_not_change_command_target(self):
        p = Profile(1600, 20, 30, 40, "S")
        self.assertEqual(p.command(4, -1), "MOVE 4 -1600 20 30 40 S")


class DemoTests(unittest.TestCase):
    @patch('demo.time.monotonic')
    def test_200rpm_400_acceleration_boundary_and_frequency(self,clock):
        clock.return_value=0;d=DemoDevice()
        self.assertEqual(d.handle('SPEED 1 1 200 400 400'),['OK SPEED 1'])
        clock.return_value=1
        s=parse_state(d.handle('STATUS')[0])
        self.assertEqual(s.rpm,200);self.assertAlmostEqual(s.pul_hz,10666.667,places=3)
        d.handle('STOP ALL');clock.return_value=2
        self.assertFalse(parse_state(d.handle('STATUS')[0]).running)
        for cmd in ('SPEED 1 1 201 400 400','SPEED 1 1 200 401 400','SPEED 1 1 200 400 401'):
            self.assertEqual(d.handle(cmd),['ERR COMMAND'])

    @patch('demo.time.monotonic')
    def test_continuous_speed_frequency_independent_stop(self,clock):
        clock.return_value=0;d=DemoDevice()
        self.assertEqual(d.handle('SPEED 2 -1 30 30 30'),['OK SPEED 2'])
        self.assertEqual(d.handle('SPEED 2 1 30 30 30'),['ERR BUSY 2'])
        clock.return_value=20
        s=parse_state(d.handle('STATUS')[1]);self.assertTrue(s.running)
        self.assertEqual((s.mode,s.rpm,s.pul_hz),('SPEED',30,1600))
        self.assertEqual(s.position,-31200)
        self.assertFalse(parse_state(d.handle('STATUS')[0]).running)
        d.handle('STOP 2');clock.return_value=22
        s=parse_state(d.handle('STATUS')[1]);self.assertFalse(s.running);self.assertEqual(s.pul_hz,0)
        for command in ('SPEED 1 0 30 30 30','SPEED 1 1 201 30 30','SPEED 1 1 30 0 30'):
            self.assertEqual(d.handle(command),['ERR COMMAND'])

    def test_parameter_roundtrip_axis_isolation_and_busy_write(self):
        d = DemoDevice()
        before = d.handle("GET 1")
        reply = d.handle("SET 3 1600 20 40 50 S")
        p = parse_parameters(reply[1])
        self.assertEqual(p.profile, Profile(1600, 20, 40, 50, "S"))
        self.assertEqual(d.handle("GET 1"), before)
        self.assertEqual(parse_parameters(d.handle("GET 3")[0]).revision, 1)
        self.assertEqual(d.handle("RUN 3 -1"), ["OK RUN 3"])
        self.assertEqual(d.axes[2].target, 1600)
        self.assertEqual(d.handle("SET 3 3200 30 30 30 TRAP"), ["ERR BUSY 3"])
        d.handle("SET 1 3200 30 401 401 TRAP")
        self.assertEqual(d.handle("GET 1"), before)

    def test_four_axes_independent_busy_stop_and_zero(self):
        d = DemoDevice()
        for i in range(1, 5):
            self.assertEqual(d.handle(f"MOVE {i} 3200 30 30 30 TRAP"), [f"OK MOVE {i}"])
        self.assertEqual(d.handle("MOVE 2 100 20 30 30 S"), ["ERR BUSY 2"])
        self.assertEqual(d.handle("ZERO 2"), ["ERR BUSY 2"])
        time.sleep(0.02)
        d.handle("STOP 2")
        states = [parse_state(s) for s in d.handle("STATUS")]
        self.assertTrue(states[0].running and states[2].running and states[3].running)
        self.assertTrue(d.axes[1].stopping)
        d.handle("STOP ALL")
        self.assertTrue(all(a.stopping or a.profile is None for a in d.axes))

    def test_demo_never_opens_a_serial_port(self):
        events = queue.Queue()
        with patch("transport.serial.serial_for_url", side_effect=AssertionError("Demo opened serial")) as serial_open:
            link = ControllerLink(events, demo=True)
            link.start()
            wait_event(events, "ready")
            wait_event(events, "state")
            link.send("MOVE 4 -100 30 30 30 S")
            time.sleep(0.08)
            link.close()
            link.join(1)
            self.assertFalse(link.is_alive())
            serial_open.assert_not_called()


def wait_event(events, kind, timeout=4):
    until = time.monotonic()+timeout
    while time.monotonic() < until:
        event = events.get(timeout=max(0.01, until-time.monotonic()))
        if event[0] == "error":
            raise AssertionError(event[1])
        if event[0] == kind:
            return event[1]
    raise AssertionError(f"Missing {kind}")


class TransportTests(unittest.TestCase):
    def test_board_reset_invalidates_cached_parameters(self):
        link = ControllerLink(queue.Queue(), demo=True)
        link._line(HELLO)
        link._line("STATE 1 IDLE POS=0 PULSES=0/0 RPM_MILLI=0 FAULT=0 DONE=0 T=1000")
        with self.assertRaises(RuntimeError):
            link._line("STATE 1 IDLE POS=0 PULSES=0/0 RPM_MILLI=0 FAULT=0 DONE=0 T=10")

    def test_fragmented_stream_and_stop_on_disconnect(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        commands = []
        def device():
            connection, _ = listener.accept()
            with connection:
                connection.settimeout(3)
                buffer = b""
                while True:
                    data = connection.recv(1024)
                    if not data:
                        break
                    buffer += data
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        command = line.decode()
                        commands.append(command)
                        if command == "HELLO":
                            connection.sendall((HELLO[:12]).encode())
                            time.sleep(0.01)
                            connection.sendall((HELLO[12:]+"\r\n").encode())
                        elif command == "STATUS":
                            reply = "".join(f"STATE {i} IDLE POS=0 PULSES=0/0 RPM_MILLI=0 FAULT=0 DONE=0 T=10\r\n" for i in range(1, 5))
                            connection.sendall(reply.encode())
                        elif command == "STOP ALL":
                            return
        server = threading.Thread(target=device, daemon=True)
        server.start()
        events = queue.Queue()
        link = ControllerLink(events, f"socket://127.0.0.1:{listener.getsockname()[1]}")
        try:
            link.start()
            wait_event(events, "ready")
            state = wait_event(events, "state")
            self.assertEqual(state.axis, 1)
            link.close()
            link.join(2)
            server.join(2)
            self.assertIn("WATCHDOG 1500", commands)
            self.assertIn("STOP ALL", commands)
            self.assertFalse(link.is_alive())
        finally:
            link.close()
            listener.close()


if __name__ == "__main__":
    unittest.main()

"""Serial I/O is confined to this worker; UI receives queue events only."""
import queue
import threading
import time
import serial
from demo import DemoDevice
from protocol import compatible_hello, parse_state, parse_parameters


class ControllerLink(threading.Thread):
    def __init__(self, events, port="", demo=False):
        super().__init__(daemon=True, name="controller-link")
        self.events = events
        self.port_name, self.demo = port, demo
        self.commands = queue.Queue(maxsize=32)
        self.stopping = threading.Event()
        self.ready = False
        self.port = None
        self.simulator = DemoDevice() if demo else None
        self.buffer = b""
        self.last_state = time.monotonic()
        self.last_ticks = {}

    def send(self, command):
        if not self.ready or self.stopping.is_set():
            raise RuntimeError("尚未连接并完成握手")
        if "\n" in command or "\r" in command or len(command) > 110:
            raise ValueError("无效命令")
        try:
            self.commands.put_nowait(command)
        except queue.Full as exc:
            raise RuntimeError("发送队列已满，请稍后操作") from exc

    def close(self):
        self.stopping.set()

    def _line(self, line):
        self.events.put(("line", line))
        if line.startswith('HELLO YS_F4Pro_LED'):
            raise RuntimeError('板上是 LED 固件，请通过 DAP 下载四轴 v4 电机固件后连接')
        if line.startswith('HELLO YS_F4Pro ') and not compatible_hello(line):
            raise RuntimeError('电机固件版本或每转脉冲数不匹配：需要四轴 v4、3200 脉冲/转')
        if self.ready and line.startswith("YS-F4Pro HAL STEPPER"):
            raise RuntimeError("下位机已重启，请重新连接并读取板端参数")
        if compatible_hello(line):
            self.ready = True
            self.last_state = time.monotonic()
            self.events.put(("ready", self.demo))
        if line.startswith("STATE "):
            state = parse_state(line)
            previous = self.last_ticks.get(state.axis)
            if previous is not None and state.tick < previous and not (previous > 0xF0000000 and state.tick < 0x10000000):
                raise RuntimeError("检测到下位机重启，请重新连接并读取板端参数")
            self.last_ticks[state.axis] = state.tick
            self.last_state = time.monotonic()
            self.events.put(("state", state))
        if line.startswith("PARAM "):
            self.events.put(("parameters", parse_parameters(line)))

    def _write(self, command):
        if self.simulator is not None:
            for line in self.simulator.handle(command):
                self._line(line)
        else:
            data = (command+"\n").encode("ascii")
            if self.port.write(data) != len(data):
                raise serial.SerialException("串口未完整发送命令")
        if command != "STATUS":
            self.events.put(("sent", command))
        else:
            self.events.put(("tx_status", command))

    def run(self):
        try:
            if not self.demo:
                self.port = serial.serial_for_url(self.port_name, baudrate=115200, timeout=0.03, write_timeout=0.5)
            self.events.put(("opening", self.demo))
            self._write("HELLO")
            started, polled, retry = time.monotonic(), 0.0, time.monotonic()
            watchdog_set = False
            while not self.stopping.is_set():
                now = time.monotonic()
                if not self.ready:
                    if now-started > 3:
                        raise RuntimeError("握手超时：需要四轴 v4 / 3200 脉冲固件，请检查串口、JP2 和波特率")
                    if now-retry > 0.7:
                        self._write("HELLO")
                        retry = now
                else:
                    if not watchdog_set:
                        self._write("WATCHDOG 1500")
                        watchdog_set = True
                    if now-polled >= 0.25:
                        self._write("STATUS")
                        polled = now
                    if now-self.last_state > 2:
                        raise RuntimeError("状态反馈超时，已断开连接；下位机通信看门狗将请求减速停止")
                    for _ in range(4):
                        try:
                            command = self.commands.get_nowait()
                        except queue.Empty:
                            break
                        self._write(command)
                if self.port is not None:
                    data = self.port.read(min(self.port.in_waiting or 1, 1024))
                    self.buffer += data
                    if len(self.buffer) > 4096:
                        raise RuntimeError("串口接收帧过长")
                    while b"\n" in self.buffer:
                        line, self.buffer = self.buffer.split(b"\n", 1)
                        self._line(line.rstrip(b"\r").decode("ascii"))
                else:
                    self.stopping.wait(0.02)
        except (OSError, RuntimeError, ValueError, serial.SerialException) as exc:
            self.events.put(("error", str(exc)))
        finally:
            if self.ready:
                try:
                    self._write("STOP ALL")
                    # Give the device a bounded opportunity to acknowledge STOP
                    # before closing the handle (closing immediately may drop TX).
                    if self.port is not None:
                        deadline = time.monotonic()+0.3
                        reply = b""
                        while time.monotonic() < deadline:
                            reply += self.port.read(min(self.port.in_waiting or 1, 1024))
                            if b"OK STOP ALL" in reply:
                                break
                except (OSError, ValueError, serial.SerialException):
                    pass
            self.ready = False
            if self.port is not None:
                self.port.close()
            self.events.put(("closed", None))

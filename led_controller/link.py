import queue
import threading
import time
import serial
from device import Demo, HELLO, parse_state


class Link(threading.Thread):
    def __init__(self, events, port='', demo=False):
        super().__init__(daemon=True)
        self.events, self.port_name = events, port
        self.demo = Demo() if demo else None
        self.stop_event = threading.Event()
        self.queue = queue.Queue(maxsize=32)
        self.ready = False

    def send(self, command):
        if not self.ready or self.stop_event.is_set():
            raise ValueError('请先连接 LED 固件或离线演示')
        if not command or len(command) > 79 or any(ord(c)<32 or ord(c)>126 for c in command):
            raise ValueError('请输入不超过 79 字符的单行 ASCII 命令')
        try:
            self.queue.put_nowait(command)
        except queue.Full as exc:
            raise ValueError('命令队列已满') from exc

    def close(self):
        self.stop_event.set()

    def run(self):
        port = None
        started = time.monotonic()
        last_state, last_poll, last_hello = started, 0, started
        buffer = b''
        def line(text):
            nonlocal last_state
            if text == HELLO:
                self.ready = True
                last_state = time.monotonic()
                self.events.put(('ready', self.demo is not None))
            elif text.startswith('LEDSTATE '):
                state = parse_state(text)
                last_state = time.monotonic()
                self.events.put(('state', state))
            self.events.put(('rx', text))
        def write(command):
            if self.demo:
                for reply in self.demo.handle(command):
                    line(reply)
            else:
                data = (command+'\n').encode('ascii')
                if port.write(data) != len(data):
                    raise ValueError('串口未完整发送')
            if command != 'STATUS':
                self.events.put(('tx', command))
        try:
            if self.demo is None:
                port = serial.serial_for_url(self.port_name, baudrate=115200, timeout=.03, write_timeout=.5)
            write('HELLO')
            while not self.stop_event.is_set():
                now = time.monotonic()
                if not self.ready:
                    if now-started > 3:
                        raise ValueError('握手失败：需要流水灯串口版固件，不能连接电机固件')
                    if now-last_hello > .7:
                        write('HELLO')
                        last_hello = now
                else:
                    if now-last_poll > .25:
                        write('STATUS')
                        last_poll = now
                    if now-last_state > 2:
                        raise ValueError('状态反馈超时，连接已断开')
                    for _ in range(4):
                        try:
                            write(self.queue.get_nowait())
                        except queue.Empty:
                            break
                if port:
                    buffer += port.read(min(port.in_waiting or 1, 1024))
                    if len(buffer) > 2048:
                        raise ValueError('串口报文过长')
                    while b'\n' in buffer:
                        data, buffer = buffer.split(b'\n', 1)
                        line(data.rstrip(b'\r').decode('ascii'))
                else:
                    self.stop_event.wait(.02)
        except (OSError, ValueError, serial.SerialException) as exc:
            self.events.put(('error', str(exc)))
        finally:
            self.ready = False
            if port:
                port.close()
            self.events.put(('closed', None))

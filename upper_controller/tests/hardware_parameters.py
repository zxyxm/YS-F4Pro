"""Explicit COM-port parameter test; never sends MOVE or RUN.

Run manually: python tests/hardware_parameters.py COM4
Writes temporary RAM parameters, verifies isolation, then restores originals.
"""
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import serial
from protocol import compatible_hello, parse_parameters, parse_state, Profile


def main(port_name):
    log = []
    originals = {}
    with serial.Serial(port_name, 115200, timeout=0.03, write_timeout=0.5) as port:
        buffer = b""
        def query(command, predicate):
            nonlocal buffer
            log.append("TX "+command)
            port.write((command+"\n").encode("ascii"))
            until = time.monotonic()+3
            while time.monotonic() < until:
                buffer += port.read(min(port.in_waiting or 1, 1024))
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    text = line.rstrip(b"\r").decode("ascii")
                    log.append("RX "+text)
                    if predicate(text):
                        return text
            raise AssertionError("Timeout: "+command)
        def read(axis):
            return parse_parameters(query(f"GET {axis}", lambda x: x.startswith(f"PARAM {axis} ")))
        query("HELLO", compatible_hello)
        baseline = {}
        for axis in range(1, 5):
            state = parse_state(query(f"STATUS {axis}", lambda x: x.startswith(f"STATE {axis} ")))
            assert not state.running and state.fault == 0, "Parameter test requires idle healthy axes"
            baseline[axis] = state
        for axis in range(1, 5):
            originals[axis] = read(axis)
        expected = dict(originals)
        try:
            for axis in range(1, 5):
                p = Profile(800+800*axis, 15+5*axis, 35+5*axis, 45+5*axis, "S" if axis%2==0 else "TRAP")
                params = parse_parameters(query(p.set_command(axis), lambda x: x.startswith(f"PARAM {axis} ")))
                assert params.profile == p
                assert params.revision == expected[axis].revision+1
                expected[axis] = params
                for other in range(1, 5):
                    assert read(other) == expected[other], "Cross-axis parameter change"
            query("SET 1 3200 30 401 401 TRAP", lambda x: x == "ERR RANGE 1")
            assert read(1) == expected[1], "Rejected SET changed parameters"
            query("SET 4 -3200 30 30 30 TRAP", lambda x: x == "ERR RANGE 4")
            assert read(4) == expected[4]
            states = []
            for axis in range(1, 5):
                state = parse_state(query(f"STATUS {axis}", lambda x: x.startswith(f"STATE {axis} ")))
                assert not state.running and state.fault == 0
                old = baseline[axis]
                assert (state.position, state.emitted, state.target, state.done) == (old.position, old.emitted, old.target, old.done), "Motion counters changed during parameter-only test"
                states.append(state.__dict__)
        finally:
            for axis, params in originals.items():
                restored = parse_parameters(query(params.profile.set_command(axis), lambda x: x.startswith(f"PARAM {axis} ")))
                assert restored.profile == params.profile
        destination = Path(__file__).resolve().parents[2]/f"backups/parameter-v3-{port_name.lower()}-test-20261112.json"
        destination.write_text(json.dumps({"port": port_name, "result": "passed", "motion_commands_sent": False, "states": states, "log": log}, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Hardware parameter test passed: four-axis SET/GET roundtrip, revision, isolation, invalid input rejection, original values restored; no motion commands sent.")


if __name__ == "__main__":
    main(sys.argv[1])

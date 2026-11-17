import tempfile
from pathlib import Path
import unittest
from axis_config import Calibration, defaults, load_calibrations, save_calibrations, to_wire, physical_text, raw_commands


class CalibrationTests(unittest.TestCase):
    def test_same_physical_speed_maps_to_existing_wire_units(self):
        self.assertEqual(to_wire("30", 3200), 30)
        self.assertEqual(to_wire("15", 6400), 30)
        self.assertEqual(physical_text(30, 6400), "15")
        self.assertEqual(to_wire("3.75", 51200), 60)
        self.assertEqual(physical_text(60, 51200), "3.75")
        with self.assertRaises(ValueError):
            to_wire("1", 800)
        for value in ("NaN", "Infinity", "-1", "0", "abc"):
            with self.assertRaises(ValueError):
                to_wire(value, 1600)

    def test_per_axis_configuration_roundtrip(self):
        values = defaults()
        values[2] = Calibration(3200, ("IN4", "IN5", "IN6"), ("高电平", "低电平", "高电平"))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"settings.json"
            save_calibrations(values, path)
            self.assertEqual(load_calibrations(path), values)
        self.assertEqual(values[1].ppr, 3200)
        with self.assertRaises(ValueError):
            Calibration(inputs=("IN1", "IN1", "IN2")).validate()

    def test_raw_ascii_commands_preserve_existing_protocol(self):
        self.assertEqual(raw_commands("GET 1\r\nSTATUS\n"), ["GET 1", "STATUS"])
        for text in ("", "读取参数", "X"*111, "PING\n"*9, "PING\x00"):
            with self.assertRaises(ValueError):
                raw_commands(text)

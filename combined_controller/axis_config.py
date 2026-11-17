"""Host-only calibration. Shared 3200-PPR firmware reference."""
from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
from protocol import PPR

PPR_OPTIONS = (200, 400, 800, 1000, 1600, 2000, 3200, 4000, 5000, 6400, 8000, 10000, 12800, 20000, 25600, 40000, 51200)
SENSOR_ROLES = ("负限位", "原点", "正限位")


@dataclass(frozen=True)
class Calibration:
    ppr: int = PPR
    inputs: tuple = ("IN1", "IN2", "IN3")
    active_levels: tuple = ("低电平", "低电平", "低电平")

    def validate(self):
        if self.ppr not in PPR_OPTIONS:
            raise ValueError("请选择支持的每转脉冲数")
        if len(self.inputs) != 3 or len(set(self.inputs)) != 3 or any(x not in {f"IN{i}" for i in range(1, 13)} for x in self.inputs):
            raise ValueError("三个开关应选择不同的 IN1～IN12 输入")
        if len(self.active_levels) != 3 or any(x not in ("低电平", "高电平") for x in self.active_levels):
            raise ValueError("无效的开关有效电平")


def config_path():
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home())))/"YSF4Pro_Controller"/"settings.json"


def defaults():
    return {axis: Calibration(inputs=tuple(f"IN{(axis-1)*3+j}" for j in (1, 2, 3))) for axis in range(1, 5)}


def load_calibrations(path=None):
    path = Path(path) if path is not None else config_path()
    result = defaults()
    if not path.exists():
        return result
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != 1:
        raise ValueError("不支持的本机配置版本")
    for axis in range(1, 5):
        item = data["axes"][str(axis)]
        cfg = Calibration(int(item["ppr"]), tuple(item["inputs"]), tuple(item["active_levels"]))
        cfg.validate()
        result[axis] = cfg
    return result


def save_calibrations(values, path=None):
    for cfg in values.values():
        cfg.validate()
    path = Path(path) if path is not None else config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"schema": 1, "axes": {str(i): asdict(v) for i, v in values.items()}}, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def to_wire(value, ppr):
    """Actual rpm/rpm/s -> existing firmware's integer reference units."""
    try:
        actual = Decimal(str(value))
        if not actual.is_finite() or actual <= 0:
            raise ValueError("速度和加减速度必须是有效正数")
        wire = actual*Decimal(ppr)/Decimal(PPR)
        if wire != wire.to_integral_value():
            step = physical_text(1, ppr)
            raise ValueError(f"当前细分下速度/加减速度须为 {step} 的整数倍，以保持原报文整数单位")
        return int(wire)
    except InvalidOperation as exc:
        raise ValueError("请输入有效速度或加减速度") from exc


def physical_text(wire, ppr):
    value = Decimal(str(wire))*Decimal(PPR)/Decimal(ppr)
    return format(value, "f").rstrip("0").rstrip(".") if "." in format(value, "f") else format(value, "f")


def raw_commands(text):
    try:
        text.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("报文仅支持 ASCII，请使用英文命令和数字") from exc
    commands = [line.strip() for line in text.splitlines() if line.strip()]
    if not commands or len(commands) > 8:
        raise ValueError("每次请输入 1～8 行报文，一行一条命令")
    if any(len(line) > 110 or any(ord(c) < 32 or ord(c) > 126 for c in line) for line in commands):
        raise ValueError("每条报文最多 110 个可打印 ASCII 字符")
    return commands

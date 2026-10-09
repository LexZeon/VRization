"""Version 1 wire messages. No dependencies on desktop or rendering APIs."""

from dataclasses import asdict, dataclass, replace
import json
import math
import time


class ProtocolError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    mode: str = "full"
    scale: float = 0.85
    offsetX: float = 0.0
    offsetY: float = 0.0
    eyeSeparation: float = 0.03
    fov: float = 80.0
    distance: float = 3.0
    distortion: float = 0.0
    sensitivity: float = 1000.0
    invertY: bool = False
    stabilization: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    def update(self, patch: dict) -> "Settings":
        if not isinstance(patch, dict) or not patch:
            raise ProtocolError("settings must be a nonempty object")
        bounds = {"scale": (0.5, 1.0), "offsetX": (-0.3, 0.3), "offsetY": (-0.3, 0.3),
                  "eyeSeparation": (-1.0, 0.2), "fov": (50.0, 110.0), "distance": (1.0, 8.0),
                  "distortion": (0.0, 0.5), "sensitivity": (100.0, 3000.0),
                  "stabilization": (0.0, 1.0)}
        clean = {}
        for key, value in patch.items():
            if key == "mode":
                if not isinstance(value, str) or value not in ("full", "cinema", "fps"):
                    raise ProtocolError("unknown mode")
                clean[key] = value
            elif key == "invertY":
                if type(value) is not bool:
                    raise ProtocolError("invertY must be boolean")
                clean[key] = value
            elif key in bounds:
                if type(value) not in (int, float):
                    raise ProtocolError(f"{key} must be finite")
                low, high = bounds[key]
                if not low <= value <= high:
                    raise ProtocolError(f"{key} outside {low}..{high}")
                clean[key] = float(value)
            else:
                raise ProtocolError(f"unknown setting: {key}")
        return replace(self, **clean)


def parse_message(raw: str) -> dict:
    try:
        msg = json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(
            ProtocolError("nonfinite JSON constant")))
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ProtocolError("invalid JSON") from exc
    if not isinstance(msg, dict) or type(msg.get("v")) is not int or msg["v"] != 1:
        raise ProtocolError("expected protocol version 1")
    kind = msg.get("type")
    if kind not in ("hello", "settings", "pose", "recenter", "ping"):
        raise ProtocolError("unknown message type")
    if kind == "hello" and "editing" in msg and type(msg["editing"]) is not bool:
        raise ProtocolError("editing must be boolean")
    if kind == "pose":
        if type(msg.get("seq")) is not int or not 0 <= msg["seq"] <= 2**53 - 1:
            raise ProtocolError("invalid pose sequence")
        for key in ("yaw", "pitch"):
            value = msg.get(key)
            if type(value) not in (float, int) or abs(value) > 100 or not math.isfinite(value):
                raise ProtocolError(f"invalid {key}")
    if kind == "settings" and not isinstance(msg.get("settings"), dict):
        raise ProtocolError("expected settings object")
    if kind == "settings" and "clientSeq" in msg:
        if type(msg["clientSeq"]) is not int or not 0 <= msg["clientSeq"] <= 2**53 - 1:
            raise ProtocolError("invalid settings client sequence")
    return msg


class TokenLimiter:
    """Bound brute-force attempts before websocket upgrade, including across IPs."""

    def __init__(self, limit: int = 5, window: float = 60.0):
        self.limit, self.window = limit, window
        self.attempts: dict[str, list[float]] = {}
        self.global_attempts: list[float] = []

    def allowed(self, address: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        self.attempts = {key: [x for x in values if now - x < self.window]
                         for key, values in self.attempts.items()
                         if any(now - x < self.window for x in values)}
        self.global_attempts = [x for x in self.global_attempts if now - x < self.window]
        return (len(self.attempts.get(address, [])) < self.limit
                and len(self.global_attempts) < self.limit * 6)

    def failed(self, address: str, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        self.attempts.setdefault(address, []).append(now)
        self.global_attempts.append(now)

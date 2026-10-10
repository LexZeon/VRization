"""Nonsecret user preferences; pairing codes and arm state are never persisted."""

from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import tempfile

from .capture import CaptureConfig
from .protocol import Settings


def preference_path() -> Path:
    return Path(os.environ.get("VRIZATION_PROFILE_DIRECTORY") or Path(os.environ.get("LOCALAPPDATA", Path.home())) / "VRization") / "preferences.json"


def default_preferences(selection: CaptureConfig) -> tuple[Settings, CaptureConfig]:
    """Reset fit and performance without capturing a different user's output."""
    return Settings(), replace(CaptureConfig(), monitor=selection.monitor, region=selection.region)


def load_preferences(path: Path | None = None) -> tuple[Settings, CaptureConfig]:
    try:
        value = json.loads((path or preference_path()).read_text(encoding="utf-8"))
        settings = Settings().update(value["settings"])
        config = value["capture"]
        if not isinstance(config, dict):
            raise ValueError("capture preferences must be an object")
        if config.get("region") is not None:
            config["region"] = tuple(config["region"])
        return settings, CaptureConfig(**config)
    except (OSError, ValueError, KeyError, TypeError):
        return Settings(), CaptureConfig()


def save_preferences(settings: Settings, config: CaptureConfig, path: Path | None = None):
    path = path or preference_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="preferences-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump({"settings": settings.to_dict(), "capture": asdict(config)}, output, indent=2)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_usb_preferences(path: Path | None = None) -> dict:
    defaults = {"enabled": True, "adb_path": "", "preferred_serial": ""}
    try:
        value = json.loads((path or preference_path().with_name("usb.json")).read_text(encoding="utf-8"))
        if type(value.get("enabled")) is bool:
            defaults["enabled"] = value["enabled"]
        for key in ("adb_path", "preferred_serial"):
            if isinstance(value.get(key), str):
                defaults[key] = value[key]
    except (OSError, ValueError, AttributeError):
        pass
    return defaults


def save_usb_preferences(value: dict, path: Path | None = None):
    path = path or preference_path().with_name("usb.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="usb-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump({key: value[key] for key in ("enabled", "adb_path", "preferred_serial")}, output, indent=2)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_input_preferences(path: Path | None = None) -> dict:
    """Persist the chosen gyro policy, never active control or an emergency latch."""
    defaults = {"gyro_control_enabled": True}
    try:
        value = json.loads((path or preference_path().with_name("input.json")).read_text(encoding="utf-8"))
        if isinstance(value, dict) and type(value.get("gyro_control_enabled")) is bool:
            defaults["gyro_control_enabled"] = value["gyro_control_enabled"]
    except (OSError, ValueError):
        pass
    return defaults


def save_input_preferences(value: dict, path: Path | None = None):
    enabled = value["gyro_control_enabled"]
    if type(enabled) is not bool:
        raise ValueError("gyro control preference must be a boolean")
    path = path or preference_path().with_name("input.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="input-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump({"gyro_control_enabled": enabled}, output, indent=2)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

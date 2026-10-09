"""Nonsecret user preferences; pairing codes and arm state are never persisted."""

from dataclasses import asdict
import json
import os
from pathlib import Path
import tempfile

from .capture import CaptureConfig
from .protocol import Settings


def preference_path() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "VRization" / "preferences.json"


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

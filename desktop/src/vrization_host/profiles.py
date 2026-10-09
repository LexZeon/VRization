"""Capture presets are goals, not measured end-to-end latency guarantees."""

from dataclasses import replace

PROFILES = {
    "Low latency · 640 / 60 FPS / Q45": {"width": 640, "fps": 60, "quality": 45},
    "Stable · 640 / 30 FPS / Q50": {"width": 640, "fps": 30, "quality": 50},
    "Quality · 960 / 30 FPS / Q60": {"width": 960, "fps": 30, "quality": 60},
}
CUSTOM = "Custom"


def apply_profile(config, name):
    return replace(config, **PROFILES[name]) if name in PROFILES else config


def capture_profile(config):
    return next((name for name, values in PROFILES.items()
                 if all(getattr(config, key) == value for key, value in values.items())), CUSTOM)


def initial_capture(config, has_saved_preferences):
    return config if has_saved_preferences else apply_profile(config, next(iter(PROFILES)))

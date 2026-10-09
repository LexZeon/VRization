"""Capture presets are goals, not measured end-to-end latency guarantees."""

from dataclasses import replace

PROFILES = {
    "Low latency · 960 / 60 FPS / Q60": {"width": 960, "fps": 60, "quality": 60},
    "Stable · 1280 / 30 FPS / Q65": {"width": 1280, "fps": 30, "quality": 65},
    "Quality · 1920 / 30 FPS / Q80": {"width": 1920, "fps": 30, "quality": 80},
}
CUSTOM = "Custom"


def apply_profile(config, name):
    return replace(config, **PROFILES[name]) if name in PROFILES else config


def capture_profile(config):
    return next((name for name, values in PROFILES.items()
                 if all(getattr(config, key) == value for key, value in values.items())), CUSTOM)


def initial_capture(config, has_saved_preferences):
    return config if has_saved_preferences else apply_profile(config, next(iter(PROFILES)))

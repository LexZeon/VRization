"""Phone-HMD JPEG goals, separate from the original direct-phone defaults."""

from dataclasses import replace

from vrization_host.profiles import CUSTOM


BALANCED = "Balanced · 1280 / 60 FPS / Q75"
SHARPER = "Sharper · 1920 / 60 FPS / Q80"
LOW_LATENCY = "Low latency · 640 / 60 FPS / Q45"
HMD_PROFILES = {
    BALANCED: {"width": 1280, "fps": 60, "quality": 75},
    SHARPER: {"width": 1920, "fps": 60, "quality": 80},
    LOW_LATENCY: {"width": 640, "fps": 60, "quality": 45},
}
_CHINESE = {
    BALANCED: "均衡 · 1280 / 60 FPS / Q75",
    SHARPER: "更清晰 · 1920 / 60 FPS / Q80",
    LOW_LATENCY: "低延迟 · 640 / 60 FPS / Q45",
    CUSTOM: "自定义",
}


def profile_label(name, language):
    return _CHINESE.get(name, name) if language == "zh" else name


def apply_hmd_profile(config, name):
    """Change only JPEG targets; preserve display selection and other settings."""
    return replace(config, **HMD_PROFILES[name]) if name in HMD_PROFILES else config


def hmd_capture_profile(config):
    return next((name for name, values in HMD_PROFILES.items()
                 if all(getattr(config, key) == value for key, value in values.items())), CUSTOM)


def initial_hmd_capture(config, has_saved_preferences):
    """A saved configuration is intentional, including the former low-latency goal."""
    return config if has_saved_preferences else apply_hmd_profile(config, BALANCED)


def limit_hmd_capture(config):
    return replace(config, width=min(1920, config.width), fps=max(30, config.fps), region=None)

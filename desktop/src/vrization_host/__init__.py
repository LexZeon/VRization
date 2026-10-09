"""Reusable host core; import HostServer with your own capture and input adapters."""

from ._version import __version__

# Preserve the public embedding API without loading capture/mouse/server code
# for a standalone read-only diagnostic invocation.
_PUBLIC_MODULES = {name: ".capture" for name in ("CaptureConfig", "CaptureSource", "Frame", "MssCaptureSource")}
_PUBLIC_MODULES.update({name: ".input" for name in ("InputSink", "PoseController", "WindowsMouseSink")})
_PUBLIC_MODULES.update(Settings=".protocol", HostServer=".server")

__all__ = ["CaptureConfig", "CaptureSource", "Frame", "MssCaptureSource", "InputSink",
           "PoseController", "WindowsMouseSink", "Settings", "HostServer"]


def __getattr__(name):
    import importlib
    if name not in _PUBLIC_MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(importlib.import_module(_PUBLIC_MODULES[name], __name__), name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))

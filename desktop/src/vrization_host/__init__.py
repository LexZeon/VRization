"""Reusable host core; import HostServer with your own capture and input adapters."""

from ._version import __version__
from .capture import CaptureConfig, CaptureSource, Frame, MssCaptureSource
from .input import InputSink, PoseController, WindowsMouseSink
from .protocol import Settings
from .server import HostServer

__all__ = ["CaptureConfig", "CaptureSource", "Frame", "MssCaptureSource", "InputSink",
           "PoseController", "WindowsMouseSink", "Settings", "HostServer"]

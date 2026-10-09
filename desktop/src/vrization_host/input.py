"""Relative input adapters; only an explicitly armed, live FPS session can move."""

import ctypes
from ctypes import wintypes
import math
import os
import threading
import time
from typing import Callable, Protocol, runtime_checkable

from .protocol import Settings
from .pose_filter import PoseStabilizer


@runtime_checkable
class InputSink(Protocol):
    """Replace with a game-engine camera adapter when embedding the host."""
    def move(self, dx: int, dy: int) -> None: ...


class WindowsMouseSink:
    def __init__(self):
        if os.name != "nt":
            raise OSError("Windows mouse input requires Windows")
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        ulong_ptr = wintypes.WPARAM

        class MouseInput(ctypes.Structure):
            _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                        ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                        ("time", wintypes.DWORD), ("dwExtraInfo", ulong_ptr)]

        class KeyboardInput(ctypes.Structure):
            _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                        ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                        ("dwExtraInfo", ulong_ptr)]

        class HardwareInput(ctypes.Structure):
            _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                        ("wParamH", wintypes.WORD)]

        class InputUnion(ctypes.Union):
            _fields_ = [("mi", MouseInput), ("ki", KeyboardInput), ("hi", HardwareInput)]

        class Input(ctypes.Structure):
            _anonymous_ = ("data",)
            _fields_ = [("type", wintypes.DWORD), ("data", InputUnion)]

        self.Input, self.MouseInput = Input, MouseInput
        self.user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int]
        self.user32.SendInput.restype = wintypes.UINT
        self.user32.GetForegroundWindow.restype = wintypes.HWND
        self.user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]

    def external_foreground(self) -> int | None:
        hwnd = self.user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return int(hwnd) if pid.value != os.getpid() else None

    def move(self, dx: int, dy: int) -> None:
        if not (dx or dy):
            return
        item = self.Input(type=0, mi=self.MouseInput(dx=dx, dy=dy, dwFlags=0x0001))
        if self.user32.SendInput(1, ctypes.byref(item), ctypes.sizeof(self.Input)) != 1:
            raise OSError("Windows refused mouse input; check game privileges")


class PoseController:
    HEARTBEAT_TIMEOUT = 0.5
    MAX_ANGLE_STEP = 0.4
    MAX_PIXEL_STEP = 120

    def __init__(self, sink: InputSink, on_state: Callable[[bool, str], None] | None = None,
                 focus_provider: Callable[[], int | None] | None = None,
                 clock: Callable[[], float] = time.perf_counter):
        self.sink, self.on_state, self.focus_provider, self.clock = sink, on_state, focus_provider, clock
        self.lock = threading.RLock()
        self.settings = Settings()
        self.connected = False
        self.armed = False
        self.last_pose_time = 0.0
        self.last_seq = -1
        self.baseline = None
        self.target_window = None
        self.armed_at = 0.0
        self.remainder = (0.0, 0.0)
        self.stabilizer = PoseStabilizer()

    def _disarm(self, reason: str):
        changed = self.armed
        self.armed = False
        self.target_window = None
        self.baseline = None
        self.remainder = (0.0, 0.0)
        self.stabilizer.reset()
        if changed and self.on_state:
            self.on_state(False, reason)

    def disarm(self, reason: str = "emergency stop"):
        with self.lock:
            self._disarm(reason)

    def set_connected(self, connected: bool):
        with self.lock:
            self.connected = connected
            self._disarm("headset disconnected" if not connected else "new headset session")
            self.last_seq, self.last_pose_time, self.baseline = -1, 0.0, None

    def set_settings(self, settings: Settings):
        with self.lock:
            if self.settings.mode != settings.mode or settings.mode != "fps":
                self._disarm("mode changed")
            filter_changed = self.stabilizer.configure(settings.stabilization)
            filtered_gain_changed = settings.stabilization > 0 and (
                self.settings.sensitivity != settings.sensitivity or self.settings.invertY != settings.invertY)
            if filter_changed or filtered_gain_changed:
                self.baseline = None
                self.remainder = (0.0, 0.0)
                self.stabilizer.reset()
            self.settings = settings

    def arm(self) -> tuple[bool, str]:
        with self.lock:
            if not self.connected:
                return False, "先连接手机 / Connect a headset first"
            if self.settings.mode != "fps":
                return False, "先选择 FPS 模式 / Select FPS mode first"
            if self.clock() - self.last_pose_time > self.HEARTBEAT_TIMEOUT:
                return False, "手机陀螺仪未就绪 / No live headset pose"
            self.armed = True
            self.armed_at = self.clock()
            self.target_window = None
            self.baseline = None
            self.remainder = (0.0, 0.0)
            self.stabilizer.reset()
            if self.on_state:
                self.on_state(True, "mouse armed; switch to your game within 5 seconds")
            return True, "已启用，5 秒内切换到游戏；F8 停止 / Armed; switch to game, F8 stops"

    def recenter(self):
        with self.lock:
            self.baseline = None
            self.remainder = (0.0, 0.0)
            self.stabilizer.reset()

    def tick(self):
        with self.lock:
            if self.armed and self.clock() - self.last_pose_time > self.HEARTBEAT_TIMEOUT:
                self._disarm("pose heartbeat expired")

    @staticmethod
    def angle_delta(value: float, previous: float) -> float:
        return (value - previous + math.pi) % (2 * math.pi) - math.pi

    def pose(self, seq: int, yaw: float, pitch: float):
        with self.lock:
            if not self.connected or seq <= self.last_seq:
                return
            if not all(math.isfinite(x) for x in (yaw, pitch)):
                return
            now = self.clock()
            if self.armed and now - self.last_pose_time > self.HEARTBEAT_TIMEOUT:
                self._disarm("pose heartbeat expired")
            self.last_seq, self.last_pose_time = seq, now
            previous, self.baseline = self.baseline, (yaw, pitch)
            if not self.armed or self.settings.mode != "fps" or previous is None:
                if self.settings.stabilization > 0:
                    self.stabilizer.reset(now)
                return
            if self.focus_provider:
                foreground = self.focus_provider()
                if self.target_window is None:
                    if foreground is None:
                        if now - self.armed_at > 5:
                            self._disarm("no game window selected within 5 seconds")
                        elif self.settings.stabilization > 0:
                            self.stabilizer.reset(now)
                        return
                    self.target_window = foreground
                    if self.settings.stabilization > 0:
                        self.stabilizer.reset(now)
                    return  # Establish a fresh baseline after the focus transition.
                if foreground != self.target_window:
                    self._disarm("foreground window changed")
                    return
            dyaw = self.angle_delta(yaw, previous[0])
            dpitch = self.angle_delta(pitch, previous[1])
            if abs(dyaw) > self.MAX_ANGLE_STEP or abs(dpitch) > self.MAX_ANGLE_STEP:
                self.remainder = (0.0, 0.0)  # Drop a sensor reset/spike; baseline already updated.
                if self.settings.stabilization > 0:
                    self.stabilizer.reset(now)
                return
            if self.settings.stabilization > 0:
                dyaw, dpitch = self.stabilizer.step(dyaw, dpitch, now)
            dx = dyaw * self.settings.sensitivity + self.remainder[0]
            dy = dpitch * self.settings.sensitivity * (1 if self.settings.invertY else -1) + self.remainder[1]
            ix = max(-self.MAX_PIXEL_STEP, min(self.MAX_PIXEL_STEP, round(dx)))
            iy = max(-self.MAX_PIXEL_STEP, min(self.MAX_PIXEL_STEP, round(dy)))
            self.remainder = (dx - round(dx), dy - round(dy))
            if self.settings.stabilization > 0:
                # Integer movement clipped by the historical cap is discarded,
                # never paid back by a filtered tail on later stationary poses.
                clipped_yaw = abs(round(dx)) > self.MAX_PIXEL_STEP
                clipped_pitch = abs(round(dy)) > self.MAX_PIXEL_STEP
                if clipped_yaw or clipped_pitch:
                    self.stabilizer.discard_lag(yaw=clipped_yaw, pitch=clipped_pitch)
            try:
                self.sink.move(ix, iy)
            except Exception as exc:
                self._disarm(str(exc))


class EmergencyHotkey:
    """Global F8 on its own Windows message thread, independent of Tk focus."""
    def __init__(self, callback, on_error=None):
        self.callback, self.on_error = callback, on_error
        self.thread = None
        self.thread_id = None
        self.ready = threading.Event()
        self.registered = False

    def start(self):
        if os.name != "nt":
            return False
        self.thread = threading.Thread(target=self._run, daemon=True, name="vr-emergency-key")
        self.thread.start()
        self.ready.wait(timeout=1)
        return self.registered

    def _run(self):
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.thread_id = kernel32.GetCurrentThreadId()
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)
        if not user32.RegisterHotKey(None, 1, 0x4000, 0x77):  # MOD_NOREPEAT, VK_F8
            if self.on_error:
                self.on_error("F8 热键被占用，请关闭占用程序 / F8 is in use")
            self.ready.set()
            return
        self.registered = True
        self.ready.set()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == 0x0312:
                    self.callback()
        finally:
            user32.UnregisterHotKey(None, 1)
            self.registered = False

    def stop(self):
        if self.thread_id is not None and os.name == "nt":
            ctypes.WinDLL("user32").PostThreadMessageW(self.thread_id, 0x0012, 0, 0)
        if self.thread:
            self.thread.join(timeout=1)

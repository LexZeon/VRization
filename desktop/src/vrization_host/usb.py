"""Original USB transports. No device driver, adb or third-party USB library is bundled.

ADB syntax: Android's official adb.1 manual. usbmux uses the public plist wire
protocol (ListDevices/Connect); no libusbmuxd application source is incorporated.
Detection and relay I/O run separately and never call Windows mouse APIs.
"""

from collections import deque
from contextlib import suppress
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import os
from pathlib import Path
import plistlib
import re
import socket
import struct
import subprocess
import sys
import threading
import time
from xml.parsers.expat import ExpatError

from aiohttp import ClientError, ClientResponseError
from .connection import ANDROID_CONTROL_PORT

ANDROID_PORT = 18765
IOS_PORT = 18766
MAX_FRAME = 8 * 1024 * 1024  # Includes the one-byte kind, excludes length prefix.
MAX_JSON = 16 * 1024


def safe_relay_error(error) -> str:
    # aiohttp handshake exceptions embed the authenticated URL in str(error).
    if isinstance(error, ClientResponseError):
        return f"Host connection failed (HTTP {error.status})"
    if isinstance(error, ClientError):
        return "Host connection unavailable"
    if isinstance(error, UnicodeError):
        return "Invalid UTF-8 USB message"
    return str(error)


def portable_adb_candidates() -> list[Path]:
    """Fixed SDK layouts rooted at the frozen app, never its working directory.

    The SDK is installed separately by the user. It is not shipped in our ZIP,
    repo or PyInstaller extraction directory. Archive layouts let a directly
    opened EXE find the same local tools as the generated launcher.
    """
    if not getattr(sys, "frozen", False):
        return []
    program = Path(sys.executable).resolve().parent
    roots = [program]
    if program.name.casefold() == "windows":
        container = program.parent
        roots.append(container)
        if container.name.casefold() == "latest" or re.fullmatch(
                r"previous-latest-\d{8}-\d{6}-[a-f0-9]{6}", container.name):
            roots.append(container.parent)
        elif container.parent.name.casefold() == "versions" and re.fullmatch(
                r"v\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?", container.name):
            roots.append(container.parent.parent)
    return [root / "tools" / "android-sdk" / "platform-tools" / "adb.exe" for root in roots]


def find_adb(explicit: str = "") -> Path | None:
    """Use a chosen or known SDK tool, never an arbitrary PATH/CWD executable."""
    candidates = [Path(explicit)] if explicit else []
    for variable in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        if os.environ.get(variable):
            candidates.append(Path(os.environ[variable]) / "platform-tools" / "adb.exe")
    local_app_data = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    candidates.extend((local_app_data / "Android" / "Sdk" / "platform-tools" / "adb.exe",
                       local_app_data / "VRization" / "tools" / "android-sdk" /
                       "platform-tools" / "adb.exe"))
    candidates.extend(portable_adb_candidates())
    for path in candidates:
        if path.name.lower() in ("adb", "adb.exe") and path.is_file():
            return path.resolve()
    return None


@dataclass(frozen=True)
class AndroidDevice:
    serial: str
    state: str
    usb: bool


def parse_adb_devices(output: str) -> list[AndroidDevice]:
    devices = []
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 2 or fields[0] == "List" or fields[0].startswith("*"):
            continue
        serial, state = fields[:2]
        # Network ADB can use an mDNS hostname instead of a numeric ip:port.
        if serial.startswith("emulator-") or ":" in serial or "._tcp" in serial:
            continue
        devices.append(AndroidDevice(serial, state, any(f.startswith("usb:") for f in fields[2:])))
    return devices


def reverse_mappings(output: str) -> set[tuple[str, str]]:
    result = set()
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 2:
            result.add(tuple(fields[-2:]))
    return result


def pnp_usb_serials(identities) -> set[str]:
    """Require a full USB VID/PID instance identity, never substring matches."""
    if isinstance(identities, str):
        identities = [identities]
    if not isinstance(identities, list):
        return set()
    result = set()
    for identity in identities:
        if isinstance(identity, str):
            match = re.fullmatch(r"USB\\VID_[0-9A-F]{4}&PID_[0-9A-F]{4}(?:&[^\\]*)?\\([^\\]+)",
                                 identity, flags=re.IGNORECASE)
            if match:
                result.add(match[1].casefold())
    return result


def windows_usb_instance_ids(load_library=None) -> list[str]:
    """Enumerate present USB instance IDs through read-only Windows SetupAPI."""
    load_library = load_library or ctypes.WinDLL
    setup = load_library("setupapi", use_last_error=True)

    class GUID(ctypes.Structure):
        _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD), ("Data4", wintypes.BYTE * 8)]

    class SP_DEVINFO_DATA(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("ClassGuid", GUID),
                    ("DevInst", wintypes.DWORD), ("Reserved", ctypes.c_size_t)]

    setup.SetupDiGetClassDevsW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, wintypes.HWND, wintypes.DWORD]
    setup.SetupDiGetClassDevsW.restype = wintypes.HANDLE
    setup.SetupDiEnumDeviceInfo.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(SP_DEVINFO_DATA)]
    setup.SetupDiEnumDeviceInfo.restype = wintypes.BOOL
    setup.SetupDiGetDeviceInstanceIdW.argtypes = [wintypes.HANDLE, ctypes.POINTER(SP_DEVINFO_DATA),
                                               wintypes.LPWSTR, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    setup.SetupDiGetDeviceInstanceIdW.restype = wintypes.BOOL
    setup.SetupDiDestroyDeviceInfoList.argtypes = [wintypes.HANDLE]
    setup.SetupDiDestroyDeviceInfoList.restype = wintypes.BOOL
    handle = setup.SetupDiGetClassDevsW(None, "USB", None, 0x00000004 | 0x00000002)
    if handle is None or handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    identities = []
    try:
        index = 0
        while True:
            info = SP_DEVINFO_DATA()
            info.cbSize = ctypes.sizeof(SP_DEVINFO_DATA)
            if not setup.SetupDiEnumDeviceInfo(handle, index, ctypes.byref(info)):
                error = ctypes.get_last_error()
                if error == 259:  # ERROR_NO_MORE_ITEMS
                    break
                raise ctypes.WinError(error)
            required = wintypes.DWORD()
            ok = setup.SetupDiGetDeviceInstanceIdW(handle, ctypes.byref(info), None, 0, ctypes.byref(required))
            if not ok and ctypes.get_last_error() != 122:  # ERROR_INSUFFICIENT_BUFFER
                raise ctypes.WinError(ctypes.get_last_error())
            if not 1 <= required.value <= 32768:
                raise ValueError("Invalid Windows USB instance ID length")
            buffer = ctypes.create_unicode_buffer(required.value)
            if not setup.SetupDiGetDeviceInstanceIdW(handle, ctypes.byref(info), buffer, len(buffer), None):
                raise ctypes.WinError(ctypes.get_last_error())
            identities.append(buffer.value)
            index += 1
    finally:
        setup.SetupDiDestroyDeviceInfoList(handle)
    return identities


class WindowsUsbPresence:
    """Read-only physical USB evidence for Windows adb backends reporting unknown."""

    def __init__(self, reader=None, *, windows=None, clock=None):
        self.reader, self.clock = reader or windows_usb_instance_ids, clock or time.monotonic
        self.windows = os.name == "nt" if windows is None else windows
        self._expires, self._serials = 0, set()

    def __call__(self, serial: str) -> bool:
        if not self.windows:
            return False
        if self.clock() >= self._expires:
            self._serials = set()
            try:
                self._serials = pnp_usb_serials(self.reader())
            except (OSError, ValueError):
                pass
            self._expires = self.clock() + 10
        present = serial.casefold() in self._serials
        if not present:
            # Enumeration can briefly precede Windows PnP discovery. Retry a
            # negative proof sooner without relaxing the physical USB check.
            self._expires = min(self._expires, self.clock() + 2)
        return present


class AdbReverse:
    def __init__(self, path: Path, runner=None, usb_presence=None, *, clock=None, remote_port=ANDROID_PORT):
        if type(remote_port) is not int or not 1 <= remote_port <= 65535:
            raise ValueError("Invalid USB reverse port")
        self.path = path
        self.remote_port = remote_port
        self.runner = runner or subprocess.run
        self.owned: tuple[str, str, str] | None = None
        self.usb_presence = usb_presence or WindowsUsbPresence()
        self.clock = clock or time.perf_counter
        self.enumeration_ready = False
        self.recent_commands = deque(maxlen=8)
        self.last_devices_probe = None

    def command(self, *args, timeout: float = 3) -> str:
        # Windowed frozen applications can have no valid inherited stdin handle.
        # ADB discovery is noninteractive; never inherit GUI standard handles.
        if args == ("devices", "-l"):
            stage = "devices"
        elif args == ("version",):
            stage = "version"
        elif args[-1:] == ("get-devpath",):
            stage = "physical_transport"
        elif args[2:5] == ("shell", "am", "start"):
            stage = "phone_connect"
        elif "reverse" in args:
            stage = ("mapping_create" if "--no-rebind" in args else
                     "mapping_remove" if "--remove" in args else "mapping_list")
        else:
            stage = "other"
        started, outcome = self.clock(), "error"
        try:
            result = self.runner([str(self.path), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                 timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if result.returncode:
                raise OSError(result.stderr.strip() or "Android USB command failed")
            outcome = "ok"
            return result.stdout
        except subprocess.TimeoutExpired:
            outcome = "timeout"
            if stage.startswith("mapping_"):
                self.enumeration_ready = False
            raise
        except OSError:
            outcome = "unavailable"
            if stage.startswith("mapping_"):
                self.enumeration_ready = False
            raise
        finally:
            # Deliberately exclude arguments, IDs, paths, stdout and stderr.
            probe = {"stage": stage, "elapsedMs": max(0, (self.clock() - started) * 1000),
                     "timeoutSeconds": timeout, "result": outcome}
            self.recent_commands.append(probe)
            if stage == "devices":
                self.last_devices_probe = probe

    def devices(self) -> list[AndroidDevice]:
        result = []
        # A cold/recovering daemon needs time to ACK its Windows startup pipe.
        # Never repeatedly cut startup off at the steady-state three-second limit.
        timeout = 3 if self.enumeration_ready else 8
        try:
            output = self.command("devices", "-l", timeout=timeout)
        except (OSError, subprocess.TimeoutExpired):
            self.enumeration_ready = False
            raise
        self.enumeration_ready = True
        for device in parse_adb_devices(output):
            usb = device.usb
            if not usb and device.state == "device":
                with suppress(OSError, subprocess.TimeoutExpired):
                    usb = self.command("-s", device.serial, "get-devpath").strip().startswith("usb:")
                if not usb:
                    usb = self.usb_presence(device.serial)
            elif not usb and device.state == "offline":
                # An offline transport cannot answer get-devpath. Present USB
                # PnP evidence is enough to explain its state, never authorize it.
                usb = self.usb_presence(device.serial)
            if usb or device.state == "unauthorized":
                result.append(AndroidDevice(device.serial, device.state, usb))
        return result

    def ensure(self, serial: str, host_port: int) -> bool:
        remote, local = f"tcp:{self.remote_port}", f"tcp:{host_port}"
        current = reverse_mappings(self.command("-s", serial, "reverse", "--list"))
        if self.owned == (serial, remote, local) and (remote, local) in current:
            return True
        if self.owned is not None:
            if not self.release():
                raise OSError("Android USB mapping cleanup unavailable")
            current = reverse_mappings(self.command("-s", serial, "reverse", "--list"))
        if any(source == remote for source, _ in current):
            return False  # Even an identical existing mapping belongs to someone else.
        self.command("-s", serial, "reverse", "--no-rebind", remote, local)
        self.owned = (serial, remote, local)
        return True

    def release(self):
        owned = self.owned
        if owned is None:
            return True
        serial, remote, local = owned
        try:
            current = reverse_mappings(self.command("-s", serial, "reverse", "--list"))
            if (remote, local) in current:
                self.command("-s", serial, "reverse", "--remove", remote)
        except (OSError, subprocess.TimeoutExpired):
            # Uncertain cleanup must revoke authorization, not forget ownership.
            # A later successful read can recover or remove only this mapping.
            return False
        self.owned = None
        return True


def pack_frame(kind: int, payload: bytes) -> bytes:
    if kind not in (1, 2) or not 1 <= len(payload) + 1 <= MAX_FRAME:
        raise ValueError("Invalid USB frame")
    return struct.pack(">I", len(payload) + 1) + bytes((kind,)) + payload


async def read_frame(reader) -> tuple[int, bytes]:
    length, = struct.unpack(">I", await reader.readexactly(4))
    if not 1 <= length <= MAX_FRAME:
        raise ValueError("Invalid USB frame length")
    kind = (await reader.readexactly(1))[0]
    if kind not in (1, 2):
        raise ValueError("Invalid USB frame kind")
    # Validate before allocation, and phone input must be JSON only.
    if kind != 1 or length - 1 > MAX_JSON:
        raise ValueError("Phone USB input must be JSON <=16 KiB")
    return kind, await reader.readexactly(length - 1)


def _receive_exact(sock, size: int, deadline=None) -> bytes:
    data = bytearray()
    while len(data) < size:
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Apple USB service response timed out")
            if hasattr(sock, "settimeout"):
                sock.settimeout(remaining)
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionError("USB service disconnected")
        data.extend(chunk)
    return bytes(data)


@dataclass(frozen=True)
class AppleDevice:
    device_id: int
    serial: str


class AppleEndpointUnavailable(ConnectionError):
    """A paired mux Connect specifically reports connection refused."""


class AppleMux:
    """Local Apple Mobile Device service, accessed by its plist message protocol."""
    def __init__(self, connector=None, address=("127.0.0.1", 27015)):
        self.connector = connector or socket.create_connection
        self.address = address

    def _socket(self):
        return self.connector(self.address, timeout=2)

    def exchange(self, sock, message: dict, tag: int = 1) -> dict:
        payload = plistlib.dumps({"ClientVersionString": "VRization-0.3.0", "ProgName": "VRization",
                                 "kLibUSBMuxVersion": 3, **message}, fmt=plistlib.FMT_XML)
        sock.sendall(struct.pack("<IIII", 16 + len(payload), 1, 8, tag) + payload)
        deadline = time.monotonic() + 2
        length, version, kind, reply_tag = struct.unpack("<IIII", _receive_exact(sock, 16, deadline))
        if not 16 <= length <= 1024 * 1024 or version != 1 or kind != 8 or reply_tag != tag:
            raise ValueError("Invalid Apple USB service response")
        try:
            result = plistlib.loads(_receive_exact(sock, length - 16, deadline))
        except (ValueError, ExpatError, plistlib.InvalidFileException) as exc:
            raise ValueError("Invalid Apple USB service plist") from exc
        if not isinstance(result, dict):
            raise ValueError("Invalid Apple USB service plist")
        return result

    def devices(self) -> list[AppleDevice]:
        with self._socket() as sock:
            result = self.exchange(sock, {"MessageType": "ListDevices"})
        entries = result.get("DeviceList", [])
        if not isinstance(entries, list):
            raise ValueError("Invalid Apple USB device list")
        devices = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            props = entry.get("Properties", {})
            identity = entry.get("DeviceID")
            if (isinstance(props, dict) and props.get("ConnectionType") == "USB"
                    and type(identity) is int and identity > 0):
                devices.append(AppleDevice(identity, str(props.get("SerialNumber", identity))))
        return devices

    def connect(self, device: AppleDevice, port=IOS_PORT):
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("Invalid Apple USB port")
        # Read only: a USB enumeration alone does not establish Trust This Computer.
        # Keep pairing keys in memory only; never log, write or return their contents.
        with self._socket() as paired:
            result = self.exchange(paired, {"MessageType": "ReadPairRecord", "PairRecordID": device.serial})
        data = result.get("PairRecordData")
        try:
            record = plistlib.loads(data) if isinstance(data, bytes) else None
        except (ValueError, ExpatError, plistlib.InvalidFileException):
            record = None
        if (not isinstance(record, dict) or not isinstance(record.get("HostID"), str)
                or not record["HostID"]):
            raise ConnectionError("Unlock your iPhone and Trust This Computer in Apple Devices")
        sock = self._socket()
        try:
            response = self.exchange(sock, {"MessageType": "Connect", "DeviceID": device.device_id,
                                           "PortNumber": socket.htons(port)})
            result = response.get("Number")
            if type(result) is not int:
                raise ValueError("Invalid Apple USB connection result")
            if result == 3:  # usbmux RESULT_CONNREFUSED, not a missing device.
                raise AppleEndpointUnavailable("Open VRization on your iPhone and tap Connect (USB)")
            if result != 0:
                raise ConnectionError("Open VRization on your iPhone and tap Connect (USB)")
            sock.setblocking(False)
            return sock
        except Exception:
            sock.close()
            raise



class UsbManager:
    def __init__(self, server, on_event=None, *, adb_path=None, preferred_serial="", adb=None, mux=None,
                 mux_address=("127.0.0.1", 27015), control_adb=None, start_request=None, ios_notify=None,
                 ios_stop_notify=None, android_video_port=ANDROID_PORT, android_control_port=ANDROID_CONTROL_PORT,
                 android_component="org.vrization.app/.MainActivity", ios_video_port=18766, ios_control_port=18767):
        self.server, self.on_event = server, on_event
        self.android_video_port, self.android_control_port = android_video_port, android_control_port
        self.android_component = android_component
        self.ios_video_port = ios_video_port
        self.adb_path, self.preferred_serial = adb_path or "", preferred_serial
        self._configured_path = self.adb_path
        self.adb, self.mux = adb, mux or AppleMux(address=mux_address)
        self.authorized = threading.Event()
        self.control_authorized = threading.Event()
        self.control_adb = control_adb
        self._control_source = adb if control_adb is not None else None
        self.enabled = threading.Event()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._connect_lock = threading.Lock()
        self._connect_generation = 0
        self._connect_pending = None
        self._ios_lock = threading.RLock()
        self._ios_generation = 0
        self._ios_start_blocked = False
        self._ios_device = self._ios_stop_target = None
        self._ios_stop_pending = None
        self._start_request = start_request
        self._thread = None
        self._last_status = None
        self._last_devices = None
        self._scan_failed = False
        self._failed_scans = 0
        from .ios_usb import IosRelay, request_ios_connect, request_ios_stop
        self.relay = IosRelay(server, self.mux, self.status, video_port=ios_video_port,
                              start_request=self._ios_request_start if start_request is not None else None)
        self.ios_notify = ios_notify or (lambda mux, device: request_ios_connect(mux, device, port=ios_control_port))
        self.ios_stop_notify = ios_stop_notify or (lambda mux, device: request_ios_stop(mux, device, port=ios_control_port))

    def status(self, message, **values):
        state = (message, values)
        if state != self._last_status:
            self._last_status = state
            if self.on_event:
                self.on_event({"event": "usb", "message": message, "values": values})

    def start(self, enabled=True):
        self.set_enabled(enabled)
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="vrization-usb-detect", daemon=True)
            self._thread.start()

    def set_enabled(self, enabled):
        self.enabled.set() if enabled else self.enabled.clear()
        if not enabled:
            self.authorized.clear()
            self.control_authorized.clear()
            self.cancel_connect()
            self.relay.request_stop()

    def request_connect(self, *, timeout=20):
        """Queue one explicit desktop Connect action, never a detection action."""
        if not self.enabled.is_set() or self._stop.is_set():
            return False
        with self._connect_lock:
            self._connect_generation += 1
            self._connect_pending = (self._connect_generation, time.perf_counter() + min(30, max(1, timeout)))
        # A new explicit desktop gesture supersedes an unconfirmed old Stop.
        with self._ios_lock:
            self._ios_generation += 1
            self._ios_start_blocked = False
            self._ios_stop_pending = self._ios_stop_target = None
        self._wake.set()
        return True

    def _ios_request_start(self, generation=None, device=None):
        with self._ios_lock:
            if (generation is not None and generation != self._ios_generation
                    or device is not None and device != self._ios_device):
                return False
            if self._ios_blocked_for(self._ios_device) or not self.enabled.is_set() or self._stop.is_set():
                return False
            return self._start_request() if self._start_request is not None else False

    def _ios_blocked_for(self, device):
        return self._ios_start_blocked and (self._ios_stop_target is None or device is None
                                            or self._ios_stop_target.serial == device.serial)

    def request_stop_phone(self):
        """Revoke pending iOS readiness before scheduling one paired Stop."""
        self.cancel_connect()
        with self._ios_lock:
            self._ios_generation += 1
            self._ios_start_blocked = True
            self._ios_stop_target = self._ios_device
            self._ios_stop_pending = (self._ios_generation, time.perf_counter() + 8)
            self.relay.request_stop()
        self._wake.set()

    def _ios_stop_confirmed(self, generation, device):
        with self._ios_lock:
            if (generation == self._ios_generation and self._ios_start_blocked
                    and device == self._ios_stop_target):
                self._ios_start_blocked = False
                self._ios_stop_pending = None

    def _service_ios_stop(self):
        # Only the existing detection thread performs this bounded notification.
        # No GUI-thread I/O, repeated intent, shared daemon reset, or SDK install.
        with self._ios_lock:
            pending = self._ios_stop_pending
            if pending is None:
                return
            generation, deadline = pending
            if time.perf_counter() > deadline:
                self._ios_stop_pending = None
                self.status("iPhone Stop is unconfirmed; tap Connect on this PC for a new attempt")
                return
        try:
            devices = self.mux.devices()
        except (OSError, ValueError, plistlib.InvalidFileException):
            return
        with self._ios_lock:
            if pending != self._ios_stop_pending or generation != self._ios_generation:
                return
            target = self._ios_stop_target
            candidates = [device for device in devices if target is not None and device.serial == target.serial]
            if target is None and len(devices) == 1:
                candidates = devices
            if len(candidates) != 1:
                return
            # IDs can be reused/reassigned. Only today's USB enumeration paired
            # with the selected phone's identity authorizes this targeted Stop.
            device = self._ios_stop_target = candidates[0]
            self._ios_stop_pending = None  # Exactly one attempt for this gesture.
        try:
            acknowledged = self.ios_stop_notify(self.mux, device)
        except (OSError, ValueError):
            acknowledged = False
        if acknowledged is True:
            self._ios_stop_confirmed(generation, device)
        else:
            with self._ios_lock:
                if generation == self._ios_generation and self._ios_start_blocked:
                    self.status("iPhone Stop is unconfirmed; tap Connect on this PC for a new attempt")

    def _probe_ios_stopped(self, device, generation):
        # A refused *paired* endpoint proves that no old video listener remains.
        # If it still accepts, close the owned probe without readiness/host WS.
        try:
            sock = (self.mux.connect(device) if self.ios_video_port == 18766 else
                    self.mux.connect(device, port=self.ios_video_port))
        except AppleEndpointUnavailable:
            self._ios_stop_confirmed(generation, device)
        except (OSError, ValueError):
            pass  # Trust, service/device loss and timeouts prove no such fact.
        else:
            sock.close()

    def cancel_connect(self):
        with self._connect_lock:
            self._connect_generation += 1
            self._connect_pending = None
        self._wake.set()

    def _take_connect(self):
        with self._connect_lock:
            pending, self._connect_pending = self._connect_pending, None
            if pending is None or time.perf_counter() > pending[1]:
                return False
            return self.enabled.is_set() and not self._stop.is_set()

    def _release_android(self):
        self.authorized.clear()
        self.control_authorized.clear()
        for adapter in (self.adb, self.control_adb):
            if adapter:
                adapter.release()

    def _ensure_control(self, selected):
        if self._control_source is not self.adb:
            self.control_authorized.clear()
            if self.control_adb and not self.control_adb.release():
                return False
            self.control_adb = None
            path = getattr(self.adb, "path", None)
            if path is not None:
                self.control_adb = AdbReverse(path, self.adb.runner, self.adb.usb_presence,
                                              remote_port=self.android_control_port)
            self._control_source = self.adb
        return self.control_adb is not None and self.control_adb.ensure(selected.serial, self.android_control_port)

    def _run(self):
        while not self._stop.is_set():
            self._wake.clear()
            self._scan_failed = False
            try:
                self.scan()
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                self.authorized.clear()
                self.control_authorized.clear()
                self._scan_failed = True
                self.status("USB: {detail}", detail=str(exc))
            self._failed_scans = min(3, self._failed_scans + 1) if self._scan_failed else 0
            self._wake.wait(min(8, 2 ** self._failed_scans) if self._failed_scans else 2)
        self._release_android()
        self.relay.stop()

    def scan(self):
        self._service_ios_stop()
        with self._connect_lock:
            expired = self._connect_pending is not None and time.perf_counter() > self._connect_pending[1]
            if expired:
                self._connect_pending = None
        if expired:
            self.status("USB connection request expired; tap Connect again")
        if self.adb_path != self._configured_path:
            self._release_android()
            if self.adb:
                if self.adb.owned or self.control_adb and self.control_adb.owned:
                    self.status("USB cleanup unavailable; retrying before switching tools")
                    self._scan_failed = True
                    return
            self.adb = None
            self._configured_path = self.adb_path
        if not self.enabled.is_set():
            self._release_android()
            self.relay.stop()
            self.status("USB off; use LAN address and pairing code")
            return
        if self.adb is None:
            path = find_adb(self.adb_path)
            if path:
                self.adb = AdbReverse(path, **({"remote_port": self.android_video_port}
                                           if self.android_video_port != ANDROID_PORT else {}))
        devices, adb_error, adb_timeout = [], False, False
        if self.adb:
            try:
                devices = self.adb.devices()
            except subprocess.TimeoutExpired:
                adb_error = adb_timeout = True
            except OSError:
                adb_error = True
        self._scan_failed = adb_error
        authorized = [d for d in devices if d.state == "device" and d.usb]
        serials = tuple(d.serial for d in authorized)
        if serials != self._last_devices:
            self._last_devices = serials
            if self.on_event:
                self.on_event({"event": "usb_devices", "serials": serials})
        selected = next((d for d in authorized if d.serial == self.preferred_serial), None)
        if not self.preferred_serial and len(authorized) == 1:
            selected = authorized[0]
        if selected:
            if self.adb.owned and self.adb.owned[0] != selected.serial:
                self.authorized.clear()
                self.control_authorized.clear()
            if self.adb.ensure(selected.serial, self.server.port):
                if self.enabled.is_set() and not self._stop.is_set():
                    self.authorized.set()
                    control_ready = self._ensure_control(selected)
                    if control_ready and self.enabled.is_set() and not self._stop.is_set():
                        self.control_authorized.set()
                        self.status("Android USB ready: {serial}", serial=selected.serial)
                        if self.server.running and self._take_connect():
                            self.adb.command("-s", selected.serial, "shell", "am", "start", "--activity-single-top",
                                             "--activity-clear-top", "-n", self.android_component,
                                             "--ez", "vrization_connect_usb", "true")
                    else:
                        self.control_authorized.clear()
                        self.status("USB control port is in use or unavailable; existing mappings were kept")
                else:
                    self._release_android()
            else:
                self.authorized.clear()
                self.control_authorized.clear()
                self.status("USB port is in use by another application; no mapping changed")
            self.relay.stop()
            return
        self._release_android()
        try:
            apple = self.mux.devices()
        except (OSError, ValueError, plistlib.InvalidFileException):
            apple = []
        if len(authorized) > 1:
            self.status("Choose an Android USB device; multiple devices are connected")
        elif any(d.state == "unauthorized" for d in devices):
            self.status("Unlock Android and allow USB debugging for this computer")
        elif any(d.state == "offline" and d.usb for d in devices):
            self.status("Android USB offline; reconnect cable, unlock the phone and allow USB debugging")
        elif apple:
            if len(apple) != 1:
                self.status("Connect only one iPhone for automatic USB pairing")
            elif self.enabled.is_set() and not self._stop.is_set():
                with self._ios_lock:
                    self._ios_device = apple[0]
                    if (self._ios_start_blocked and self._ios_stop_target is not None
                            and self._ios_stop_target.serial == apple[0].serial):
                        self._ios_stop_target = apple[0]
                self._service_ios_stop()
                if self.server.running and self._take_connect():
                    self.ios_notify(self.mux, apple[0])
                with self._ios_lock:
                    generation, blocked = self._ios_generation, self._ios_blocked_for(apple[0])
                    stop_target = self._ios_stop_target
                if blocked:
                    if apple[0] == stop_target:
                        self._probe_ios_stopped(apple[0], generation)
                    return
                if not self.server.controller.connected:
                    with self._ios_lock:
                        if generation == self._ios_generation and not self._ios_blocked_for(apple[0]):
                            self.relay.start(apple[0],
                                             on_video_absent=lambda: self._ios_stop_confirmed(generation, apple[0]),
                                             start_request=(lambda: self._ios_request_start(generation, apple[0]))
                                             if self._start_request is not None else None)
        elif self.adb is None:
            self.status("USB waiting: install Android Platform Tools or Apple Devices; LAN is available")
        elif adb_timeout:
            probe = getattr(self.adb, "last_devices_probe", None)
            startup = probe is not None and probe["timeoutSeconds"] > 3
            self.status("Android USB startup or recovery timed out; retrying automatically" if startup else
                        "Android USB detection timed out; retrying automatically")
        elif adb_error:
            self.status("Android USB unavailable; check the official Platform Tools path")
        else:
            self.status("Connect a USB phone; enable Android USB debugging or install Apple Devices")

    def stop(self):
        self._stop.set()
        self.cancel_connect()
        self.authorized.clear()
        self.control_authorized.clear()
        self.relay.stop()
        if self._thread:
            self._thread.join(timeout=12)


# Lazy spelling keeps the original embedding API while avoiding circular imports.
def __getattr__(name):
    if name in ("IOSUsbRelay", "IosRelay"):
        from .ios_usb import IosRelay
        return IosRelay
    raise AttributeError(name)

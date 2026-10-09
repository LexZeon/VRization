"""Original USB transports. No device driver, adb or third-party USB library is bundled.

ADB syntax: Android's official adb.1 manual. usbmux uses the public plist wire
protocol (ListDevices/Connect); no libusbmuxd application source is incorporated.
Detection and relay I/O run separately and never call Windows mouse APIs.
"""

import asyncio
from contextlib import suppress
from dataclasses import dataclass
import os
import json
from pathlib import Path
import plistlib
import re
import socket
import struct
import subprocess
import threading
import time
from xml.parsers.expat import ExpatError

from aiohttp import ClientError, ClientSession, ClientTimeout, WSMsgType

ANDROID_PORT = 18765
IOS_PORT = 18766
MAX_FRAME = 8 * 1024 * 1024  # Includes the one-byte kind, excludes length prefix.
MAX_JSON = 16 * 1024


def find_adb(explicit: str = "") -> Path | None:
    """Only use an explicitly chosen SDK tool or standard Android SDK locations."""
    candidates = [Path(explicit)] if explicit else []
    for variable in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        if os.environ.get(variable):
            candidates.append(Path(os.environ[variable]) / "platform-tools" / "adb.exe")
    candidates.append(Path(os.environ.get("LOCALAPPDATA", Path.home())) /
                      "Android" / "Sdk" / "platform-tools" / "adb.exe")
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


class WindowsUsbPresence:
    """Read-only physical USB evidence for Windows adb backends reporting unknown."""
    QUERY = ("[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new(); "
             "@(Get-CimInstance Win32_PnPEntity | Where-Object { "
             "$_.PNPDeviceID -like 'USB\\VID_*' -and $_.ConfigManagerErrorCode -eq 0 } | "
             "Select-Object -ExpandProperty PNPDeviceID) | ConvertTo-Json -Compress")

    def __init__(self, runner=None, *, windows=None, clock=None):
        self.runner, self.clock = runner or subprocess.run, clock or time.monotonic
        self.windows = os.name == "nt" if windows is None else windows
        self._expires, self._serials = 0, set()

    def __call__(self, serial: str) -> bool:
        if not self.windows:
            return False
        if self.clock() >= self._expires:
            self._serials = set()
            executable = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
            try:
                result = self.runner([str(executable), "-NoProfile", "-NonInteractive", "-Command", self.QUERY],
                                     capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=4,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                if result.returncode == 0:
                    self._serials = pnp_usb_serials(json.loads(result.stdout or "[]"))
            except (OSError, ValueError, subprocess.TimeoutExpired):
                pass
            self._expires = self.clock() + 10
        return serial.casefold() in self._serials


class AdbReverse:
    def __init__(self, path: Path, runner=None, usb_presence=None):
        self.path = path
        self.runner = runner or subprocess.run
        self.owned: tuple[str, str, str] | None = None
        self.usb_presence = usb_presence or WindowsUsbPresence()

    def command(self, *args) -> str:
        result = self.runner([str(self.path), *args], capture_output=True, text=True,
                             timeout=3, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if result.returncode:
            raise OSError(result.stderr.strip() or "Android USB command failed")
        return result.stdout

    def devices(self) -> list[AndroidDevice]:
        result = []
        for device in parse_adb_devices(self.command("devices", "-l")):
            usb = device.usb
            if not usb and device.state == "device":
                with suppress(OSError, subprocess.TimeoutExpired):
                    usb = self.command("-s", device.serial, "get-devpath").strip().startswith("usb:")
                if not usb:
                    usb = self.usb_presence(device.serial)
            if usb or device.state == "unauthorized":
                result.append(AndroidDevice(device.serial, device.state, usb))
        return result

    def ensure(self, serial: str, host_port: int) -> bool:
        remote, local = f"tcp:{ANDROID_PORT}", f"tcp:{host_port}"
        current = reverse_mappings(self.command("-s", serial, "reverse", "--list"))
        if self.owned == (serial, remote, local) and (remote, local) in current:
            return True
        if self.owned is not None:
            self.release()
            current = reverse_mappings(self.command("-s", serial, "reverse", "--list"))
        if any(source == remote for source, _ in current):
            return False  # Even an identical existing mapping belongs to someone else.
        self.command("-s", serial, "reverse", "--no-rebind", remote, local)
        self.owned = (serial, remote, local)
        return True

    def release(self):
        owned, self.owned = self.owned, None
        if owned:
            serial, remote, local = owned
            with suppress(OSError, subprocess.TimeoutExpired):
                current = reverse_mappings(self.command("-s", serial, "reverse", "--list"))
                if (remote, local) in current:
                    self.command("-s", serial, "reverse", "--remove", remote)


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


class AppleMux:
    """Local Apple Mobile Device service, accessed by its plist message protocol."""
    def __init__(self, connector=None, address=("127.0.0.1", 27015)):
        self.connector = connector or socket.create_connection
        self.address = address

    def _socket(self):
        return self.connector(self.address, timeout=2)

    def exchange(self, sock, message: dict, tag: int = 1) -> dict:
        payload = plistlib.dumps({"ClientVersionString": "VRization-0.2.0", "ProgName": "VRization",
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
        devices = []
        for entry in result.get("DeviceList", []):
            if not isinstance(entry, dict):
                continue
            props = entry.get("Properties", {})
            identity = entry.get("DeviceID")
            if (isinstance(props, dict) and props.get("ConnectionType") == "USB"
                    and type(identity) is int and identity > 0):
                devices.append(AppleDevice(identity, str(props.get("SerialNumber", identity))))
        return devices

    def connect(self, device: AppleDevice):
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
                                           "PortNumber": socket.htons(IOS_PORT)})
            if response.get("Number") != 0:
                raise ConnectionError("Open VRization on your iPhone and tap Connect (USB)")
            sock.setblocking(False)
            return sock
        except Exception:
            sock.close()
            raise


class IosRelay:
    def __init__(self, server, mux=None, on_status=None, *, mux_address=("127.0.0.1", 27015)):
        self.server, self.mux = server, mux or AppleMux(address=mux_address)
        self.on_status = on_status or (lambda *args, **kwargs: None)
        self._thread = None
        self._loop = None
        self._task = None
        self._stop = threading.Event()

    @property
    def active(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self, device: AppleDevice):
        if self.active:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, args=(device,), name="vrization-ios-usb", daemon=True)
        self._thread.start()

    def _run(self, device):
        try:
            asyncio.run(self._relay(device))
        except (ClientError, OSError, ValueError, asyncio.IncompleteReadError, asyncio.TimeoutError) as exc:
            self.on_status("iOS USB: {detail}", detail=str(exc))
        except asyncio.CancelledError:
            pass

    async def _relay(self, device):
        self._loop, self._task = asyncio.get_running_loop(), asyncio.current_task()
        # Already on the dedicated I/O thread. A bounded blocking connect avoids
        # leaking a late socket from a cancelled executor future.
        sock = self.mux.connect(device)
        try:
            if self._stop.is_set():
                return
            reader, writer = await asyncio.open_connection(sock=sock)
        except BaseException:
            sock.close()
            raise
        finally:
            if self._stop.is_set():
                sock.close()
        try:
            if self._stop.is_set():
                return
            url = f"http://127.0.0.1:{self.server.port}/ws?token={self.server.token}"
            async with ClientSession(timeout=ClientTimeout(total=None, sock_connect=2)) as session:
                async with session.ws_connect(url, max_msg_size=MAX_FRAME - 1, compress=0) as ws:
                    self.on_status("iPhone USB connected")

                    async def to_phone():
                        async for message in ws:
                            if message.type == WSMsgType.TEXT:
                                payload, kind = message.data.encode("utf-8"), 1
                            elif message.type == WSMsgType.BINARY:
                                payload, kind = message.data, 2
                            else:
                                break
                            writer.write(pack_frame(kind, payload))
                            await asyncio.wait_for(writer.drain(), 2)

                    async def to_host():
                        while True:
                            _, payload = await read_frame(reader)
                            await asyncio.wait_for(ws.send_str(payload.decode("utf-8")), 2)

                    tasks = [asyncio.create_task(to_phone()), asyncio.create_task(to_host())]
                    try:
                        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                        for task in done:
                            task.result()
                    finally:
                        for task in tasks:
                            task.cancel()
                        await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            writer.close()
            with suppress(OSError, asyncio.TimeoutError):
                await asyncio.wait_for(writer.wait_closed(), 2)
            self._loop = self._task = None
            self.on_status("iPhone USB disconnected")

    def stop(self):
        self.request_stop()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=8)

    def request_stop(self):
        self._stop.set()
        if self._loop and self._task:
            with suppress(RuntimeError):
                self._loop.call_soon_threadsafe(self._task.cancel)


class UsbManager:
    def __init__(self, server, on_event=None, *, adb_path=None, preferred_serial="", adb=None, mux=None,
                 mux_address=("127.0.0.1", 27015)):
        self.server, self.on_event = server, on_event
        self.adb_path, self.preferred_serial = adb_path or "", preferred_serial
        self._configured_path = self.adb_path
        self.adb, self.mux = adb, mux or AppleMux(address=mux_address)
        self.authorized = threading.Event()
        self.enabled = threading.Event()
        self._stop = threading.Event()
        self._thread = None
        self._last_status = None
        self._last_devices = None
        self.relay = IosRelay(server, self.mux, self.status)

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
            self.relay.request_stop()

    def _run(self):
        while not self._stop.is_set():
            try:
                self.scan()
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                self.authorized.clear()
                self.status("USB: {detail}", detail=str(exc))
            self._stop.wait(2)
        self.authorized.clear()
        self.relay.stop()
        if self.adb:
            self.adb.release()

    def scan(self):
        if self.adb_path != self._configured_path:
            self.authorized.clear()
            if self.adb:
                self.adb.release()
            self.adb = None
            self._configured_path = self.adb_path
        if not self.enabled.is_set():
            self.authorized.clear()
            self.relay.stop()
            if self.adb:
                self.adb.release()
            self.status("USB off; use LAN address and pairing code")
            return
        if self.adb is None:
            path = find_adb(self.adb_path)
            if path:
                self.adb = AdbReverse(path)
        devices, adb_error = [], False
        if self.adb:
            try:
                devices = self.adb.devices()
            except (OSError, subprocess.TimeoutExpired):
                adb_error = True
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
            if self.adb.ensure(selected.serial, self.server.port):
                if self.enabled.is_set() and not self._stop.is_set():
                    self.authorized.set()
                    self.status("Android USB ready: {serial}", serial=selected.serial)
                else:
                    self.authorized.clear()
                    self.adb.release()
            else:
                self.authorized.clear()
                self.status("USB port is in use by another application; no mapping changed")
            self.relay.stop()
            return
        self.authorized.clear()
        if self.adb:
            self.adb.release()
        try:
            apple = self.mux.devices()
        except (OSError, ValueError, plistlib.InvalidFileException):
            apple = []
        if len(authorized) > 1:
            self.status("Choose an Android USB device; multiple devices are connected")
        elif any(d.state == "unauthorized" for d in devices):
            self.status("Unlock Android and allow USB debugging for this computer")
        elif apple:
            if len(apple) != 1:
                self.status("Connect only one iPhone for automatic USB pairing")
            elif (self.enabled.is_set() and not self._stop.is_set()
                  and self.server.running and not self.server.controller.connected):
                self.relay.start(apple[0])
            elif not self.server.running:
                self.status("iPhone found; start streaming and open the phone app")
        elif self.adb is None:
            self.status("USB waiting: install Android Platform Tools or Apple Devices; LAN is available")
        elif adb_error:
            self.status("Android USB unavailable; check the official Platform Tools path")
        else:
            self.status("Connect a USB phone; enable Android USB debugging or install Apple Devices")

    def stop(self):
        self._stop.set()
        self.authorized.clear()
        self.relay.stop()
        if self._thread:
            self._thread.join(timeout=12)


# Public spelling used by integration fixtures and embedding applications.
IOSUsbRelay = IosRelay

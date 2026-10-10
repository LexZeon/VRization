"""Original paired iOS USB control and video adapters, independent of host UI."""
import asyncio
from concurrent.futures import Future, InvalidStateError
from contextlib import suppress
import json
import struct
import threading
import time

from aiohttp import ClientError, ClientSession, ClientTimeout, WSMsgType

IOS_CONTROL_PORT = 18767


def request_ios_connect(mux, device):
    """Send one explicit PC request to a foreground, paired iOS app; never poll."""
    from .usb import pack_frame
    with mux.connect(device, port=IOS_CONTROL_PORT) as sock:
        sock.setblocking(True)
        sock.settimeout(2)
        sock.sendall(pack_frame(1, b'{"v":1,"type":"connect"}'))


def request_ios_stop(mux, device):
    """One paired Stop, acknowledged only after native video/renderer cleanup."""
    from .usb import _receive_exact, pack_frame
    with mux.connect(device, port=IOS_CONTROL_PORT) as sock:
        sock.setblocking(True)
        sock.settimeout(2)
        sock.sendall(pack_frame(1, b'{"v":1,"type":"stop"}'))
        deadline = time.monotonic() + 2
        length, = struct.unpack(">I", _receive_exact(sock, 4, deadline))
        if not 1 <= length <= 16 * 1024 + 1:
            raise ValueError("Invalid iOS Stop acknowledgment length")
        body = _receive_exact(sock, length, deadline)
        validate_ios_control(body[0], body[1:], "stopped")
        return True


def validate_ios_control(kind, payload, expected):
    value = json.loads(payload.decode("utf-8"))
    if (kind != 1 or len(payload) > 16 * 1024 or not isinstance(value, dict) or set(value) != {"v", "type"}
            or type(value["v"]) is not int or value["v"] != 1 or value["type"] != expected):
        raise ValueError("Expected explicit iOS connection control")


def validate_ios_connect(kind, payload):
    """A paired TCP accept alone cannot request capture; require phone readiness."""
    validate_ios_control(kind, payload, "connect")


class IosRelay:
    def __init__(self, server, mux=None, on_status=None, *, mux_address=("127.0.0.1", 27015),
                 start_request=None, on_video_absent=None):
        if mux is None:
            from .usb import AppleMux
            mux = AppleMux(address=mux_address)
        self.server, self.mux = server, mux
        self.on_status = on_status or (lambda *args, **kwargs: None)
        self.start_request = start_request
        self.on_video_absent = on_video_absent
        self._thread = self._loop = self._task = None
        self._stop = threading.Event()

    @property
    def active(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self, device, *, on_video_absent=None, start_request=None):
        if self.active:
            return
        self._stop.clear()
        absent = on_video_absent or self.on_video_absent
        request = start_request if start_request is not None else self.start_request
        self._thread = threading.Thread(target=self._run, args=(device, absent, request), name="vrization-ios-usb", daemon=True)
        self._thread.start()

    def _run(self, device, on_video_absent=None, start_request=None):
        from .usb import safe_relay_error
        try:
            kwargs = {} if on_video_absent is None else {"on_video_absent": on_video_absent}
            if start_request is not None:
                kwargs["start_request"] = start_request
            asyncio.run(self._relay(device, **kwargs))
        except (ClientError, OSError, ValueError, asyncio.IncompleteReadError, asyncio.TimeoutError) as error:
            self.on_status("iOS USB: {detail}", detail=safe_relay_error(error))
        except asyncio.CancelledError:
            pass

    async def _relay(self, device, *, on_video_absent=None, start_request=None):
        from .usb import AppleEndpointUnavailable, MAX_FRAME, pack_frame, read_frame
        self._loop, self._task = asyncio.get_running_loop(), asyncio.current_task()
        absence_callback = on_video_absent or self.on_video_absent
        request_start = start_request if start_request is not None else self.start_request
        sock = writer = pending_start = peer_wait = None
        try:
            try:
                sock = self.mux.connect(device)
            except AppleEndpointUnavailable:
                if absence_callback is not None and not self._stop.is_set():
                    absence_callback()
                raise
            if self._stop.is_set():
                return
            reader, writer = await asyncio.open_connection(sock=sock)
            sock = None  # The StreamWriter now owns the socket.
            # An old listener may accept TCP but reject this second peer. Only a
            # current explicit phone attempt sends readiness before host hello.
            # Consume it here for running hosts too; it is not a host message.
            kind, payload = await asyncio.wait_for(read_frame(reader), 2)
            validate_ios_connect(kind, payload)
            if self._stop.is_set():
                return
            if not self.server.running and request_start is not None:
                # While the GUI accepts startup, phone Disconnect / background
                # must retire its queued identity. The phone sends no protocol
                # data until host hello; EOF or early bytes end this attempt.
                peer_wait = asyncio.create_task(reader.read(1))
                requested = request_start()
                pending_start = requested if isinstance(requested, Future) else None
                if requested is False:
                    raise ConnectionError("Computer connection request unavailable")
                deadline = time.monotonic() + 8
                while True:
                    if self._stop.is_set():
                        return
                    if peer_wait.done():
                        peer_wait.result()
                        raise ConnectionError("Phone connection attempt ended before startup")
                    acknowledged = pending_start is None
                    if pending_start is not None and pending_start.done():
                        try:
                            acknowledged = bool(pending_start.result())
                        except Exception:
                            acknowledged = False
                        if not acknowledged:
                            raise ConnectionError("Computer connection request cancelled")
                    if self.server.running and acknowledged:
                        break
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Computer streaming start timed out")
                    await asyncio.sleep(.05)
                peer_wait.cancel()
                await asyncio.gather(peer_wait, return_exceptions=True)
                peer_wait = None
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
            # Fail only this still-pending coordinator identity; GUI acceptance
            # must reject it before ANY awaited cleanup can yield to queued UI.
            if pending_start is not None and not pending_start.done():
                with suppress(InvalidStateError):
                    pending_start.set_result(False)
            if sock is not None:
                sock.close()
            if writer is not None:
                writer.close()
            try:
                if peer_wait is not None:
                    peer_wait.cancel()
                    await asyncio.gather(peer_wait, return_exceptions=True)
                if writer is not None:
                    with suppress(OSError, asyncio.TimeoutError):
                        await asyncio.wait_for(writer.wait_closed(), 2)
            finally:
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

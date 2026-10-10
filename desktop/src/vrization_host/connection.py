"""Reusable connection requests, independent of widgets and video transport.

A desktop adapter consumes requests on its own UI thread. The small USB-only
HTTP service carries explicit Connect actions; JPEG still travels directly
through the existing video server. No driver or shared ADB service is changed.
"""

import asyncio
from concurrent.futures import Future
import ipaddress
import threading

from aiohttp import web

ANDROID_CONTROL_PORT = 18764


class ConnectionCoordinator:
    """Coalesce concurrent Connect actions and invalidate pending work on Stop.

    ``emit`` queues a ``connect_request`` event in the embedding application.
    Call ``accept`` immediately before starting its video service, and then
    ``complete`` with the result. Neither this module nor a network callback
    accesses widgets, display configuration or input authorization.
    """

    def __init__(self, emit, is_running, is_stopping=None):
        self.emit, self.is_running = emit, is_running
        self.is_stopping = is_stopping or (lambda: False)
        self._lock = threading.RLock()
        self._pending = None
        self._closed = False

    def request(self):
        with self._lock:
            if self._closed or self.is_stopping() or self.is_running():
                result = Future()
                result.set_result(not self._closed and not self.is_stopping())
                return result
            if self._pending is not None and not self._pending.done():
                return self._pending
            result = self._pending = Future()
            try:
                self.emit({"event": "connect_request", "request": result})
            except Exception:
                self._pending = None
                result.set_result(False)
            return result

    def accept(self, request):
        with self._lock:
            return (not self._closed and not self.is_stopping()
                    and request is self._pending and not request.done())

    def complete(self, request, ready):
        with self._lock:
            if request is self._pending:
                self._pending = None
            if not request.done():
                request.set_result(bool(ready))

    def cancel(self, *, close=False):
        with self._lock:
            self._closed = self._closed or close
            request, self._pending = self._pending, None
            if request is not None and not request.done():
                request.set_result(False)


def trusted_usb_request(request, port, authorized):
    """Require native loopback HTTP and independently established USB trust."""
    try:
        local = ipaddress.ip_address(request.remote or "").is_loopback
    except ValueError:
        return False
    hosts = request.headers.getall("Host", [])
    allowed = {f"{name}:{port}" for name in ("127.0.0.1", "localhost", "[::1]")}
    if not local or len(hosts) != 1 or hosts[0].lower() not in allowed or "Origin" in request.headers:
        return False
    try:
        return bool(authorized())
    except Exception:
        return False


class UsbConnectService:
    """Always-available control listener for an explicitly pressed phone button.

    The listener is local only, has no video or pairing code, and is distinct
    from stopping the video service. Legacy clients retain port 18765 / 8765.
    """

    def __init__(self, coordinator, authorized, *, port=ANDROID_CONTROL_PORT, timeout=8):
        self.coordinator, self.authorized = coordinator, authorized
        self.port, self.timeout = port, timeout
        self._thread = None
        self._loop = None
        self._stop = None
        self._ready = threading.Event()
        self._error = None

    def make_app(self):
        app = web.Application(client_max_size=1024)
        app.router.add_post("/connect", self._connect)
        return app

    async def _connect(self, request):
        headers = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
        if not trusted_usb_request(request, self.port, self.authorized):
            return web.json_response({"error": "USB unauthorized"}, status=403, headers=headers)
        await request.read()  # Enforce the small body limit before queuing an action.
        pending = self.coordinator.request()
        try:
            # Shield a coalesced request from one HTTP client's cancellation.
            ready = await asyncio.wait_for(asyncio.shield(asyncio.wrap_future(pending)), self.timeout)
        except asyncio.TimeoutError:
            self.coordinator.complete(pending, False)
            ready = False
        ready = ready and trusted_usb_request(request, self.port, self.authorized)
        return web.json_response({"v": 1, "name": "VRization", "ready": ready},
                                 status=200 if ready else 503, headers=headers)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._ready.clear()
        self._error = None
        self._thread = threading.Thread(target=self._thread_main, name="vr-usb-connect", daemon=True)
        self._thread.start()
        if not self._ready.wait(3):
            raise TimeoutError("USB control service did not start")
        if self._error:
            raise OSError("USB control port is unavailable")

    def _thread_main(self):
        try:
            asyncio.run(self._run())
        except Exception as error:
            self._error = type(error).__name__
            self._ready.set()

    async def _run(self):
        self._loop, self._stop = asyncio.get_running_loop(), asyncio.Event()
        runner = web.AppRunner(self.make_app(), access_log=None, shutdown_timeout=0.2)
        try:
            await runner.setup()
            site = web.TCPSite(runner, "127.0.0.1", self.port)
            await site.start()
            if not self.port:
                self.port = site._server.sockets[0].getsockname()[1]
            self._ready.set()
            await self._stop.wait()
        finally:
            await runner.cleanup()

    def stop(self):
        self.coordinator.cancel(close=True)
        if self._loop and self._loop.is_running() and self._stop:
            try:
                self._loop.call_soon_threadsafe(self._stop.set)
            except RuntimeError:
                pass  # The loop already completed cleanup.
        if self._thread:
            self._thread.join(timeout=3)
            if self._thread.is_alive():
                raise TimeoutError("USB control service is still stopping")

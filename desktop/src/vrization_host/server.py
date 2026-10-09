"""An embeddable authenticated, single-headset streaming service."""

import asyncio
from contextlib import suppress
import hmac
import ipaddress
import json
import secrets
import threading
import time

from aiohttp import web, WSMsgType

from ._version import __version__
from .capture import CaptureConfig, CaptureWorker, LatestFrameBuffer, MssCaptureSource
from .input import PoseController, WindowsMouseSink
from .protocol import ProtocolError, Settings, TokenLimiter, parse_message


class HostServer:
    def __init__(self, capture_source=None, input_sink=None, settings: Settings | None = None,
                 capture_config: CaptureConfig | None = None, on_event=None,
                 host: str = "0.0.0.0", port: int = 8765, usb_authorized=None):
        self.capture_source = capture_source if capture_source is not None else MssCaptureSource()
        sink = input_sink if input_sink is not None else WindowsMouseSink()
        self.settings = settings or Settings()
        self._settings_revision = 0
        self.capture_config = capture_config or CaptureConfig()
        self.on_event = on_event
        self.host, self.port = host, port
        # Embedders must explicitly opt in. LAN clients can never obtain a code.
        self.usb_authorized = usb_authorized
        self.token = f"{secrets.randbelow(1_000_000):06d}"
        self.lock = threading.RLock()
        self.controller = PoseController(sink, self._input_state,
                                         getattr(sink, "external_foreground", None))
        self.controller.set_settings(self.settings)
        self._thread = None
        self._loop = None
        self._stop_signal = None
        self._started = threading.Event()
        self._start_error = None
        self._ws = None
        self._worker = None
        self._watchdog = None
        self._buffer = None
        self._broadcast_lock = None
        self._limiter = TokenLimiter()
        self.running = False

    def _emit(self, event: str, **data):
        if self.on_event:
            try:
                self.on_event({"event": event, **data})
            except Exception:
                pass  # A host application's observer cannot terminate the stream.

    def _input_state(self, armed: bool, reason: str):
        self._emit("input", armed=armed, reason=reason)

    def get_capture_config(self):
        with self.lock:
            return self.capture_config

    def set_capture_config(self, config: CaptureConfig):
        with self.lock:
            self.capture_config = config

    def get_settings_snapshot(self) -> tuple[Settings, int]:
        with self.lock:
            return self.settings, self._settings_revision

    def update_settings(self, patch: dict, *, client_seq: int | None = None, response_socket=None):
        owner = self._ws if response_socket is None else response_socket
        with self.lock:
            self.settings = self.settings.update(patch)
            self.controller.set_settings(self.settings)
            self._settings_revision += 1
            result = self.settings
            revision = self._settings_revision
        self._emit("settings", settings=result.to_dict(), revision=revision)
        if owner is not None and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._broadcast_settings(owner, client_seq), self._loop)
        return result

    async def _broadcast_settings(self, owner, client_seq: int | None = None):
        # Read the latest snapshot only after acquiring the send lock. Older
        # scheduled broadcasts can never overwrite a newer state on the phone.
        async with self._broadcast_lock:
            ws = self._ws
            if ws is not owner or ws.closed:
                return  # A queued acknowledgement belongs to its original session.
            settings, revision = self.get_settings_snapshot()
            message = {"v": 1, "type": "settings", "settings": settings.to_dict(), "revision": revision}
            if client_seq is not None:
                message["clientSeq"] = client_seq
            with suppress(ConnectionError, RuntimeError, asyncio.TimeoutError):
                await asyncio.wait_for(ws.send_json(message), 2)

    def arm(self) -> tuple[bool, str]:
        return self.controller.arm()

    def disarm(self, reason="emergency stop"):
        self.controller.disarm(reason)

    def recenter(self):
        self.controller.recenter()

    def make_app(self) -> web.Application:
        app = web.Application(client_max_size=16 * 1024)
        app.router.add_get("/health", self._health)
        app.router.add_get("/usb-bootstrap", self._usb_bootstrap)
        app.router.add_get("/ws", self._connect)
        app.on_startup.append(self._startup)
        app.on_shutdown.append(self._shutdown)
        app.on_cleanup.append(self._cleanup)
        return app

    async def _health(self, request):
        return web.json_response({"name": "VRization", "version": __version__, "protocol": 1,
                                  "connected": self._ws is not None})

    async def _usb_bootstrap(self, request):
        try:
            loopback = ipaddress.ip_address(request.remote or "").is_loopback
        except ValueError:
            loopback = False
        # Android's reverse tunnel preserves its phone-side Host port (18765).
        # Do not trust DNS-resolved names, forwarded headers, or browser origins.
        allowed_hosts = {f"{name}:{port}" for name in ("127.0.0.1", "localhost", "[::1]")
                         for port in (self.port, 18765)}
        host_headers = request.headers.getall("Host", [])
        native_host = (len(host_headers) == 1 and host_headers[0].lower() in allowed_hosts
                       and "Origin" not in request.headers)
        authorized = False
        if loopback and native_host and self.usb_authorized is not None:
            try:
                authorized = bool(self.usb_authorized())
            except Exception:
                pass
        headers = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
        if not authorized:
            return web.json_response({"error": "USB unauthorized"}, status=403, headers=headers)
        if not self.running:
            return web.json_response({"error": "Streaming not running"}, status=503, headers=headers)
        return web.json_response({"v": 1, "name": "VRization", "version": __version__,
                                  "port": self.port, "token": self.token}, headers=headers)

    def _capture_error(self, error):
        self.controller.disarm("capture unavailable")
        self._emit("error", message=error)

    async def _startup(self, app):
        self._loop = asyncio.get_running_loop()
        self._buffer = LatestFrameBuffer()
        self._broadcast_lock = asyncio.Lock()
        self._worker = CaptureWorker(self.capture_source, self.get_capture_config, self._loop,
                                     self._buffer, self._capture_error)
        self._worker.start()
        self._watchdog = asyncio.create_task(self._watch_input())

    async def _shutdown(self, app):
        self.controller.disarm("server stopping")
        if self._ws:
            await self._ws.close(code=1001, message=b"host stopping")

    async def _cleanup(self, app):
        if self._watchdog:
            self._watchdog.cancel()
            with suppress(asyncio.CancelledError):
                await self._watchdog
        if self._worker:
            self._worker.stop()
        self.controller.set_connected(False)

    async def _watch_input(self):
        while True:
            await asyncio.sleep(0.1)
            self.controller.tick()

    async def _connect(self, request):
        address = request.remote or "unknown"
        if not self._limiter.allowed(address):
            return web.Response(status=429, text="Too many pairing attempts. Wait one minute.",
                                headers={"Retry-After": "60"})
        supplied = request.query.get("token", "")
        if not hmac.compare_digest(supplied.encode("utf-8"), self.token.encode("ascii")):
            self._limiter.failed(address)
            return web.Response(status=401, text="Incorrect pairing code")
        if self._ws is not None:
            return web.Response(status=409, text="A headset is already connected")
        ws = web.WebSocketResponse(heartbeat=10, max_msg_size=16 * 1024,
                                   compress=False, writer_limit=64 * 1024)
        self._ws = ws  # Claim before the first await so a duplicate cannot steal ownership.
        sender = None
        try:
            await ws.prepare(request)
            self.controller.set_connected(True)
            self._emit("connection", connected=True, address=address)
            settings, revision = self.get_settings_snapshot()
            await ws.send_json({"v": 1, "type": "hello", "name": "VRization",
                                "version": __version__, "settings": settings.to_dict(), "revision": revision,
                                "stream": {"codec": "jpeg", "fps": self.capture_config.fps,
                                           "maxWidth": self.capture_config.width},
                                "mouseArmed": False})
            sender = asyncio.create_task(self._send_frames(ws))
            self._worker.active.set()
            errors, tokens, refill_at = 0, 180.0, time.monotonic()
            async for message in ws:
                if message.type == WSMsgType.TEXT:
                    now = time.monotonic()
                    tokens = min(180.0, tokens + (now - refill_at) * 120)
                    refill_at = now
                    if tokens < 1:
                        await ws.close(code=1008, message=b"message rate exceeded")
                        break
                    tokens -= 1
                    try:
                        msg = parse_message(message.data)
                        kind = msg["type"]
                        if kind == "settings":
                            self.update_settings(msg["settings"], client_seq=msg.get("clientSeq"), response_socket=ws)
                        elif kind == "pose":
                            self.controller.pose(msg["seq"], msg["yaw"], msg["pitch"])
                        elif kind == "recenter":
                            self.controller.recenter()
                        elif kind == "ping":
                            await ws.send_json({"v": 1, "type": "pong"})
                        # A client's optional hello is accepted without changing state.
                    except (ProtocolError, TypeError, ValueError) as exc:
                        errors += 1
                        await ws.send_json({"v": 1, "type": "error", "message": str(exc)[:200]})
                        if errors >= 5:
                            await ws.close(code=1008, message=b"invalid protocol messages")
                            break
                elif message.type == WSMsgType.BINARY:
                    await ws.close(code=1003, message=b"client binary messages unsupported")
                    break
                elif message.type == WSMsgType.ERROR:
                    break
        finally:
            if sender:
                sender.cancel()
                with suppress(asyncio.CancelledError, ConnectionError, RuntimeError):
                    await sender
            if self._ws is ws:
                self._ws = None
                self._worker.active.clear()
                self.controller.set_connected(False)
                self._emit("connection", connected=False, address=address)
        return ws

    async def _send_frames(self, ws):
        after = self._buffer.sequence
        count, sent_bytes, started = 0, 0, time.perf_counter()
        capture_total = queue_total = send_total = 0.0
        fresh_count = 0
        previous_frame = None
        try:
            while not ws.closed:
                after, frame = await self._buffer.next(after)
                send_started = time.perf_counter()
                await asyncio.wait_for(ws.send_bytes(frame.jpeg), timeout=2)
                sent_at = time.perf_counter()
                send_total += (sent_at - send_started) * 1000
                if frame is not previous_frame and frame.ready_at is not None and frame.capture_ms is not None:
                    # Same host QPC clock only. Static refresh packets must not
                    # inflate queue latency; these are not phone/video latency.
                    queue_total += max(0, (send_started - frame.ready_at) * 1000)
                    capture_total += frame.capture_ms
                    fresh_count += 1
                previous_frame = frame
                count += 1
                sent_bytes += len(frame.jpeg)
                elapsed = sent_at - started
                if elapsed >= 1:
                    self._emit("stats", fps=count / elapsed, mbps=sent_bytes * 8 / elapsed / 1_000_000,
                               width=frame.width, height=frame.height,
                               captureMs=capture_total / fresh_count if fresh_count else None,
                               queueMs=queue_total / fresh_count if fresh_count else None,
                               sendMs=send_total / count)
                    count, sent_bytes, started = 0, 0, sent_at
                    capture_total = queue_total = send_total = 0.0
                    fresh_count = 0
        except (asyncio.TimeoutError, ConnectionError, RuntimeError):
            self.controller.disarm("stream connection stalled")
            await ws.close(code=1001, message=b"stream stalled")

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self.token = f"{secrets.randbelow(1_000_000):06d}"
        self._limiter = TokenLimiter()
        self._started.clear()
        self._start_error = None
        self._thread = threading.Thread(target=self._thread_main, daemon=True, name="vr-network")
        self._thread.start()
        if not self._started.wait(8):
            raise TimeoutError("Host did not start within 8 seconds")
        if self._start_error:
            raise RuntimeError(self._start_error)

    def _thread_main(self):
        try:
            asyncio.run(self._run())
        except Exception as exc:
            self._start_error = str(exc)
            self._emit("error", message=str(exc))
            self._started.set()
        finally:
            self.running = False
            self._emit("server", running=False)

    async def _run(self):
        self._stop_signal = asyncio.Event()
        runner = web.AppRunner(self.make_app(), access_log=None)
        try:
            await runner.setup()
            await web.TCPSite(runner, self.host, self.port).start()
            self.running = True
            self._emit("server", running=True)
            self._started.set()
            await self._stop_signal.wait()
        finally:
            await runner.cleanup()

    def stop(self):
        self.controller.disarm("server stopped")
        if self._loop and self._loop.is_running() and self._stop_signal:
            self._loop.call_soon_threadsafe(self._stop_signal.set)
        if self._thread:
            self._thread.join(timeout=6)

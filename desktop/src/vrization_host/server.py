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
from .protocol import (ENHANCED_FIRST_PERSON_CAPABILITY, ProtocolError, Settings,
                       TokenLimiter, parse_message)


class HostServer:
    def __init__(self, capture_source=None, input_sink=None, settings: Settings | None = None,
                 capture_config: CaptureConfig | None = None, on_event=None,
                 host: str = "0.0.0.0", port: int = 8765, usb_authorized=None, *, auto_control: bool = False):
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
                                         getattr(sink, "external_foreground", None), auto_control=auto_control)
        self.controller.set_settings(self.settings)
        self._capture_failed = False
        self._thread = None
        self._loop = None
        self._stop_signal = None
        self._started = threading.Event()
        self._start_error = None
        self._ws = None
        self.session_generation = 0
        self._sender = None
        self._stopping = threading.Event()
        self._settings_schema2 = False
        self._enhanced_first_person = False
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

    def get_latest_frame(self):
        """Return an immutable frame for local previews, without new capture work.

        The network loop replaces the owned Frame reference atomically. A preview
        retains that reference only; it never accesses native/GPU resources.
        """
        buffer = self._buffer
        return buffer.frame if self.running and buffer is not None else None

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

    def _wire_settings(self, settings: Settings) -> dict:
        values = settings.to_dict()
        if not self._settings_schema2:
            values.pop("stabilization", None)
        if values["mode"] == "fps_enhanced" and not self._enhanced_first_person:
            values["mode"] = "fps"
        return values

    async def _broadcast_settings(self, owner, client_seq: int | None = None):
        # Read the latest snapshot only after acquiring the send lock. Older
        # scheduled broadcasts can never overwrite a newer state on the phone.
        async with self._broadcast_lock:
            ws = self._ws
            if ws is not owner or ws.closed:
                return  # A queued acknowledgement belongs to its original session.
            settings, revision = self.get_settings_snapshot()
            message = {"v": 1, "type": "settings", "settings": self._wire_settings(settings), "revision": revision,
                       "enhancedFirstPerson": self._enhanced_first_person}
            if client_seq is not None:
                message["clientSeq"] = client_seq
            with suppress(ConnectionError, RuntimeError, asyncio.TimeoutError):
                await asyncio.wait_for(ws.send_json(message), 2)

    def arm(self) -> tuple[bool, str]:
        with self.lock:
            if self._capture_failed or self._stopping.is_set():
                return False, "Restart streaming before resuming gyro control"
            return self.controller.arm()

    def set_auto_control(self, enabled: bool):
        self.controller.configure_auto_control(enabled)
        self._emit("input_policy")

    def resume_control(self) -> tuple[bool, str]:
        with self.lock:
            if self._capture_failed or self._stopping.is_set():
                return False, "Restart streaming before resuming gyro control"
            self.controller.resume_control()
        self._emit("input_policy")
        return True, "Gyro control ready; select First-person and connect your phone"

    def get_control_state(self) -> dict:
        with self.controller.lock:
            return {"enabled": self.controller.auto_control, "armed": self.controller.armed,
                    "paused": self.controller.suspended, "connected": self.controller.connected,
                    "mode": self.controller.settings.mode}

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
        ws = self._ws
        return web.json_response({"name": "VRization", "version": __version__, "protocol": 1,
                                  "connected": ws is not None and not ws.closed and not self._stopping.is_set(),
                                  "running": self.running, "stopping": self._stopping.is_set()})

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
        if not self.running or self._stopping.is_set():
            return web.json_response({"error": "Streaming not running"}, status=503, headers=headers)
        return web.json_response({"v": 1, "name": "VRization", "version": __version__,
                                  "port": self.port, "token": self.token}, headers=headers)

    def _capture_error(self, error):
        with self.lock:
            self._capture_failed = True
            self.controller.disarm("capture unavailable")
        self._emit("error", message=error)

    async def _startup(self, app):
        with self.lock:
            self._capture_failed = False
        self._loop = asyncio.get_running_loop()
        self._buffer = LatestFrameBuffer()
        self._broadcast_lock = asyncio.Lock()
        self._worker = CaptureWorker(self.capture_source, self.get_capture_config, self._loop,
                                     self._buffer, self._capture_error)
        self._worker.start()
        self._watchdog = asyncio.create_task(self._watch_input())

    async def _shutdown(self, app):
        self.controller.set_connected(False)
        if self._buffer:
            self._buffer.frame = None
        if self._worker:
            self._worker.active.clear()
        if self._sender:
            self._sender.cancel()
            with suppress(asyncio.CancelledError, ConnectionError, RuntimeError):
                await self._sender
        if self._ws:
            await self._ws.close(code=1001, message=b"host stopping", drain=False)

    async def _cleanup(self, app):
        if self._watchdog:
            self._watchdog.cancel()
            with suppress(asyncio.CancelledError):
                await self._watchdog
        if self._worker:
            # Keep the loop responsive during a slow native capture teardown.
            # Do not allow a new worker to reuse the source before it is closed.
            await asyncio.to_thread(self._worker.stop)
            while self._worker.thread.is_alive():
                await asyncio.sleep(0.05)
        self.controller.set_connected(False)
        if self._buffer:
            self._buffer.frame = None

    async def _watch_input(self):
        while True:
            await asyncio.sleep(0.1)
            self.controller.tick()

    async def _connect(self, request):
        if self._stopping.is_set():
            return web.Response(status=503, text="Streaming is stopping")
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
        ws = web.WebSocketResponse(heartbeat=10, timeout=1, max_msg_size=16 * 1024,
                                   compress=False, writer_limit=64 * 1024)
        self._ws = ws  # Claim before the first await so a duplicate cannot steal ownership.
        self.session_generation += 1
        session_generation = self.session_generation
        self._settings_schema2 = request.query.get("settingsSchema") == "2"
        self._enhanced_first_person = request.query.get("enhancedFirstPerson") == "1"
        sender = None
        try:
            await ws.prepare(request)
            with self.lock:
                stopping = self._stopping.is_set()
                if not stopping:
                    self.controller.set_connected(True)
            if stopping:
                await ws.close(code=1001, message=b"host stopping", drain=False)
                return ws
            self._emit("connection", connected=True, address=address, session=session_generation)
            settings, revision = self.get_settings_snapshot()
            await ws.send_json({"v": 1, "type": "hello", "name": "VRization",
                                "version": __version__, "settings": self._wire_settings(settings), "revision": revision,
                                "capabilities": ["stabilization", ENHANCED_FIRST_PERSON_CAPABILITY],
                                "enhancedFirstPerson": self._enhanced_first_person,
                                "stream": {"codec": "jpeg", "fps": self.capture_config.fps,
                                           "maxWidth": self.capture_config.width},
                                "mouseArmed": False})
            sender = asyncio.create_task(self._send_frames(ws))
            self._sender = sender
            self._worker.active.set()
            errors, tokens, refill_at = 0, 180.0, time.monotonic()
            async for message in ws:
                if self._stopping.is_set() or self._ws is not ws:
                    break
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
                            if msg["settings"].get("mode") == "fps_enhanced" and not self._enhanced_first_person:
                                raise ProtocolError("Enhanced first person requires capability negotiation")
                            self.update_settings(msg["settings"], client_seq=msg.get("clientSeq"), response_socket=ws)
                        elif kind == "pose":
                            self.controller.pose(msg["seq"], msg["yaw"], msg["pitch"])
                        elif kind == "recenter":
                            self.controller.recenter()
                        elif kind == "ping":
                            await ws.send_json({"v": 1, "type": "pong"})
                        elif kind == "hello":
                            if msg.get("editing") is True:
                                # A control pause only: false/exit can never authorize input.
                                self.controller.disarm("headset editor opened")
                            upgraded = False
                            if (ENHANCED_FIRST_PERSON_CAPABILITY in msg.get("capabilities", [])
                                    and not self._enhanced_first_person):
                                self._enhanced_first_person = True
                                upgraded = True
                            if type(msg.get("settingsSchema")) is int and msg["settingsSchema"] == 2 and not self._settings_schema2:
                                # USB relays start with the legacy settings shape. A
                                # validated client can opt in without another hello.
                                self._settings_schema2 = True
                                upgraded = True
                            if upgraded:
                                await self._broadcast_settings(ws)
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
            # Revoke ownership/input/status before any awaited sender teardown.
            # A blocked old task cannot keep the phone shown as connected or
            # later clear an independently established replacement session.
            if self._ws is ws:
                self._ws = None
                if self._sender is sender:
                    self._sender = None
                self._settings_schema2 = False
                self._enhanced_first_person = False
                self._worker.active.clear()
                self.controller.set_connected(False)
                self._emit("connection", connected=False, address=address, session=session_generation)
            if sender:
                sender.cancel()
                with suppress(asyncio.CancelledError, ConnectionError, RuntimeError):
                    await sender
        return ws

    async def _send_frames(self, ws):
        session_generation = self.session_generation
        after = self._buffer.sequence
        count, sent_bytes, started = 0, 0, time.perf_counter()
        capture_total = queue_total = send_total = 0.0
        fresh_count = 0
        previous_frame = None
        masked_notice_sent = False
        try:
            while not ws.closed and not self._stopping.is_set():
                after, frame = await self._buffer.next(after)
                if self._stopping.is_set() or self._ws is not ws:
                    break
                send_started = time.perf_counter()
                await asyncio.wait_for(ws.send_bytes(frame.jpeg), timeout=2)
                sent_at = time.perf_counter()
                if frame.protected_content_masked and not masked_notice_sent:
                    masked_notice_sent = True
                    self._emit("capture_masked", session=session_generation,
                               message="Windows has blacked out protected content; the remaining desktop continues streaming.")
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
                    self._emit("stats", session=session_generation, fps=count / elapsed, mbps=sent_bytes * 8 / elapsed / 1_000_000,
                               width=frame.width, height=frame.height,
                               captureMs=capture_total / fresh_count if fresh_count else None,
                               queueMs=queue_total / fresh_count if fresh_count else None,
                               sendMs=send_total / count)
                    count, sent_bytes, started = 0, 0, sent_at
                    capture_total = queue_total = send_total = 0.0
                    fresh_count = 0
        except (asyncio.TimeoutError, ConnectionError, RuntimeError):
            if self._ws is ws:
                self.controller.disarm("stream connection stalled")
            await ws.close(code=1001, message=b"stream stalled")

    def start(self):
        if self._thread and self._thread.is_alive():
            if self._stopping.is_set():
                raise RuntimeError("Streaming is still stopping; wait for cleanup to finish")
            return
        self._stopping.clear()
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

    def request_stop(self):
        """Immediately revoke streaming/input; completion remains asynchronous."""
        with self.lock:
            self._stopping.set()
            self.running = False
            self.controller.disarm("streaming stopped")
            self.controller.set_connected(False)
        if self._worker:
            self._worker.active.clear()
            self._worker.stop_event.set()
        if self._loop and self._loop.is_running() and self._stop_signal:
            def signal():
                if self._sender:
                    self._sender.cancel()
                self._stop_signal.set()
            with suppress(RuntimeError):  # The same loop may already be closing.
                self._loop.call_soon_threadsafe(signal)

    def stop(self, timeout: float = 6) -> bool:
        self.request_stop()
        if self._thread:
            self._thread.join(timeout=timeout)
            return not self._thread.is_alive()
        return True

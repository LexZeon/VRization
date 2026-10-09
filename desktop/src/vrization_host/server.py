"""An embeddable authenticated, single-headset streaming service."""

import asyncio
from contextlib import suppress
import hmac
import json
import secrets
import threading
import time

from aiohttp import web, WSMsgType

from .capture import CaptureConfig, CaptureWorker, LatestFrameBuffer, MssCaptureSource
from .input import PoseController, WindowsMouseSink
from .protocol import ProtocolError, Settings, TokenLimiter, parse_message


class HostServer:
    def __init__(self, capture_source=None, input_sink=None, settings: Settings | None = None,
                 capture_config: CaptureConfig | None = None, on_event=None,
                 host: str = "0.0.0.0", port: int = 8765):
        self.capture_source = capture_source if capture_source is not None else MssCaptureSource()
        sink = input_sink if input_sink is not None else WindowsMouseSink()
        self.settings = settings or Settings()
        self.capture_config = capture_config or CaptureConfig()
        self.on_event = on_event
        self.host, self.port = host, port
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

    def update_settings(self, patch: dict):
        with self.lock:
            self.settings = self.settings.update(patch)
            self.controller.set_settings(self.settings)
            result = self.settings
        self._emit("settings", settings=result.to_dict())
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._broadcast_settings(), self._loop)
        return result

    async def _broadcast_settings(self):
        ws = self._ws
        if ws and not ws.closed:
            with suppress(ConnectionError, RuntimeError, asyncio.TimeoutError):
                await asyncio.wait_for(ws.send_json({"v": 1, "type": "settings",
                                                     "settings": self.settings.to_dict()}), 2)

    def arm(self) -> tuple[bool, str]:
        return self.controller.arm()

    def disarm(self, reason="emergency stop"):
        self.controller.disarm(reason)

    def recenter(self):
        self.controller.recenter()

    def make_app(self) -> web.Application:
        app = web.Application(client_max_size=16 * 1024)
        app.router.add_get("/health", self._health)
        app.router.add_get("/ws", self._connect)
        app.on_startup.append(self._startup)
        app.on_shutdown.append(self._shutdown)
        app.on_cleanup.append(self._cleanup)
        return app

    async def _health(self, request):
        return web.json_response({"name": "VRization", "version": "0.1.0", "protocol": 1,
                                  "connected": self._ws is not None})

    async def _startup(self, app):
        self._loop = asyncio.get_running_loop()
        self._buffer = LatestFrameBuffer()
        self._worker = CaptureWorker(self.capture_source, self.get_capture_config, self._loop,
                                     self._buffer, lambda error: self._emit("error", message=error))
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
            await ws.send_json({"v": 1, "type": "hello", "name": "VRization",
                                "version": "0.1.0", "settings": self.settings.to_dict(),
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
                            with self.lock:
                                self.settings = self.settings.update(msg["settings"])
                                self.controller.set_settings(self.settings)
                            self._emit("settings", settings=self.settings.to_dict())
                            await self._broadcast_settings()
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
        count, sent_bytes, started = 0, 0, time.monotonic()
        try:
            while not ws.closed:
                after, frame = await self._buffer.next(after)
                await asyncio.wait_for(ws.send_bytes(frame.jpeg), timeout=2)
                count += 1
                sent_bytes += len(frame.jpeg)
                elapsed = time.monotonic() - started
                if elapsed >= 1:
                    self._emit("stats", fps=count / elapsed, mbps=sent_bytes * 8 / elapsed / 1_000_000,
                               width=frame.width, height=frame.height)
                    count, sent_bytes, started = 0, 0, time.monotonic()
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

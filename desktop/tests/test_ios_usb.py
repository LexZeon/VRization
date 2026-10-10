"""Paired control and relay lifetime tests; no Apple service, capture or OS input."""
import asyncio
from concurrent.futures import Future
import json
import socket
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from aiohttp.test_utils import TestServer

from vrization_host.capture import CaptureConfig
from vrization_host.ios_usb import IOS_CONTROL_PORT, IosRelay, request_ios_connect, request_ios_stop, validate_ios_connect
from vrization_host.server import HostServer
from vrization_host.usb import AppleDevice, pack_frame, read_frame
from test_native_client_wire import SyntheticJpegSource, RecordingInputSink


class OwnedSocket:
    def __init__(self):
        self.closed = False
        self.sent = []
    def setblocking(self, blocking):
        self.blocking = blocking
    def settimeout(self, timeout):
        self.timeout = timeout
    def sendall(self, payload):
        self.sent.append(payload)
    def close(self):
        self.closed = True
    def __enter__(self):
        return self
    def __exit__(self, *_):
        self.close()


class Writer:
    def __init__(self, sock):
        self.sock = sock
    def close(self):
        self.sock.close()
    async def wait_closed(self):
        pass


def ready_stream(sock, payload=b'{"v":1,"type":"connect"}'):
    reader = asyncio.StreamReader()
    if payload is not None:
        reader.feed_data(pack_frame(1, payload))
    else:
        reader.feed_eof()
    return reader, Writer(sock)


class IosControlTests(unittest.TestCase):
    def test_started_relay_keeps_its_captured_request_when_adapter_changes(self):
        entered, release, calls = threading.Event(), threading.Event(), []
        relay = IosRelay(SimpleNamespace(running=False), start_request=lambda: calls.append("original"))
        async def delayed(device, *, start_request):
            entered.set()
            while not release.is_set():
                await asyncio.sleep(.001)
            start_request()
        with patch.object(relay, "_relay", delayed):
            try:
                relay.start(AppleDevice(1, "FIXTURE"))
                self.assertTrue(entered.wait(1))
                relay.start_request = lambda: calls.append("replacement")
                release.set()
                relay._thread.join(timeout=1)
                self.assertFalse(relay.active)
            finally:
                release.set(); relay.stop()
        self.assertEqual(calls, ["original"])

    def test_explicit_pc_request_sends_one_bounded_control_then_closes(self):
        sock, calls = OwnedSocket(), []
        device = AppleDevice(1, "FIXTURE")
        def connect(selected, port):
            calls.append((selected, port))
            return sock
        request_ios_connect(SimpleNamespace(connect=connect), device)
        self.assertEqual(calls, [(device, IOS_CONTROL_PORT)])
        self.assertEqual(sock.sent, [pack_frame(1, b'{"v":1,"type":"connect"}')])
        self.assertTrue(sock.closed)
        self.assertEqual(sock.timeout, 2)

    def test_video_readiness_rejects_invalid_or_unrelated_controls(self):
        validate_ios_connect(1, b'{"v":1,"type":"connect"}')
        for payload in (b'{}', b'{"v":true,"type":"connect"}', b'{"v":2,"type":"connect"}',
                        b'{"v":1,"type":"pose"}', b'{"v":1,"type":"connect","arm":true}'):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                validate_ios_connect(1, payload)
        with self.assertRaises(ValueError):
            validate_ios_connect(2, b'{"v":1,"type":"connect"}')

    def test_stop_waits_for_exact_framed_ack_and_closes_control_peer(self):
        sock, calls = OwnedSocket(), []
        response = bytearray(pack_frame(1, b'{"v":1,"type":"stopped"}'))
        def receive(size):
            count = min(size, 2); result = bytes(response[:count]); del response[:count]; return result
        sock.recv = receive
        def connect(device, port):
            calls.append(port); return sock
        self.assertTrue(request_ios_stop(SimpleNamespace(connect=connect), AppleDevice(1, "FIXTURE")))
        self.assertEqual(calls, [18767])
        self.assertEqual(sock.sent, [pack_frame(1, b'{"v":1,"type":"stop"}')])
        self.assertTrue(sock.closed)

    def test_missing_invalid_or_unrelated_stop_ack_never_counts_as_success(self):
        for payload in (b"", pack_frame(1, b'{"v":1,"type":"connect"}'),
                        pack_frame(1, b'{"v":true,"type":"stopped"}'),
                        pack_frame(2, b'{"v":1,"type":"stopped"}'), b"\xff\xff\xff\xff"):
            with self.subTest(payload=payload):
                sock, response = OwnedSocket(), bytearray(payload)
                def receive(size):
                    result = bytes(response[:size]); del response[:size]; return result
                sock.recv = receive
                with self.assertRaises((OSError, ValueError)):
                    request_ios_stop(SimpleNamespace(connect=lambda device, port: sock), AppleDevice(1, "FIXTURE"))
                self.assertTrue(sock.closed)

    def test_failed_paired_control_is_not_retried_and_send_failure_closes(self):
        for phase in ("pair", "send"):
            with self.subTest(phase=phase):
                sock, calls = OwnedSocket(), []
                def connect(selected, port):
                    calls.append(port)
                    if phase == "pair":
                        raise PermissionError("fixture trust missing")
                    def fail(payload):
                        raise OSError("fixture peer closed")
                    sock.sendall = fail
                    return sock
                with self.assertRaises(OSError):
                    request_ios_connect(SimpleNamespace(connect=connect), AppleDevice(1, "FIXTURE"))
                self.assertEqual(calls, [18767])
                self.assertEqual(sock.closed, phase == "send")


class IosRelayTests(unittest.IsolatedAsyncioTestCase):
    async def test_attempt_specific_request_rejects_stale_readiness_before_constructor_fallback(self):
        sock, calls = OwnedSocket(), []
        relay = IosRelay(SimpleNamespace(running=False), SimpleNamespace(connect=lambda _: sock),
                         start_request=lambda: calls.append("wrong identity"))
        with patch("vrization_host.ios_usb.asyncio.open_connection", new_callable=AsyncMock,
                   return_value=ready_stream(sock)), patch("vrization_host.ios_usb.ClientSession") as session:
            with self.assertRaises(ConnectionError):
                await relay._relay(AppleDevice(1, "FIXTURE"), start_request=lambda: False)
            session.assert_not_called()
        self.assertEqual(calls, []); self.assertTrue(sock.closed)

    async def test_only_explicit_paired_endpoint_absence_reports_listener_gone(self):
        from vrization_host.usb import AppleEndpointUnavailable
        for error in (AppleEndpointUnavailable("fixture endpoint missing"), PermissionError("fixture untrusted")):
            with self.subTest(error=type(error).__name__):
                calls = []
                def connect(_):
                    raise error
                relay = IosRelay(SimpleNamespace(running=False), SimpleNamespace(connect=connect), on_video_absent=lambda: calls.append(True))
                with self.assertRaises(OSError):
                    await relay._relay(AppleDevice(1, "FIXTURE"))
                self.assertEqual(calls, [True] if isinstance(error, AppleEndpointUnavailable) else [])
    async def test_pairing_failure_cannot_request_host_start(self):
        calls = []
        def connect(_):
            raise PermissionError("fixture pairing unavailable")
        relay = IosRelay(SimpleNamespace(running=False), SimpleNamespace(connect=connect),
                         start_request=lambda: calls.append("start"))
        with self.assertRaises(OSError):
            await relay._relay(AppleDevice(1, "FIXTURE"))
        self.assertEqual(calls, [])

    async def test_stop_after_ready_validation_cannot_queue_new_start(self):
        sock, calls = OwnedSocket(), []
        relay = IosRelay(SimpleNamespace(running=False), SimpleNamespace(connect=lambda _: sock),
                         start_request=lambda: calls.append("start"))
        async def ready_then_stopped(_):
            relay._stop.set()
            return 1, b'{"v":1,"type":"connect"}'
        with patch("vrization_host.ios_usb.asyncio.open_connection", new_callable=AsyncMock,
                   return_value=ready_stream(sock)), patch("vrization_host.usb.read_frame", side_effect=ready_then_stopped), \
             patch("vrization_host.ios_usb.ClientSession") as session:
            await relay._relay(AppleDevice(1, "FIXTURE"))
            session.assert_not_called()
        self.assertEqual(calls, []); self.assertTrue(sock.closed)

    async def test_cancel_while_waiting_for_gui_closes_owned_peer_without_websocket(self):
        sock, entered, calls = OwnedSocket(), asyncio.Event(), []
        def request():
            calls.append("start"); entered.set(); return True
        relay = IosRelay(SimpleNamespace(running=False), SimpleNamespace(connect=lambda _: sock),
                         start_request=request)
        with patch("vrization_host.ios_usb.asyncio.open_connection", new_callable=AsyncMock, return_value=ready_stream(sock)) as open_stream:
            task = asyncio.create_task(relay._relay(AppleDevice(1, "FIXTURE")))
            await asyncio.wait_for(entered.wait(), 1)
            relay.request_stop()
            with self.assertRaises(asyncio.CancelledError):
                await task
            open_stream.assert_awaited_once()
        self.assertEqual(calls, ["start"])
        self.assertTrue(sock.closed)

    async def test_declined_start_closes_peer_and_never_opens_websocket(self):
        sock = OwnedSocket()
        relay = IosRelay(SimpleNamespace(running=False), SimpleNamespace(connect=lambda _: sock),
                         start_request=lambda: False)
        with patch("vrization_host.ios_usb.asyncio.open_connection", new_callable=AsyncMock, return_value=ready_stream(sock)) as open_stream:
            with self.assertRaises(ConnectionError):
                await relay._relay(AppleDevice(1, "FIXTURE"))
            open_stream.assert_awaited_once()
        self.assertTrue(sock.closed)

    async def test_occupied_old_listener_tcp_accept_without_readiness_cannot_wake(self):
        sock, calls = OwnedSocket(), []
        relay = IosRelay(SimpleNamespace(running=False), SimpleNamespace(connect=lambda _: sock),
                         start_request=lambda: calls.append("start"))
        # An occupied old native listener refuses the new peer after TCP accept.
        with patch("vrization_host.ios_usb.asyncio.open_connection", new_callable=AsyncMock,
                   return_value=ready_stream(sock, None)):
            with self.assertRaises(asyncio.IncompleteReadError):
                await relay._relay(AppleDevice(1, "FIXTURE"))
        self.assertEqual(calls, []); self.assertTrue(sock.closed)

    async def test_failed_request_identity_cannot_attach_to_later_running_host(self):
        sock, entered, pending = OwnedSocket(), asyncio.Event(), Future()
        host = SimpleNamespace(running=False)
        def request():
            entered.set(); return pending
        relay = IosRelay(host, SimpleNamespace(connect=lambda _: sock), start_request=request)
        with patch("vrization_host.ios_usb.asyncio.open_connection", new_callable=AsyncMock,
                   return_value=ready_stream(sock)), patch("vrization_host.ios_usb.ClientSession") as session:
            task = asyncio.create_task(relay._relay(AppleDevice(1, "FIXTURE")))
            await asyncio.wait_for(entered.wait(), 1)
            pending.set_result(False); host.running = True
            with self.assertRaises(ConnectionError):
                await task
            session.assert_not_called()
        self.assertTrue(sock.closed)

    async def test_stopping_pending_peer_invalidates_queued_start_identity(self):
        sock, entered, pending = OwnedSocket(), asyncio.Event(), Future()
        def request():
            entered.set(); return pending
        relay = IosRelay(SimpleNamespace(running=False), SimpleNamespace(connect=lambda _: sock), start_request=request)
        with patch("vrization_host.ios_usb.asyncio.open_connection", new_callable=AsyncMock,
                   return_value=ready_stream(sock)):
            task = asyncio.create_task(relay._relay(AppleDevice(1, "FIXTURE")))
            await asyncio.wait_for(entered.wait(), 1); relay.request_stop()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertTrue(pending.done()); self.assertFalse(pending.result()); self.assertTrue(sock.closed)

    async def test_request_identity_fails_before_async_writer_cleanup_yields(self):
        sock, entered, pending = OwnedSocket(), asyncio.Event(), Future()
        reader, writer = ready_stream(sock)
        checks = []
        async def delayed_close():
            checks.append((pending.done(), pending.result() if pending.done() else None, sock.closed))
            await asyncio.sleep(0)
        writer.wait_closed = delayed_close
        def request():
            entered.set(); return pending
        relay = IosRelay(SimpleNamespace(running=False), SimpleNamespace(connect=lambda _: sock), start_request=request)
        with patch("vrization_host.ios_usb.asyncio.open_connection", new_callable=AsyncMock, return_value=(reader, writer)):
            task = asyncio.create_task(relay._relay(AppleDevice(1, "FIXTURE")))
            await asyncio.wait_for(entered.wait(), 1); reader.feed_eof()
            with self.assertRaises(ConnectionError):
                await task
        self.assertEqual(checks, [(True, False, True)])

    async def test_phone_eof_before_gui_accept_retires_start_identity(self):
        sock, entered, pending = OwnedSocket(), asyncio.Event(), Future()
        reader, writer = ready_stream(sock)
        def request():
            entered.set(); return pending
        relay = IosRelay(SimpleNamespace(running=False), SimpleNamespace(connect=lambda _: sock), start_request=request)
        with patch("vrization_host.ios_usb.asyncio.open_connection", new_callable=AsyncMock,
                   return_value=(reader, writer)), patch("vrization_host.ios_usb.ClientSession") as session:
            task = asyncio.create_task(relay._relay(AppleDevice(1, "FIXTURE")))
            await asyncio.wait_for(entered.wait(), 1); reader.feed_eof()
            with self.assertRaises(ConnectionError):
                await task
            session.assert_not_called()
        self.assertTrue(pending.done()); self.assertFalse(pending.result()); self.assertTrue(sock.closed)

    async def test_phone_video_accept_requests_start_before_authenticated_stream(self):
        host = HostServer(capture_source=SyntheticJpegSource(), input_sink=RecordingInputSink(),
                          capture_config=CaptureConfig(fps=5))
        server = TestServer(host.make_app())
        await server.start_server()
        host.port = server.port
        paired, requested, accepted = [], [], asyncio.Future()
        async def phone(reader, writer):
            writer.write(pack_frame(1, b'{"v":1,"type":"connect"}')); await writer.drain()
            accepted.set_result((reader, writer))
        phone_server = await asyncio.start_server(phone, "127.0.0.1", 0)
        port = phone_server.sockets[0].getsockname()[1]
        def connect(device):
            result = socket.create_connection(("127.0.0.1", port), timeout=2)
            result.setblocking(False); paired.append(device); return result
        def request():
            self.assertEqual(len(paired), 1)
            requested.append(True); host.running = True; return True
        relay = IosRelay(host, SimpleNamespace(connect=connect), start_request=request)
        task = asyncio.create_task(relay._relay(AppleDevice(1, "FIXTURE")))
        writer = None
        try:
            reader, writer = await asyncio.wait_for(accepted, 2)
            kind, payload = await asyncio.wait_for(read_frame(reader), 3)
            self.assertEqual((kind, json.loads(payload)["type"]), (1, "hello"))
            self.assertEqual(requested, [True])
            self.assertTrue(host.controller.connected)
            self.assertFalse(host.controller.armed)
            writer.close(); await writer.wait_closed(); writer = None
            # A real USB EOF closes the authenticated WebSocket and host ownership.
            with self.assertRaises(asyncio.IncompleteReadError):
                await asyncio.wait_for(task, 3)
            for _ in range(40):
                if not host.controller.connected:
                    break
                await asyncio.sleep(.025)
            self.assertFalse(host.controller.connected)
            self.assertEqual(host.controller.sink.moves, [])
        finally:
            task.cancel(); await asyncio.gather(task, return_exceptions=True)
            if writer is not None:
                writer.close(); await writer.wait_closed()
            phone_server.close(); await phone_server.wait_closed(); await server.close()

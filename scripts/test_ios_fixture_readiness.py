"""Fixture readiness failures must end before native UI tests can run."""
import asyncio
from io import BytesIO
from http.server import BaseHTTPRequestHandler
import json
import os
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.response import addinfourl

import build_ios
from ios_usb_fixture import LANHandshakeHold, LoopbackObservationServer


class LANHandshakeHoldTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_hold_does_not_run_upgrade_until_explicit_release(self):
        gate = LANHandshakeHold()
        gate.held.set()
        calls = []
        async def handler(request):
            calls.append(request.path)
            return "upgraded"
        pending = asyncio.create_task(gate.handle(SimpleNamespace(path="/ws"), handler))
        await asyncio.sleep(.04)
        self.assertEqual(gate.pending, 1)
        self.assertEqual(calls, [])
        gate.held.clear()
        self.assertEqual(await asyncio.wait_for(pending, .2), "upgraded")
        self.assertEqual(gate.pending, 0)
        self.assertEqual(calls, ["/ws"])

    async def test_cancellation_releases_count_and_cannot_run_stale_upgrade(self):
        gate = LANHandshakeHold()
        gate.held.set()
        calls = []
        async def handler(request):
            calls.append(request.path)
            return "upgraded"
        pending = asyncio.create_task(gate.handle(SimpleNamespace(path="/ws"), handler))
        await asyncio.sleep(.04)
        pending.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await pending
        gate.held.clear()
        self.assertEqual(gate.pending, 0)
        self.assertEqual(calls, [])
        self.assertEqual(await gate.handle(SimpleNamespace(path="/ws"), handler), "upgraded")
        self.assertEqual(calls, ["/ws"])

    async def test_health_is_available_while_upgrade_is_held(self):
        gate = LANHandshakeHold()
        gate.held.set()
        async def handler(request):
            return request.path
        self.assertEqual(await asyncio.wait_for(gate.handle(SimpleNamespace(path="/health"), handler), .2), "/health")
        self.assertEqual(gate.pending, 0)


class FixtureReadinessTests(unittest.TestCase):
    def test_real_loopback_health_and_snapshot_complete_readiness_without_dns(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass
            def do_GET(self):
                value = {"name": "VRization", "protocol": 1, "running": True} if self.path == "/health" \
                    else {"fixtureReady": True}
                body = json.dumps(value).encode()
                self.send_response(200); self.send_header("Content-Length", str(len(body)))
                self.end_headers(); self.wfile.write(body)
        with patch("socket.getfqdn", side_effect=AssertionError("unexpected reverse DNS")):
            server = LoopbackObservationServer(("127.0.0.1", 0), Handler)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            opening = build_ios._loopback_opener.open
            def local_response(url, timeout):
                path = url.rsplit("/", 1)[1]
                return opening(f"http://127.0.0.1:{server.server_port}/{path}", timeout=timeout)
            try:
                self.wait(local_response)
            finally:
                server.shutdown(); server.server_close(); worker.join(timeout=1)
        self.assertFalse(worker.is_alive())

    def test_local_observer_starts_even_when_system_reverse_dns_is_unavailable(self):
        with patch("socket.getfqdn", side_effect=AssertionError("unexpected reverse DNS")), \
             patch("socket.gethostbyaddr", side_effect=AssertionError("unexpected DNS resolver")):
            server = LoopbackObservationServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
        try:
            self.assertEqual(server.server_address[0], "127.0.0.1")
            self.assertGreater(server.server_port, 0)
            self.assertEqual(server.server_name, "localhost")
        finally:
            server.server_close()

    def test_observation_fixture_rejects_broad_network_binding(self):
        with self.assertRaises(ValueError):
            LoopbackObservationServer(("0.0.0.0", 0), BaseHTTPRequestHandler)

    def setUp(self):
        self.now = 0
        self.fixture = SimpleNamespace(poll=lambda: None)
        self.calls = []

    def sleep(self, delay):
        self.now += delay

    def response(self, url, timeout):
        self.calls.append((url, timeout))
        value = {"name": "VRization", "protocol": 1, "running": True} if url.endswith("/health") \
            else {"fixtureReady": True}
        return BytesIO(json.dumps(value).encode())

    def wait(self, opener, timeout=2):
        with patch.object(build_ios.time, "monotonic", side_effect=lambda: self.now), \
             patch.object(build_ios.time, "sleep", side_effect=self.sleep), \
             patch.object(build_ios._loopback_opener, "open", side_effect=opener):
            build_ios.wait_for_fixture_ready(self.fixture, timeout=timeout)

    def test_loopback_transport_never_discovers_or_uses_system_environment_proxy(self):
        requests = []
        def local_http(handler, request):
            requests.append((request.host, request.has_proxy()))
            response = addinfourl(BytesIO(b"local fixture"), {}, request.full_url, 200)
            response.msg = "OK"
            return response
        with patch.dict(os.environ, {"http_proxy": "http://proxy.invalid:3128", "no_proxy": ""}), \
             patch("urllib.request.getproxies", side_effect=AssertionError("system proxy discovery")), \
             patch("urllib.request.HTTPHandler.http_open", new=local_http):
            with build_ios.make_loopback_opener().open("http://127.0.0.1:18765/health", timeout=1) as response:
                self.assertEqual(response.read(), b"local fixture")
        self.assertEqual(requests, [("127.0.0.1:18765", False)])

    def test_ready_requires_both_live_host_and_completed_observation(self):
        self.wait(self.response)
        self.assertEqual([url.rsplit("/", 1)[1] for url, _ in self.calls], ["health", "snapshot"])
        self.assertTrue(all(0 < timeout <= 1 for _, timeout in self.calls))
        self.assertEqual(self.now, 0)

    def test_health_alone_does_not_accept_incomplete_usb_startup(self):
        snapshots = iter([False, True])
        def opening(url, timeout):
            if url.endswith("/snapshot"):
                return BytesIO(json.dumps({"fixtureReady": next(snapshots)}).encode())
            return self.response(url, timeout)
        self.wait(opening)
        self.assertEqual(self.now, .5)

    def test_connection_failure_is_bounded_and_never_runs_native_tests(self):
        def opening(url, timeout):
            self.calls.append((url, timeout))
            raise OSError("fixture not listening")
        with self.assertRaisesRegex(RuntimeError, "within 2 seconds; see fixture.log"):
            self.wait(opening)
        self.assertEqual(self.now, 2)
        self.assertEqual(len(self.calls), 4)

    def test_early_child_exit_fails_immediately_without_waiting_or_http(self):
        self.fixture.poll = lambda: 1
        with self.assertRaisesRegex(RuntimeError, "exit 1"):
            self.wait(self.response)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.now, 0)

    def test_unrelated_or_malformed_http_service_does_not_count_as_fixture(self):
        for content in (b"not json", b"[]", b'{"running":true}', b'{"name":"VRization","running":true,"protocol":true}'):
            with self.subTest(content=content):
                self.now = 0
                with self.assertRaises(RuntimeError):
                    self.wait(lambda url, timeout: BytesIO(content))
                self.assertEqual(self.now, 2)


if __name__ == "__main__":
    unittest.main()

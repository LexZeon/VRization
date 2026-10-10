"""Fixture readiness failures must end before native UI tests can run."""
from io import BytesIO
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.response import addinfourl

import build_ios


class FixtureReadinessTests(unittest.TestCase):
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

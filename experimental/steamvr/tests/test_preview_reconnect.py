"""Real loopback reconnect of a failed source; no USB/runtime/device/input."""
import asyncio
import threading
import unittest

from aiohttp import ClientSession
from aiohttp.test_utils import TestServer
from vrization_host.capture import CaptureConfig
from vrization_steamvr.host import PreviewHost
from preview_fixtures import RecordingPoseSink, SyntheticStereoSource, next_binary, next_json, negotiate


class PreviewReconnectTests(unittest.IsolatedAsyncioTestCase):
    async def test_new_confirmed_phone_rebuilds_failed_capture_without_resuming_tracking(self):
        await self.check_reconnect(dormant=False)

    async def test_new_confirmed_phone_rebuilds_dormant_capture_before_failure_is_observed(self):
        await self.check_reconnect(dormant=True)

    async def check_reconnect(self, *, dormant):
        entered, release = threading.Event(), threading.Event()
        class Source(SyntheticStereoSource):
            failed = False
            def read(source, config):
                if source.failed:
                    if dormant:
                        entered.set()
                        if not release.wait(3):
                            raise RuntimeError("Fixture release missing")
                        return super().read(config)
                    raise OSError("Selected HMD disconnected; mirror exited")
                return super().read(config)
            def close(source):
                super().close()
                source.failed = False

        source, sink = Source(), RecordingPoseSink()
        host = PreviewHost(route="steamvr-phone", capture_source=source, pose_sink=sink,
                           capture_config=CaptureConfig(fps=60))
        server = TestServer(host.make_app())
        await server.start_server()
        host.running, host.port = True, server.port
        async def connect(client):
            ws = await client.ws_connect(server.make_url(f"/ws?token={host.token}"))
            await next_json(ws,"hello")
            return ws
        try:
            async with ClientSession() as client:
                first = await connect(client)
                await negotiate(first)
                await next_binary(first)
                source.failed = True
                if dormant:
                    self.assertTrue(await asyncio.to_thread(entered.wait,3))
                    self.assertFalse(host._capture_failed)
                    host.disarm("F8 emergency stop")
                else:
                    async with asyncio.timeout(3):
                        while not host._capture_failed:
                            await asyncio.sleep(.005)
                self.assertTrue(host.hmd.paused)
                await first.close()
                async with asyncio.timeout(3):
                    while host._ws is not None:
                        await asyncio.sleep(.005)
                fresh = await connect(client)
                self.assertEqual(source.closes, 0, "Raw connection alone cannot rebuild capture")
                self.assertEqual(host._capture_failed,not dormant)
                await negotiate(fresh)
                if dormant:
                    self.assertTrue(host._worker._source_reset.is_set(), "Recovery must not depend on observed failure")
                    release.set()
                self.assertEqual(await next_binary(fresh), source.jpeg)
                self.assertEqual(source.closes, 1)
                self.assertFalse(host._capture_failed)
                self.assertTrue(host.hmd.paused, "Connection recovery must keep the input pause")
                self.assertIsNone(host.hmd.output)
                self.assertFalse(any(q is not None for q, *_ in sink.snapshot()))
                await negotiate(fresh)
                await next_binary(fresh)
                self.assertEqual(source.closes, 1, "Repeated hello is not repeated recovery")
        finally:
            release.set()
            await server.close()


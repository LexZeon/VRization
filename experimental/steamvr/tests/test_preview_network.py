"""Real loopback HTTP/WebSocket preview tests with synthetic JPEG and recorded poses.

No desktop capture, mouse injection, native memory, USB or SteamVR hardware.
The held negotiation boundary is observed for >2 seconds without short sleeps.
"""
import asyncio
from io import BytesIO
import json
import math
import unittest
from unittest.mock import Mock

from aiohttp import ClientSession, WSMsgType
from aiohttp.test_utils import TestServer
from PIL import Image
from vrization_host.capture import CaptureConfig
from vrization_host.protocol import Settings
from vrization_steamvr.host import PreviewHost
from preview_fixtures import (CAPS, RecordingMouse, RecordingPoseSink, SyntheticStereoSource,
                              barrier, free_port, negotiate, next_binary, next_json, packet)


class PreviewNetworkTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.source= SyntheticStereoSource()
        self.sink=RecordingPoseSink()
        self.host=PreviewHost(route="steamvr-phone",capture_source=self.source,pose_sink=self.sink,
                              capture_config=CaptureConfig(fps=30),host="127.0.0.1")
        self.server=TestServer(self.host.make_app(),host="127.0.0.1")
        await self.server.start_server()
        self.host.port,self.host.running=self.server.port,True
        self.client=ClientSession()

    async def asyncTearDown(self):
        await self.client.close()
        await self.server.close()

    async def connect(self):
        ws=await self.client.ws_connect(self.server.make_url(
            f"/ws?token={self.host.token}&settingsSchema=2&enhancedFirstPerson=1&streamSession=1"))
        hello=await next_json(ws,"hello")
        self.assertFalse(hello["streamSession"]["accepted"])
        self.assertEqual(hello["streamSession"]["streamLayout"],"sbs")
        self.assertEqual(hello["streamSession"]["inputTarget"],"virtual-hmd")
        return ws,hello["streamSession"]["epoch"]

    async def test_successful_json_confirmation_is_sent_before_any_sbs_binary(self):
        ws,_=await self.connect()
        entered,release=asyncio.Event(),asyncio.Event()
        actual=self.host._broadcast_settings
        async def held(owner,client_seq=None):
            if self.host.stream_session.accepted:
                entered.set()
                await release.wait()
            return await actual(owner,client_seq)
        self.host._broadcast_settings=held
        pending=None
        try:
            await ws.send_json({"v":1,"type":"hello","settingsSchema":2,"capabilities":CAPS})
            await asyncio.wait_for(entered.wait(),4)
            self.assertFalse(self.host._session_ready)
            self.assertFalse(self.host.hmd.accepted)
            pending=asyncio.create_task(ws.receive())
            done,_=await asyncio.wait({pending},timeout=2.1)
            self.assertFalse(done,"Video escaped the held true-settings confirmation")
            self.assertGreater(self.source.reads,0,"A real capture worker must be producing queued synthetic frames")
            release.set()
            first=await asyncio.wait_for(pending,4)
            self.assertEqual(first.type,WSMsgType.TEXT)
            self.assertTrue(json.loads(first.data)["streamSession"]["accepted"])
            self.assertTrue(self.host._session_ready)
            jpeg=await next_binary(ws)
            image=Image.open(BytesIO(jpeg)).convert("RGB")
            self.assertEqual(image.size,(128,64))
            self.assertGreater(image.getpixel((32,32))[0],200)
            self.assertGreater(image.getpixel((96,32))[2],200)
        finally:
            release.set()
            if pending and not pending.done():
                pending.cancel()
                await asyncio.gather(pending,return_exceptions=True)
            await ws.close()

    async def test_missing_either_capability_closes_without_stereo_video_or_pose(self):
        for caps in ([],["stereo-sbs"],["hmd-orientation"]):
            with self.subTest(capabilities=caps):
                ws,_=await self.connect()
                await ws.send_json({"v":1,"type":"hello","capabilities":caps})
                msg=await asyncio.wait_for(ws.receive(),4)
                self.assertEqual(msg.type,WSMsgType.TEXT)
                self.assertEqual(json.loads(msg.data)["type"],"error")
                closing=await asyncio.wait_for(ws.receive(),4)
                self.assertIn(closing.type,(WSMsgType.CLOSE,WSMsgType.CLOSED))
                self.assertEqual(ws.close_code,1008)
                await ws.close()
                self.assertFalse(self.host.hmd.accepted)
                self.assertIsNone(self.sink.last[0])

    async def test_hmd_pose_before_acceptance_is_rejected_then_full_orientation_works(self):
        ws,epoch=await self.connect()
        await ws.send_json(packet(epoch,1))
        self.assertIn("negotiat",(await next_json(ws,"error"))["message"].lower())
        self.assertIsNone(self.sink.last[0])
        await negotiate(ws)
        q=[-.021869850273803754,-.3837819133455947,-.4617914702766405,.7993633658215358]
        await ws.send_json(packet(epoch,1,q))
        await barrier(ws)
        for actual,expected in zip(self.sink.last[0],q):
            self.assertAlmostEqual(actual,expected,places=12)
        await ws.close()

    async def test_virtual_hmd_rejects_mouse_messages_and_never_calls_mouse_controller(self):
        ws,epoch=await self.connect()
        await negotiate(ws)
        self.host.controller.pose=Mock(side_effect=AssertionError("Euler mouse path must not execute"))
        await ws.send_json({"v":1,"type":"pose","seq":1,"yaw":.2,"pitch":.1})
        self.assertIn("quaternion",(await next_json(ws,"error"))["message"])
        self.host.controller.pose.assert_not_called()
        await ws.send_json(packet(epoch,1))
        await barrier(ws)
        self.assertIsNotNone(self.sink.last[0])
        self.host.controller.pose.assert_not_called()
        await ws.close()

    async def test_editor_pause_only_hello_keeps_transport_but_remote_actions_never_resume(self):
        ws,epoch=await self.connect()
        await negotiate(ws)
        await ws.send_json(packet(epoch,1))
        await barrier(ws)
        self.assertIsNotNone(self.sink.last[0])
        await ws.send_json({"v":1,"type":"hello","editing":True})
        await barrier(ws)
        self.assertFalse(ws.closed)
        self.assertTrue(self.host.hmd.paused)
        self.assertIsNone(self.sink.last[0])
        await ws.send_json({"v":1,"type":"settings","clientSeq":2,"settings":{"mode":"fps_enhanced","scale":.6}})
        snapshot=await next_json(ws,"settings",lambda value:value.get("clientSeq")==2)
        self.assertTrue(snapshot["streamSession"]["accepted"])
        await ws.send_json({"v":1,"type":"hello","editing":False})
        await ws.send_json({"v":1,"type":"recenter"})
        await ws.send_json(packet(epoch,2,(0,math.sin(.3),0,math.cos(.3))))
        await barrier(ws)
        self.assertTrue(self.host.hmd.paused)
        self.assertIsNone(self.sink.last[0])
        self.assertTrue(self.host.resume_control()[0])
        await ws.send_json(packet(epoch,3,(0,math.sin(.4),0,math.cos(.4))))
        await barrier(ws)
        self.assertEqual(self.sink.last[0],(0.,0.,0.,1.))
        await ws.close()

    async def test_epoch_sequence_clock_replay_and_missing_sensor_cannot_fake_tracking(self):
        ws,epoch=await self.connect()
        await negotiate(ws)
        await ws.send_json(packet(epoch,4,(0,math.sin(.2),0,math.cos(.2)),time_us=10000))
        await barrier(ws)
        expected=self.sink.last[0]
        for bad in (packet(epoch-1 if epoch>1 else epoch+1,5),packet(epoch,4),packet(epoch,3),packet(epoch,5,time_us=9999)):
            await ws.send_json(bad)
        await barrier(ws)
        self.assertEqual(self.sink.last[0],expected)
        await ws.send_json(packet(epoch,5,q=None,valid=False,time_us=10001))
        await barrier(ws)
        self.assertIsNone(self.sink.last[0])
        self.assertIsNone(self.host.hmd.current)
        await ws.close()

    async def test_f8_pause_and_reconnect_preserve_latch_and_increment_the_epoch(self):
        first,epoch=await self.connect()
        await negotiate(first)
        await first.send_json(packet(epoch,1))
        await barrier(first)
        self.host.disarm("synthetic F8")
        self.assertIsNone(self.sink.last[0])
        await first.close()
        second,new_epoch=await self.connect()
        self.assertGreater(new_epoch,epoch)
        await negotiate(second)
        await second.send_json(packet(new_epoch,1))
        await barrier(second)
        self.assertTrue(self.host.hmd.paused)
        self.assertIsNone(self.sink.last[0])
        self.assertTrue(self.host.resume_control()[0])
        await second.send_json(packet(new_epoch,2))
        await barrier(second)
        self.assertIsNotNone(self.sink.last[0])
        await second.close()

    async def test_late_cancelled_sender_cannot_clear_the_replacement_hmd_session(self):
        entered,cancelled,release,finished=(asyncio.Event() for _ in range(4))
        actual=self.host._send_frames
        calls=[]
        async def blocked(ws):
            calls.append(ws)
            if len(calls)>1:
                return await actual(ws)
            entered.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                await release.wait()
            finally:
                finished.set()
        self.host._send_frames=blocked
        first,epoch=await self.connect()
        try:
            await negotiate(first)
            await asyncio.wait_for(entered.wait(),4)
            await first.close()
            await asyncio.wait_for(cancelled.wait(),4)
            self.assertFalse(finished.is_set())
            second,new_epoch=await self.connect()
            await negotiate(second)
            await second.send_json(packet(new_epoch,1))
            await barrier(second)
            release.set()
            await asyncio.wait_for(finished.wait(),4)
            await barrier(second)
            self.assertEqual(self.host.hmd.epoch,new_epoch)
            self.assertGreater(new_epoch,epoch)
            self.assertTrue(self.host.hmd.connected)
            self.assertTrue(self.host.hmd.accepted)
            self.assertIsNotNone(self.sink.last[0])
            await second.close()
        finally:
            release.set()


class PreviewDirectCompatibilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_legacy_direct_phone_gets_mono_video_and_original_mouse_deltas(self):
        sink=RecordingMouse()
        host=PreviewHost(route="direct-phone",capture_source=SyntheticStereoSource(),input_sink=sink,
                         settings=Settings(mode="fps"),auto_control=True,capture_config=CaptureConfig(fps=30))
        server=TestServer(host.make_app(),host="127.0.0.1")
        await server.start_server()
        try:
            async with ClientSession() as client:
                async with client.ws_connect(server.make_url(f"/ws?token={host.token}")) as ws:
                    hello=await next_json(ws,"hello")
                    self.assertEqual(hello["streamSession"]["streamLayout"],"mono")
                    self.assertEqual(hello["streamSession"]["inputTarget"],"mouse")
                    self.assertTrue(hello["streamSession"]["accepted"])
                    self.assertNotIn("stabilization",hello["settings"])
                    self.assertTrue((await next_binary(ws)).startswith(b"\xff\xd8"))
                    await ws.send_json({"v":1,"type":"pose","seq":1,"yaw":0,"pitch":0})
                    await ws.send_json({"v":1,"type":"pose","seq":2,"yaw":.04,"pitch":0})
                    await barrier(ws)
                    self.assertEqual(sink.moves,[(40,0)])
                    await ws.send_json(packet(hello["streamSession"]["epoch"],1))
                    self.assertIn("mouse",(await next_json(ws,"error"))["message"])
                    self.assertEqual(sink.moves,[(40,0)])
        finally:
            await server.close()


class PreviewThreadStopTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stop_restart_invalidates_pose_transport_and_preserves_pause(self):
        sink=RecordingPoseSink()
        source=SyntheticStereoSource()
        host=PreviewHost(route="steamvr-phone",capture_source=source,pose_sink=sink,
                         host="127.0.0.1",port=free_port(),capture_config=CaptureConfig(fps=30))
        try:
            await asyncio.to_thread(host.start)
            old_token=host.token
            async with ClientSession() as client:
                ws=await client.ws_connect(f"http://127.0.0.1:{host.port}/ws?token={host.token}&settingsSchema=2&enhancedFirstPerson=1")
                first=await next_json(ws,"hello")
                await negotiate(ws)
                await ws.send_json(packet(first["streamSession"]["epoch"],1))
                await barrier(ws)
                self.assertIsNotNone(sink.last[0])
                host.request_stop()
                self.assertTrue(host.hmd.paused)
                self.assertIsNone(sink.last[0])
                self.assertTrue(await asyncio.to_thread(host.stop,4))
                await ws.close()
                self.assertFalse(host.running)
                self.assertIsNone(host._ws)
                self.assertFalse(host._worker.thread.is_alive())
                self.assertGreater(source.closes,0)
                await asyncio.to_thread(host.start)
                self.assertNotEqual(host.token,old_token)
                async with client.ws_connect(f"http://127.0.0.1:{host.port}/ws?token={host.token}&settingsSchema=2&enhancedFirstPerson=1") as fresh:
                    hello=await next_json(fresh,"hello")
                    await negotiate(fresh)
                    await fresh.send_json(packet(hello["streamSession"]["epoch"],1))
                    await barrier(fresh)
                    self.assertTrue(host.hmd.paused)
                    self.assertIsNone(sink.last[0])
                    self.assertTrue(host.resume_control()[0])
                    await fresh.send_json(packet(hello["streamSession"]["epoch"],2))
                    await barrier(fresh)
                    self.assertIsNotNone(sink.last[0])
        finally:
            self.assertTrue(await asyncio.to_thread(host.stop,5))


if __name__ == "__main__":
    unittest.main()

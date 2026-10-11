"""Real loopback video reset keeps pose/epoch and never releases a pause."""
import asyncio
import json
import threading
import unittest
from unittest.mock import Mock,patch

from aiohttp import ClientSession,WSMsgType
from aiohttp.test_utils import TestServer
from vrization_host.capture import CaptureConfig
from vrization_host.protocol import ProtocolError
from vrization_host.gui import HostWindow
from vrization_steamvr.app import PhoneWindow
from vrization_steamvr.host import PreviewHost
from vrization_steamvr.session import MAX_SAFE,VIDEO_REFRESH,parse_preview_message
from preview_fixtures import CAPS,RecordingPoseSink,SyntheticStereoSource,barrier,next_binary,next_json,packet


def refresh(epoch=1,request_id=1):
    return {"v":1,"type":"refreshVideo","epoch":epoch,"requestId":request_id}


class VideoRefreshParserTests(unittest.TestCase):
    def test_exact_safe_request_and_version(self):
        self.assertEqual(parse_preview_message(json.dumps(refresh(MAX_SAFE,MAX_SAFE))),refresh(MAX_SAFE,MAX_SAFE))
        for key in ("epoch","requestId","v"):
            for value in (True,False,0,-1,1.5,"1",None,MAX_SAFE+1):
                with self.subTest(key=key,value=value):
                    msg=refresh();msg[key]=value
                    with self.assertRaises(ProtocolError):parse_preview_message(json.dumps(msg))
        for key in refresh():
            msg=refresh();del msg[key]
            with self.subTest(missing=key),self.assertRaises(ProtocolError):parse_preview_message(json.dumps(msg))
        msg=refresh();msg["paused"]=False
        with self.assertRaises(ProtocolError):parse_preview_message(json.dumps(msg))


class VideoRefreshNetworkTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.entered,self.release=threading.Event(),threading.Event()
        self.release.set()
        outer=self
        class Source(SyntheticStereoSource):
            def close(source):
                source.closes+=1;outer.entered.set()
                if not outer.release.wait(4):raise RuntimeError("Missing fixture release")
        self.source,self.sink=Source(),RecordingPoseSink();self.events=[]
        self.host=PreviewHost(route="steamvr-phone",capture_source=self.source,pose_sink=self.sink,
            capture_config=CaptureConfig(fps=60),on_event=self.events.append)
        self.server=TestServer(self.host.make_app());await self.server.start_server()
        self.host.running,self.host.port=True,self.server.port
        self.client=ClientSession()
        self.sockets=[]

    async def asyncTearDown(self):
        self.release.set()
        for ws in self.sockets:await ws.close()
        await self.client.close();await self.server.close()

    async def connect(self,capability=True,negotiate=True):
        ws=await self.client.ws_connect(self.server.make_url(f"/ws?token={self.host.token}"))
        self.sockets.append(ws)
        hello=await next_json(ws,"hello");self.assertIn(VIDEO_REFRESH,hello["capabilities"])
        epoch=hello["streamSession"]["epoch"]
        if negotiate:
            await ws.send_json({"v":1,"type":"hello","capabilities":CAPS+([VIDEO_REFRESH] if capability else [])})
            await next_json(ws,"settings",lambda x:x["streamSession"]["accepted"])
            await next_binary(ws)
        return ws,epoch

    async def wait_closed_source(self):
        self.assertTrue(await asyncio.to_thread(self.entered.wait,3))

    async def test_live_refresh_preserves_real_pose_epoch_baseline_and_fit(self):
        ws,epoch=await self.connect();self.host.hmd.enable(True)
        await ws.send_json(packet(epoch,1,(0,.1,0,.99498743710662)));await barrier(ws)
        before=(self.host.hmd.output,self.host.hmd.baseline,self.host.settings,self.host.session_generation)
        owner=self.host._ws
        self.release.clear();await ws.send_json(refresh(epoch));await self.wait_closed_source()
        self.assertFalse(self.host._frames_allowed());self.assertFalse(self.host.hmd.paused)
        await ws.send_json(packet(epoch,2,(0,.2,0,.9797958971132712)));await barrier(ws)
        self.assertEqual(self.host.hmd.last_seq,2);self.assertIsNotNone(self.host.hmd.output)
        self.assertEqual(self.host.hmd.baseline,before[1]);self.assertIs(self.host._ws,owner)
        self.release.set();ack=await next_json(ws,"videoRefresh")
        self.assertEqual(ack,{"v":1,"type":"videoRefresh","epoch":epoch,"requestId":1,"paused":False})
        self.assertEqual(await next_binary(ws),self.source.jpeg)
        self.assertEqual((self.host.hmd.baseline,self.host.settings,self.host.session_generation),before[1:])
        self.assertEqual(self.source.closes,1);self.assertFalse(self.host._capture_failed)
        self.assertFalse(self.host.hmd.paused);self.assertTrue(self.host.hmd.accepted)

    async def test_f8_during_worker_close_remains_latched_and_is_reported_in_ack(self):
        ws,epoch=await self.connect();self.release.clear()
        await ws.send_json(refresh(epoch));await self.wait_closed_source()
        self.host.disarm("F8 emergency stop")
        self.release.set();ack=await next_json(ws,"videoRefresh")
        self.assertTrue(ack["paused"]);await next_binary(ws)
        self.assertTrue(self.host.hmd.paused);self.assertIsNone(self.host.hmd.output)
        self.assertFalse(any(q is not None for q,*_ in self.sink.snapshot()))

    async def test_absent_capability_and_wrong_epoch_cannot_reset_capture(self):
        ws,epoch=await self.connect(capability=False)
        await ws.send_json(refresh(epoch));await next_json(ws,"error")
        self.assertEqual(self.source.closes,0)
        await ws.send_json({"v":1,"type":"hello","capabilities":CAPS+[VIDEO_REFRESH]})
        await next_json(ws,"settings")
        await ws.send_json(refresh(epoch+1));await next_json(ws,"error")
        self.assertEqual(self.source.closes,0);self.assertIsNone(self.host._video_refresh_pending)

    async def test_raw_connection_is_not_video_refresh_authority(self):
        ws,epoch=await self.connect(negotiate=False)
        await ws.send_json(refresh(epoch));await next_json(ws,"error")
        self.assertEqual(self.source.closes,0);self.assertFalse(self.host._session_ready)

    async def test_duplicate_and_pending_requests_do_not_restart_a_second_helper(self):
        ws,epoch=await self.connect();self.release.clear()
        await ws.send_json(refresh(epoch));await self.wait_closed_source()
        await ws.send_json(refresh(epoch,2));await next_json(ws,"error")
        self.release.set();await next_json(ws,"videoRefresh");await next_binary(ws)
        await ws.send_json(refresh(epoch));await next_json(ws,"error")
        self.assertEqual(self.source.closes,1)

    async def test_stop_during_close_cannot_ack_or_open_video_again(self):
        ws,epoch=await self.connect();self.release.clear()
        await ws.send_json(refresh(epoch));await self.wait_closed_source()
        self.host.request_stop();self.release.set()
        # TestServer deliberately has no HostServer runner/stop-signal task;
        # a message lets its real connection loop observe the Stop gate.
        await ws.send_json({"v":1,"type":"ping"})
        async with asyncio.timeout(3):
            while not ws.closed:
                msg=await ws.receive()
                if msg.type==WSMsgType.TEXT:self.assertNotEqual(json.loads(msg.data).get("type"),"videoRefresh")
        self.assertTrue(self.host.hmd.paused);self.assertFalse(self.host.hmd.connected)
        self.assertFalse(any(event["event"]=="video_refreshed" for event in self.events))

    async def test_pc_live_refresh_uses_the_same_worker_without_disconnecting(self):
        ws,epoch=await self.connect(capability=False);self.release.clear()
        self.assertTrue(self.host.request_video_refresh());await self.wait_closed_source()
        self.assertFalse(self.host.hmd.paused);self.release.set()
        async with asyncio.timeout(3):
            while not any(event["event"]=="video_refreshed" for event in self.events):await asyncio.sleep(.005)
        await next_binary(ws)
        self.assertEqual(self.host.session_generation,epoch);self.assertFalse(self.host.hmd.paused)
        self.assertTrue(self.host.hmd.accepted);self.assertEqual(self.source.closes,1)

    async def test_old_session_close_completion_cannot_ack_a_replacement_session(self):
        old,epoch=await self.connect();self.release.clear()
        await old.send_json(refresh(epoch));await self.wait_closed_source()
        await old.close()
        async with asyncio.timeout(3):
            while self.host._ws is not None:await asyncio.sleep(.005)
        new,new_epoch=await self.connect(negotiate=False)
        self.assertGreater(new_epoch,epoch);self.assertIsNone(self.host._video_refresh_pending)
        self.release.set();await barrier(new)
        self.assertFalse(any(event["event"]=="video_refreshed" for event in self.events))
        self.assertFalse(self.host._session_ready);self.assertFalse(self.host.hmd.accepted)

    async def test_overlapping_completion_callbacks_send_only_one_ack(self):
        ws,epoch=await self.connect();owner=self.host._ws
        entered,release=asyncio.Event(),asyncio.Event();calls=[]
        actual=owner.send_json
        async def held(message,*args,**kwargs):
            if message.get("type")=="videoRefresh":
                calls.append(message);entered.set();await release.wait()
            return await actual(message,*args,**kwargs)
        owner.send_json=held
        try:
            await ws.send_json(refresh(epoch));await asyncio.wait_for(entered.wait(),3)
            await self.host._finish_video_refresh()
            self.assertEqual(len(calls),1);self.assertFalse(self.host._frames_allowed())
            release.set();await next_json(ws,"videoRefresh");await next_binary(ws)
            self.assertEqual(len(calls),1);self.assertTrue(self.host._frames_allowed())
        finally:release.set();owner.send_json=actual

    async def test_partially_delivered_ack_failure_revokes_its_own_connection(self):
        ws,epoch=await self.connect();owner=self.host._ws;actual=owner.send_json
        async def partial(message,*args,**kwargs):
            await actual(message,*args,**kwargs)
            if message.get("type")=="videoRefresh":raise ConnectionError("Fixture drain failure after delivery")
        owner.send_json=partial
        await ws.send_json(refresh(epoch));await next_json(ws,"videoRefresh")
        async with asyncio.timeout(3):
            while not ws.closed:
                msg=await ws.receive()
                self.assertNotEqual(msg.type,WSMsgType.BINARY)
        self.assertFalse(any(event["event"]=="video_refreshed" for event in self.events))
        self.assertFalse(self.host.hmd.connected)


class VideoRefreshGuiTests(unittest.TestCase):
    def test_hmd_uses_live_reset_but_closed_direct_and_editor_use_existing_flow(self):
        for route,editor,accepted in (("steamvr-phone",None,True),("steamvr-phone",None,False),
                                     ("direct-phone",None,True),("steamvr-phone",Mock(),True)):
            with self.subTest(route=route,editor=bool(editor),accepted=accepted):
                window=PhoneWindow.__new__(PhoneWindow);window.route=route;window.language="en"
                window.editor=editor;window._stop_in_progress=False;window._log=Mock();window.server=Mock()
                window.server.request_video_refresh.return_value=accepted
                with patch.object(HostWindow,"refresh_connection",return_value=False) as fallback:
                    actual=window.refresh_connection()
                live=route=="steamvr-phone" and editor is None and accepted
                self.assertEqual(actual,live)
                self.assertEqual(fallback.call_count,0 if live else 1)
                window.server.resume_control.assert_not_called();window.server.recenter.assert_not_called()

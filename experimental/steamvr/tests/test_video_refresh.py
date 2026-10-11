"""Explicit HMD Refresh recovers old pauses without overriding newer intent."""
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
from vrization_host.server import HostServer
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
        pending=self.host._video_refresh_pending
        self.assertTrue(self.host.request_video_refresh())
        self.assertIs(self.host._video_refresh_pending,pending)
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

    async def test_explicit_phone_refresh_recovers_editor_pause_without_replaying_motion(self):
        ws,epoch=await self.connect()
        await ws.send_json(packet(epoch,1,(0,.1,0,.99498743710662)));await barrier(ws)
        await ws.send_json({"v":1,"type":"hello","editing":True})
        await next_json(ws,"settings");self.assertTrue(self.host.hmd.paused)
        await ws.send_json({"v":1,"type":"settings","settings":{"scale":.6}})
        await next_json(ws,"settings")
        await ws.send_json({"v":1,"type":"hello","editing":False})
        await next_json(ws,"settings")
        self.assertTrue(self.host.hmd.paused,"Save/editor exit alone is not Refresh")
        owner=self.host._ws;before=len(self.sink.snapshot())
        self.release.clear();await ws.send_json(refresh(epoch));await self.wait_closed_source()
        await ws.send_json(packet(epoch,2,(0,.2,0,.9797958971132712)));await barrier(ws)
        self.assertIsNone(self.host.hmd.output)
        self.release.set();ack=await next_json(ws,"videoRefresh");await next_binary(ws)
        self.assertFalse(ack["paused"]);self.assertFalse(self.host.hmd.paused)
        self.assertIsNone(self.host.hmd.output,"Recovery must wait for a new real sensor sample")
        self.assertTrue(all(q is None for q,*_ in self.sink.snapshot()[before:]))
        self.assertIs(self.host._ws,owner);self.assertEqual(self.host.session_generation,epoch)
        self.assertEqual(self.host.settings.scale,.6)
        await ws.send_json(packet(epoch,3,(0,.3,0,.953939201416946)));await barrier(ws)
        self.assertEqual(self.host.hmd.output,(0.,0.,0.,1.))
        await ws.send_json(packet(epoch,4,(0,.4,0,.916515138991168)));await barrier(ws)
        self.assertIsNotNone(self.host.hmd.output);self.assertNotEqual(self.host.hmd.output,(0.,0.,0.,1.))

    async def test_explicit_pc_refresh_recovers_an_existing_enabled_pause(self):
        ws,epoch=await self.connect();self.host.disarm("F8 before explicit Refresh")
        self.assertTrue(self.host.hmd.paused);self.release.clear()
        self.assertTrue(self.host.request_video_refresh());await self.wait_closed_source()
        self.release.set()
        async with asyncio.timeout(3):
            while not any(e["event"]=="video_refreshed" for e in self.events):await asyncio.sleep(.005)
        await next_binary(ws)
        self.assertFalse(self.host.hmd.paused);self.assertIsNone(self.host.hmd.output)
        self.assertEqual(self.host.session_generation,epoch)
        self.assertTrue(next(e for e in self.events if e["event"]=="video_refreshed")["resumed"])

    async def test_disabled_tracking_stays_disabled_after_explicit_refresh(self):
        ws,epoch=await self.connect();self.host.hmd.enable(False)
        await ws.send_json(refresh(epoch));ack=await next_json(ws,"videoRefresh");await next_binary(ws)
        self.assertTrue(ack["paused"]);self.assertFalse(self.host.hmd.enabled)
        self.assertIsNone(self.host.hmd.output)

    async def test_disable_then_enable_during_reset_cannot_restore_a_newer_pause(self):
        ws,epoch=await self.connect();self.host.disarm("existing pause");self.release.clear()
        await ws.send_json(refresh(epoch));await self.wait_closed_source()
        self.host.hmd.enable(False);self.host.hmd.enable(True)
        self.release.set();ack=await next_json(ws,"videoRefresh");await next_binary(ws)
        self.assertTrue(ack["paused"]);self.assertTrue(self.host.hmd.paused)
        self.assertIsNone(self.host.hmd.output)

    async def test_phone_click_joins_pending_pc_reset_and_receives_one_matching_ack(self):
        ws,epoch=await self.connect();self.host.disarm("existing pause");self.release.clear()
        self.assertTrue(self.host.request_video_refresh());await self.wait_closed_source()
        await ws.send_json(refresh(epoch));await barrier(ws)
        self.assertEqual(self.host._video_refresh_pending[2],1)
        self.release.set();ack=await next_json(ws,"videoRefresh");await next_binary(ws)
        self.assertEqual(ack,{"v":1,"type":"videoRefresh","epoch":epoch,"requestId":1,"paused":False})
        self.assertEqual(self.source.closes,1);self.assertFalse(self.host.hmd.paused)

    async def test_pc_full_reconnect_refresh_recovers_only_after_confirmed_new_session(self):
        await self.check_pc_reconnect_refresh(new_pause=False)

    async def test_new_f8_during_pc_reconnect_refresh_keeps_tracking_paused(self):
        await self.check_pc_reconnect_refresh(new_pause=True)

    async def check_pc_reconnect_refresh(self, *, new_pause):
        old,epoch=await self.connect();self.host.disarm("existing editor pause")
        token=self.host.hmd.refresh_pause_token();await old.close()
        async with asyncio.timeout(3):
            while self.host._ws is not None:await asyncio.sleep(.005)
        # The GUI arms its explicit intent after old Stop cleanup and before
        # starting the listener/USB request; normal Connect never calls this.
        self.host.refresh_after_reconnect(resume_token=token)
        if new_pause:self.host.disarm("new F8 during reconnect")
        new,new_epoch=await self.connect(negotiate=False)
        self.assertGreater(new_epoch,epoch);self.assertTrue(self.host.hmd.paused)
        self.assertIsNotNone(self.host._refresh_after_reconnect)
        await new.send_json({"v":1,"type":"hello","capabilities":CAPS+[VIDEO_REFRESH]})
        await next_json(new,"settings");await next_binary(new)
        self.assertIsNone(self.host._refresh_after_reconnect)
        self.assertEqual(self.host.hmd.paused,new_pause)
        self.assertIsNone(self.host.hmd.output)
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

    async def test_stop_after_finish_checks_atomically_revokes_resume_and_next_session_stays_paused(self):
        ws,epoch=await self.connect();self.host.disarm("old pause before explicit Refresh")
        self.release.clear();await ws.send_json(refresh(epoch));await self.wait_closed_source()
        entered,release=threading.Event(),threading.Event();observed={}
        actual_stop=HostServer.request_stop
        actual_resume=self.host.hmd.resume_for_refresh
        def held_base_stop(host):
            # PreviewHost must already have revoked connected/accepted under
            # one HMD lock, before the inherited stopping flag can be set.
            entered.set()
            if not release.wait(3):raise RuntimeError("Missing deterministic Stop release")
            return actual_stop(host)
        def stop_between_check_and_resume(token):
            stop=threading.Thread(target=self.host.request_stop)
            stop.start()
            try:
                if not entered.wait(3):raise RuntimeError("Stop did not reach inherited boundary")
                observed.update(stopping=self.host._stopping.is_set(),paused=self.host.hmd.paused,
                    connected=self.host.hmd.connected,accepted=self.host.hmd.accepted,
                    token_equal=self.host.hmd.refresh_pause_token()==token)
                observed["resumed"]=actual_resume(token)
                return observed["resumed"]
            finally:
                release.set();stop.join(3)
                observed["stop_finished"]=not stop.is_alive()
        with patch.object(HostServer,"request_stop",held_base_stop), \
                patch.object(self.host.hmd,"resume_for_refresh",stop_between_check_and_resume):
            self.release.set()
            async with asyncio.timeout(4):
                while "stop_finished" not in observed:await asyncio.sleep(.005)
        self.assertEqual(observed,{"stopping":False,"paused":True,"connected":False,"accepted":False,
                                   "token_equal":True,"resumed":False,"stop_finished":True})
        self.assertTrue(self.host.hmd.paused);self.assertFalse(self.host.hmd.connected)
        self.assertFalse(any(q is not None for q,*_ in self.sink.snapshot()))
        self.assertFalse(any(e["event"]=="video_refreshed" for e in self.events))
        # TestServer has no HostServer runner; let the real receive loop observe
        # Stop, then simulate a listener restart without injecting any pose.
        await ws.send_json({"v":1,"type":"ping"})
        async with asyncio.timeout(3):
            while not ws.closed:
                message=await ws.receive()
                if message.type==WSMsgType.TEXT:
                    payload=json.loads(message.data)
                    if payload.get("type")=="videoRefresh":self.assertTrue(payload["paused"])
        self.host._stopping.clear();self.host.running=True
        new,new_epoch=await self.connect(negotiate=False)
        self.assertGreater(new_epoch,epoch);self.assertTrue(self.host.hmd.paused)
        await new.send_json({"v":1,"type":"hello","capabilities":CAPS+[VIDEO_REFRESH]})
        await next_json(new,"settings",lambda x:x["streamSession"]["accepted"])
        self.assertTrue(self.host.hmd.paused,"Ordinary Connect cannot clear the Stop latch")
        self.assertIsNone(self.host._refresh_after_reconnect)

    async def test_pc_live_refresh_uses_the_same_worker_without_disconnecting(self):
        ws,epoch=await self.connect(capability=False);self.release.clear()
        self.assertTrue(self.host.request_video_refresh());await self.wait_closed_source()
        self.assertTrue(self.host.request_video_refresh())
        self.assertTrue(self.host.request_video_refresh())
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
                window.server.refresh_after_reconnect.assert_not_called()
                if route=="steamvr-phone" and editor is None and not accepted:
                    self.assertIsNotNone(window._hmd_refresh_reconnect_token)

    def test_full_refresh_intent_is_armed_before_start_and_cancelled_by_stop_or_failure(self):
        window=PhoneWindow.__new__(PhoneWindow);window.server=Mock();window._stop_in_progress=False
        window._hmd_refresh_reconnect_token=17;order=[]
        window.server.refresh_after_reconnect.side_effect=lambda **kw:order.append(("arm",kw))
        with patch.object(HostWindow,"start",side_effect=lambda **kw:order.append(("start",kw)) or True):
            self.assertTrue(window.start(notify_phone=False))
        self.assertEqual(order,[("arm",{"resume_token":17}),("start",{"notify_phone":False})])
        self.assertIsNone(window._hmd_refresh_reconnect_token)
        window._hmd_refresh_reconnect_token=18
        with patch.object(HostWindow,"stop") as stop:window.stop()
        stop.assert_called_once_with(for_refresh=False)
        self.assertIsNone(window._hmd_refresh_reconnect_token)
        window.server.cancel_refresh_recovery.assert_called_once()
        window._hmd_refresh_reconnect_token=19
        window._stop_in_progress=True
        with patch.object(HostWindow,"start") as start:
            self.assertFalse(window.start());start.assert_not_called()
        self.assertEqual(window._hmd_refresh_reconnect_token,19)
        window._stop_in_progress=False
        with patch.object(HostWindow,"start",return_value=False):self.assertFalse(window.start())
        self.assertEqual(window.server.cancel_refresh_recovery.call_count,2)

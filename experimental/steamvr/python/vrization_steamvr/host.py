"""Original host extension: stereo negotiation and full HMD poses, never mouse."""
import asyncio
from vrization_host.protocol import ProtocolError
from vrization_host.server import HostServer
from . import __version__
from .ipc import PoseMap, tick_ms
from .pose import HmdPoseGate
from .session import Session, STEREO, ORIENTATION, VIDEO_REFRESH, parse_preview_message

class NoMouse:
    def move(self, dx, dy):
        raise RuntimeError("Virtual HMD route cannot inject mouse movement")


class PreviewHost(HostServer):
    def __init__(self, *, route="direct-phone", pose_sink=None, clock=tick_ms, **kwargs):
        self._session_ready=False
        self._video_refresh_pending=None
        self._video_refresh_ack_owner=None
        self._client_video_refresh=False
        self._video_refresh_last_id=0
        self._refresh_after_reconnect=None
        self.stream_session=Session(route)
        self.route=route
        self.pose_sink=pose_sink if pose_sink is not None else PoseMap() if route=="steamvr-phone" else None
        self.hmd=HmdPoseGate(self.pose_sink,clock) if self.pose_sink is not None else None
        if route=="steamvr-phone":
            kwargs["input_sink"]=NoMouse()
            kwargs["auto_control"]=False
        kwargs.setdefault("port",8766)
        kwargs.setdefault("usb_bootstrap_ports",(18775,))
        super().__init__(**kwargs)

    def _host_capabilities(self):
        return super()._host_capabilities()+[STEREO,ORIENTATION,VIDEO_REFRESH]

    def _host_version(self):
        return __version__

    def _outgoing_session_fields(self):
        return {"streamSession":self.stream_session.descriptor(),"previewVersion":__version__}

    def _parse_client_message(self,data):
        return parse_preview_message(data)

    def _session_opened(self,generation):
        self._video_refresh_pending=None
        self._video_refresh_ack_owner=None
        self._client_video_refresh=False
        self._video_refresh_last_id=0
        self._session_ready=self.route=="direct-phone"
        self.stream_session.open(generation)
        if self.hmd:self.hmd.open(generation)

    def _session_closed(self,generation):
        self._video_refresh_pending=None
        self._video_refresh_ack_owner=None
        self._client_video_refresh=False
        self._session_ready=False
        self.stream_session.close()
        if self.hmd:self.hmd.close()

    def _frames_allowed(self):
        return self._session_ready and self._video_refresh_pending is None

    async def _on_client_hello(self,msg,ws):
        first_confirmation=not self.stream_session.accepted
        if not self.stream_session.accepted:
            try:
                self.stream_session.negotiate(msg.get("capabilities",[]))
            except ProtocolError as error:
                await ws.send_json({"v":1,"type":"error","message":str(error)})
                await ws.close(code=1008,message=b"SteamVR capabilities required",drain=False)
                return
        if self.hmd:
            if msg.get("editing") is True:self.disarm("headset editor opened")
        # Always a complete authoritative snapshot; even LAN query opt-in waits
        # until validated client hello before any SBS byte may be transmitted.
        sent = await self._broadcast_settings(ws)
        if sent and self._ws is ws and not ws.closed and not self._stopping.is_set():
            if VIDEO_REFRESH in msg.get("capabilities",[]):self._client_video_refresh=True
            if self.hmd:self.hmd.negotiate()
            self._session_ready=True
            recovery=self._refresh_after_reconnect
            if (first_confirmation and self.hmd and recovery is not None
                    and self.session_generation>recovery[1]):
                self._refresh_after_reconnect=None
                self._begin_video_refresh(ws,None,resume_token=recovery[0])
            elif first_confirmation and self.hmd and (self.session_generation>1 or self._capture_failed):
                # Reconnecting a real phone must replace a Mirror that exited
                # while its HMD was absent, even if the idle worker has not yet
                # discovered that exit. Only the capture worker closes it;
                # the existing tracking pause remains latched.
                self._buffer.frame=None
                self._worker.request_source_reset()
        elif self._ws is ws:
            await ws.close(code=1001,message=b"Session confirmation stalled",drain=False)

    async def _handle_custom_message(self,msg,ws):
        kind=msg["type"]
        if kind=="refreshVideo":
            if (not self.hmd or not self._session_ready or not self.stream_session.accepted
                    or not self._client_video_refresh or self._ws is not ws or ws.closed
                    or self._stopping.is_set() or msg["epoch"]!=self.stream_session.epoch):
                raise ProtocolError("Video refresh needs the current negotiated HMD session")
            if msg["requestId"]<=self._video_refresh_last_id:
                raise ProtocolError("Video refresh request is stale")
            pending=self._video_refresh_pending
            if pending is not None:
                # A phone click can join a PC-owned reset rather than time out
                # and unnecessarily disconnect. One phone ACK owns the receipt.
                if pending[0] is ws and pending[1]==msg["epoch"] and pending[2] is None:
                    self._video_refresh_pending=(ws,pending[1],msg["requestId"],pending[3],pending[4])
                    self._video_refresh_last_id=msg["requestId"]
                    return True
                raise ProtocolError("Video refresh is already pending")
            if not self._begin_video_refresh(ws,msg["requestId"]):
                raise ProtocolError("Video refresh is unavailable")
            self._video_refresh_last_id=msg["requestId"]
            return True
        if kind=="hmdPose":
            if self.hmd is None:raise ProtocolError("Direct phone uses mouse poses")
            if not self._session_ready:raise ProtocolError("HMD pose needs negotiated capabilities")
            self.hmd.pose(msg)
            return True
        if self.hmd and kind=="pose":
            raise ProtocolError("Virtual HMD requires a full quaternion, not a mouse pose")
        if self.hmd and kind=="recenter":
            self.hmd.recenter(phone_reset=True)
            return True
        return False

    def _begin_video_refresh(self,ws,request_id,*,resume_token=None):
        # Loop-owned transaction; actual GPU/helper cleanup belongs to the worker.
        if (not self.hmd or not self._session_ready or not self.stream_session.accepted
                or self._ws is not ws or ws.closed or self._stopping.is_set()
                or self._video_refresh_pending is not None):return False
        pending=(ws,self.stream_session.epoch,request_id)
        token=self.hmd.refresh_pause_token() if resume_token is None else resume_token
        self._video_refresh_pending=(*pending,0,token)
        self._buffer.frame=None
        receipt=self._worker.request_source_reset()
        if not receipt:
            self._video_refresh_pending=None
            return False
        self._video_refresh_pending=(*pending,receipt,token)
        return True

    def request_video_refresh(self):
        """Explicit PC Refresh: reset video and recover an existing HMD pause."""
        if (not self.running or not self.hmd or not self._session_ready or self._ws is None
                or self._ws.closed or self._stopping.is_set()):return False
        owner=self._ws
        pending=self._video_refresh_pending
        if pending is not None:
            # A repeated local click must not become a full reconnect/pause.
            # Coalesce only the current session's already-owned video reset.
            return pending[0] is owner and pending[1]==self.stream_session.epoch
        token=self.hmd.refresh_pause_token()
        async def request():self._begin_video_refresh(owner,None,resume_token=token)
        asyncio.run_coroutine_threadsafe(request(),self._loop)
        return True

    def refresh_after_reconnect(self, *, resume_token=None):
        """One PC Refresh intent, consumed by a later confirmed HMD session."""
        if self.hmd:
            token=self.hmd.refresh_pause_token() if resume_token is None else resume_token
            self._refresh_after_reconnect=(token,self.session_generation)

    def cancel_refresh_recovery(self):
        self._refresh_after_reconnect=None

    def _capture_source_reset(self):
        super()._capture_source_reset()
        # Read the transaction on the event loop, after request_source_reset()
        # has returned its receipt. Even an immediate close cannot ACK early.
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._finish_video_refresh(),self._loop)

    async def _finish_video_refresh(self):
        pending=self._video_refresh_pending
        if pending is None or self._worker.completed_reset_generation<pending[3]:return
        ws,epoch,request_id,_,resume_token=pending
        if (self._video_refresh_pending is not pending or self._ws is not ws or ws.closed
                or self._stopping.is_set() or self.stream_session.epoch!=epoch):return
        if self._video_refresh_ack_owner is pending:return
        self._video_refresh_ack_owner=pending
        resumed=self.hmd.resume_for_refresh(resume_token)
        try:
            if request_id is not None:
                await asyncio.wait_for(ws.send_json({"v":1,"type":"videoRefresh","epoch":epoch,
                    "requestId":request_id,"paused":self.hmd.paused or not self.hmd.enabled}),2)
        except (ConnectionError,RuntimeError,asyncio.TimeoutError):
            # ACK bytes may have arrived before drain failed. Revoke only this
            # owner so a peer cannot cancel its deadline yet wait forever.
            if self._video_refresh_pending is pending and self._ws is ws:
                await ws.close(code=1001,message=b"Video refresh acknowledgement stalled",drain=False)
            return
        finally:
            if self._video_refresh_ack_owner is pending:self._video_refresh_ack_owner=None
        if self._video_refresh_pending is pending and self._ws is ws and not self._stopping.is_set():
            self._video_refresh_pending=None
            self._emit("video_refreshed",epoch=epoch,requestId=request_id,
                       paused=self.hmd.paused or not self.hmd.enabled,resumed=resumed)

    def set_auto_control(self,enabled):
        if self.hmd:
            self.hmd.enable(enabled)
            # Keep inherited Euler controller disabled in every code path.
            super().set_auto_control(False)
        else:super().set_auto_control(enabled)

    def disarm(self,reason="emergency stop"):
        if self.hmd:self.hmd.pause(invalidate_refresh=reason!="streaming stopped")
        super().disarm(reason)

    def resume_control(self):
        if self.hmd:
            if self._capture_failed or self._stopping.is_set():
                return False,"Restart streaming before resuming HMD tracking"
            self.hmd.resume()
            self._emit("input_policy")
            return True,"SteamVR orientation ready; F8 pauses tracking"
        return super().resume_control()

    def get_control_state(self):
        if self.hmd:
            return {"enabled":self.hmd.enabled,"armed":self.hmd.output is not None,
                    "paused":self.hmd.paused,"connected":self.controller.connected,
                    "mode":self.settings.mode}
        return super().get_control_state()

    def recenter(self):
        if self.hmd:self.hmd.recenter()
        else:super().recenter()

    async def _watch_input(self):
        while True:
            await asyncio.sleep(.05)
            self.controller.tick()
            if self.hmd:self.hmd.tick()

    def start(self):
        if self.hmd:
            action=getattr(self.pose_sink,"start",None)
            if action:action()
            self.pose_sink.publish(None,0,False,self.hmd.paused)
        try:super().start()
        except Exception:
            if self.hmd:
                action=getattr(self.pose_sink,"close",None)
                if action:action()
            raise

    def request_stop(self):
        if self.hmd:self.hmd.stop()
        self.cancel_refresh_recovery()
        super().request_stop()

    def stop(self,timeout=6):
        complete=super().stop(timeout)
        if complete and self.hmd:
            self.hmd.close()
            action=getattr(self.pose_sink,"close",None)
            if action:action()
        return complete

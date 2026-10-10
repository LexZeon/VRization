"""Original host extension: stereo negotiation and full HMD poses, never mouse."""
import asyncio
from vrization_host.protocol import ProtocolError
from vrization_host.server import HostServer
from . import __version__
from .ipc import PoseMap, tick_ms
from .pose import HmdPoseGate
from .session import Session, STEREO, ORIENTATION, parse_preview_message

class NoMouse:
    def move(self, dx, dy):
        raise RuntimeError("Virtual HMD route cannot inject mouse movement")


class PreviewHost(HostServer):
    def __init__(self, *, route="direct-phone", pose_sink=None, clock=tick_ms, **kwargs):
        self._session_ready=False
        self.stream_session=Session(route)
        self.route=route
        self.pose_sink=pose_sink if pose_sink is not None else PoseMap() if route=="steamvr-phone" else None
        self.hmd=HmdPoseGate(self.pose_sink,clock) if self.pose_sink is not None else None
        if route=="steamvr-phone":
            kwargs["input_sink"]=NoMouse()
            kwargs["auto_control"]=False
        kwargs.setdefault("port",8766)
        super().__init__(**kwargs)

    def _host_capabilities(self):
        return super()._host_capabilities()+[STEREO,ORIENTATION]

    def _outgoing_session_fields(self):
        return {"streamSession":self.stream_session.descriptor(),"previewVersion":__version__}

    def _parse_client_message(self,data):
        return parse_preview_message(data)

    def _session_opened(self,generation):
        self._session_ready=self.route=="direct-phone"
        self.stream_session.open(generation)
        if self.hmd:self.hmd.open(generation)

    def _session_closed(self,generation):
        self._session_ready=False
        self.stream_session.close()
        if self.hmd:self.hmd.close()

    def _frames_allowed(self):
        return self._session_ready

    async def _on_client_hello(self,msg,ws):
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
            if self.hmd:self.hmd.negotiate()
            self._session_ready=True
        elif self._ws is ws:
            await ws.close(code=1001,message=b"Session confirmation stalled",drain=False)

    async def _handle_custom_message(self,msg,ws):
        kind=msg["type"]
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

    def set_auto_control(self,enabled):
        if self.hmd:
            self.hmd.enable(enabled)
            # Keep inherited Euler controller disabled in every code path.
            super().set_auto_control(False)
        else:super().set_auto_control(enabled)

    def disarm(self,reason="emergency stop"):
        if self.hmd:self.hmd.pause()
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
        if self.hmd:self.hmd.pause()
        super().request_stop()

    def stop(self,timeout=6):
        complete=super().stop(timeout)
        if complete and self.hmd:
            self.hmd.close()
            action=getattr(self.pose_sink,"close",None)
            if action:action()
        return complete

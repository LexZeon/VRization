"""Full orientation with local emergency latch and monotonic session ownership."""
import math
import threading


def multiply(a, b):
    x,y,z,w=a; X,Y,Z,W=b
    return (w*X+x*W+y*Z-z*Y, w*Y-x*Z+y*W+z*X,
            w*Z+x*Y-y*X+z*W, w*W-x*X-y*Y-z*Z)


def inverse(q):
    return (-q[0],-q[1],-q[2],q[3])

class HmdPoseGate:
    def __init__(self, sink, tick_ms):
        self.sink, self.tick_ms = sink, tick_ms
        self.lock = threading.RLock()
        self.epoch=0; self.last_seq=-1; self.last_time=-1; self.last_tick=0
        self._last_publish_tick=0
        self.connected=False; self.accepted=False; self.paused=False; self.enabled=True
        self.pause_generation=0
        self.pending_baseline=False; self.current=None; self.baseline=(0.,0.,0.,1.); self.output=None

    def open(self, epoch):
        with self.lock:
            self.epoch=epoch; self.last_seq=-1; self.last_time=-1; self.last_tick=0
            self.connected=True; self.accepted=False; self.current=self.output=None
            self.baseline=(0.,0.,0.,1.)
            self._invalidate()

    def _invalidate(self):
        self.sink.publish(None, self.last_seq, self.connected, self.paused or not self.enabled)
        self._last_publish_tick=self.tick_ms()

    def negotiate(self):
        with self.lock:
            self.accepted=True

    def close(self):
        with self.lock:
            self.connected=False; self.accepted=False; self.current=self.output=None
            self._invalidate()

    def stop(self):
        # Revoke the current session in the same lock used by refresh recovery.
        # A GUI full Refresh may retain its token for a later new session, but
        # no already-in-flight completion may clear this Stop's pause.
        with self.lock:
            self.paused=True; self.connected=False; self.accepted=False
            self.current=self.output=None; self._invalidate()

    def pause(self, *, invalidate_refresh=True):
        with self.lock:
            if invalidate_refresh:self.pause_generation+=1
            self.paused=True; self.output=None; self._invalidate()

    def enable(self, enabled):
        with self.lock:
            if not enabled:self.pause_generation+=1
            self.enabled=bool(enabled)
            if not enabled: self.output=None; self._invalidate()

    def resume(self):
        with self.lock:
            self.paused=False; self.enabled=True
            self.baseline=self.current or (0.,0.,0.,1.)
            self.pending_baseline=True
            self.current=self.output=None; self._invalidate()

    def refresh_pause_token(self):
        with self.lock:return self.pause_generation

    def resume_for_refresh(self, token):
        """An explicit HMD Refresh may recover an existing enabled pause.

        Never replay stored motion, recenter an already-active stream, or
        override a newer pause/disable while capture is being rebuilt.
        """
        with self.lock:
            if (token!=self.pause_generation or not self.connected or not self.accepted
                    or not self.enabled or not self.paused):return False
            self.resume()
            return True

    def recenter(self, *, phone_reset=False):
        with self.lock:
            self.baseline=(0.,0.,0.,1.) if phone_reset else self.current or (0.,0.,0.,1.)
            self.pending_baseline=False
            self.output=None; self._invalidate()

    def pose(self, msg):
        with self.lock:
            if not self.connected or not self.accepted or msg["epoch"]!=self.epoch or msg["seq"]<=self.last_seq:
                return False
            if msg["timeUs"]<self.last_time:return False
            self.last_seq=msg["seq"]; self.last_time=msg["timeUs"]; self.last_tick=self.tick_ms()
            if not msg["trackingValid"]:
                self.current=self.output=None; self._invalidate(); return True
            self.current=msg["q"]
            if self.paused or not self.enabled:
                self._invalidate(); return True
            if self.pending_baseline:
                self.baseline=self.current; self.pending_baseline=False
            q=multiply(inverse(self.baseline),self.current)
            norm=math.sqrt(sum(x*x for x in q)); q=tuple(x/norm for x in q)
            if self.output and sum(a*b for a,b in zip(q,self.output))<0: q=tuple(-x for x in q)
            self.output=q
            self.sink.publish(q,self.last_seq,True,False)
            self._last_publish_tick=self.last_tick
            return True

    def tick(self):
        with self.lock:
            if not self.connected or not self.accepted:
                return
            now=self.tick_ms()
            if self.output is not None and now-self.last_tick>500:
                self.output=None; self._invalidate()
            elif self.output is None and now-self._last_publish_tick>=100:
                # Keep transport presence fresh while tracking is unavailable
                # (editor, pause, no sensor or stale pose). Never replay a valid
                # quaternion or advance the phone's sequence/pose timestamp.
                self._invalidate()

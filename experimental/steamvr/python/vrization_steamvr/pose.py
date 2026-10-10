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
        self.connected=False; self.accepted=False; self.paused=False; self.enabled=True
        self.pending_baseline=False; self.current=None; self.baseline=(0.,0.,0.,1.); self.output=None

    def open(self, epoch):
        with self.lock:
            self.epoch=epoch; self.last_seq=-1; self.last_time=-1; self.last_tick=0
            self.connected=True; self.accepted=False; self.current=self.output=None
            self.baseline=(0.,0.,0.,1.)
            self._invalidate()

    def _invalidate(self):
        self.sink.publish(None, self.last_seq, self.connected, self.paused or not self.enabled)

    def negotiate(self):
        with self.lock:
            self.accepted=True

    def close(self):
        with self.lock:
            self.connected=False; self.accepted=False; self.current=self.output=None
            self._invalidate()

    def pause(self):
        with self.lock:
            self.paused=True; self.output=None; self._invalidate()

    def enable(self, enabled):
        with self.lock:
            self.enabled=bool(enabled)
            if not enabled: self.output=None; self._invalidate()

    def resume(self):
        with self.lock:
            self.paused=False; self.enabled=True
            self.baseline=self.current or (0.,0.,0.,1.)
            self.pending_baseline=True
            self.current=self.output=None; self._invalidate()

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
            return True

    def tick(self):
        with self.lock:
            if self.output is not None and self.tick_ms()-self.last_tick>500:
                self.output=None; self._invalidate()

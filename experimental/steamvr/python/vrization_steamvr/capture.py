"""Bounded native compositor capture; GPU scales before CPU JPEG encoding."""
from io import BytesIO
from pathlib import Path
import os
import time
from PIL import Image
from vrization_host.capture import Frame
from .ipc import FrameReader,frame_name
from .runtime import OwnedProcess,native_helper


def overlay_config(config,monitor):
    """Respect both shared-map dimensions while retaining the user's ceiling."""
    width,height=monitor["width"],monitor["height"]
    if width<=0 or height<=0:raise ValueError("Selected display is unavailable")
    ceiling=min(config.width,1920,int(1080*max(width,height)/height))
    from dataclasses import replace
    return replace(config,width=max(320,ceiling))


class MirrorCaptureSource:
    def __init__(self,*,process_factory=OwnedProcess,reader_factory=FrameReader,helper=native_helper):
        self.process_factory,self.reader_factory,self.helper=process_factory,reader_factory,helper
        self.process=self.reader=None;self.key=None;self.last_tick=None;self.frame=None;self.started=0

    def read(self,config):
        key=(min(1920,max(320,config.width//2*2)),config.fps)
        if self.key!=key:
            self.close()
            name=frame_name()
            self.process=self.process_factory(self.helper("Mirror"),["--frame-map",name,"--width",key[0],"--fps",key[1]],
                log=Path(os.environ.get("VRIZATION_PROFILE_DIRECTORY","."))/"mirror.log")
            self.reader=self.reader_factory(name,stereo=True)
            self.key=key;self.started=time.perf_counter()
        code=self.process.poll()
        if code is not None:raise OSError(f"SteamVR mirror exited ({code}); select Phone HMD in SteamVR, then restart streaming.")
        started=time.perf_counter();sample=self.reader.read()
        if sample is None:
            self.frame=None
            if started-self.started>65:raise TimeoutError("SteamVR supplied no Phone HMD compositor frames; check the runtime and driver.")
            return None
        width,height,bgra,tick=sample
        if self.last_tick==tick and self.frame and self.quality==config.quality:return self.frame
        image=Image.frombytes("RGB",(width,height),bgra,"raw","BGRX")
        output=BytesIO();image.save(output,"JPEG",quality=config.quality,optimize=False,subsampling=0)
        ready=time.perf_counter()
        self.frame=Frame(output.getvalue(),width,height,time.monotonic(),(ready-started)*1000,ready)
        self.last_tick=tick;self.quality=config.quality;self.started=ready
        return self.frame

    def close(self):
        try:
            if self.process:self.process.close()
        finally:
            self.process=None
            if self.reader:self.reader.close()
            self.reader=None;self.key=None;self.last_tick=None;self.frame=None

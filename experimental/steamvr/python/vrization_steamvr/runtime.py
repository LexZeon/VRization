"""Discover installed OpenVR paths and manage only this preview's resources."""
import json
import os
from pathlib import Path
import subprocess
import sys

from .ipc import StopEvent


def bundle_root():
    if getattr(sys,"frozen",False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[4]/"artifacts/steamvr/native-bundle"


def native_helper(name):
    path=bundle_root()/"native"/f"VRization-SteamVR-{name}.exe"
    if name not in {"Mirror","Overlay"} or not path.is_file():
        raise FileNotFoundError("The native SteamVR bundle is missing; extract the complete Windows ZIP.")
    return path


def discover_runtime(path=None):
    """Read the user's OpenVR runtime inventory without changing its settings."""
    path=Path(path) if path else Path(os.environ.get("LOCALAPPDATA","."))/"openvr/openvrpaths.vrpath"
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
        for candidate in data.get("runtime",[]):
            root=Path(candidate)
            if (root/"bin/win64/vrpathreg.exe").is_file():return root
    except (OSError,ValueError,TypeError):pass
    return None


class DriverManager:
    def __init__(self,runtime=None,driver=None,run=subprocess.run):
        self.runtime=Path(runtime) if runtime else discover_runtime()
        self.driver=(Path(driver) if driver else bundle_root()/"drivers/vrization_phone").resolve()
        self.run=run

    def change(self,register):
        if self.runtime is None:raise FileNotFoundError("Install and launch SteamVR once before registering this driver.")
        if not (self.driver/"driver.vrdrivermanifest").is_file():
            raise FileNotFoundError("Extract the complete preview ZIP before registering its driver.")
        command=[str(self.runtime/"bin/win64/vrpathreg.exe"),"adddriver" if register else "removedriver",str(self.driver)]
        result=self.run(command,capture_output=True,text=True,timeout=15,
                        creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        if result.returncode:raise OSError((result.stderr or result.stdout or "Driver registration failed").strip())
        return result.stdout.strip()


class OwnedProcess:
    """One child, one stop event; no discovery or termination of other apps."""
    def __init__(self,executable,args,*,popen=subprocess.Popen,event_factory=StopEvent,log=None):
        self.event=event_factory()
        self.log=None
        self.process=None
        try:
            if log is not None:
                Path(log).parent.mkdir(parents=True,exist_ok=True)
                self.log=open(log,"ab",buffering=0)
            self.process=popen([str(executable),*map(str,args),"--stop-event",self.event.name],
                               stdin=subprocess.DEVNULL,stdout=self.log or subprocess.DEVNULL,
                               stderr=subprocess.STDOUT,
                               creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        except Exception:
            self.close();raise

    def poll(self):return self.process.poll() if self.process else 0

    def close(self):
        if self.event:self.event.signal()
        try:
            if self.process and self.process.poll() is None:
                try:self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.terminate()
                    try:self.process.wait(timeout=1)
                    except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=1)
        finally:
            self.process=None
            if self.event:self.event.close();self.event=None
            if self.log:self.log.close();self.log=None


def diagnostics():
    from . import __version__
    root=bundle_root();runtime=discover_runtime()
    return {"version":__version__,"channel":"steamvr-experimental","runtimeDetected":runtime is not None,
            "nativeHelpersPresent":all((root/"native"/f"VRization-SteamVR-{name}.exe").is_file()
                                        for name in ("Mirror","Overlay")),
            "driverPresent":(root/"drivers/vrization_phone/bin/win64/driver_vrization_phone.dll").is_file(),
            "routes":["direct-phone","steamvr-phone","steamvr-headset"],
            "hostPort":8766,"androidPorts":[18774,18775],"iosPorts":[18776,18777],
            "hardwareVerified":False,"startsCapture":False,"injectsMouse":False,"registersDriver":False}

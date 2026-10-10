"""Versioned user-session Windows shared memory; no network pose control."""
import ctypes
from ctypes import wintypes
import math
import os
import re
import struct
import threading
import time
import uuid

POSE_NAME = r"Local\VRizationPhonePoseV1"
POSE_SIZE = 128
FRAME_SIZE = 64 + 1920*1080*4
POSE = struct.Struct("<4sIIIQQ4d3dI36s")
FRAME = struct.Struct("<4sIIIIIIIQ24s")


def tick_ms():
    if os.name == "nt":
        kernel=ctypes.WinDLL("kernel32",use_last_error=True)
        kernel.GetTickCount64.restype=ctypes.c_uint64
        return int(kernel.GetTickCount64())
    return int(time.monotonic()*1000)  # Software fixture only on non-Windows.


def frame_name():
    return "Local\\VRizationFrame-" + uuid.uuid4().hex


def decode_frame(header, pixels, now, *, stereo=False):
    if len(header)!=64: raise ValueError("Invalid frame header size")
    magic,version,size,sequence,width,height,stride,flags,tick,reserved=FRAME.unpack(header)
    if magic!=b"VRF1" or version!=1 or size!=64 or sequence&1 or flags&~1:
        raise ValueError("Invalid frame header")
    if not flags&1 or not 0<=now-tick<=500: return None
    if not 1<=width<=1920 or not 1<=height<=1080 or stride!=width*4 or (stereo and width%2):
        raise ValueError("Invalid frame dimensions")
    if len(pixels)!=stride*height: raise ValueError("Invalid frame payload")
    return width,height,pixels,tick


class WindowsMap:
    def __init__(self,name,size,*,writer=False):
        if os.name!="nt": raise OSError("Native shared memory requires Windows")
        if not re.fullmatch(r"Local\\VRization(?:PhonePoseV1|Frame-[0-9a-f]{32})",name):
            raise ValueError("Invalid owned mapping name")
        self.name,self.size,self.writer=name,size,writer
        self.kernel=ctypes.WinDLL("kernel32",use_last_error=True)
        k=self.kernel
        k.CreateFileMappingW.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.DWORD,wintypes.LPCWSTR]
        k.CreateFileMappingW.restype=wintypes.HANDLE
        k.OpenFileMappingW.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.LPCWSTR];k.OpenFileMappingW.restype=wintypes.HANDLE
        k.MapViewOfFile.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.DWORD,wintypes.DWORD,ctypes.c_size_t];k.MapViewOfFile.restype=ctypes.c_void_p
        k.UnmapViewOfFile.argtypes=[ctypes.c_void_p];k.CloseHandle.argtypes=[wintypes.HANDLE]
        k.InterlockedIncrement.argtypes=[ctypes.POINTER(ctypes.c_long)];k.InterlockedIncrement.restype=ctypes.c_long
        access=2 if writer else 4
        if writer:
            self.handle=k.CreateFileMappingW(ctypes.c_void_p(-1),None,4,0,size,name)
            error=ctypes.get_last_error()
            if self.handle and error==183:
                k.CloseHandle(self.handle);raise FileExistsError("Another preview owns this mapping")
        else:
            self.handle=k.OpenFileMappingW(access,False,name)
        if not self.handle:raise ctypes.WinError(ctypes.get_last_error())
        self.address=k.MapViewOfFile(self.handle,access,0,0,size)
        if not self.address:
            k.CloseHandle(self.handle);raise ctypes.WinError(ctypes.get_last_error())
        self.lock=threading.Lock()
        if writer:ctypes.memset(self.address,0,size)

    def snapshot(self, payload_size):
        for _ in range(4):
            before=ctypes.string_at(self.address+12,4)
            if int.from_bytes(before,"little")&1:continue
            data=ctypes.string_at(self.address,payload_size)
            if before==ctypes.string_at(self.address+12,4):return data
        return None

    def write(self,header,pixels=b""):
        if not self.writer or len(header)+len(pixels)>self.size:raise ValueError("Invalid owned write")
        with self.lock:
            seq=ctypes.cast(self.address+12,ctypes.POINTER(ctypes.c_long))
            self.kernel.InterlockedIncrement(seq)
            ctypes.memmove(self.address,header[:12],12)
            ctypes.memmove(self.address+16,header[16:],len(header)-16)
            if pixels:ctypes.memmove(self.address+len(header),pixels,len(pixels))
            self.kernel.InterlockedIncrement(seq)

    def close(self):
        if self.address:
            self.kernel.UnmapViewOfFile(self.address);self.address=None
            self.kernel.CloseHandle(self.handle);self.handle=None


class PoseMap:
    def __init__(self):self.mapping=None;self.lock=threading.RLock()
    def start(self):
        with self.lock:
            if self.mapping is None:self.mapping=WindowsMap(POSE_NAME,POSE_SIZE,writer=True)
    def publish(self,q,seq,connected,paused):
        with self.lock:
            if self.mapping is None:return
            valid=q is not None and connected and not paused
            values=q if valid else (0.,0.,0.,1.)
            flags=int(connected) | (2 if valid else 0) | (4 if paused else 0)
            header=POSE.pack(b"VRP1",1,128,0,tick_ms(),max(0,seq),*values,0.,1.6,0.,flags,bytes(36))
            self.mapping.write(header)
    def close(self):
        with self.lock:
            if self.mapping:
                self.publish(None,0,False,True);self.mapping.close();self.mapping=None


class StopEvent:
    """One manual-reset event owned by one helper invocation."""
    def __init__(self):
        if os.name!="nt":raise OSError("Native helpers require Windows")
        self.name="Local\\VRizationStop-"+uuid.uuid4().hex
        self.kernel=ctypes.WinDLL("kernel32",use_last_error=True)
        self.kernel.CreateEventW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.BOOL,wintypes.LPCWSTR]
        self.kernel.CreateEventW.restype=wintypes.HANDLE
        self.kernel.SetEvent.argtypes=[wintypes.HANDLE]
        self.kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        self.handle=self.kernel.CreateEventW(None,True,False,self.name)
        if not self.handle:raise ctypes.WinError(ctypes.get_last_error())
    def signal(self):
        if self.handle:self.kernel.SetEvent(self.handle)
    def close(self):
        if self.handle:self.kernel.CloseHandle(self.handle);self.handle=None


class FrameReader:
    def __init__(self,name,*,stereo=False):self.name=name;self.stereo=stereo;self.mapping=None
    def read(self):
        if self.mapping is None:
            try:self.mapping=WindowsMap(self.name,FRAME_SIZE)
            except OSError:return None
        for _ in range(4):
            header=self.mapping.snapshot(64)
            if header is None:continue
            fields=FRAME.unpack(header);width,height,stride=fields[4:7]
            if not 1<=width<=1920 or not 1<=height<=1080 or stride!=width*4:
                return decode_frame(header,b"",tick_ms(),stereo=self.stereo)
            data=self.mapping.snapshot(64+stride*height)
            if data is None or data[:64]!=header:continue
            return decode_frame(data[:64],data[64:],tick_ms(),stereo=self.stereo)
        return None
    def close(self):
        if self.mapping:self.mapping.close();self.mapping=None


class FrameWriter:
    def __init__(self,name):self.mapping=WindowsMap(name,FRAME_SIZE,writer=True)
    def publish(self,width,height,pixels):
        header=FRAME.pack(b"VRF1",1,64,0,width,height,width*4,1,tick_ms(),bytes(24))
        decode_frame(header,pixels,tick_ms())
        self.mapping.write(header,pixels)
    def close(self):
        if self.mapping:
            self.mapping.write(FRAME.pack(b"VRF1",1,64,0,0,0,0,0,tick_ms(),bytes(24)))
            self.mapping.close();self.mapping=None

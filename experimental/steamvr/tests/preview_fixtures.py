"""Original synthetic fixtures: no desktop capture, mouse, native driver or USB."""
import asyncio
from io import BytesIO
import json
import socket
import threading
import time

from aiohttp import WSMsgType
from PIL import Image
from vrization_host.capture import Frame


CAPS = ["enhanced-first-person", "stereo-sbs", "hmd-orientation"]


class SyntheticStereoSource:
    def __init__(self):
        image = Image.new("RGB", (128, 64), (220, 30, 10))
        image.paste((10, 30, 220), (64, 0, 128, 64))
        output = BytesIO()
        image.save(output, "JPEG", quality=90, subsampling=0)
        self.jpeg = output.getvalue()
        self.reads = 0
        self.closes = 0

    def read(self, config):
        self.reads += 1
        return Frame(self.jpeg, 128, 64, time.perf_counter())

    def close(self):
        self.closes += 1


class RecordingPoseSink:
    def __init__(self):
        self.lock = threading.Lock()
        self.records = []
        self.starts = self.closes = 0

    def start(self):
        self.starts += 1

    def publish(self, q, seq, connected, paused):
        with self.lock:
            self.records.append((q, seq, connected, paused))

    def close(self):
        self.closes += 1

    def snapshot(self):
        with self.lock:
            return list(self.records)

    @property
    def last(self):
        return self.snapshot()[-1]


class RecordingMouse:
    def __init__(self):
        self.moves = []

    def move(self, dx, dy):
        self.moves.append((dx, dy))


def packet(epoch=1, seq=1, q=(0, 0, 0, 1), *, valid=True, time_us=None):
    result = {"v": 1, "type": "hmdPose", "epoch": epoch, "seq": seq,
              "timeUs": seq * 1000 if time_us is None else time_us, "trackingValid": valid}
    if q is not None:
        result["q"] = list(q)
    return result


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def next_json(ws, kind, predicate=lambda value: True, timeout=4):
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            raise AssertionError("Missing JSON " + kind)
        msg = await asyncio.wait_for(ws.receive(), remaining)
        if msg.type == WSMsgType.TEXT:
            value = json.loads(msg.data)
            if value.get("type") == kind and predicate(value):
                return value
        elif msg.type != WSMsgType.BINARY:
            raise AssertionError("Socket ended before JSON " + kind + ": " + str(msg.type))


async def next_binary(ws, timeout=4):
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        msg = await asyncio.wait_for(ws.receive(), max(0, deadline - asyncio.get_running_loop().time()))
        if msg.type == WSMsgType.BINARY:
            return msg.data
        if msg.type != WSMsgType.TEXT:
            raise AssertionError("Socket ended before video: " + str(msg.type))


async def barrier(ws):
    await ws.send_json({"v": 1, "type": "ping"})
    await next_json(ws, "pong")


async def negotiate(ws):
    await ws.send_json({"v": 1, "type": "hello", "client": "synthetic-test", "settingsSchema": 2,
                        "capabilities": CAPS})
    return await next_json(ws, "settings", lambda msg: msg["streamSession"]["accepted"])

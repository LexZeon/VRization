"""CPU pixel fixtures and synthetic loopback protocol; no native/device evidence."""
import asyncio
from contextlib import redirect_stdout
from io import BytesIO, StringIO
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
import zipfile

from aiohttp import ClientSession, WSMsgType
from PIL import Image
import build_ios_steamvr as build
from ios_steamvr_test_host import StereoCard


class StereoPixelOracleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="steamvr-checker-cpu-")
        self.output = Path(self.temporary.name)
        self.previous = build.OUT; build.OUT = self.output
        self.shots = self.output / "screenshots"; self.shots.mkdir()
        self.source = Image.open(BytesIO(StereoCard().jpeg)).convert("RGB")
        self.profile = {"scale": .85, "offsetX": 0, "offsetY": .12, "eyeSeparation": 0}
        self.saved = {**self.profile, "scale": .72}
        self.report = {"checkpoints": [
            {"name": name, "settings": settings}
            for name, settings in (("steamvr-lan-connected", self.profile),
                                    ("steamvr-editor-saved", self.saved),
                                    ("steamvr-usb-connected", self.profile),
                                    ("steamvr-lan-refreshed", self.saved),
                                    ("steamvr-usb-refreshed", self.profile))]}
    def tearDown(self):
        build.OUT = self.previous; self.temporary.cleanup()

    def render(self, profile, defect=None):
        # Independent rectangular compositing, not a copy of the inverse
        # screen-point oracle. Distinct eye crops come from the original JPEG.
        canvas = Image.new("RGB", (1400, 700))
        for eye in (0, 1):
            source_eye = 1-eye if defect == "swapped-eyes" else 0 if defect == "duplicated-left" else eye
            crop = self.source.crop((source_eye*640, 0, (source_eye+1)*640, 480))
            aspect = 1280/480 if defect == "packed-aspect" else 1 if defect == "square-projection" else 640/480
            max_width, max_height = 700*profile["scale"], 700*profile["scale"]
            width = round(min(max_width, max_height*aspect)); height = round(width/aspect)
            resized = crop.resize((width, height), Image.Resampling.BILINEAR)
            if defect == "second-warp":
                warped = Image.new("RGB", resized.size)
                original = resized.load(); pixels = warped.load()
                import math
                angle = math.radians(80)/2
                for y in range(height):
                    for x in range(width):
                        qx, qy = 2*(x+.5)/width-1, 2*(y+.5)/height-1
                        r = math.hypot(qx,qy)
                        factor = math.tan(r*angle)/(r*math.tan(angle)) if r else 1
                        sx, sy = (qx*factor+1)*width/2, (qy*factor+1)*height/2
                        if 0 <= sx < width and 0 <= sy < height: pixels[x,y] = original[int(sx),int(sy)]
                resized = warped
            cx = eye*700+350+profile["offsetX"]*350+(2*eye-1)*profile["eyeSeparation"]*350
            cy = 350-profile["offsetY"]*350
            canvas.paste(resized, (round(cx-width/2),round(cy-height/2)))
        return canvas

    def exports(self, defect=None):
        # Names match the export lookup; files stay inside a temporary CPU-only
        # directory and can never replace actual xcresult attachments.
        phases = (("STEAMVR-01-LAN-enhanced-independent-eyes", self.profile),
                  ("STEAMVR-02-LAN-cinema-independent-eyes", self.profile),
                  ("STEAMVR-03-SBS-editor-half-aspect", self.profile),
                  ("STEAMVR-04-SBS-saved-profile", self.saved),
                  ("STEAMVR-05-disconnected-clears-Metal", None),
                  ("STEAMVR-06-USB-independent-eyes", self.profile),
                  ("STEAMVR-07-USB-disconnected-clears-Metal", None),
                  ("STEAMVR-08-LAN-refreshed-independent-eyes", self.saved),
                  ("STEAMVR-09-USB-refreshed-independent-eyes", self.profile))
        attachments = []
        for index, (name, profile) in enumerate(phases):
            image = self.render(profile, defect) if profile else Image.new("RGB", (1400,700))
            filename = f"CPU-checker-fixture-{index}.png"; image.save(self.shots/filename)
            attachments.append({"suggestedHumanReadableName":name+"_CPU-only", "exportedFileName":filename})
        (self.shots/"manifest.json").write_text(json.dumps([{"attachments":attachments}]),encoding="utf-8")

    def testCorrectIndependentRectangularEyesAndRefreshPassSeventySamples(self):
        self.exports()
        with redirect_stdout(StringIO()): build.check_stereo_pixels(self.report)
        report = json.loads((self.shots/"stereo-check.json").read_text())
        self.assertEqual(len(report["samples"]), 70); self.assertEqual(report["failures"], [])

    def testEyeDuplicationSwapAspectSquareAndSecondWarpAreRejected(self):
        for defect in ("duplicated-left", "swapped-eyes", "packed-aspect", "square-projection", "second-warp"):
            with self.subTest(defect=defect):
                self.exports(defect)
                with redirect_stdout(StringIO()), self.assertRaises(AssertionError): build.check_stereo_pixels(self.report)
                self.assertTrue(json.loads((self.shots/"stereo-check.json").read_text())["failures"])

    def testSourcePackagePreservesGuideAndLocalLicenseLinks(self):
        # Exercise packaging with an explicitly synthetic app placeholder.
        # This is archive validation, never a Simulator build claim.
        app = self.output/"simulator/Build/Products/Debug-iphonesimulator/VRizationSteamVRApp.app"
        app.mkdir(parents=True); (app/"checker-test-placeholder.txt").write_text("CPU packaging fixture")
        with redirect_stdout(StringIO()): build.package_simulator()
        with zipfile.ZipFile(self.output/"VRization-SteamVR-iOS-source.zip") as archive:
            names = set(archive.namelist())
            for required in ("ios/VRizationSteamVR.xcodeproj/project.pbxproj", "ios/SteamVR/Package.swift",
                             "experimental/steamvr/docs/IOS.md", "experimental/steamvr/native/README.md",
                             "experimental/steamvr/native/licenses/README.md",
                             "experimental/steamvr/native/licenses/OpenVR-LICENSE.txt", "LICENSE"):
                self.assertIn(required,names)
            self.assertFalse(any(".build/" in name or name.endswith((".dll",".exe")) for name in names))


class LiveRefreshFixtureTests(unittest.IsolatedAsyncioTestCase):
    async def testActualFixtureRecordsCompletedRefreshWhileKeepingEpochSettingsAndPause(self):
        # Launch the actual fixture with its synthetic pixels/pose sink/usbmux.
        # The client is a loopback WebSocket, never a physical phone or OS input.
        def free_port():
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0)); return probe.getsockname()[1]
        port, observation = free_port(), free_port()
        while observation == port: observation = free_port()
        with tempfile.TemporaryDirectory(prefix="ios-refresh-event-regression-") as temporary:
            process = subprocess.Popen([sys.executable, "-X", "utf8", str(build.ROOT / "scripts/ios_steamvr_test_host.py"),
                "--port", str(port), "--control-port", str(observation), "--report", str(Path(temporary) / "host.json")],
                cwd=build.ROOT, env=os.environ.copy(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            try:
                async with ClientSession(trust_env=False) as client:
                    async def snapshot(path="snapshot", post=False):
                        operation = client.post if post else client.get
                        async with operation(f"http://127.0.0.1:{observation}/{path}") as response:
                            self.assertEqual(response.status, 200); return await response.json()
                    deadline = asyncio.get_running_loop().time() + 10
                    while True:
                        if process.poll() is not None:
                            self.fail("Synthetic fixture exited: " + process.communicate()[0].decode("utf-8", errors="replace"))
                        try:
                            if (await snapshot())["fixtureReady"]: break
                        except OSError: pass
                        self.assertLess(asyncio.get_running_loop().time(), deadline)
                        await asyncio.sleep(.025)
                    async with client.ws_connect(f"http://127.0.0.1:{port}/ws?token=123456") as ws:
                        hello = await ws.receive_json(timeout=3)
                        self.assertEqual(hello["type"], "hello")
                        self.assertIn("video-refresh", hello["capabilities"])
                        await ws.send_json({"v": 1, "type": "hello", "settingsSchema": 2,
                            "capabilities": ["enhanced-first-person", "stereo-sbs", "hmd-orientation", "video-refresh"]})
                        while True:
                            message = await ws.receive(timeout=3)
                            self.assertIn(message.type, (WSMsgType.TEXT, WSMsgType.BINARY))
                            if message.type == WSMsgType.TEXT:
                                full = json.loads(message.data)
                                if full.get("type") == "settings" and full["streamSession"]["accepted"]: break
                        before = await snapshot("pause-tracking", post=True)
                        self.assertTrue(before["connected"]); self.assertTrue(before["paused"])
                        self.assertEqual(before["videoRefreshes"], [])
                        for request_id in (1, 2):
                            await ws.send_json({"v": 1, "type": "refreshVideo", "epoch": before["epoch"], "requestId": request_id})
                            while True:
                                message = await ws.receive(timeout=3)
                                self.assertIn(message.type, (WSMsgType.TEXT, WSMsgType.BINARY))
                                if message.type == WSMsgType.TEXT:
                                    acknowledgement = json.loads(message.data)
                                    if acknowledgement.get("type") == "videoRefresh": break
                            self.assertEqual(acknowledgement, {"v": 1, "type": "videoRefresh", "epoch": before["epoch"],
                                "requestId": request_id, "paused": True})
                            deadline = asyncio.get_running_loop().time() + 3
                            while True:
                                after = await snapshot()
                                if len(after["videoRefreshes"]) == request_id: break
                                self.assertLess(asyncio.get_running_loop().time(), deadline)
                                await asyncio.sleep(.025)
                            self.assertEqual(after["videoRefreshes"][-1]["requestId"], request_id)
                            self.assertEqual(after["videoRefreshes"][-1]["epoch"], before["epoch"])
                            self.assertIs(after["videoRefreshes"][-1]["paused"], True)
                            self.assertTrue(after["connected"]); self.assertTrue(after["paused"])
                            self.assertEqual(after["epoch"], before["epoch"])
                            self.assertEqual(after["settings"], before["settings"])
                            self.assertEqual(after["mouseMoves"], [])
                            self.assertTrue(all(pose["q"] is None for pose in after["poses"]))
                            while (await ws.receive(timeout=3)).type != WSMsgType.BINARY: pass
            finally:
                if process.poll() is None: process.terminate()
                try: process.communicate(timeout=8)
                except subprocess.TimeoutExpired: process.kill(); process.communicate(timeout=3)


if __name__ == "__main__": unittest.main()

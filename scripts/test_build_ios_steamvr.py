"""Checker-only CPU fixtures, never native screenshots or device evidence."""
from contextlib import redirect_stdout
from io import BytesIO, StringIO
import json
from pathlib import Path
import tempfile
import unittest

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
                                    ("steamvr-usb-connected", self.profile))]}
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
                  ("STEAMVR-07-USB-disconnected-clears-Metal", None))
        attachments = []
        for index, (name, profile) in enumerate(phases):
            image = self.render(profile, defect) if profile else Image.new("RGB", (1400,700))
            filename = f"CPU-checker-fixture-{index}.png"; image.save(self.shots/filename)
            attachments.append({"suggestedHumanReadableName":name+"_CPU-only", "exportedFileName":filename})
        (self.shots/"manifest.json").write_text(json.dumps([{"attachments":attachments}]),encoding="utf-8")

    def testCorrectIndependentRectangularEyesPassFiftySamples(self):
        self.exports()
        with redirect_stdout(StringIO()): build.check_stereo_pixels(self.report)
        report = json.loads((self.shots/"stereo-check.json").read_text())
        self.assertEqual(len(report["samples"]), 50); self.assertEqual(report["failures"], [])

    def testEyeDuplicationSwapAspectSquareAndSecondWarpAreRejected(self):
        for defect in ("duplicated-left", "swapped-eyes", "packed-aspect", "square-projection", "second-warp"):
            with self.subTest(defect=defect):
                self.exports(defect)
                with redirect_stdout(StringIO()), self.assertRaises(AssertionError): build.check_stereo_pixels(self.report)
                self.assertTrue(json.loads((self.shots/"stereo-check.json").read_text())["failures"])


if __name__ == "__main__": unittest.main()

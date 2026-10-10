"""Build/test the separate unsigned iOS SteamVR preview; never register a driver."""
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import re
from statistics import median
import subprocess
import sys
import time
from urllib.request import ProxyHandler, build_opener
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/ios-steamvr"
spec = importlib.util.spec_from_file_location("stable_ios_build_helpers", ROOT / "scripts/build_ios.py")
helpers = importlib.util.module_from_spec(spec); spec.loader.exec_module(helpers)
opener = build_opener(ProxyHandler({}))


def run(*args, **kwargs):
    print("+ " + " ".join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), cwd=ROOT, check=True, **kwargs)


def wait_fixture(process, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None: raise RuntimeError("Preview fixture exited before readiness")
        try:
            with opener.open("http://127.0.0.1:18785/health", timeout=1) as response: health = json.loads(response.read(8192))
            with opener.open("http://127.0.0.1:18789/snapshot", timeout=1) as response: snapshot = json.loads(response.read(8192))
            if health.get("running") is True and snapshot.get("fixtureReady") is True: return
        except (OSError, ValueError): pass
        time.sleep(.5)
    raise RuntimeError("Preview fixture readiness deadline exceeded")


def check_stereo_pixels(report):
    from PIL import Image, ImageOps
    shots = OUT / "screenshots"
    manifest = json.loads((shots / "manifest.json").read_text(encoding="utf-8"))
    attachments = [item for group in manifest for item in group["attachments"]]
    checkpoints = {item["name"]: item for item in report["checkpoints"]}
    def image_named(name):
        matches = [item for item in attachments if item["suggestedHumanReadableName"].startswith(name + "_")]
        assert len(matches) == 1, f"Expected one native screenshot for {name}"
        with Image.open(shots / matches[0]["exportedFileName"]) as image:
            return ImageOps.exif_transpose(image).convert("RGB")
    records, failures = [], []
    phases = (("STEAMVR-01-LAN-enhanced-independent-eyes", "steamvr-lan-connected"),
              ("STEAMVR-02-LAN-cinema-independent-eyes", "steamvr-lan-connected"),
              ("STEAMVR-04-SBS-saved-profile", "steamvr-editor-saved"),
              ("STEAMVR-06-USB-independent-eyes", "steamvr-usb-connected"))
    for name, checkpoint in phases:
        image = image_named(name); settings = checkpoints[checkpoint]["settings"]
        width, height = image.size; assert width > height
        for eye in (0, 1):
            ew = width // 2 if eye == 0 else width - width // 2
            origin, sign = (0, -1) if eye == 0 else (width // 2, 1)
            fx, fy = min(1, (640/480)/(ew/height)), min(1, (ew/height)/(640/480))
            scale = settings["scale"]
            sep = max(fx*scale-1, settings["eyeSeparation"])
            ox = min(max(settings["offsetX"], -(1+sep-fx*scale)), 1+sep-fx*scale)
            # Shared HeadsetFit bounds horizontal offset at the seam; vertical
            # placement retains its validated profile value and may be clipped.
            oy = settings["offsetY"]
            def point(u, v):
                return (round(origin+ew*(.5+((2*u-1)*fx*scale+ox+sign*sep)/2)),
                        round(height*(.5-((1-2*v)*fy*scale+oy)/2)))
            expected = ((196,35,53),(34,155,74)) if eye == 0 else ((31,83,196),(214,170,34))
            for (u, v), color in zip(((.25,.25),(.75,.75)), expected):
                x,y = point(u,v)
                pixels = [image.getpixel((x+dx,y+dy)) for dx in (-1,0,1) for dy in (-1,0,1)]
                actual = [round(median(pixel[c] for pixel in pixels)) for c in range(3)]
                records.append({"kind":"eye-color","screenshot":name,"eye":eye,"sourceUV":[u,v],"screenXY":[x,y],"actualRGB":actual,"expectedRGB":color})
                if max(abs(a-b) for a,b in zip(actual,color)) > 12: failures.append(f"{name}: eye {eye} wrong color/source")
            # Straight border locations also require half-image aspect and
            # bypass both Cinema and enhanced angular projection on SBS.
            for uv in ((13.5/640,.2),(625.5/640,.8)):
                x,y = point(*uv)
                count = sum(min(rgb)>180 and max(rgb)-min(rgb)<25
                            for rgb in (image.getpixel((x+dx,y+dy)) for dx in range(-3,4) for dy in range(-3,4)))
                records.append({"kind":"straight-border","screenshot":name,"eye":eye,"sourceUV":uv,"screenXY":[x,y],"whitePixels":count})
                if count < 2: failures.append(f"{name}: eye {eye} aspect or projection changed straight border")
            x,y = point(.5,-.06); actual = image.getpixel((x,y))
            records.append({"kind":"outside-mask","screenshot":name,"eye":eye,"screenXY":[x,y],"actualRGB":actual})
            if max(actual)>5: failures.append(f"{name}: eye {eye} outside content is not black")
    for name in ("STEAMVR-05-disconnected-clears-Metal", "STEAMVR-07-USB-disconnected-clears-Metal"):
        image = image_named(name)
        for u,v in ((.25,.25),(.75,.25),(.25,.75),(.75,.75),(.5,.5)):
            xy=(round(image.width*u),round(image.height*v)); actual=image.getpixel(xy)
            records.append({"kind":"disconnected-black","screenshot":name,"screenXY":xy,"actualRGB":actual})
            if max(actual)>5: failures.append(f"{name}: disconnected surface retains pixels")
    (shots/"stereo-check.json").write_text(json.dumps({"samples":records,"failures":failures},indent=2),encoding="utf-8")
    assert not failures, "; ".join(failures)
    print(f"{len(records)} native SBS/color/aspect/projection/disconnect checks passed.",flush=True)


def package_simulator():
    app = OUT / "simulator/Build/Products/Debug-iphonesimulator/VRizationSteamVRApp.app"
    assert app.is_dir()
    archive = OUT / "VRization-SteamVR-iOS-Simulator.zip"
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as target:
        for path in sorted(app.rglob("*")):
            if path.is_file(): target.write(path,path.relative_to(app.parent))
    source = OUT / "VRization-SteamVR-iOS-source.zip"
    with zipfile.ZipFile(source,"w",zipfile.ZIP_DEFLATED) as target:
        for path in sorted((ROOT/"ios").rglob("*")):
            if path.is_file() and not any(part in {".build",".swiftpm","DerivedData","xcuserdata"} for part in path.parts):
                target.write(path,path.relative_to(ROOT))
        for name in ("LICENSE","CHANGELOG.md","THIRD_PARTY_NOTICES.md"):
            path=ROOT/name
            if path.is_file(): target.write(path,name)
        # Preserve the included guide's local provenance/operation links.
        for name in ("experimental/steamvr/docs/IOS.md", "experimental/steamvr/native/README.md",
                     "experimental/steamvr/native/licenses/README.md", "experimental/steamvr/native/licenses/OpenVR-LICENSE.txt"):
            guide = ROOT/name
            if guide.is_file(): target.write(guide, guide.relative_to(ROOT))
    print(f"Unsigned Simulator and source packages created: {archive.name}, {source.name}",flush=True)


def main():
    if sys.platform != "darwin": raise SystemExit("Requires macOS / Xcode; does not create a signed iPhone app.")
    OUT.mkdir(parents=True,exist_ok=True)
    if not os.environ.get("DEVELOPER_DIR"):
        candidates=[]
        for app in Path("/Applications").glob("Xcode_*.app"):
            match=re.fullmatch(r"Xcode_([0-9.]+)\.app",app.name)
            if match: candidates.append((tuple(map(int,match[1].split("."))),app))
        if candidates: os.environ["DEVELOPER_DIR"]=str(max(candidates)[1]/"Contents/Developer")
    # Make source imports deterministic even when a developer installed stable
    # VRization editable in the Python environment.
    os.environ["PYTHONPATH"] = os.pathsep.join((str(ROOT/"desktop/src"),str(ROOT/"experimental/steamvr/python")))
    run("xcodebuild","-version")
    run(sys.executable, "scripts/test_build_ios_steamvr.py")
    run("swift","test","--package-path","ios")
    run("swift","test","--package-path","ios/SteamVR")
    common=["xcodebuild","-project","ios/VRizationSteamVR.xcodeproj","-scheme","VRizationSteamVR",
            "-configuration","Debug","CODE_SIGNING_ALLOWED=NO","-quiet"]
    arch=platform.machine()
    run(*common,f"ARCHS={arch}","ONLY_ACTIVE_ARCH=YES","-destination","generic/platform=iOS Simulator","-derivedDataPath",OUT/"simulator","build")
    run(*common,"-destination","generic/platform=iOS","-derivedDataPath",OUT/"device","build")
    result=run("xcrun","simctl","list","devices","available","--json",capture_output=True,text=True)
    phones=[]
    for runtime,rows in json.loads(result.stdout)["devices"].items():
        if ".iOS-" in runtime:
            version=tuple(map(int,re.findall(r"\d+",runtime.split(".iOS-",1)[1])))
            for row in rows:
                if row.get("isAvailable") and row["name"].startswith("iPhone"):
                    phones.append((version,tuple(map(int,re.findall(r"\d+",row["name"]))) or (0,),row["name"],row["udid"]))
    if not phones: raise SystemExit("Install an iPhone Simulator runtime in Xcode Settings.")
    runtime,_,name,device=max(phones)
    (OUT/"environment.json").write_text(json.dumps({"simulator":name,"runtime":runtime,"architecture":arch,
        "developerDirectory":os.environ.get("DEVELOPER_DIR"),"physicalPhoneTested":False,"nativeDriverRegistered":False},indent=2),encoding="utf-8")
    run("xcrun","simctl","bootstatus",device,"-b",timeout=180)
    simulator_app=Path(os.environ["DEVELOPER_DIR"])/"Applications/Simulator.app"
    run("open","-a",simulator_app,"--args","-CurrentDeviceUDID",device,timeout=30)
    with (OUT/"fixture.log").open("w",encoding="utf-8") as output:
        fixture=subprocess.Popen([sys.executable,"-u",str(ROOT/"scripts/ios_steamvr_test_host.py"),"--report",str(OUT/"host-report.json")],
                                 cwd=ROOT,stdout=output,stderr=subprocess.STDOUT)
        try:
            wait_fixture(fixture)
            helpers.run_with_deadline(*common,f"ARCHS={arch}","ONLY_ACTIVE_ARCH=YES","-destination",f"platform=iOS Simulator,id={device},arch={arch}",
                "-derivedDataPath",OUT/"simulator","-parallel-testing-enabled","NO","-test-timeouts-enabled","YES",
                "-default-test-execution-time-allowance","180","-maximum-test-execution-time-allowance","180",
                "-destination-timeout","120","-resultBundlePath",OUT/"UI.xcresult","test",timeout=1200)
        finally:
            fixture.terminate()
            try: fixture.wait(timeout=15)
            except subprocess.TimeoutExpired: fixture.kill(); fixture.wait()
            helpers.OUT=OUT; helpers.export_ui_report()
            print((OUT/"fixture.log").read_text(encoding="utf-8",errors="replace")[-12288:],flush=True)
    report=json.loads((OUT/"host-report.json").read_text(encoding="utf-8"))
    assert not report["mouseMoves"] and not report["nativeDriverRegistered"] and not report["physicalPhoneTested"]
    assert all(record["q"] is None for record in report["poses"]), "No sensor must produce invalid tracking, never fake a quaternion"
    assert any(record["seq"]>0 and record["connected"] for record in report["poses"]), "Native phone did not report invalid tracking"
    checkpoints={item["name"]:item for item in report["checkpoints"]}
    for name in ("steamvr-lan-connected","steamvr-editor-saved","steamvr-usb-connected"):
        assert checkpoints[name]["connected"] and not checkpoints[name]["mouseMoves"]
    for name in ("steamvr-lan-disconnected","steamvr-usb-disconnected"):
        assert not checkpoints[name]["connected"]
    check_stereo_pixels(report)
    package_simulator()


if __name__ == "__main__": main()

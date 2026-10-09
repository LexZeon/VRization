# 🥽 VRization

**Put your PC screen inside a phone VR viewer.**

[简体中文](README.md) · [Quick start (Chinese)](docs/QUICKSTART.zh-CN.md) · [Build](docs/BUILD.md) · [Architecture](docs/ARCHITECTURE.md)

VRization streams a Windows desktop or rectangular region to an Android phone, renders the image side by side, and optionally maps phone rotation to PC mouse movement. Its reusable Android library (written in Java) and separated host components provide a starting point for embedding these features in other applications.

**v0.1.0-alpha is a working baseline.** CPU JPEG over WebSocket is intended to establish the capture, viewing, settings and input paths. It does not promise production VR latency. Both eyes receive the same 2D source: ordinary games do not acquire stereoscopic depth.

| Mode | Behavior |
| --- | --- |
| 🖥️ Full screen | A fixed image in each eye; no sensor control. |
| 🎬 Cinema | A virtual screen viewed through phone rotation. |
| 🎯 FPS | Side-by-side viewing plus rotation-to-mouse input, explicitly armed on the PC. Press **F8** to stop input. |

Adjust image scale and offsets for large phones, eye separation, field of view, screen distance, distortion, recentering, mouse sensitivity and vertical inversion. The host also offers display / region selection and stream quality controls.

## 📸 Interface

| Windows host | Android client |
| --- | --- |
| ![Running Windows host](docs/images/desktop.png) | ![Running Android client](docs/images/android.png) |

Phone screenshots use a Google-free Android 6.0 / API 23 emulator receiving the project's original [animated calibration card](examples/embedded_host.py). They document connection and rendering, not physical headset compatibility or latency / performance benchmarks.

## 🚀 Try it

1. Download the Windows archive and Android APK from [Releases](https://github.com/LexZeon/VRization/releases), or [build from source](docs/BUILD.md).
2. Connect both devices to the same trusted LAN. Prefer wired Ethernet for the PC and a strong Wi-Fi connection for the phone.
3. Start the host, choose a display or region, and start streaming. Allow the Windows firewall prompt only for a trusted private network.
4. Enter the host's displayed IP address, port and pairing code on the phone. Start in full-screen mode.
5. Adjust the image to your viewer, recenter cinema mode, and explicitly arm PC mouse input before trying FPS mode.

Windows 10 / 11 x64 is the desktop target. Android 6.0+ and compatible derivatives need no Google services; derivative-system compatibility depends on their APK, rendering and sensor support. Full-screen viewing does not require a gyroscope. Games may reject simulated mouse input, especially under raw-input or anti-cheat restrictions.

The host requires Microsoft Visual C++ v14 x64 runtime. If launch reports a missing `VCRUNTIME140` DLL or error 126, use [Microsoft's official runtime guide](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist/) and [current x64 installer](https://aka.ms/vc14/vc_redist.x64.exe).

## 🧩 Reuse and limitations

See [architecture](docs/ARCHITECTURE.md) and [protocol v1](docs/PROTOCOL.md) for integration. The current deliverable is source-level modules, not a stable public SDK, Unity / Unreal plug-in or OpenXR driver.

Audio, hardware video encoding, WebRTC, dedicated USB transport, native stereo game rendering and 6DoF position tracking are not included. Real-world performance and device support require testing on your hardware.

See the [validation record (Chinese)](docs/VALIDATION.md) for the 12 host checks, 6 Android core checks, Windows capture and API 23 emulator observations. Physical gyro behavior, headset optics and actual FPS game input remain unverified.

Transport uses **unencrypted `ws://`**. The pairing code is an access gate, not encryption. Use trusted LANs only; do not expose the port to the internet. See [security](SECURITY.md).

## 🤝 License and credit

Original code is [MIT](LICENSE), including commercial use subject to its notice requirements. Dependencies retain their licenses. See [third-party notices](THIRD_PARTY_NOTICES.md), [NOTICE](NOTICE) and [contributing](CONTRIBUTING.md). No implementation source was copied from another VR application.

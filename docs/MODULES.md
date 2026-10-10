# 🗂️ Module catalogue / 模块目录

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

This catalogue maps every maintained production Python file under `desktop/src/vrization_host`, Android app/core Java file, Swift core file, and iOS app Swift/Metal file to its responsibility, important entry points and reuse boundary. Tests, generated files and build output are excluded from those source tables. Release tools, test-support scripts and primary platform resources are listed separately. Entries describe the current source tree; platform build and physical-device evidence belong in [Validation](VALIDATION.md) and [Compatibility](COMPATIBILITY.md).

### Integration boundaries

Use `HostServer` with a replacement `CaptureSource` and `InputSink` to stream another image source or direct poses into a game camera. The Android AAR combines pure Java settings/geometry/connection policy with Android sensor and GLES adapters. The Swift package `VRizationCore` uses Foundation and leaves UIKit, Network, Core Motion and Metal in app adapters. These are practical seams for reuse; app assembly classes still own their platform lifecycle. The current video is a desktop image displayed for both eyes. A game's native stereo rendering needs a separate image-source/render integration.

Connection control and video have separate lifetimes. Android phone-side USB control uses loopback port 18764; video uses 18765, reversed to the desktop video service on 8765. A fresh phone Connect performs one control request; automatic discovery and PC-originated Connect do not repeatedly wake a stopped PC. The iOS paired-device control listener uses 18767, while its framed video listener uses 18766. Local Stop/Disconnect cancels pending work and releases owned resources; a new explicit action is required for a new request. See [USB](USB.md), [Protocol](PROTOCOL.md) and [Architecture](ARCHITECTURE.md) for their contracts.

### Windows host

Directory: `desktop/src/vrization_host/`

| Source file | Responsibility | Important entries | Reuse boundary |
| --- | --- | --- | --- |
| `desktop/src/vrization_host/__init__.py` | Lazy package exports for the embeddable host; avoids loading capture/input for diagnostics. | `HostServer`, `CaptureSource`, `InputSink`, `Settings`, `__version__` | Use this public import surface with replacement capture and input adapters. |
| `desktop/src/vrization_host/__main__.py` | Selects the GUI or the read-only USB diagnostic command. | `main()`, `--usb-diagnostics` | Process entry adapter; keep independent of the embedding API. |
| `desktop/src/vrization_host/_version.py` | One host version value used by the package and control panel. | `__version__` | Release metadata; update together with platform package versions. |
| `desktop/src/vrization_host/capture.py` | Capture contracts, output sizing and a worker with bounded latest-frame handoff; MSS fallback. | `CaptureConfig`, `Frame`, `CaptureSource.read()/close()`, `MssCaptureSource`, `CaptureWorker`, `LatestFrameBuffer` | Implement `CaptureSource` for a game texture or another platform; return owned image data and close resources. |
| `desktop/src/vrization_host/connection.py` | Coalesces explicit Connect requests and serves a separate loopback USB control endpoint. | `ConnectionCoordinator.request()/accept()/complete()/cancel()`, `UsbConnectService`, `trusted_usb_request()` | Inject an event queue and running/stopping predicates; it never accesses widgets or input permission. |
| `desktop/src/vrization_host/gui.py` | Tk control panel wiring: capture selection, profiles, Connect/Stop, USB status, editor and local gyro preference/pause/resume. | `HostWindow.start()/stop()/close()`, `configure_dpi_awareness()`, `main()` | Replace the UI while retaining host, coordinator, USB manager and settings contracts. |
| `desktop/src/vrization_host/i18n.py` | English-first translation lookup and local language preference. | `translate()`, `load_language()`, `save_language()` | Desktop text catalogue; other front ends can supply their own presentation layer. |
| `desktop/src/vrization_host/input.py` | Pose-to-relative-input conversion, manual/automatic policy, freshness checks and latched emergency pause. Automatic policy controls every foreground window; legacy manual focus checks remain. | `InputSink.move()`, `WindowsMouseSink`, `PoseController.pose()/tick()/recenter()/arm()/disarm()/configure_auto_control()/resume_control()`, `EmergencyHotkey` | Replace `InputSink` with a game-camera adapter; keep validated sessions, local policy and pause-latch gates. |
| `desktop/src/vrization_host/ios_usb.py` | Paired iOS Connect/Stop control and framed video/control relay; validates readiness before host start and awaits Stop acknowledgment. | `request_ios_connect()/request_ios_stop()`, `validate_ios_connect()`, `IosRelay.start()/stop()/request_stop()` | Inject the paired-device multiplexer and start callback; transport has no UI ownership. |
| `desktop/src/vrization_host/pose_filter.py` | Original speed-adaptive smoothing of accepted angular increments; strength zero bypasses smoothing. | `PoseStabilizer.configure()/reset()/discard_lag()/step()` | Dependency-free math; preserve angle/time units and reset at session/control transitions. |
| `desktop/src/vrization_host/profiles.py` | Named capture presets and initial capture defaults; preset targets are not measured latency. | `apply_profile()`, `capture_profile()`, `initial_capture()` | Policy values can be reused with a different UI or capture adapter. |
| `desktop/src/vrization_host/protocol.py` | Versioned JSON settings/control validation and pairing-attempt limiting. | `Settings.to_dict()/update()`, `parse_message()`, `ProtocolError`, `TokenLimiter` | Wire contract independent of desktop rendering; match the phone codecs when extending it. |
| `desktop/src/vrization_host/server.py` | Authenticated single-headset WebSocket service, USB bootstrap, frame sending and input watchdog. | `HostServer.make_app()/start()/stop()/request_stop()`, `update_settings()`, `arm()/disarm()/recenter()/set_auto_control()/resume_control()/get_control_state()` | Embed `HostServer` with capture/input adapters and status callbacks; keep capture explicit, with local input policy and latched PC Resume. |
| `desktop/src/vrization_host/storage.py` | Local non-secret host/capture/USB preferences and separately saved default-enabled gyro preference (`input.json`); excludes pairing codes, live armed state and pause latch. | `default_preferences()`, `load_preferences()/save_preferences()`, `load_usb_preferences()/save_usb_preferences()`, `load_input_preferences()/save_input_preferences()` | Swap the storage adapter while retaining validated value defaults and secret exclusions. |
| `desktop/src/vrization_host/usb.py` | Authorized Android discovery/reverse mappings and paired Apple multiplexer access; owns device transport lifetimes. | `UsbManager.start()/scan()/request_connect()/cancel_connect()/stop()`, `AdbReverse`, `AppleMux`, `WindowsUsbPresence`, `pack_frame()/read_frame()` | Device adapter boundary: inject ADB/mux/presence implementations; do not make the UI own subprocesses or sockets. |
| `desktop/src/vrization_host/usb_diagnostics.py` | Redacted read-only USB report for source and frozen executable entry points. | `collect_usb_diagnostics()`, `main()` | Reuse troubleshooting output without starting video, changing mappings or controlling input. |
| `desktop/src/vrization_host/usb_tools.py` | Validates and imports an offline official Windows Platform-Tools ZIP into a stable tools location. | `import_platform_tools()`, `default_tools_directory()`, `UsbToolsError` | Windows package-management adapter; stable error codes are translated by the UI. |
| `desktop/src/vrization_host/view_edit.py` | Pure per-eye fit geometry and save/discard draft transactions. | `fit_size()`, `resolved_fit()`, `eye_bounds()`, `dragged()`, `EditTransaction.preview()/commit()/discard()` | Reuse without Tk/network; keep normalized per-eye coordinates and committed/draft separation. |
| `desktop/src/vrization_host/view_editor.py` | Tk visual headset editor, handles, preview and save/discard callbacks. | `HeadsetEditor.begin()/move()/end()/save()/discard()/draw()` | Replace widget drawing/gestures; keep geometry and transaction rules in `view_edit.py`. |
| `desktop/src/vrization_host/windows_capture.py` | Windows monitor-layout validation and reusable GDI capture with prescaling before Python encoding. | `WindowsDisplayLayout.validate()`, `WindowsGdiCapture.grab()/close()`, `CaptureLayoutChanged` | Windows-only capture backend; adapt through `CaptureSource`, not through GUI calls. |
| `desktop/src/vrization_host/windows_gpu.py` | System DXGI/D3D11 display duplication, crop/rotation and GPU resize with owned output buffers. | `WindowsGpuCapture.grab()/close()`, `GpuScaler.render()/close()`, `validate_capture_request()`, `UnsupportedGpuCapture` | Windows-only native resource adapter; preserve thread ownership and unsupported-backend fallback rules. |

### Android application adapters

Directory: `android/app/src/main/java/org/vrization/app/`

| Source file | Responsibility | Important entries | Reuse boundary |
| --- | --- | --- | --- |
| `android/app/src/main/java/org/vrization/app/ConnectionMode.java` | USB/LAN local preference, with USB as the default. | `ConnectionMode`, `fromPreference()` | Small app policy; do not couple it to rendering. |
| `android/app/src/main/java/org/vrization/app/HeadsetEditorView.java` | Transparent Android touch overlay for mirrored movement, corner resize and safe control space. | `onDraw()`, `onTouchEvent()`, `reserveTop()` | Android View adapter; the owner handles save/discard, transport and storage. |
| `android/app/src/main/java/org/vrization/app/HeadsetTouch.java` | Maps finger deltas and selected eye/corner to core geometry operations. | `pan()`, `resize()` | Replace gesture interpretation while reusing `HeadsetGeometry`. |
| `android/app/src/main/java/org/vrization/app/HostSessionGate.java` | Accepts video only after a valid host hello; tracks advertised stabilization support. | `receive()`, `receiveJpeg()`, `isEstablished()`, `supportsStabilization()` | Protocol gate independent of UI; pair it with strict settings decoding. |
| `android/app/src/main/java/org/vrization/app/InitialUsbDetection.java` | Allows one fresh foreground automatic USB attempt; respects stopped/recreated sessions. | `onForeground()`, `stop()` | Automatic-discovery policy separate from explicit Connect. |
| `android/app/src/main/java/org/vrization/app/MainActivity.java` | Native UI and lifecycle wiring: Connect intents, local profile, editor, render/sensor adapters and installed version label. | `onCreate()/onNewIntent()/onResume()/onPause()`, `connectOrDisconnect()`, `connectFromExplicitUsbRequest()`, `startHeadsetEdit()` | Application assembly layer; embed core classes rather than copying the whole Activity into a game. |
| `android/app/src/main/java/org/vrization/app/PhoneFrameStats.java` | Constant-space, session-bound receive FPS and receive-to-texture-submission measurements. | `newSession()`, `clear()`, `decoded()`, `uploaded()` | Clock-based diagnostics; these values exclude PC and physical display latency. |
| `android/app/src/main/java/org/vrization/app/PhoneProfile.java` | Complete committed phone settings, saved-profile priority and extended-schema migration. | `snapshot()`, `commit()`, `reset()`, `waitForExtendedSnapshot()` | Keep editor drafts outside persistence and restore only after validated host capabilities. |
| `android/app/src/main/java/org/vrization/app/PingTracker.java` | One outstanding application ping and its round-trip result. | `shouldSend()`, `pong()`, `reset()` | Reuse the timing policy; RTT is distinct from video latency. |
| `android/app/src/main/java/org/vrization/app/PoseSendGate.java` | Suppresses pose output while disconnected/editing or when socket output is already queued. | `maySend()`, `setEnabled()` | Small input backpressure policy; no delayed pose replay. |
| `android/app/src/main/java/org/vrization/app/SessionDispatcher.java` | Serial connection owner with generation checks for queued callbacks and final close. | `invalidate()`, `dispatch()`, `deliverCurrent()`, `close()` | Inject an executor; preserve generation checks where callbacks reach app state. |
| `android/app/src/main/java/org/vrization/app/SettingsJson.java` | Android JSON adapter for validated local profiles and host-compatible settings payloads. | `encode()`, `encodeForHost()`, `decode()` | Replace `JSONObject` at a platform boundary; keep shared value/schema rules. |
| `android/app/src/main/java/org/vrization/app/SettingsSync.java` | Rejects stale host snapshots, reconciles revisions/client sequences and protects active gestures. | `newSession()`, `edited()`, `beginGesture()/endGesture()`, `nextSequence()`, `sent()`, `accept()` | Pure reconciliation policy; drive it from one owner thread. |
| `android/app/src/main/java/org/vrization/app/SettingsValues.java` | Strict Java map value codec, schema keys and numeric/type limits. | `encode()`, `encodeForHost()`, `decode()` | Transport-neutral app codec; preserve validation when replacing JSON. |
| `android/app/src/main/java/org/vrization/app/StreamClient.java` | OkHttp WebSocket, one-shot USB wake/bootstrap, bounded retries, cancellation and latest-only JPEG decoding. | `connect()`, `connectUsb()`, `disconnect()`, `shutdown()`, `sendSettings()`, `sendPose()`, `pauseForEditor()` | Android/OkHttp/Bitmap adapter; use core ownership/policy helpers and clear frames on disconnect. |
| `android/app/src/main/java/org/vrization/app/UsbBootstrap.java` | Strictly validates USB discovery fields and keeps video destination on the fixed loopback tunnel. | `parse()`, `ENDPOINT` | Discovery codec; never accept an arbitrary host/redirect from bootstrap JSON. |

### Reusable Android core

Directory: `android/vr-core/src/main/java/org/vrization/core/`

| Source file | Responsibility | Important entries | Reuse boundary |
| --- | --- | --- | --- |
| `android/vr-core/src/main/java/org/vrization/core/AndroidPoseSource.java` | Android rotation-vector tracking, display remapping and a relative recentered pose. | `isAvailable()`, `start()/stop()/recenter()`, `onSensorChanged()` | Android sensor adapter for `PoseSource`; replace it for engine-provided tracking. |
| `android/vr-core/src/main/java/org/vrization/core/HeadsetEdit.java` | Local draft transaction; only Save produces a changed committed value. | `draft()`, `preview()`, `update()`, `save()`, `discard()` | Pure Java; embed the transaction without network or persistence. |
| `android/vr-core/src/main/java/org/vrization/core/HeadsetGeometry.java` | Normalized per-eye fit, seam limits, mirrored panning and proportional corner resize. | `fit()`, `bounds()`, `resolveFit()`, `pan()`, `mirroredPan()`, `resize()` | Pure Java math; match coordinate units in a replacement renderer/editor. |
| `android/vr-core/src/main/java/org/vrization/core/PoseMath.java` | Angle wrapping, rotation math and relative origin sampling. | `wrap()`, `relative()`, `Center`, `RotationCenter.recenter()/sample()` | Pure Java; keep radians and rotation-matrix conventions consistent with the host. |
| `android/vr-core/src/main/java/org/vrization/core/PoseSource.java` | Replaceable tracking contract and pose callback. | `Listener.onPose()`, `isAvailable()`, `start()/stop()/recenter()` | Primary tracking seam for another Android app/game. |
| `android/vr-core/src/main/java/org/vrization/core/SocketAttempt.java` | Owns one cancellable socket attempt and rejects callbacks from replaced/cancelled sockets. | `start()`, `attach()`, `isCurrent()`, `deliverCurrent()`, `cancel()` | Pure Java cancellation ownership; attach a transport-specific cancel callback. |
| `android/vr-core/src/main/java/org/vrization/core/TextureStorage.java` | Tracks successfully allocated texture dimensions/format and context reset. | `needsAllocation()`, `allocated()`, `reset()` | Internal pure allocation policy; renderer owns actual GLES objects. |
| `android/vr-core/src/main/java/org/vrization/core/TransportEndpoints.java` | Shared Android phone-side USB control/video tunnel constants. | `USB_HOST`, `USB_CONTROL_PORT`, `USB_VIDEO_PORT`, `USB_CONNECT`, `USB_BOOTSTRAP` | Pure Java endpoint contract; update desktop reverse mappings together. |
| `android/vr-core/src/main/java/org/vrization/core/UsbConnectRequest.java` | One explicit foreground Connect request, consumed once without intent replay. | `request()`, `isPending()`, `consume()`, `cancel()` | Pure Java intent/lifecycle policy; separate a user action from automatic discovery. |
| `android/vr-core/src/main/java/org/vrization/core/UsbConnectionAttempt.java` | Bounded USB discovery/socket retry policy and one-shot phone-originated host wake. | `Source`, `start()`, `takeHostWake()`, `beginDiscovery()`, `beginSocket()`, `established()`, `cancel()` | Pure Java state machine; adapter supplies monotonic time, timers and network work. |
| `android/vr-core/src/main/java/org/vrization/core/VrRenderer.java` | GLES2 stereo image renderer, Cinema projection, lens/fit settings and owned frame cleanup. | `setSettings()`, `setPose()`, `submitFrame()`, `pauseFrames()/resumeFrames()/clearFrames()` | Android GLES/Bitmap adapter; replace texture and render calls for another engine. |
| `android/vr-core/src/main/java/org/vrization/core/VrSettings.java` | Copyable, normalized settings value and default limits shared by UI/render/transport. | `copy()`, `normalize()` | Pure Java value model; pass copies across threads and keep wire fields aligned. |

### Reusable Swift core

Directory: `ios/Sources/VRizationCore/`

| Source file | Responsibility | Important entries | Reuse boundary |
| --- | --- | --- | --- |
| `ios/Sources/VRizationCore/ConnectionInput.swift` | Validates LAN host/port/pairing input and constructs the WebSocket URL. | `ConnectionInput.url()` | Foundation-only input boundary; use before opening network tasks. |
| `ios/Sources/VRizationCore/HeadsetFit.swift` | Per-eye fit rectangles, finger-coordinate mapping, seam-aware mirrored pan and proportional resize. | `FitPoint`, `FitRect`, `HeadsetFit.fit()/eyeRect()/mirroredPan()/resize()` | Foundation math; reuse with UIKit, Metal or an engine editor. |
| `ios/Sources/VRizationCore/HostSessionGate.swift` | Validates hello before JSON/JPEG session events; tracks supported settings schema. | `HostSessionGate.receiveText()/receiveJPEG()/reset()`, `Event` | Transport-independent gate for WebSocket or framed USB. |
| `ios/Sources/VRizationCore/LocalProfileSync.swift` | Restores a saved phone profile once after a valid hello, then reconciles live host edits. | `newSession()`, `beginPreview()/endPreview()`, `receive()`, `Reception` | Pure synchronization policy; storage and controls remain in adapters. |
| `ios/Sources/VRizationCore/PhonePreferences.swift` | Complete Codable phone profile, language/transport preferences, legacy migration and local reset. | `PhonePreferences.validated()`, `PhonePreferencesStore.load()/save()/reset()` | Foundation/UserDefaults adapter; no fields for pairing codes or session credentials. |
| `ios/Sources/VRizationCore/PoseMath.swift` | Validated angle/rotation operations, screen-to-world remap and relative origin. | `PoseMath.wrap()/screenToWorld()`, `Pose`, `RotationCenter.recenter()/sample()` | Foundation math; replace platform tracking while retaining matrix/radian conventions. |
| `ios/Sources/VRizationCore/SessionGeneration.swift` | Invalidates old session work and rechecks queued callbacks on their owner queue. | `invalidate()`, `isCurrent()`, `dispatch()`, `close()` | Foundation/Dispatch ownership helper; adapters still cancel actual resources. |
| `ios/Sources/VRizationCore/SettingsSync.swift` | Revision/client-sequence reconciliation with active-gesture and stale-echo protection. | `newSession()`, `edited()`, `beginGesture()/endGesture()`, `sent()`, `accept()` | Foundation policy; serialize mutation on one owner queue. |
| `ios/Sources/VRizationCore/USBConnectionControl.swift` | Framed Connect/Stop commands and stopped acknowledgment for a paired PC to manage a foreground USB attempt. | `USBConnectionControl.port`, `connectMessage()/stopMessage()/stoppedMessage()`, `action()`, `validateConnect()` | Control protocol independent of video framing; listener is an app adapter. |
| `ios/Sources/VRizationCore/USBFraming.swift` | Bounded length/kind/payload framing and incremental decoding for JSON and JPEG. | `USBFrame`, `USBFraming.length()/decode()/encode()`, `USBFrameDecoder.feed()/reset()` | Foundation codec; can be shared by a new paired USB transport. |
| `ios/Sources/VRizationCore/VRProtocol.swift` | Versioned host message codec, capability/schema validation, settings, poses and control messages. | `decodeHostMessage()`, `encodeSettings()`, `encodePose()`, `hello()`, `recenter()`, `ping()` | Shared wire contract; extend with matching desktop and Android changes. |
| `ios/Sources/VRizationCore/VRSettings.swift` | Strict settings model, defaults, patch application, Codable support and stable validation errors. | `VRSettings.validated()/applying()/decode()`, `VRCoreError`, `WireValue` | Foundation value/schema layer; keep bounds and field names aligned across clients. |

### iOS application adapters and shaders

Directory: `ios/VRizationApp/`

| Source file | Responsibility | Important entries | Reuse boundary |
| --- | --- | --- | --- |
| `ios/VRizationApp/AppDelegate.swift` | Creates the viewer scene and forwards scene foreground/background/disconnect lifecycle. | `AppDelegate`, `SceneDelegate.sceneWillResignActive()/sceneDidBecomeActive()/sceneDidDisconnect()` | UIKit application assembly; reuse lower layers in a different app or game. |
| `ios/VRizationApp/HeadsetEditorView.swift` | UIKit live flat preview overlay with mirrored pan, corner resize and save/discard callbacks. | `draft`, `onDraft`, `onSave`, `onDiscard`, `refreshVideoAspect()` | UI gesture adapter over `HeadsetFit`; it does not persist drafts or own the stream. |
| `ios/VRizationApp/JPEGDecoder.swift` | Serial latest-only JPEG decode and normalized RGBA image delivery with generation checks. | `reset()`, `submit()`, `onImage` | CoreGraphics decoder adapter; replace for another codec while bounding pending frames. |
| `ios/VRizationApp/Localization.swift` | Reads the explicit saved language and loads its offline strings bundle. | `L.language`, `L.text()` | Presentation adapter over `PhonePreferencesStore`; English is the default. |
| `ios/VRizationApp/MotionSource.swift` | Core Motion device tracking, landscape remap, relative recenter and lifecycle stop. | `available`, `onPose`, `start()/stop()/recenter()` | Apple tracking adapter; use `PoseMath` with engine-provided rotations if replacing it. |
| `ios/VRizationApp/StereoRenderer.swift` | Metal texture ownership, per-eye rendering, Cinema transforms and clearing disconnected video. | `setSettings()`, `setPose()`, `submit()`, `clear()`, `draw(in:)` | Metal/MTKView adapter; core geometry/settings can be retained with another renderer. |
| `ios/VRizationApp/StereoShaders.metal` | GPU full-screen vertex and stereo fragment projection, fit and lens sampling. | `stereoVertex`, `stereoFragment`, `Uniforms` | Metal shader boundary; CPU uniform layout must match when porting shaders. |
| `ios/VRizationApp/StreamClient.swift` | URLSession WebSocket or USB listener session, protocol gates, bounded sends, decode and cancellation. | `connectUSB()`, `connect()`, `disconnect()`, `sendSettings()`, `sendPose()`, `pauseForEditor()` | Foundation/CoreGraphics network adapter on the main queue; preserve generation/resource cleanup. |
| `ios/VRizationApp/USBControlListener.swift` | Foreground-only loopback control listener for paired PC Connect/Stop; acknowledges Stop after video cleanup. | `start()/stop()`, `onConnect`, `onStop`, `onFailure` | Network-framework control adapter; bind loopback and validate the tiny framed command. |
| `ios/VRizationApp/USBListener.swift` | Single-peer loopback video listener, framed JSON/JPEG reads and explicit readiness response. | `start()/stop()`, `acknowledgedHost()`, `send()`, `onFrame` | Network-framework USB endpoint; paired desktop relay supplies the physical transport. |
| `ios/VRizationApp/ViewerController.swift` | UIKit controls, saved profile/synchronization, transport selection, editor, bundle version label and render/motion wiring. | `viewDidLoad()`, `suspendSession()`, `resumeDisplay()`, `startUSBControl()`, `closeEditor()` | App assembly layer; use core models and small adapters in another interface. |

### Build, verification and release tools

Directory: `scripts/`

| Source file | Responsibility | Important entries | Reuse boundary |
| --- | --- | --- | --- |
| `scripts/archive_releases.py` | Downloads verified releases, retains each version and atomically publishes a runnable latest copy. | `prepare_release()`, `publish_latest()`, `main()` | Release/archive tooling, not runtime; accepts a destination directory. |
| `scripts/build_ios.py` | macOS core tests, device/simulator SDK builds and simulator UI/render verification. | `main()`, `export_ui_report()`, `check_rendered_card_colors()`, `check_rendered_seam()` | Requires Apple build tools; simulator evidence does not prove physical iPhone USB. |
| `scripts/build-android.ps1` | Validates JDK/SDK paths, then runs Android unit tests, lint, APK and reusable core build. | `-JavaHome`, `-AndroidHome`, Gradle tasks | Windows build entry; use equivalent Gradle tasks on other operating systems. |
| `scripts/build-windows.ps1` | Installs locked runtime/build dependencies, collects licenses, tests and freezes the host. | `-Python`, pytest, PyInstaller | Build-environment script; executable packaging uses `desktop/VRization.spec`. |
| `scripts/check_docs.py` | Checks English-first bilingual sections and local Markdown links. | `owned_pages()`, `check_page()`, `main()` | Repository documentation gate; it checks structure, not translation accuracy. |
| `scripts/collect_licenses.py` | Collects installed runtime versions and full license texts for redistribution. | `collect()` | Packaging provenance utility; run in the pinned release environment. |
| `scripts/ios_test_host.py` | Loopback synthetic video fixture for iOS UI tests; its input sink never moves the mouse. | `main()`, `NoMouse` | Test support script; it neither captures a display nor measures real USB performance. |
| `scripts/ios_usb_fixture.py` | Fake Apple multiplexer that relays to a real iOS Simulator TCP listener. | `SimulatedAppleMux.start()/stop()`, `Handler`, `NoAndroid` | CI fixture for framing/relay; excludes a physical cable, driver or trust prompt. |
| `scripts/package_release.py` | Packages Windows/APK/AAR/iOS assets with offline docs and license texts. | `package_windows()`, `package_android()`, `package_ios_source()`, `package_ios()`, `main()` | Release tooling; keeps private signing material outside packaged archives. |
| `scripts/prepare_release_notes.py` | Produces bilingual release notes whose documentation links refer to the published tag. | `prepare()`, command-line entry | GitHub release text adapter; use tagged links for immutable published documentation. |
| `scripts/smoke_windows_package.py` | Extracts the public ZIP into a clean location and runs read-only executable USB diagnostics. | `smoke()`, `main()` | Packaging smoke check without developer SDK assumptions; does not prove live streaming. |
| `scripts/verify_android_release.py` | Verifies an APK and requires the existing public signing-certificate fingerprint. | `verify_apk()`, `read_fingerprint()`, `main()` | Publication gate; reads public certificate data, never a private signing key. |
| `scripts/android-release-certificate.sha256` | Public signing-certificate fingerprint baseline for APK upgrade compatibility. | `verify_android_release.py` input | Release identity data, not a signing key; change only through an intentional signer migration. |

### Package, resources and CI entry points

| Source file | Responsibility | Important entries | Reuse boundary |
| --- | --- | --- | --- |
| `desktop/launcher.py` | Frozen executable entry that uses the same dispatcher as the Python module. | `vrization_host.__main__.main` | Packaging adapter. |
| `desktop/VRization.spec` | PyInstaller executable, imports and redistribution data; avoids collecting unrelated system runtimes. | `Analysis`, `EXE` | Windows executable packaging policy. |
| `desktop/pyproject.toml` | Host package metadata, pinned runtime requirements and GUI entry point. | `vrization-host` | Python installation/package entry. |
| `desktop/requirements-lock.txt` | Exact desktop runtime dependency versions used by the build. | `build-windows.ps1` input | Reproducible environment data. |
| `android/settings.gradle` | Declares app/core projects and dependency repositories. | `:app`, `:vr-core` | Build graph. |
| `android/build.gradle` | Shared Android Gradle plugin declaration. | Android Gradle plugin | Root build configuration. |
| `android/app/build.gradle` | APK ID, version, API levels, dependencies and both bundled languages. | `defaultConfig`, `dependencies` | Android application packaging configuration. |
| `android/vr-core/build.gradle` | Android library/AAR API levels and compilation settings. | `com.android.library` | Reusable Android library packaging. |
| `android/app/src/main/AndroidManifest.xml` | App entry Activity, landscape/configuration behavior, GLES requirement and network permissions. | `MainActivity` | Platform registration; gyro is optional. |
| `android/app/src/main/res/values/strings.xml` | Default English UI strings and selectable language/mode arrays. | Android resource lookup | Presentation data. |
| `android/app/src/main/res/values-zh/strings.xml` | Chinese UI strings/arrays with the same resource keys. | Android resource lookup | Presentation data. |
| `android/app/src/main/res/xml/network_security_config.xml` | Network policy for the current cleartext LAN/USB protocol. | Android network security configuration | Platform network adapter policy. |
| `ios/Package.swift` | Exposes the Foundation-based `VRizationCore` library and core test target. | `VRizationCore` product | Swift Package integration without the UIKit/Metal app. |
| `ios/VRization.xcodeproj/project.pbxproj` | Registers core/app/shader/resource sources, SDK targets and app/test build settings. | Xcode project targets | Apple app build assembly. |
| `ios/VRizationApp/Info.plist` | App metadata, bundle version, scene and platform permission descriptions. | Bundle metadata | iOS registration and installed version source. |
| `ios/VRizationApp/en.lproj/Localizable.strings` | Default English iOS UI catalogue. | `L.text()` | Offline presentation data. |
| `ios/VRizationApp/zh-Hans.lproj/Localizable.strings` | Chinese iOS UI catalogue using matching keys. | `L.text()` | Offline presentation data. |
| `ios/VRizationApp/en.lproj/InfoPlist.strings` | English system permission descriptions. | Localized bundle metadata | Platform presentation data. |
| `ios/VRizationApp/zh-Hans.lproj/InfoPlist.strings` | Chinese system permission descriptions. | Localized bundle metadata | Platform presentation data. |
| `.github/workflows/build.yml` | Docs, Windows package smoke, Android test/lint/build, iOS simulator checks and gated tag publication. | `documentation`, `windows`, `android`, `ios`, `release` jobs | CI orchestration; artifacts and release gates have separate purposes. |

<!-- vrization:chinese -->
## 简体中文

本目录逐一说明 `desktop/src/vrization_host` 下全部维护中的生产 Python 文件、Android 应用及核心 Java 文件、Swift 核心文件，以及 iOS 应用 Swift、Metal 文件的职责、重要入口和移植边界。源码表不包含测试、生成文件和构建产物；发布工具、测试辅助脚本及主要平台资源另列。目录描述当前源码，平台构建和物理设备验证结果见[验证记录](VALIDATION.md)与[兼容性](COMPATIBILITY.md)。

### 集成边界

用替代 `CaptureSource` 和 `InputSink` 接入 `HostServer`，可以串流其他图像源，或把姿态直接送入游戏视角。Android AAR 同时包含纯 Java 设置、几何与连接策略，以及 Android 传感器、GLES 适配器。Swift 包 `VRizationCore` 使用 Foundation，把 UIKit、Network、Core Motion 和 Metal 保留在应用适配层。这些边界可用于复用；应用装配类仍负责平台生命周期。当前视频是供双眼观看的同一桌面图像；原生立体游戏渲染需要另外接入图像源和渲染。

连接控制与视频使用不同生命周期。Android 手机侧 USB 控制使用本机 18764 端口，视频使用 18765，并反向映射到电脑视频服务的 8765。一次新的手机主动连接只请求控制端点一次；自动检测和电脑发起的连接不会反复唤起已停止的电脑。iOS 已配对设备控制监听器使用 18767，带帧边界的视频监听器使用 18766。本地停止、断开会取消待处理任务并释放持有资源；新请求需要新的显式动作。约定详见 [USB](USB.md)、[协议](PROTOCOL.md)与[架构](ARCHITECTURE.md)。

### Windows 电脑端

目录：`desktop/src/vrization_host/`

| 源文件 | 职责 | 重要入口 | 移植边界 |
| --- | --- | --- | --- |
| `desktop/src/vrization_host/__init__.py` | 可嵌入电脑端的延迟加载导出；诊断入口不必加载采集和输入组件。 | `HostServer`, `CaptureSource`, `InputSink`, `Settings`, `__version__` | 通过这些公开导出接入替代采集器和输入适配器。 |
| `desktop/src/vrization_host/__main__.py` | 选择图形界面或只读 USB 诊断命令。 | `main()`, `--usb-diagnostics` | 进程入口适配层；与嵌入接口分离。 |
| `desktop/src/vrization_host/_version.py` | 统一提供 Python 包和电脑控制界面使用的版本号。 | `__version__` | 发布元数据；与各平台包版本一起更新。 |
| `desktop/src/vrization_host/capture.py` | 定义采集接口、输出尺寸和只保留最新帧的采集线程，提供 MSS 后备实现。 | `CaptureConfig`, `Frame`, `CaptureSource.read()/close()`, `MssCaptureSource`, `CaptureWorker`, `LatestFrameBuffer` | 游戏纹理或其他平台实现 `CaptureSource`；交付拥有独立生命周期的图像数据并释放资源。 |
| `desktop/src/vrization_host/connection.py` | 合并显式连接请求，并提供独立的本机 USB 控制端点。 | `ConnectionCoordinator.request()/accept()/complete()/cancel()`, `UsbConnectService`, `trusted_usb_request()` | 注入事件队列及运行、停止状态判断；模块不访问控件或授予输入控制权限。 |
| `desktop/src/vrization_host/gui.py` | Tk 控制面板总装：采集范围、预设、连接与停止、USB 状态、编辑器及输入偏好／暂停恢复。 | `HostWindow.start()/stop()/close()`, `configure_dpi_awareness()`, `main()` | 可以替换界面，沿用电脑服务、连接协调器、USB 管理器和设置接口。 |
| `desktop/src/vrization_host/i18n.py` | 英文优先的文字查询及本地语言偏好。 | `translate()`, `load_language()`, `save_language()` | 电脑端文案目录；其他前端可使用自己的展示层。 |
| `desktop/src/vrization_host/input.py` | 姿态转相对输入、手动／自动策略、新鲜度校验和紧急暂停锁；自动策略控制所有前台窗口，旧手动模式保留焦点检查。 | `InputSink.move()`, `WindowsMouseSink`, `PoseController.pose()/tick()/recenter()/arm()/disarm()/configure_auto_control()/resume_control()`, `EmergencyHotkey` | 用游戏视角适配器替换 `InputSink`，保留合法会话、本地策略与暂停锁门控。 |
| `desktop/src/vrization_host/ios_usb.py` | 向已配对 iOS 发送连接、停止控制并转接带帧边界的视频、消息；先校验就绪握手再启动电脑，并等待停止确认。 | `request_ios_connect()/request_ios_stop()`, `validate_ios_connect()`, `IosRelay.start()/stop()/request_stop()` | 注入已配对设备的复用连接和启动回调；传输层不持有界面。 |
| `desktop/src/vrization_host/pose_filter.py` | 对已接受的角度增量进行原创速度自适应防抖；强度为零时直接通过。 | `PoseStabilizer.configure()/reset()/discard_lag()/step()` | 无第三方依赖的数学逻辑；保留角度、时间单位以及会话和控制切换时的重置。 |
| `desktop/src/vrization_host/profiles.py` | 提供命名采集预设及初始默认值；预设目标不代表已测得的延迟。 | `apply_profile()`, `capture_profile()`, `initial_capture()` | 策略参数可复用于不同界面或采集实现。 |
| `desktop/src/vrization_host/protocol.py` | 校验带版本的 JSON 设置和控制消息，限制配对尝试。 | `Settings.to_dict()/update()`, `parse_message()`, `ProtocolError`, `TokenLimiter` | 与电脑渲染无关的协议约定；扩展时同时匹配手机编解码器。 |
| `desktop/src/vrization_host/server.py` | 经过配对校验的单头显 WebSocket 服务，负责 USB 引导、发帧及输入看门狗。 | `HostServer.make_app()/start()/stop()/request_stop()`, `update_settings()`, `arm()/disarm()/recenter()/set_auto_control()/resume_control()/get_control_state()` | 通过采集、输入适配器和状态回调嵌入 `HostServer`；保留主动采集、本地输入策略和电脑主动恢复暂停锁。 |
| `desktop/src/vrization_host/storage.py` | 保存电脑／采集／USB 非敏感偏好，独立 `input.json` 保存默认启用的陀螺仪偏好；不保存配对码、实时授权状态或暂停锁。 | `default_preferences()`, `load_preferences()/save_preferences()`, `load_usb_preferences()/save_usb_preferences()`, `load_input_preferences()/save_input_preferences()` | 可替换存储适配器，保留值校验、默认值及敏感字段排除规则。 |
| `desktop/src/vrization_host/usb.py` | 发现已授权 Android、管理反向端口映射和已配对 Apple 复用连接，负责设备传输生命周期。 | `UsbManager.start()/scan()/request_connect()/cancel_connect()/stop()`, `AdbReverse`, `AppleMux`, `WindowsUsbPresence`, `pack_frame()/read_frame()` | 设备适配边界：可注入 ADB、复用连接及物理连接检测实现；子进程和套接字由适配层持有。 |
| `desktop/src/vrization_host/usb_diagnostics.py` | 供源码及打包程序使用的脱敏只读 USB 报告。 | `collect_usb_diagnostics()`, `main()` | 可复用诊断输出，无需开启视频、修改端口映射或控制输入。 |
| `desktop/src/vrization_host/usb_tools.py` | 校验并导入离线官方 Windows Platform-Tools ZIP，保存到稳定工具目录。 | `import_platform_tools()`, `default_tools_directory()`, `UsbToolsError` | Windows 工具包适配层；界面负责翻译稳定的错误码。 |
| `desktop/src/vrization_host/view_edit.py` | 纯双眼适配几何与保存、弃用草稿事务。 | `fit_size()`, `resolved_fit()`, `eye_bounds()`, `dragged()`, `EditTransaction.preview()/commit()/discard()` | 不依赖 Tk 或网络；复用时保留每眼归一化坐标及已保存值与草稿的边界。 |
| `desktop/src/vrization_host/view_editor.py` | Tk 可视化头显编辑器，提供顶点、预览及保存、弃用回调。 | `HeadsetEditor.begin()/move()/end()/save()/discard()/draw()` | 可替换控件绘制和手势；几何及事务规则继续放在 `view_edit.py`。 |
| `desktop/src/vrization_host/windows_capture.py` | 校验 Windows 显示器布局，并提供在 Python 编码前缩放的可复用 GDI 采集。 | `WindowsDisplayLayout.validate()`, `WindowsGdiCapture.grab()/close()`, `CaptureLayoutChanged` | 仅适用于 Windows 的后端；通过 `CaptureSource` 接入。 |
| `desktop/src/vrization_host/windows_gpu.py` | 使用系统 DXGI/D3D11 复制显示输出、裁剪、旋转和 GPU 缩放，并返回独立持有的输出缓冲区。 | `WindowsGpuCapture.grab()/close()`, `GpuScaler.render()/close()`, `validate_capture_request()`, `UnsupportedGpuCapture` | Windows 原生资源适配层；移植时保留线程所有权及不支持后端时的后备规则。 |

### Android 应用适配层

目录：`android/app/src/main/java/org/vrization/app/`

| 源文件 | 职责 | 重要入口 | 移植边界 |
| --- | --- | --- | --- |
| `android/app/src/main/java/org/vrization/app/ConnectionMode.java` | USB 与局域网连接偏好，默认使用 USB。 | `ConnectionMode`, `fromPreference()` | 应用策略值；与渲染分离。 |
| `android/app/src/main/java/org/vrization/app/HeadsetEditorView.java` | 透明 Android 触控覆盖层，提供双眼镜像移动、顶点缩放及控件预留空间。 | `onDraw()`, `onTouchEvent()`, `reserveTop()` | Android View 适配层；保存、弃用、传输和存储由调用方负责。 |
| `android/app/src/main/java/org/vrization/app/HeadsetTouch.java` | 把手指位移、选中的眼睛或顶点映射到核心几何操作。 | `pan()`, `resize()` | 可替换手势解释，复用 `HeadsetGeometry`。 |
| `android/app/src/main/java/org/vrization/app/HostSessionGate.java` | 仅在收到有效电脑握手后接受视频，并记录电脑声明的防抖能力。 | `receive()`, `receiveJpeg()`, `isEstablished()`, `supportsStabilization()` | 与界面无关的协议门槛；配合严格的设置解码。 |
| `android/app/src/main/java/org/vrization/app/InitialUsbDetection.java` | 允许初次进入前台时进行一次自动 USB 尝试，尊重停止或重建会话状态。 | `onForeground()`, `stop()` | 把自动检测策略与显式连接分开。 |
| `android/app/src/main/java/org/vrization/app/MainActivity.java` | 原生界面和生命周期总装：连接 Intent、本地偏好、编辑器、渲染、传感器及安装包版本标签。 | `onCreate()/onNewIntent()/onResume()/onPause()`, `connectOrDisconnect()`, `connectFromExplicitUsbRequest()`, `startHeadsetEdit()` | 应用装配层；向游戏移植时接入核心类，按游戏界面重建装配。 |
| `android/app/src/main/java/org/vrization/app/PhoneFrameStats.java` | 固定空间的会话内接收帧率及接收到纹理提交的时间统计。 | `newSession()`, `clear()`, `decoded()`, `uploaded()` | 基于本地时钟的诊断；统计不含电脑端或实际屏幕显示延迟。 |
| `android/app/src/main/java/org/vrization/app/PhoneProfile.java` | 管理手机完整已保存设置、已保存偏好优先级及扩展协议迁移。 | `snapshot()`, `commit()`, `reset()`, `waitForExtendedSnapshot()` | 草稿不进入持久化；在确认电脑能力后恢复偏好。 |
| `android/app/src/main/java/org/vrization/app/PingTracker.java` | 管理最多一个待回应应用 Ping 及往返时间。 | `shouldSend()`, `pong()`, `reset()` | 可复用计时策略；往返时间与视频延迟分别解释。 |
| `android/app/src/main/java/org/vrization/app/PoseSendGate.java` | 断开、编辑或套接字发送积压时禁止输出姿态。 | `maySend()`, `setEnabled()` | 轻量输入背压策略；不补发延迟的旧姿态。 |
| `android/app/src/main/java/org/vrization/app/SessionDispatcher.java` | 串行管理连接，以代际校验过滤排队回调并执行最终关闭。 | `invalidate()`, `dispatch()`, `deliverCurrent()`, `close()` | 可注入执行器；回调触及应用状态时保留代际检查。 |
| `android/app/src/main/java/org/vrization/app/SettingsJson.java` | 适配 Android JSON，处理有效本地偏好与兼容电脑端的设置消息。 | `encode()`, `encodeForHost()`, `decode()` | 可在平台边界替换 `JSONObject`，保留共用值和协议规则。 |
| `android/app/src/main/java/org/vrization/app/SettingsSync.java` | 拒绝过时电脑快照，协调版本和客户端序号，并保护正在进行的手势。 | `newSession()`, `edited()`, `beginGesture()/endGesture()`, `nextSequence()`, `sent()`, `accept()` | 纯同步策略；由同一个所属线程驱动。 |
| `android/app/src/main/java/org/vrization/app/SettingsValues.java` | 严格 Java Map 编解码，定义协议字段及数值、类型范围。 | `encode()`, `encodeForHost()`, `decode()` | 与具体传输无关的应用编解码器；替换 JSON 时保留校验。 |
| `android/app/src/main/java/org/vrization/app/StreamClient.java` | 管理 OkHttp WebSocket、一次性 USB 唤起与引导、有界重试、取消及只保留最新 JPEG 的解码。 | `connect()`, `connectUsb()`, `disconnect()`, `shutdown()`, `sendSettings()`, `sendPose()`, `pauseForEditor()` | Android、OkHttp、Bitmap 适配层；复用核心所有权和策略工具，断开时清空画面。 |
| `android/app/src/main/java/org/vrization/app/UsbBootstrap.java` | 严格校验 USB 发现字段，使视频目标保持为固定本机隧道。 | `parse()`, `ENDPOINT` | 发现响应编解码器；引导 JSON 不得指定任意主机或重定向。 |

### 可复用 Android 核心

目录：`android/vr-core/src/main/java/org/vrization/core/`

| 源文件 | 职责 | 重要入口 | 移植边界 |
| --- | --- | --- | --- |
| `android/vr-core/src/main/java/org/vrization/core/AndroidPoseSource.java` | Android 旋转向量跟踪、屏幕方向映射及回正后的相对姿态。 | `isAvailable()`, `start()/stop()/recenter()`, `onSensorChanged()` | `PoseSource` 的 Android 传感器适配器；引擎提供跟踪时可替换。 |
| `android/vr-core/src/main/java/org/vrization/core/HeadsetEdit.java` | 本地草稿事务；只有保存才生成更新后的已提交值。 | `draft()`, `preview()`, `update()`, `save()`, `discard()` | 纯 Java；可以独立于网络和存储嵌入。 |
| `android/vr-core/src/main/java/org/vrization/core/HeadsetGeometry.java` | 每眼归一化适配、接缝范围、镜像平移和顶点等比例缩放。 | `fit()`, `bounds()`, `resolveFit()`, `pan()`, `mirroredPan()`, `resize()` | 纯 Java 数学；替换渲染器或编辑器时保持坐标单位一致。 |
| `android/vr-core/src/main/java/org/vrization/core/PoseMath.java` | 角度折返、旋转数学及相对原点采样。 | `wrap()`, `relative()`, `Center`, `RotationCenter.recenter()/sample()` | 纯 Java；弧度和旋转矩阵约定需与电脑端一致。 |
| `android/vr-core/src/main/java/org/vrization/core/PoseSource.java` | 可替换的跟踪接口及姿态回调。 | `Listener.onPose()`, `isAvailable()`, `start()/stop()/recenter()` | 向其他 Android 应用或游戏移植时的主要跟踪边界。 |
| `android/vr-core/src/main/java/org/vrization/core/SocketAttempt.java` | 管理一次可取消套接字尝试，拒绝被替换或取消的旧套接字回调。 | `start()`, `attach()`, `isCurrent()`, `deliverCurrent()`, `cancel()` | 纯 Java 取消所有权；附加具体传输的取消回调即可。 |
| `android/vr-core/src/main/java/org/vrization/core/TextureStorage.java` | 记录成功分配的纹理尺寸、格式及上下文重置。 | `needsAllocation()`, `allocated()`, `reset()` | 内部纯分配策略；实际 GLES 对象由渲染器持有。 |
| `android/vr-core/src/main/java/org/vrization/core/TransportEndpoints.java` | 集中定义 Android 手机侧 USB 控制和视频隧道常量。 | `USB_HOST`, `USB_CONTROL_PORT`, `USB_VIDEO_PORT`, `USB_CONNECT`, `USB_BOOTSTRAP` | 纯 Java 端点约定；修改时同时更新电脑反向端口映射。 |
| `android/vr-core/src/main/java/org/vrization/core/UsbConnectRequest.java` | 一次显式前台连接请求，消费后不会随 Intent 再次播放。 | `request()`, `isPending()`, `consume()`, `cancel()` | 纯 Java Intent 和生命周期策略；区分用户动作与自动检测。 |
| `android/vr-core/src/main/java/org/vrization/core/UsbConnectionAttempt.java` | 有界 USB 发现与套接字重试策略，手机主动连接时只唤起电脑一次。 | `Source`, `start()`, `takeHostWake()`, `beginDiscovery()`, `beginSocket()`, `established()`, `cancel()` | 纯 Java 状态机；适配器提供单调时间、定时器及网络执行。 |
| `android/vr-core/src/main/java/org/vrization/core/VrRenderer.java` | GLES2 双眼图像渲染、大屏幕投影、镜片与画面适配设置，以及持有帧的清理。 | `setSettings()`, `setPose()`, `submitFrame()`, `pauseFrames()/resumeFrames()/clearFrames()` | Android GLES、Bitmap 适配器；在其他引擎中替换纹理和绘制调用。 |
| `android/vr-core/src/main/java/org/vrization/core/VrSettings.java` | 供界面、渲染和传输使用的可复制、归一化设置值及默认范围。 | `copy()`, `normalize()` | 纯 Java 值模型；跨线程传副本，并保持协议字段一致。 |

### 可复用 Swift 核心

目录：`ios/Sources/VRizationCore/`

| 源文件 | 职责 | 重要入口 | 移植边界 |
| --- | --- | --- | --- |
| `ios/Sources/VRizationCore/ConnectionInput.swift` | 校验局域网主机、端口与配对输入，构造 WebSocket 地址。 | `ConnectionInput.url()` | 仅依赖 Foundation 的输入边界；在开启网络任务前使用。 |
| `ios/Sources/VRizationCore/HeadsetFit.swift` | 每眼适配矩形、手指坐标映射、接缝感知的镜像平移及等比例缩放。 | `FitPoint`, `FitRect`, `HeadsetFit.fit()/eyeRect()/mirroredPan()/resize()` | Foundation 数学逻辑；可搭配 UIKit、Metal 或引擎编辑器。 |
| `ios/Sources/VRizationCore/HostSessionGate.swift` | 在接收 JSON、JPEG 会话事件前校验握手，并记录支持的设置协议。 | `HostSessionGate.receiveText()/receiveJPEG()/reset()`, `Event` | 可用于 WebSocket 或带帧边界 USB 的独立传输门槛。 |
| `ios/Sources/VRizationCore/LocalProfileSync.swift` | 有效握手后恢复一次手机已保存偏好，之后协调电脑实时修改。 | `newSession()`, `beginPreview()/endPreview()`, `receive()`, `Reception` | 纯同步策略；存储和控件保留在适配层。 |
| `ios/Sources/VRizationCore/PhonePreferences.swift` | 完整 Codable 手机偏好、语言和传输选择、旧版迁移及本地重置。 | `PhonePreferences.validated()`, `PhonePreferencesStore.load()/save()/reset()` | Foundation、UserDefaults 适配器；没有配对码或会话凭据存储字段。 |
| `ios/Sources/VRizationCore/PoseMath.swift` | 有效角度与旋转运算、屏幕到世界的方向映射及相对原点。 | `PoseMath.wrap()/screenToWorld()`, `Pose`, `RotationCenter.recenter()/sample()` | Foundation 数学逻辑；可替换平台跟踪，保留矩阵和弧度约定。 |
| `ios/Sources/VRizationCore/SessionGeneration.swift` | 使旧会话任务失效，并在所属队列再次检查排队回调。 | `invalidate()`, `isCurrent()`, `dispatch()`, `close()` | Foundation、Dispatch 所有权工具；实际资源仍由适配器取消。 |
| `ios/Sources/VRizationCore/SettingsSync.swift` | 协调版本、客户端序号，保护活动手势并过滤过时回声。 | `newSession()`, `edited()`, `beginGesture()/endGesture()`, `sent()`, `accept()` | Foundation 策略；状态变更应在同一所属队列串行执行。 |
| `ios/Sources/VRizationCore/USBConnectionControl.swift` | 为已配对电脑提供带帧边界的连接、停止命令及停止确认，管理前台手机 USB 尝试。 | `USBConnectionControl.port`, `connectMessage()/stopMessage()/stoppedMessage()`, `action()`, `validateConnect()` | 独立于视频传输的控制协议；监听器属于应用适配层。 |
| `ios/Sources/VRizationCore/USBFraming.swift` | 对 JSON 和 JPEG 进行有界长度、类型、内容封装及增量解码。 | `USBFrame`, `USBFraming.length()/decode()/encode()`, `USBFrameDecoder.feed()/reset()` | Foundation 编解码器；可供新的已配对 USB 传输复用。 |
| `ios/Sources/VRizationCore/VRProtocol.swift` | 带版本的电脑消息编解码、能力和协议校验，以及设置、姿态和控制消息。 | `decodeHostMessage()`, `encodeSettings()`, `encodePose()`, `hello()`, `recenter()`, `ping()` | 共用协议约定；扩展时同时调整电脑和 Android。 |
| `ios/Sources/VRizationCore/VRSettings.swift` | 严格设置模型、默认值、补丁应用、Codable 支持及稳定校验错误。 | `VRSettings.validated()/applying()/decode()`, `VRCoreError`, `WireValue` | Foundation 值和协议层；不同客户端的范围和字段名需一致。 |

### iOS 应用适配层与着色器

目录：`ios/VRizationApp/`

| 源文件 | 职责 | 重要入口 | 移植边界 |
| --- | --- | --- | --- |
| `ios/VRizationApp/AppDelegate.swift` | 创建观看场景，并转发前台、后台和场景断开的生命周期。 | `AppDelegate`, `SceneDelegate.sceneWillResignActive()/sceneDidBecomeActive()/sceneDidDisconnect()` | UIKit 应用装配层；在其他应用或游戏中复用下层组件。 |
| `ios/VRizationApp/HeadsetEditorView.swift` | UIKit 实时平面预览覆盖层，提供镜像平移、顶点缩放及保存、弃用回调。 | `draft`, `onDraft`, `onSave`, `onDiscard`, `refreshVideoAspect()` | `HeadsetFit` 的界面手势适配层；不保存草稿或持有串流。 |
| `ios/VRizationApp/JPEGDecoder.swift` | 串行解码最新 JPEG，以代际校验交付统一 RGBA 图像。 | `reset()`, `submit()`, `onImage` | CoreGraphics 解码适配器；替换编码格式时仍限制待处理帧数量。 |
| `ios/VRizationApp/Localization.swift` | 读取明确保存的语言，加载离线文字资源包。 | `L.language`, `L.text()` | `PhonePreferencesStore` 上的展示适配层；默认使用英文。 |
| `ios/VRizationApp/MotionSource.swift` | Core Motion 设备跟踪、横屏映射、相对回正及生命周期停止。 | `available`, `onPose`, `start()/stop()/recenter()` | Apple 跟踪适配器；替换时可把引擎旋转数据交给 `PoseMath`。 |
| `ios/VRizationApp/StereoRenderer.swift` | Metal 纹理所有权、双眼绘制、大屏幕变换及断开后的视频清理。 | `setSettings()`, `setPose()`, `submit()`, `clear()`, `draw(in:)` | Metal、MTKView 适配器；替换渲染器时可保留核心几何和设置。 |
| `ios/VRizationApp/StereoShaders.metal` | GPU 全屏顶点和双眼片元投影、画面适配及镜片采样。 | `stereoVertex`, `stereoFragment`, `Uniforms` | Metal 着色器边界；移植时 CPU uniform 布局必须匹配。 |
| `ios/VRizationApp/StreamClient.swift` | 在 URLSession WebSocket 或 USB 监听器上管理会话、协议门槛、有界发送、解码和取消。 | `connectUSB()`, `connect()`, `disconnect()`, `sendSettings()`, `sendPose()`, `pauseForEditor()` | 主队列中的 Foundation、CoreGraphics 网络适配层；保留代际和资源清理。 |
| `ios/VRizationApp/USBControlListener.swift` | 仅前台工作的本机控制监听器，接收已配对电脑的连接、停止动作；完成视频清理后确认停止。 | `start()/stop()`, `onConnect`, `onStop`, `onFailure` | Network 框架控制适配器；绑定本机并校验小型带帧边界命令。 |
| `ios/VRizationApp/USBListener.swift` | 单对端本机视频监听器，读取带帧边界的 JSON、JPEG，并发送显式就绪响应。 | `start()/stop()`, `acknowledgedHost()`, `send()`, `onFrame` | Network 框架 USB 端点；物理传输由已配对电脑转接层提供。 |
| `ios/VRizationApp/ViewerController.swift` | UIKit 控件、已保存偏好与同步、连接选择、编辑器、安装包版本标签，以及渲染和运动跟踪总装。 | `viewDidLoad()`, `suspendSession()`, `resumeDisplay()`, `startUSBControl()`, `closeEditor()` | 应用装配层；在其他界面中使用核心模型和小型适配器。 |

### 构建、校验和发布工具

目录：`scripts/`

| 源文件 | 职责 | 重要入口 | 移植边界 |
| --- | --- | --- | --- |
| `scripts/archive_releases.py` | 下载经过校验的发布包，保留各版本并更新可运行的最新版副本。 | `prepare_release()`, `publish_latest()`, `main()` | 发布归档工具，独立于运行时；接受目标目录。 |
| `scripts/build_ios.py` | 在 macOS 运行核心测试、真机和模拟器 SDK 构建，以及模拟器界面、渲染校验。 | `main()`, `export_ui_report()`, `check_rendered_card_colors()`, `check_rendered_seam()` | 依赖 Apple 构建工具；模拟器结果不能证明物理 iPhone USB。 |
| `scripts/build-android.ps1` | 校验 JDK、SDK 路径，运行 Android 单元测试、lint、APK 及可复用核心构建。 | `-JavaHome`, `-AndroidHome`, Gradle tasks | Windows 构建入口；其他系统可执行对应 Gradle 任务。 |
| `scripts/build-windows.ps1` | 安装锁定的运行和构建依赖，收集许可证、测试并打包电脑端。 | `-Python`, pytest, PyInstaller | 构建环境脚本；可执行文件使用 `desktop/VRization.spec` 打包。 |
| `scripts/check_docs.py` | 检查英文在前的双语分区和本地 Markdown 链接。 | `owned_pages()`, `check_page()`, `main()` | 仓库文档门槛；检查结构，不验证翻译准确性。 |
| `scripts/collect_licenses.py` | 收集已安装运行依赖的版本与完整许可证，以便再分发。 | `collect()` | 打包来源记录工具；在锁定的发布环境执行。 |
| `scripts/ios_test_host.py` | iOS 界面测试的本机合成视频环境；输入适配器不会移动鼠标。 | `main()`, `NoMouse` | 测试辅助脚本；不采集显示器或测量真实 USB 性能。 |
| `scripts/ios_usb_fixture.py` | 模拟 Apple 复用服务，转接到实际 iOS 模拟器 TCP 监听器。 | `SimulatedAppleMux.start()/stop()`, `Handler`, `NoAndroid` | CI 的封装和转接测试环境；不覆盖物理数据线、驱动或信任提示。 |
| `scripts/package_release.py` | 把 Windows、APK、AAR 和 iOS 成果连同离线文档、许可证打包。 | `package_windows()`, `package_android()`, `package_ios_source()`, `package_ios()`, `main()` | 发布工具；私有签名材料不进入归档。 |
| `scripts/prepare_release_notes.py` | 生成双语版本说明，文档链接指向发布标签。 | `prepare()`, command-line entry | GitHub 发布文案适配器；已发布说明使用标签固定文档。 |
| `scripts/smoke_windows_package.py` | 把公开 ZIP 解压到干净目录，执行程序的只读 USB 诊断入口。 | `smoke()`, `main()` | 不依赖开发 SDK 假设的打包冒烟检查；不代表真实串流已经验证。 |
| `scripts/verify_android_release.py` | 校验 APK，并要求与既有公开签名证书指纹一致。 | `verify_apk()`, `read_fingerprint()`, `main()` | 发布门槛；读取公开证书数据，不读取私有签名密钥。 |
| `scripts/android-release-certificate.sha256` | 用于 APK 升级兼容性的公开签名证书指纹基线。 | `verify_android_release.py` input | 发布身份数据，非签名密钥；只有明确迁移签名身份时才调整。 |

### 打包、资源和 CI 入口

| 源文件 | 职责 | 重要入口 | 移植边界 |
| --- | --- | --- | --- |
| `desktop/launcher.py` | 打包程序入口，与 Python 模块使用同一分发器。 | `vrization_host.__main__.main` | 打包适配层。 |
| `desktop/VRization.spec` | 定义 PyInstaller 可执行文件、导入和再分发数据，避免收集无关系统运行库。 | `Analysis`, `EXE` | Windows 可执行文件打包策略。 |
| `desktop/pyproject.toml` | 电脑端包元数据、锁定运行依赖和图形界面入口。 | `vrization-host` | Python 安装和打包入口。 |
| `desktop/requirements-lock.txt` | 电脑构建使用的精确运行依赖版本。 | `build-windows.ps1` input | 可重复构建的环境数据。 |
| `android/settings.gradle` | 声明应用、核心项目和依赖仓库。 | `:app`, `:vr-core` | 构建关系。 |
| `android/build.gradle` | 共用 Android Gradle 插件声明。 | Android Gradle plugin | 根构建配置。 |
| `android/app/build.gradle` | APK 标识、版本、API 级别、依赖以及同时打包两种语言。 | `defaultConfig`, `dependencies` | Android 应用打包配置。 |
| `android/vr-core/build.gradle` | Android 库、AAR 的 API 级别及编译设置。 | `com.android.library` | 可复用 Android 库打包。 |
| `android/app/src/main/AndroidManifest.xml` | 应用 Activity 入口、横屏和配置行为、GLES 要求及网络权限。 | `MainActivity` | 平台注册信息；陀螺仪为可选硬件。 |
| `android/app/src/main/res/values/strings.xml` | 默认英文界面文字及可选语言、模式数组。 | Android resource lookup | 展示数据。 |
| `android/app/src/main/res/values-zh/strings.xml` | 使用相同资源键的中文界面文字与数组。 | Android resource lookup | 展示数据。 |
| `android/app/src/main/res/xml/network_security_config.xml` | 当前明文局域网和 USB 协议的网络策略。 | Android network security configuration | 平台网络适配策略。 |
| `ios/Package.swift` | 提供基于 Foundation 的 `VRizationCore` 库和核心测试目标。 | `VRizationCore` product | 独立于 UIKit、Metal 应用的 Swift Package 集成入口。 |
| `ios/VRization.xcodeproj/project.pbxproj` | 注册核心、应用、着色器、资源源文件以及 SDK 目标、应用和测试构建设置。 | Xcode project targets | Apple 应用构建总装。 |
| `ios/VRizationApp/Info.plist` | 应用元数据、包版本、场景及平台权限说明。 | Bundle metadata | iOS 注册信息与已安装版本来源。 |
| `ios/VRizationApp/en.lproj/Localizable.strings` | 默认英文 iOS 界面文案目录。 | `L.text()` | 离线展示数据。 |
| `ios/VRizationApp/zh-Hans.lproj/Localizable.strings` | 使用对应键的中文 iOS 界面文案目录。 | `L.text()` | 离线展示数据。 |
| `ios/VRizationApp/en.lproj/InfoPlist.strings` | 英文系统权限说明。 | Localized bundle metadata | 平台展示数据。 |
| `ios/VRizationApp/zh-Hans.lproj/InfoPlist.strings` | 中文系统权限说明。 | Localized bundle metadata | 平台展示数据。 |
| `.github/workflows/build.yml` | 编排文档、Windows 包冒烟、Android 测试、lint 和构建、iOS 模拟器检查及受门槛约束的标签发布。 | `documentation`, `windows`, `android`, `ios`, `release` jobs | CI 总装；工作流产物与正式发布门槛各司其职。 |

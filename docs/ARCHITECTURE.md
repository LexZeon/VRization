# 🧩 Architecture and integration / 架构与集成

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

v0.2.0-alpha separates the image source, transport, rendering and input sink. Reuse includes an embeddable Python host, an Android AAR and the Foundation-based Swift package `VRizationCore`. The Android and iOS apps default to USB, with LAN as an explicit alternative. Alpha APIs may change.

```mermaid
flowchart LR
    A[Display or rectangle] --> B[CaptureSource]
    B --> C[JPEG encoding]
    C --> D[HostServer / WebSocket v1]
    D --> T[LAN or USB adapter]
    T --> E[Android or iOS client]
    E --> F[GLES or Metal / both eyes]
    G[Android sensors or Core Motion] --> F
    G --> E
    E -->|pose| D
    D --> H[Local authorization and pose deltas]
    H --> I[InputSink]
    I --> J[Windows mouse]
```

### Modules

| Path | Responsibility |
| --- | --- |
| `desktop/src/vrization_host/` | Python capture, protocol, server, input adapter and GUI. |
| `desktop/tests/` | Core checks without real games. |
| `android/vr-core/` | Reusable Android settings, pose interfaces and GLES renderer. |
| `android/app/` | Connection UI, WebSocket client, JPEG decoding and settings. |
| `ios/Sources/VRizationCore/` | Foundation-based protocol, settings synchronization, rotation math, session gates and USB framing. |
| `ios/VRizationApp/` | UIKit UI, URLSession / Network transport, Core Motion, JPEG decoding and Metal renderer. |
| `docs/` | Tutorials, protocol, integration and scope. |

`vr-core` is written in Java but depends on Android OpenGL ES, Bitmap and sensor APIs. Its AAR embeds in Android software; it is not a platform-independent Java / Unity / Unreal library. Other platforms can implement the protocol and adapt pose / rendering to their engine.

### Replace the host image source

`CaptureSource` defines `read(config: CaptureConfig) -> Frame` and `close()`. `Frame` contains JPEG bytes, width, height and monotonic `captured_at`. The default source captures and encodes the desktop. An adapter can supply game-rendered images, remote application output or test frames.

On Windows, the original GDI backend scales the selected physical-pixel rectangle into a bounded top-down DIB before copying pixels into Python. It completes GDI writes before reading the bitmap, returns an owned byte copy, and creates / releases resources on the dedicated capture thread. If the native operation is unsupported or fails, MSS captures **the same validated rectangle**. `MssCaptureSource(prefer_native=False)` selects MSS explicitly. Pre-scaling reduces the bytes copied into Python but does not guarantee the target frame rate, especially for a busy high-resolution desktop.

Before either Windows backend reads pixels, a fresh display-layout query checks output names and coordinates against the cached monitor selection. A mismatch or unverifiable layout stops new frames instead of capturing stale coordinates; Stop, reselect the display / region, then Start again. Output names identify Windows display outputs, not physical panel serial numbers. Any capture error immediately disarms FPS mouse control; resuming requires explicit authorization again. See the measured session and its limits in [validation](VALIDATION.md).

Inject adapters with `HostServer(capture_source=..., input_sink=...)`. Capture and input are independent; sending images does not require enabling input.

The runnable [embedded_host.py](../examples/embedded_host.py) provides an original animated calibration card and a logging input sink. It neither captures the user's screen nor sends OS input. After installing the host package, run `python examples/embedded_host.py` from the root, choose **LAN** on the phone, then use the printed port and code plus the PC's LAN IP. This example does not enable automatic USB pairing.

```python
# Implement CaptureSource.read / close and InputSink.move in your adapters.
server = HostServer(capture_source=my_capture, input_sink=my_input)
```

v1 carries JPEG. Hardware H.264 / H.265 requires new framing, timestamps, keyframe recovery and a compatible decoder; do not send a video bitstream to the v1 JPEG decoder.

### USB adapters and capture presets

`desktop/src/vrization_host/usb.py` provides `UsbManager`, `AdbReverse`, `AppleMux` and `IOSUsbRelay`. Detection runs outside the Tk thread; iOS relay I/O has its own thread. The Windows GUI enables USB detection by default, but importing / embedding `HostServer` does not. An embedder must explicitly own the manager lifecycle and authorization callback:

```python
from vrization_host.usb import UsbManager

server = HostServer(capture_source=my_capture, input_sink=my_input)
usb = UsbManager(server, adb_path=my_official_sdk_adb_path)
server.usb_authorized = usb.authorized.is_set
server.start()  # The host application decides when screen capture is permitted.
usb.start(enabled=True)
# On exit: usb.stop(), then server.stop().
```

Android uses an owned, non-rebinding official ADB reverse mapping and a guarded loopback bootstrap. Native Windows SetupAPI verifies physical USB instances when ADB omits its USB path. iOS uses Apple's local USB service, an existing pairing record and the app's loopback listener; the relay bridges an authenticated host WebSocket into bounded JSON / JPEG frames. Neither route arms mouse input. See [protocol details](PROTOCOL.md) and [USB prerequisites](USB.md). No ADB, Apple driver or libusbmuxd library is bundled.

Capture profiles alter only maximum long edge, target FPS and JPEG quality: low latency `960 / 60 / 60` for new GUI users, stable `1280 / 30 / 65`, quality `1920 / 30 / 80`, or custom. Existing saved capture settings and monitor / region selection are retained. Embedding `CaptureConfig()` retains its `1280 / 30 / 75` defaults. Latest-frame handoff bounds stale work; it does not eliminate capture, JPEG, USB / network, decoder or presentation latency. Received FPS and link RTT are separate diagnostics, not end-to-end measurements.

### Embed in an Android application / game

`VrSettings` holds display and input settings; `PoseSource` abstracts orientation; `AndroidPoseSource` uses platform sensors; `VrRenderer` renders. The app's connection / settings UI can be replaced by the host application.

Run `./gradlew :vr-core:assembleRelease` in `android/`. Copy `vr-core/build/outputs/aar/vr-core-release.aar` into the host's `libs/` and add `implementation files('libs/vr-core-release.aar')`.

```java
VrRenderer renderer = new VrRenderer();
GLSurfaceView surface = new GLSurfaceView(activity);
surface.setEGLContextClientVersion(2);
surface.setRenderer(renderer);
renderer.setSettings(new VrSettings());

AndroidPoseSource pose = new AndroidPoseSource(
    activity, activity.getWindowManager().getDefaultDisplay());
if (pose.isAvailable()) {
    pose.start((yaw, pitch, roll, timestampNanos) ->
        renderer.setPose(yaw, pitch, roll));
}
// After JPEG decoding or when the host's image is ready:
// renderer.submitFrame(bitmap);
```

Integrate this wiring with your Activity lifecycle. Resume `GLSurfaceView`, call `renderer.resumeFrames()` and start sensors on foreground entry. Stop sensors, disconnect, call `renderer.pauseFrames()` and pause the surface on exit. **`submitFrame(bitmap)` transfers ownership**: the renderer recycles that Bitmap, so do not reuse it. Decode / receive off the main thread and avoid queues of stale frames.

`PoseMath` has no Android dependency and can seed a separate math core; the complete AAR still needs Android. You can reuse pose only for a host camera, or render your own images without the Windows mouse adapter. Preserve original MIT notices when redistributing the library.

### Embed Swift core or an iOS viewer

Add the local Swift package at `ios/` to an Xcode project and depend on **VRizationCore**. The package uses Foundation without UIKit, Metal, Core Motion or Network dependencies. It exposes `VRSettings`, `VRProtocol`, `SettingsSync`, `SessionGeneration`, `HostSessionGate`, `ConnectionInput`, `PoseMath`, `RotationCenter`, `USBFraming` and `USBFrameDecoder`. It contains no third-party package dependencies. The package declares iOS 13 / macOS 10.15 minima; the complete viewer app targets iOS / iPadOS 15+ and needs Metal.

```swift
import VRizationCore

let poseJSON = try VRProtocol.encodePose(sequence: 1, yaw: 0.12, pitch: 0.03)
let usbFrame = try USBFraming.encode(USBFrame(kind: .json, payload: poseJSON))
// Send poseJSON through WebSocket, or usbFrame through the USB connection.
```

Integrators can reuse validation, synchronization or math alone. The complete app supplies `StreamClient`, `USBListener`, `MotionSource`, `JPEGDecoder` and `StereoRenderer`; adapt their lifecycle and UI for your host application. Stop network / listener and motion on backgrounding, clear stale session work, and reconnect explicitly. A custom in-game camera sink can consume pose without the Windows mouse adapter. The core is not an installed Unity / Unreal plugin or an ABI-stable SDK. Preserve original MIT notices. See [iOS build and signing](IOS.md).

### Windows and verification boundaries

The supplied host targets Windows 10 / 11 **x64**, with physical-pixel capture coordinates and a modern DPI-awareness API plus older Windows fallbacks. Actual local desktop evidence is from Windows 11; the fallback tests do not establish a Windows 10 hardware pass or every mixed-DPI monitor combination. Select the intended display by its current name, and verify small-window / scaling behavior on your system.

Hardware Huawei Android checks and the iOS simulated-usbmux / Simulator checks are recorded separately in [validation](VALIDATION.md). A native Simulator session does not verify an actual iPhone, motion-axis direction, viewer optics or real FPS games. USB does not make system mouse injection universal; raw input, privilege boundaries and game protection can reject it.

### Port to another platform

1. Implement [protocol v1](PROTOCOL.md), JPEG reception and settings.
2. Render one 2D frame in both eye regions and validate full screen first.
3. Integrate pose and calibrate axes, radians and landscape orientation.
4. If using remote mouse input, retain local authorization, sequence / number checks, disconnect stop and an emergency stop.
5. True stereo requires engine-side per-eye rendering and a new protocol; current desktop duplication cannot create it.

Swift protocol / math reuse is available now; engine adapters and a stable SDK remain possible future work. Alpha interfaces carry no long-term compatibility promise.

---

<!-- vrization:chinese -->
## 简体中文

v0.2.0-alpha 把画面来源、传输、渲染与输入接收拆为相邻组件。现在可复用 Python 主机、Android AAR 与基于 Foundation 的 Swift 包 `VRizationCore`。Android / iOS 应用默认 USB，局域网为显式可选项；公共接口仍处于 Alpha，可能调整。

```mermaid
flowchart LR
    A[电脑显示器或矩形区域] --> B[CaptureSource]
    B --> C[JPEG 编码]
    C --> D[HostServer / WebSocket v1]
    D --> T[局域网或 USB 适配器]
    T --> E[Android 或 iOS 客户端]
    E --> F[GLES 或 Metal 双眼显示]
    G[Android 传感器或 Core Motion] --> F
    G --> E
    E -->|pose| D
    D --> H[授权门与姿态增量]
    H --> I[InputSink]
    I --> J[Windows 鼠标]
```

### 目录

| 路径 | 职责 |
| --- | --- |
| `desktop/src/vrization_host/` | Python 采集、协议、服务器、鼠标适配器与桌面界面。 |
| `desktop/tests/` | 不依赖真实游戏的核心检查。 |
| `android/vr-core/` | 可复用 Android library：设置、旋转传感器接口与 OpenGL ES 双眼渲染。 |
| `android/app/` | 连接界面、WebSocket 客户端、JPEG 解码和设置交互。 |
| `ios/Sources/VRizationCore/` | Foundation 协议、设置同步、旋转数学、会话门与 USB 分帧。 |
| `ios/VRizationApp/` | UIKit 界面、URLSession / Network 传输、Core Motion、JPEG 解码与 Metal 渲染。 |
| `docs/` | 教程、协议、移植与版本边界。 |

`vr-core` 使用 Java 编写，但依赖 Android 的 OpenGL ES、Bitmap 与传感器 API。它可生成 AAR 并嵌入其他 Android 软件；不能直接作为无平台依赖的 Java / Unity / Unreal 库使用。跨平台客户端可以独立实现协议，将姿态与显示逻辑适配到目标引擎。

### 替换电脑画面来源

桌面端 `CaptureSource` 接口定义 `read(config: CaptureConfig) -> Frame` 和 `close()`。`Frame` 包含 `jpeg: bytes`、`width`、`height` 和单调时钟 `captured_at`；默认实现采集并编码桌面。其他软件可以提供自己的 JPEG 帧，例如游戏已渲染的图像、远程应用输出或测试画面，再交给同一主机服务。

Windows 上的原创 GDI 后端先把选定的物理像素矩形缩放到大小受限、从上到下排列的 DIB，再把像素复制进 Python。读取位图前完成 GDI 写入，返回拥有独立内存的字节副本；资源在专用采集线程创建和释放。原生操作不受支持或失败时，MSS 采集**同一个已校验矩形**；`MssCaptureSource(prefer_native=False)` 可显式选择 MSS。预缩放减少复制进 Python 的像素数据量，但不保证达到目标帧率，尤其在忙碌的高分辨率桌面上。

任一 Windows 后端读取像素前，都会重新查询显示布局，把输出名称与坐标同缓存的显示器选择核对。失配或无法确认布局时，停止产生新帧，不继续采集旧坐标；需停止串流、重新选择显示器 / 区域，再启动。输出名称代表 Windows 显示输出，不是物理面板序列号。任何采集错误都会立即解除 FPS 鼠标授权；恢复控制必须重新明确授权。实际测量及其限制见 [验证记录](VALIDATION.md)。

通过 `HostServer(capture_source=..., input_sink=...)` 注入适配器。画面与输入接口分开，集成者可以只发送图像而不启用任何输入。

可运行的 [embedded_host.py](../examples/embedded_host.py) 用原创动态校准卡和日志输入接收器替换桌面采集 / 系统鼠标，不采集用户屏幕、不发送 OS 输入。安装电脑包后，在仓库根目录执行 `python examples/embedded_host.py`，手机显式选择**局域网**，填写控制台端口、配对码和电脑局域网 IP。此示例默认不开自动 USB 配对。

示意接口关系（具体类名与构造参数以源码为准）：

```python
# 自己实现 CaptureSource.read / close 与 InputSink.move。
server = HostServer(capture_source=my_capture, input_sink=my_input)
```

当前传输的数据是 JPEG。若替换为硬件 H.264 / H.265，应一起设计新帧封装、时间戳、关键帧恢复和客户端解码，不能直接把视频码流发送给 v1 的 JPEG 解码器。

### USB 适配器与捕获预设

`desktop/src/vrization_host/usb.py` 提供 `UsbManager`、`AdbReverse`、`AppleMux`、`IOSUsbRelay`。检测在 Tk 线程之外运行，iOS 中继 IO 使用独立线程。Windows 界面默认启用 USB 检测，但导入 / 嵌入 `HostServer` 不会自动开启；宿主须主动管理生命周期和授权回调：

```python
from vrization_host.usb import UsbManager

server = HostServer(capture_source=my_capture, input_sink=my_input)
usb = UsbManager(server, adb_path=my_official_sdk_adb_path)
server.usb_authorized = usb.authorized.is_set
server.start()  # 由宿主决定何时允许采集画面。
usb.start(enabled=True)
# 退出时先 usb.stop()，再 server.stop()。
```

Android 使用自己拥有且不重新绑定他人端口的官方 ADB reverse，再经受保护的回环 bootstrap 配对；ADB 不提供 USB 路径时，用 Windows 原生 SetupAPI 验证物理 USB 实例。iOS 使用 Apple 本地 USB 服务、已有配对记录及手机回环监听；中继把已认证主机 WebSocket 桥接成有限长 JSON / JPEG 帧。两条路线都不自动授权鼠标。详见 [协议](PROTOCOL.md)、[USB 前提](USB.md)。软件不附带 ADB、Apple 驱动或 libusbmuxd 库。

捕获预设只改变最长边、目标帧率和 JPEG 质量：新界面用户默认低延迟 `960 / 60 / 60`，稳定 `1280 / 30 / 65`，画质 `1920 / 30 / 80`，或自定义。已有保存配置以及显示器 / 选区均保留。嵌入 `CaptureConfig()` 仍默认 `1280 / 30 / 75`。最新帧交接限制旧任务积累，但不消除采集、JPEG、USB / 网络、解码与显示延迟；接收帧率和链路 RTT 是独立诊断，不是端到端测量。

### 嵌入 Android 软件 / 游戏

`VrSettings` 表达观看和输入设置；`PoseSource` 隔离姿态来源；`AndroidPoseSource` 使用平台传感器；`VrRenderer` 负责显示。app 提供连接与设置界面，可根据宿主软件重写。

在 `android/` 运行 `./gradlew :vr-core:assembleRelease` 可生成 `vr-core/build/outputs/aar/vr-core-release.aar`，放进宿主的 `libs/` 并通过 `implementation files('libs/vr-core-release.aar')` 引入。最小显示接线为：

```java
VrRenderer renderer = new VrRenderer();
GLSurfaceView surface = new GLSurfaceView(activity);
surface.setEGLContextClientVersion(2);
surface.setRenderer(renderer);
renderer.setSettings(new VrSettings());

AndroidPoseSource pose = new AndroidPoseSource(
    activity, activity.getWindowManager().getDefaultDisplay());
if (pose.isAvailable()) {
    pose.start((yaw, pitch, roll, timestampNanos) ->
        renderer.setPose(yaw, pitch, roll));
}
// JPEG 解码或宿主图像就绪后：renderer.submitFrame(bitmap)。
```

这是接线片段，需放到宿主 Activity 的生命周期中。`PoseMath` 中的角度处理不依赖 Android，可作为抽出跨平台数学核心的起点；整个 AAR 仍依赖 Android。

嵌入时让宿主负责生命周期：进入前台时恢复 `GLSurfaceView`、调用 `renderer.resumeFrames()` 并启用传感器；离开时停止传感器、断开连接、调用 `renderer.pauseFrames()` 并暂停 `GLSurfaceView`。`submitFrame(bitmap)` **接管 Bitmap 所有权**，渲染器会回收提交的 Bitmap；不要再复用该实例。确保画面解码与网络接收不阻塞主线程；避免积累过期帧增加延迟。

只需要头部输入时可以复用姿态接口，自行映射到宿主相机；只需要 VR 盒子显示时可以用自己的图像来源，不运行 Windows 鼠标适配器。

### 嵌入 Swift 核心或 iOS 观看端

在 Xcode 项目添加 `ios/` 本地 Swift 包并依赖 **VRizationCore**。该包使用 Foundation，不依赖 UIKit、Metal、Core Motion 或 Network；公开 `VRSettings`、`VRProtocol`、`SettingsSync`、`SessionGeneration`、`HostSessionGate`、`ConnectionInput`、`PoseMath`、`RotationCenter`、`USBFraming`、`USBFrameDecoder`，没有第三方包依赖。包声明最低 iOS 13 / macOS 10.15，完整观看应用要求 iOS / iPadOS 15+ 和 Metal。

```swift
import VRizationCore

let poseJSON = try VRProtocol.encodePose(sequence: 1, yaw: 0.12, pitch: 0.03)
let usbFrame = try USBFraming.encode(USBFrame(kind: .json, payload: poseJSON))
// WebSocket 发送 poseJSON；USB 连接发送 usbFrame。
```

可以只复用校验、同步或数学。完整应用提供 `StreamClient`、`USBListener`、`MotionSource`、`JPEGDecoder`、`StereoRenderer`，需按宿主生命周期和界面调整；进入后台时停止网络 / 监听与姿态，清掉旧会话任务，并显式重连。游戏内部相机可直接接收姿态而不运行 Windows 鼠标适配器。核心不是已安装的 Unity / Unreal 插件，也不是 ABI 稳定 SDK；分发时保留原创 MIT 声明。参见 [iOS 构建和签名](IOS.md)。

### Windows 与验证边界

电脑发行目标为 Windows 10 / 11 **x64**，采集使用物理像素坐标，并优先现代 DPI API、回退较旧 Windows API。本地实际桌面证据来自 Windows 11；回退单测不代表 Windows 10 硬件或所有混合 DPI 显示器组合已经通过。按当前名称选择目标显示器，核对自己系统的小窗口和缩放表现。

华为 Android 硬件检查与 iOS 模拟 usbmux / 模拟器检查在 [验证记录](VALIDATION.md) 分开列出。原生模拟器会话不验证真实 iPhone、姿态轴向、盒子镜片或真实 FPS 游戏。USB 不会令系统鼠标输入通用化；原始输入、权限边界和游戏保护可能拒绝它。

### 移植到其他平台

1. 按 [协议 v1](PROTOCOL.md) 实现连接、JPEG 帧接收和设置消息。
2. 把一张二维图像绘制到左右眼区域，先验证固定全屏。
3. 接入目标平台姿态，把坐标轴、角度单位和横屏方向校准清楚。
4. 如需要鼠标控制，在电脑端保留主动授权、序号 / 数值校验、断线停止与紧急停止。
5. 如需要真正立体游戏画面，在游戏 / 引擎侧为左右眼分别渲染，并定义新协议。这超出当前二维桌面复制能力。

Swift 协议 / 数学已经可以复用；引擎适配器和稳定 SDK 仍是未来方向。现阶段不要把 Alpha 接口作为长期兼容承诺。

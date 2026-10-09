# 🧩 Architecture and integration / 架构与集成

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

VRization separates the image source, transport, rendering and input sink. Reuse currently means source integration or an Android library; alpha APIs may change.

```mermaid
flowchart LR
    A[Display or rectangle] --> B[CaptureSource]
    B --> C[JPEG encoding]
    C --> D[HostServer / WebSocket v1]
    D --> E[Android StreamClient]
    E --> F[VrRenderer / both eyes]
    G[PoseSource / rotation sensor] --> F
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
| `docs/` | Tutorials, protocol, integration and scope. |

`vr-core` is written in Java but depends on Android OpenGL ES, Bitmap and sensor APIs. Its AAR embeds in Android software; it is not a platform-independent Java / Unity / Unreal library. Other platforms can implement the protocol and adapt pose / rendering to their engine.

### Replace the host image source

`CaptureSource` defines `read(config: CaptureConfig) -> Frame` and `close()`. `Frame` contains JPEG bytes, width, height and monotonic `captured_at`. The default source captures and encodes the desktop. An adapter can supply game-rendered images, remote application output or test frames.

Inject adapters with `HostServer(capture_source=..., input_sink=...)`. Capture and input are independent; sending images does not require enabling input.

The runnable [embedded_host.py](../examples/embedded_host.py) provides an original animated calibration card and a logging input sink. It neither captures the user's screen nor sends OS input. After installing the host package, run `python examples/embedded_host.py` from the root, then connect the phone using the printed port and code plus the PC's LAN IP.

```python
# Implement CaptureSource.read / close and InputSink.move in your adapters.
server = HostServer(capture_source=my_capture, input_sink=my_input)
```

v1 carries JPEG. Hardware H.264 / H.265 requires new framing, timestamps, keyframe recovery and a compatible decoder; do not send a video bitstream to the v1 JPEG decoder.

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

### Port to another platform

1. Implement [protocol v1](PROTOCOL.md), JPEG reception and settings.
2. Render one 2D frame in both eye regions and validate full screen first.
3. Integrate pose and calibrate axes, radians and landscape orientation.
4. If using remote mouse input, retain local authorization, sequence / number checks, disconnect stop and an emergency stop.
5. True stereo requires engine-side per-eye rendering and a new protocol; current desktop duplication cannot create it.

A separate math core, engine adapters and stable SDK are possible future work. Alpha interfaces carry no long-term compatibility promise.

---

<!-- vrization:chinese -->
## 简体中文

VRization 把“从哪里来画面”“怎样传输”“怎样显示”“怎样发出输入”拆为相邻组件。当前的复用方式是源码 / Android library 集成；公共接口仍处于 Alpha，可能随版本调整。

```mermaid
flowchart LR
    A[电脑显示器或矩形区域] --> B[CaptureSource]
    B --> C[JPEG 编码]
    C --> D[HostServer / WebSocket v1]
    D --> E[Android StreamClient]
    E --> F[VrRenderer 双眼显示]
    G[PoseSource 旋转传感器] --> F
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
| `docs/` | 教程、协议、移植与版本边界。 |

`vr-core` 使用 Java 编写，但依赖 Android 的 OpenGL ES、Bitmap 与传感器 API。它可生成 AAR 并嵌入其他 Android 软件；不能直接作为无平台依赖的 Java / Unity / Unreal 库使用。跨平台客户端可以独立实现协议，将姿态与显示逻辑适配到目标引擎。

### 替换电脑画面来源

桌面端 `CaptureSource` 接口定义 `read(config: CaptureConfig) -> Frame` 和 `close()`。`Frame` 包含 `jpeg: bytes`、`width`、`height` 和单调时钟 `captured_at`；默认实现采集并编码桌面。其他软件可以提供自己的 JPEG 帧，例如游戏已渲染的图像、远程应用输出或测试画面，再交给同一主机服务。

通过 `HostServer(capture_source=..., input_sink=...)` 注入适配器。画面与输入接口分开，集成者可以只发送图像而不启用任何输入。

可直接运行的 [embedded_host.py](../examples/embedded_host.py) 用原创动态校准卡替换桌面采集，用日志接收器替换系统鼠标，不采集用户屏幕、不发送 OS 输入。安装电脑端包后，在仓库根目录执行 `python examples/embedded_host.py`，再用手机连接控制台显示的端口和配对码；服务的电脑 IP 仍需填写局域网地址。

示意接口关系（具体类名与构造参数以源码为准）：

```python
# 自己实现 CaptureSource.read / close 与 InputSink.move。
server = HostServer(capture_source=my_capture, input_sink=my_input)
```

当前传输的数据是 JPEG。若替换为硬件 H.264 / H.265，应一起设计新帧封装、时间戳、关键帧恢复和客户端解码，不能直接把视频码流发送给 v1 的 JPEG 解码器。

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

### 移植到其他平台

1. 按 [协议 v1](PROTOCOL.md) 实现连接、JPEG 帧接收和设置消息。
2. 把一张二维图像绘制到左右眼区域，先验证固定全屏。
3. 接入目标平台姿态，把坐标轴、角度单位和横屏方向校准清楚。
4. 如需要鼠标控制，在电脑端保留主动授权、序号 / 数值校验、断线停止与紧急停止。
5. 如需要真正立体游戏画面，在游戏 / 引擎侧为左右眼分别渲染，并定义新协议。这超出当前二维桌面复制能力。

未来可能抽出纯数学核心、引擎适配器和稳定 SDK。现阶段不要把 Alpha 接口作为长期兼容承诺。

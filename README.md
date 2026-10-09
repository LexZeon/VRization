# 🥽 VRization

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

**Put your PC screen inside a phone VR viewer.**

![Alpha](https://img.shields.io/badge/version-0.1.1--alpha-orange)
![License](https://img.shields.io/badge/license-MIT-green)
![Desktop](https://img.shields.io/badge/desktop-Windows%2010%2F11-blue)
![Android](https://img.shields.io/badge/Android-6.0%2B-3DDC84)
[![Build](https://github.com/LexZeon/VRization/actions/workflows/build.yml/badge.svg)](https://github.com/LexZeon/VRization/actions/workflows/build.yml)

[简体中文](#简体中文) · [Quick start / 上手教程](docs/QUICKSTART.zh-CN.md) · [Build](docs/BUILD.md) · [Architecture](docs/ARCHITECTURE.md)

VRization streams a Windows desktop or rectangular region to an Android phone, renders the image side by side, and optionally maps phone rotation to PC mouse movement. Its reusable Android library (written in Java) and separated host components provide a starting point for embedding these features in other applications.

**v0.1.1-alpha is a working baseline.** CPU JPEG over WebSocket is intended to establish the capture, viewing, settings and input paths. It does not promise production VR latency. Both eyes receive the same 2D source: ordinary games do not acquire stereoscopic depth.

| Mode | Behavior |
| --- | --- |
| 🖥️ Full screen | A fixed image in each eye; no sensor control. |
| 🎬 Cinema | A virtual screen viewed through phone rotation. |
| 🎯 FPS | Side-by-side viewing plus rotation-to-mouse input, explicitly armed on the PC. Press **F8** to stop input. |

Adjust image scale and offsets for large phones, eye separation, field of view, screen distance, distortion, recentering, mouse sensitivity and vertical inversion. The host also offers display / region selection and stream quality controls.

### 📸 Interface

| Windows host | Android client |
| --- | --- |
| ![Running Windows host](docs/images/desktop.png) | ![Running Android client](docs/images/android.png) |

Phone screenshots show the final v0.1.1 English interface on a Google-free Android 6.0 / API 23 emulator receiving the project's original [animated calibration card](examples/embedded_host.py). They document connection and rendering, not physical headset compatibility or latency / performance benchmarks.

### 🚀 Try it

1. Download the Windows archive and Android APK from [Releases](https://github.com/LexZeon/VRization/releases/tag/v0.1.1-alpha), or [build from source](docs/BUILD.md).
2. Connect both devices to the same trusted LAN. Prefer wired Ethernet for the PC and a strong Wi-Fi connection for the phone.
3. Start the host, choose a display or region, and start streaming. Allow the Windows firewall prompt only for a trusted private network.
4. Enter the host's displayed IP address, port and pairing code on the phone. Start in full-screen mode.
5. Adjust the image to your viewer, recenter cinema mode, and explicitly arm PC mouse input before trying FPS mode.

Windows 10 / 11 x64 is the desktop target. Android 6.0+ and compatible derivatives need no Google services; derivative-system compatibility depends on their APK, rendering and sensor support. Full-screen viewing does not require a gyroscope. Games may reject simulated mouse input, especially under raw-input or anti-cheat restrictions.

The host requires Microsoft Visual C++ v14 x64 runtime. If launch reports a missing `VCRUNTIME140` DLL or error 126, use [Microsoft's official runtime guide](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist/) and [current x64 installer](https://aka.ms/vc14/vc_redist.x64.exe).

### 🧩 Reuse and limitations

See [architecture](docs/ARCHITECTURE.md) and [protocol v1](docs/PROTOCOL.md) for integration. The current deliverable is source-level modules, not a stable public SDK, Unity / Unreal plug-in or OpenXR driver.

Audio, hardware video encoding, WebRTC, dedicated USB transport, native stereo game rendering and 6DoF position tracking are not included. Real-world performance and device support require testing on your hardware.

See the [validation record / 验证记录](docs/VALIDATION.md) for the first-release record and v0.1.1 checks (20 host tests, 6 Android core tests and 9 app regression tests). Physical gyro behavior, headset optics and actual FPS game input remain unverified.

Transport uses **unencrypted `ws://`**. The pairing code is an access gate, not encryption. Use trusted LANs only; do not expose the port to the internet. See [security](SECURITY.md).

### 🤝 License and credit

Original code is [MIT](LICENSE), including commercial use subject to its notice requirements. Dependencies retain their licenses. See [third-party notices](THIRD_PARTY_NOTICES.md), [NOTICE](NOTICE) and [contributing](CONTRIBUTING.md). No implementation source was copied from another VR application.

### ✨ Fit different phones and viewers

- Scale and horizontal / vertical offsets fit a large phone's effective image inside the lenses.
- Eye separation, field of view, virtual distance and distortion adapt the presentation to your viewer.
- Recenter sets the current head orientation as forward.
- Mouse sensitivity and invert Y adjust FPS controls.
- Display / rectangle, **longest output edge**, FPS and JPEG quality control capture cost while preserving aspect ratio.
- Full-screen mode needs no sensor; compatible Android derivatives depend on their APK, graphics, network and sensor support.

<details>
<summary>🥽 Both-eye viewing and viewer-fit controls</summary>

![The same 2D frame in both eyes with controls hidden](docs/images/android-vr.png)

Long-press or Back restores hidden controls. Double-tap recenters.

![Viewer-fit settings](docs/images/android-settings.png)

Adjust scale and offsets for your phone and lenses rather than assuming one shared preset.

</details>


Both applications offer **English / 简体中文**, default to English, and save the choice locally. Use the PC header selector or the phone settings language selector. PC switching preserves the stream but disarms mouse input; phone switching rebuilds the screen, disconnects and requires reconnecting. See [compatibility targets and observed tests](docs/COMPATIBILITY.md).

### 🌐 Documentation languages

Every project-owned public page presents complete **English first**, then complete **Chinese below**. Both sections must be maintained together. Automated documentation checks verify structure and file links, not translation quality. Original license texts remain unchanged.

The host separates capture, JPEG transport and input; Android `vr-core` exposes pose and GLES rendering. A cross-platform client can implement [protocol v1](docs/PROTOCOL.md). See the [roadmap](docs/ROADMAP.md) for future adapters and codecs. The Android AAR depends on Android framework APIs and is not a platform-independent Java SDK.

---

<!-- vrization:chinese -->
## 简体中文

**把电脑画面装进手机 VR 盒子。**

Windows 桌面串流 · Android / 兼容 Android 的系统 · 可复用的核心模块

![Alpha](https://img.shields.io/badge/version-0.1.1--alpha-orange)
![License](https://img.shields.io/badge/license-MIT-green)
![Desktop](https://img.shields.io/badge/desktop-Windows%2010%2F11-blue)
![Android](https://img.shields.io/badge/Android-6.0%2B-3DDC84)
[![Build](https://github.com/LexZeon/VRization/actions/workflows/build.yml/badge.svg)](https://github.com/LexZeon/VRization/actions/workflows/build.yml)

[🚀 上手教程](docs/QUICKSTART.zh-CN.md) · [🛠️ 开发与构建](docs/BUILD.md) · [🧩 集成指南](docs/ARCHITECTURE.md) · [English](README.en.md)


VRization 是一个开源的电脑 → 手机串流实验项目。电脑端采集显示器或指定矩形区域，手机端将画面显示在 VR 盒子的左右眼区域。你可以让画面固定在眼前，也可以把它当成一个随头部转动观看的虚拟大屏幕，或者用手机的姿态控制电脑游戏视角。

> **当前版本：可运行的 Alpha 基础版。** 使用 CPU 编码 JPEG + WebSocket，优先打通安装、串流、调节与模块复用；尚未达到专用 VR 串流产品的画质、延迟和稳定性。左右眼接收同一张二维桌面图像，**不会把普通游戏自动变成立体 3D**。

### 🎮 三种观看方式

| 模式 | 画面表现 | 手机姿态 | 适合做什么 |
| --- | --- | --- | --- |
| 🖥️ 全屏模式 | 同一画面分别填入左右眼区域 | 不参与画面或鼠标控制 | 稳定观看桌面、视频和普通游戏 |
| 🎬 大屏幕模式 | 电脑或选区画面放在虚拟平面上 | 转头改变观看方向 | 像在眼前放了一块大屏幕 |
| 🎯 FPS 游戏模式 | 左右眼显示游戏画面 | 转头映射成电脑鼠标移动 | 在支持普通鼠标输入的游戏里试验头部瞄准 |

FPS 控制需要在**电脑端主动授权**。手机连接或切换模式不会自动接管鼠标；按电脑键盘 **F8** 可以立即停止控制。不同游戏、独占全屏、原始输入和反作弊机制可能不接受这种输入，建议先用桌面或离线游戏验证。

### ✨ 为不同手机与盒子留出调节空间

- **画面缩放与水平 / 垂直偏移**：大手机也能把有效画面收进镜片可见区域。
- **左右眼间距、视场角、虚拟屏幕距离、畸变调节**：根据盒子镜片与佩戴方式微调。
- **重新居中**：把当前头部方向设为正前方。
- **鼠标灵敏度与 Y 轴反转**：调整 FPS 头部控制手感。
- **显示器 / 矩形选区、输出最长边、帧率和 JPEG 质量**：保持画面比例，同时限制横屏与竖屏的解码负担。
- **纯局域网、无需 Google 服务**：Android 6.0+，可在提供 Android APK 兼容层的系统上尝试安装。兼容性仍取决于设备的图形、网络与传感器实现；全屏模式不要求陀螺仪。

### 📸 看看界面

电脑端负责选画面、开串流和授权 FPS；手机端负责连接、观看和调整镜片中的布局。

| 电脑控制台 | 手机客户端 |
| --- | --- |
| ![VRization 电脑端实际界面](docs/images/desktop-zh.png) | ![VRization Android 客户端实际界面](docs/images/android.png) |

图示来自项目运行界面。手机图为最终 v0.1.1 默认英文界面，运行于不含 Google 服务的 Android 6.0 / API 23 模拟器，画面为本项目的 [动态校准卡示例](examples/embedded_host.py)；可在语言设置切换简体中文。截图展示连接与显示流程，不代表手机盒子实机测试结果；接收帧率不是延迟或性能基准。

<details>
<summary>🥽 展开：双眼观看与盒子适配设置</summary>

![隐藏设置后的双眼画面，接收同一张二维校准卡](docs/images/android-vr.png)

隐藏操作区后，将同一张二维画面显示在左右眼区域。长按画面或按返回键可恢复设置。

![手机端画面缩放、位置、双眼间距与镜片畸变调节](docs/images/android-settings.png)

用缩放与偏移让大手机的有效画面收进盒子镜片范围。不同手机与镜片需要分别调整。

</details>

### 🚀 五步把电脑放进盒子

1. 在 [Releases](https://github.com/LexZeon/VRization/releases/tag/v0.1.1-alpha) 下载 Windows 电脑端压缩包与 Android APK；首次体验建议使用同一个版本。
2. 让电脑与手机连接同一可信局域网。电脑尽量接网线，手机靠近 5 GHz / 6 GHz 路由器。
3. 打开电脑端，选显示器或矩形区域，再开始串流。如果 Windows 弹出防火墙提示，只允许可信的**专用网络**。
4. 在手机端填写电脑端显示的 IP 地址、端口与配对码，连接后先试全屏模式。
5. 调整缩放、偏移和眼间距，确认两眼舒适对齐，再放入 VR 盒子。大屏幕模式先重新居中；FPS 模式还需在电脑端授权鼠标控制。

Windows 端需要 Microsoft Visual C++ v14 x64 运行库。多数电脑已经安装；如果启动提示缺少 `VCRUNTIME140*.dll`、加载 Python DLL 失败或错误 126，再按 [微软官方说明](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist/) 安装 [当前受支持的 x64 运行库](https://aka.ms/vc14/vc_redist.x64.exe)。

详细步骤、截图说明和常见问题见 [上手教程](docs/QUICKSTART.zh-CN.md)。还没有下载产物时，可以按 [构建指南](docs/BUILD.md) 从源码启动。

### 🧩 为移植而拆开的结构

```text
Windows 桌面端                         Android 手机端
采集 → JPEG 编码 → WebSocket ───────→ 解码 → 双眼显示
鼠标输入 ← 姿态增量与本机授权 ←─────── 旋转传感器
                 ↑                      ↑
          Python 主机模块          Android vr-core library
```

`vr-core` 是 Java 编写的 Android library，提供姿态与双眼渲染接口；桌面端把采集、网络和输入分开。集成到其他 Android 软件 / 游戏时，可以复用核心库；跨平台客户端可以按协议替换画面来源、传输或输入适配器。当前提供源码级模块和协议说明，尚无 Unity / Unreal 插件、OpenXR 驱动或公开稳定 SDK。

参见 [架构与移植](docs/ARCHITECTURE.md)、[协议 v1](docs/PROTOCOL.md) 和 [后续路线](docs/ROADMAP.md)。

### 🧪 当前边界

Alpha 版尚未提供音频、硬件视频编码、WebRTC、USB 专用通道、原生立体渲染或 6DoF 位置追踪。没有承诺帧率或端到端延迟数字；实际体验取决于电脑、手机和网络。传感器不足的设备可以使用全屏模式，大屏幕 / FPS 需要兼容的旋转传感器。已完成的检查与尚需实测的项目见 [验证记录](docs/VALIDATION.md)。

串流使用明文 `ws://`，配对码只是基础访问门槛，**不是加密**。只在可信局域网使用，不要把服务端口映射到公网。详见 [安全说明](SECURITY.md)。

### 🤝 开源与致谢

原创代码以 [MIT](LICENSE) 授权，允许商业使用并要求保留相关许可与版权声明。依赖保留各自许可证；来源、用途、作者与分发注意事项记录在 [第三方声明](THIRD_PARTY_NOTICES.md) 和 [NOTICE](NOTICE)。本项目没有复制其他 VR 应用的实现源码。

感谢 aiohttp、MSS、Pillow、OkHttp、Okio、Kotlin 及相关工具的维护者。欢迎提交兼容性记录、问题、翻译与 PR，开始前可看 [贡献指南](CONTRIBUTING.md)。


两端可选 **English / 简体中文**，默认英文，各自保存。电脑在顶部切换，手机在设置中切换；电脑切换保持串流但解除鼠标授权，手机切换会重建界面并断线，需要重连。支持目标与实际检查分开记录，见 [兼容性](docs/COMPATIBILITY.md)。

### 🌐 文档语言

所有项目自有公共页面在同一页先完整英文、再完整中文，修改时同步维护两种语言。自动文档检查只验证结构和文件链接，不判断翻译质量；原始许可证全文保持不变。

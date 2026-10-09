# 🥽 VRization v0.2.0-alpha — release notes / 发布说明

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

Windows screen → Android, iPhone or iPad VR viewing, with fixed full screen, a head-tracked cinema screen and gyro-to-mouse FPS mode. English is the default; Simplified Chinese is selectable and saved. FPS still requires explicit PC arming; **F8** stops input.

### New in v0.2.0-alpha

- Native iOS / iPadOS 15+ client: UIKit, Metal, Core Motion and a reusable dependency-free Swift core package. Includes viewer-fit settings, recentering, settings acknowledgments, session validation, foreground lifecycle handling and language choice.
- **USB is the default** on the Windows host and both mobile clients. Authorized physical Android devices use official ADB reverse forwarding and local host discovery; iOS uses Apple's Windows USB service and an original framed relay. LAN with manual pairing remains available.
- Automatic authorized-device detection: one Android phone is selected automatically; multiple Android devices require selection. iOS supports one attached Apple mobile device. Start streaming on the PC and keep the phone app in the foreground. Backgrounding or changing phone language requires explicit reconnecting.
- Low-latency preset for new configurations: maximum long edge **960**, target **60 FPS**, JPEG quality **60**. Stable, quality and custom settings let you balance load and clarity. The phone reports receive FPS and link round trip; neither measures end-to-end video latency.
- Windows DPI fallbacks, USB mapping ownership / cleanup, local bootstrap request restrictions, and bounded iOS framing / handshake validation.
- Illustrated bilingual USB / iOS guides and a verified local release archive tool that preserves historical versions and a fully extracted latest Windows program. Every project-owned public page remains complete English first, then Chinese below.

### Verification and limits

The new Android APK upgraded a physical **HUAWEI Pura 70 Ultra** in place, using the same local signing certificate. Real USB host discovery, automatic connection after a fresh app launch, JPEG reception, both-eye rendering and real sensor-pose reception were observed. These tests used an original calibration card and a fake mouse sink; they do not establish headset optics, game compatibility or gyro-axis accuracy. Exact checks, build outcomes and later measurements are recorded in [validation](https://github.com/LexZeon/VRization/blob/main/docs/VALIDATION.md).

The iOS USB bridge has software / simulated-device tests. **No physical iPhone USB test has been completed.** iOS source and Mac Simulator builds require different installation steps: a physical iPhone needs a Mac, Xcode and your Apple signing. No signed, directly installable iPhone IPA is supplied. See [the iOS guide](https://github.com/LexZeon/VRization/blob/main/docs/IOS.md).

### Downloads

- `VRization-Windows-x64.zip`: extract completely and run `VRization-Host.exe`; Windows 10 / 11 x64 target.
- `VRization-Android-debug.apk`: Android 6.0+ test-signed APK. APK-compatible derivatives depend on their device capabilities.
- `VRization-vr-core-alpha.aar`: reusable Android core; alpha APIs.
- `VRization-iOS-source.zip`: editable Xcode project and Swift core; sign for your own device on a Mac.
- `VRization-iOS-Simulator.zip`: Mac Simulator build, not an iPhone installer or a Windows app.
- `VRization-Licenses.zip` and `SHA256SUMS.txt`: license / provenance records and download checksums.

### First USB connection

Android: install official Platform Tools → enable and authorize USB debugging → connect a data cable → select the display and Start streaming on the PC → open the phone app in USB mode. iPhone: first sign / install with Xcode, install Apple Devices on Windows and approve Trust, then keep the app in the foreground. Use the phone connection button if its first attempt has ended. Follow the [USB tutorial](https://github.com/LexZeon/VRization/blob/main/docs/USB.md) and [download / archive guide](https://github.com/LexZeon/VRization/blob/main/docs/DOWNLOADS.md).

### Alpha boundaries

CPU JPEG sends the same 2D image to both eyes. Audio, hardware video encoding, native game stereo and 6DoF tracking are not provided. Actual frame rate and latency depend on the hardware; a 60 FPS target is not a performance guarantee. LAN `ws://` is unencrypted: use trusted networks and never expose the port to the internet. USB requires platform authorization and never arms mouse input automatically.

Android uses a debug signature; a build from another machine can require uninstalling the old app and clearing its settings. The Windows EXE has no commercial code signature and requires Microsoft's Visual C++ v14 x64 runtime, supplied separately. For a missing DLL / error 126, follow [Microsoft's runtime guide](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist/).

---

<!-- vrization:chinese -->
## 简体中文

Windows 电脑画面 → Android、iPhone 或 iPad VR 观看，支持固定全屏、头部追踪虚拟大屏幕与陀螺仪转鼠标 FPS 模式。默认英文，可选择并保存简体中文。FPS 仍需电脑主动授权，**F8** 停止输入。

### v0.2.0-alpha 新增

- 原生 iOS / iPadOS 15+ 客户端，使用 UIKit、Metal、Core Motion，以及无外部依赖的可复用 Swift 核心包。包含盒子适配、回正、设置确认、会话校验、前台生命周期处理与语言选择。
- Windows 和两种手机端均**默认 USB**。已授权 Android 真机通过官方 ADB 反向转发与本机服务发现连接；iOS 通过 Apple 的 Windows USB 服务和原创分帧中继连接。保留手动配对的局域网方式。
- 自动检测授权设备：一台 Android 自动选择，多台需选择；iOS 支持连接一台 Apple 移动设备。电脑需开始串流，手机需保持前台。手机进入后台或切换语言后需显式重连。
- 新配置默认低延迟预设：最长边 **960**、目标 **60 FPS**、JPEG 质量 **60**。另有稳定、清晰与自定义设置。手机显示接收帧率和链路往返时间，两者都不是端到端视频延迟。
- Windows DPI 回退、USB 映射归属与清理、本地 bootstrap 请求限制，以及 iOS 分帧大小与握手校验。
- 新增双语图文 USB / iOS 教程及校验式本地归档工具，保留历史版本和完整解压的最新版 Windows 程序。所有自有公共页面继续先完整英文、再完整中文。

### 验证与限制

新版 APK 使用同一本地签名在 **HUAWEI Pura 70 Ultra 真机**覆盖升级，已观察到真实 USB 服务发现、新启动自动连接、JPEG 接收、双眼渲染与真实传感器姿态接收。测试采用原创校准卡与假鼠标接收器，不代表镜片舒适度、游戏兼容性或陀螺仪轴向已经验证。确切检查、构建结果与后续测量见 [验证记录](https://github.com/LexZeon/VRization/blob/main/docs/VALIDATION.md)。

iOS USB 目前有软件 / 模拟设备桥接测试，**尚未完成真实 iPhone USB 测试**。iOS 源码与 Mac 模拟器构建安装方式不同：真机需要 Mac、Xcode 和自己的 Apple 签名，未提供可直接安装的已签名 iPhone IPA。详见 [iOS 教程](https://github.com/LexZeon/VRization/blob/main/docs/IOS.md)。

### 下载

- `VRization-Windows-x64.zip`：完整解压后运行 `VRization-Host.exe`；目标 Windows 10 / 11 x64。
- `VRization-Android-debug.apk`：Android 6.0+ 测试签名 APK；兼容 APK 的衍生系统取决于设备能力。
- `VRization-vr-core-alpha.aar`：可复用 Android 核心，仍为 Alpha API。
- `VRization-iOS-source.zip`：可编辑 Xcode 项目和 Swift 核心，在 Mac 为自己的真机签名。
- `VRization-iOS-Simulator.zip`：Mac 模拟器构建，不是 iPhone 安装包或 Windows 软件。
- `VRization-Licenses.zip` 与 `SHA256SUMS.txt`：许可证 / 来源记录与下载校验值。

### 首次 USB 连接

Android：安装官方 Platform Tools → 开启 USB 调试并授权 → 接数据线 → 电脑选择屏幕并开始串流 → 手机打开 USB 模式。iPhone：先用 Xcode 签名安装，Windows 安装 Apple Devices 并允许信任，保持手机应用前台。如果首次连接尝试已结束，点手机连接按钮。详见 [USB 教程](https://github.com/LexZeon/VRization/blob/main/docs/USB.md) 与 [下载 / 本地归档说明](https://github.com/LexZeon/VRization/blob/main/docs/DOWNLOADS.md)。

### Alpha 边界

CPU JPEG 向两眼发送同一二维图像，未提供音频、硬件视频编码、原生游戏立体画面与 6DoF 追踪。实际帧率与延迟取决于硬件，目标 60 FPS 不是性能保证。局域网 `ws://` 未加密，仅在可信网络使用，不要开放到公网。USB 需要平台授权，不会自动开启鼠标控制。

Android 使用测试签名，其他机器构建可能需要卸载旧版并清除设置。Windows EXE 没有商业代码签名，需要另行安装微软 Visual C++ v14 x64 运行库。缺少 DLL / 错误 126 时见 [微软运行库说明](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist/)。

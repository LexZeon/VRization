# 🥽 VRization v0.3.0-alpha — release notes / 发布说明

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

This release adds visual headset fitting and saved phone profiles to the Windows / Android / iOS viewer. The GPU capture, USB transports and latency work were published separately in [v0.2.0-alpha](releases/v0.2.0-alpha.md); its verified downloads and local archive are retained. v0.3 application builds / UI acceptance are being completed; only checks explicitly recorded in [validation](VALIDATION.md) count as passed.

### New in v0.3.0-alpha

- Visual headset fitting is first in each application's settings: Windows **Headset editor**, Android **Fit headset visually**, and iOS **Visual headset fit editor**. Drag either eye horizontally for linked spacing, vertically to move both, or a corner to resize both while keeping centers and aspect ratio fixed. The PC offers an approximate phone-shaped preview with a selectable aspect ratio.
- Linked mirrored eye spacing works on all three applications: left-eye left / right-eye right widens, left-eye right / right-eye left narrows. Global offsetX is preserved; vertical movement and corner resize stay normal, and FPS mouse mapping is unchanged. Connected Save synchronizes PC ↔ phone through normal validated settings / acknowledgments / broadcasts and preserves committed profiles on both sides; offline Save stays local until a valid connection.
- **Save / Discard:** the editor is a local draft. Preview dragging sends no host setting updates and writes no preferences. Phone Save commits the complete draft; PC Save updates only the fit fields into current host settings, preserving other concurrent changes; Discard restores the entry snapshot. A flat, undistorted preview preserves the actual viewing mode and other optical values. Editing pauses phone pose messages and sends disarm-only hello metadata on entry; it never arms mouse control. The PC preview reuses existing JPEGs without starting another capture.
- **Persistent phone profiles:** committed VR settings survive restarts and offline changes. After a validated host hello, a saved phone profile is restored through one normal settings update with a fresh client sequence. Subsequent host changes retain revision / acknowledgment synchronization. Pairing secrets are not saved.
- **Reset all settings:** restore VR defaults, English and USB. Windows restores low-latency capture defaults (640 / 60 / Q45) and automatic USB choice, while preserving the explicitly chosen capture display / rectangle and ADB executable path. Phone reset clears its preferences / pairing field and disconnects without reconnecting automatically.
- The original reusable Python geometry / transaction module and matching Android / Swift geometry use the same normalized coordinates, center-fixed corner projection and wire bounds. See [the behavior and integration contract](EDITING.md).

### Verification and inherited limits

The original Python geometry / transaction has 20 automated checks for aspect fit, both-eye spacing, all four corners, all four selected-eye drag directions, clamp limits, preserved global X, gesture-start deltas, invalid inputs and commit / discard. These are pure checks with no screen capture, OS mouse input or physical headset. Application and device acceptance must be recorded separately; inherited v0.2 performance numbers are not new v0.3 measurements.

Targets remain Windows 10 / 11 x64, Android 6.0+ with GLES 2.0, and iOS / iPadOS 15+ with Metal. The iOS USB bridge has native Simulator / simulated-usbmux evidence; **physical iPhone USB, physical headset optics and real FPS game input remain unverified**. iPhone installation still needs a Mac, Xcode and your Apple signing. The Simulator download is arm64 for an Apple Silicon Mac, not an iPhone IPA or Windows app.

Capture profiles remain longest edge / target FPS / JPEG quality: low **640 / 60 / Q45**, stable **640 / 30 / Q50**, quality **960 / 30 / Q60**, plus custom. Both eyes receive the same 2D image. No audio, hardware video encoding, native game stereo or 6DoF position tracking is supplied. FPS targets, link RTT and phone-local texture-submission times are not end-to-end video-latency guarantees. See [performance boundaries](PERFORMANCE.md).

### Downloads and setup

The asset names remain `VRization-Windows-x64.zip`, `VRization-Android-debug.apk`, `VRization-vr-core-alpha.aar`, `VRization-iOS-source.zip`, `VRization-iOS-Simulator.zip`, `VRization-Licenses.zip` and `SHA256SUMS.txt`. Completely extract Windows, keep its license / documentation folders and use the separate Microsoft Visual C++ v14 x64 runtime. The APK remains test-signed; preserving application data on upgrade requires a matching certificate. iOS source is editable, not pre-signed for your phone.

Follow [quick start](QUICKSTART.md), [USB setup](USB.md), [iOS signing](IOS.md) and [verified download / local archive instructions](DOWNLOADS.md). Select the intended display before starting capture. USB connection, profile restore, Save and Reset never authorize PC mouse input; FPS needs explicit PC arming and **F8** remains the stop key. LAN `ws://` remains unencrypted and should be used only on trusted networks.

[Release history](releases/README.md)

---

<!-- vrization:chinese -->
## 简体中文

本版在 Windows / Android / iOS 观看端加入可视盒子适配与手机本地配置。GPU 采集、USB 传输和延迟优化已先独立发布为 [v0.2.0-alpha](releases/v0.2.0-alpha.md)，已校验下载与本地归档继续保留。v0.3 应用构建 / 界面验收正在完成，只有 [验证记录](VALIDATION.md) 明确记载的检查才算通过。

### v0.3.0-alpha 新增

- 三端设置首位提供可视适配：Windows **画面编辑**、Android **可视化适配 VR 盒子**、iOS **可视化盒子画面编辑器**。横向拖任一眼联动间距、竖向同步移动，拖角点同步缩放，中心与图像比例保持；电脑提供可选择宽高比的近似手机形预览。
- 三端镜像联动眼间距：左眼向左 / 右眼向右拉开，左眼向右 / 右眼向左收拢；整体 offsetX 保留，竖向与角点缩放保持正常，FPS 鼠标映射不变。已连接的保存经普通合法设置 / 确认 / 广播同步电脑 ↔ 手机，两端保留已提交配置；离线保存先留在本地，等合法连接。
- **保存 / 放弃**：编辑器是本地草稿。预览拖动不向主机更新设置、不保存偏好；手机保存提交完整草稿，电脑只把适配字段合并到当前主机设置并保留其他并发变化；放弃恢复进入快照。平面、无畸变预览保留实际模式与其他光学值。编辑暂停手机姿态，进入时发送仅解除授权的 hello 元数据，不授权鼠标；电脑预览复用已有 JPEG，不新增采集。
- **手机配置持久保存**：已提交 VR 设置在重启和离线更改后保留。合法主机 hello 后，用新客户端序号通过一次普通设置更新恢复手机配置；后续电脑改动仍按 revision / 确认同步。不保存配对秘密。
- **重置全部设置**：恢复 VR 默认、英文和 USB。Windows 恢复低延迟采集默认 640 / 60 / Q45 与 USB 自动选择，但保留明确选择的采集显示器 / 选区及 ADB 程序路径；手机清除偏好 / 配对字段并断线，不自动重连。
- 原创可复用 Python 几何 / 事务模块和对应 Android / Swift 几何共用归一化坐标、中心固定的角点投影与协议边界。见 [操作行为与集成合同](EDITING.md)。

### 验证与继承限制

原创 Python 几何 / 事务已有 20 项自动检查，覆盖比例适配、双眼间距、四角、选中眼四种横向方向、端点限制、整体 X 保留、手势起点总位移、非法输入及提交 / 放弃。它们不采屏、不发操作系统鼠标输入，也不使用真实盒子；应用与设备验收需另记。v0.2 的性能数字不能当作新的 v0.3 测量。

目标仍为 Windows 10 / 11 x64、支持 GLES 2.0 的 Android 6.0+，以及支持 Metal 的 iOS / iPadOS 15+。iOS USB 有原生模拟器 / 模拟 usbmux 证据，**真实 iPhone USB、实际盒子镜片与真实 FPS 游戏输入仍未验证**。iPhone 安装仍需 Mac、Xcode 和自己的 Apple 签名；模拟器下载为 Apple Silicon Mac 的 arm64 应用，不是 iPhone IPA 或 Windows 软件。

预设仍按最长边 / 目标 FPS / JPEG 质量表示：低延迟 **640 / 60 / Q45**、稳定 **640 / 30 / Q50**、画质 **960 / 30 / Q60**，另有自定义。两眼接收同一二维图像，没有音频、硬件视频编码、原生游戏立体或 6DoF 位置追踪。目标 FPS、链路 RTT 和手机本地纹理提交耗时都不保证端到端视频延迟，见 [性能边界](PERFORMANCE.md)。

### 下载与安装

产物名称仍为 `VRization-Windows-x64.zip`、`VRization-Android-debug.apk`、`VRization-vr-core-alpha.aar`、`VRization-iOS-source.zip`、`VRization-iOS-Simulator.zip`、`VRization-Licenses.zip` 与 `SHA256SUMS.txt`。Windows 完整解压，保留许可 / 文档文件夹，另行使用 Microsoft Visual C++ v14 x64 运行库。APK 仍为测试签名，保留数据覆盖升级要求签名一致；iOS 源码可编辑，没有替你的手机预先签名。

按 [上手教程](QUICKSTART.md)、[USB 前提](USB.md)、[iOS 签名](IOS.md) 与 [已校验下载 / 本地归档](DOWNLOADS.md) 使用。采集前明确选择画面。USB 连接、配置恢复、保存和重置均不会授权电脑鼠标；FPS 须电脑主动授权，**F8** 仍为停止键。局域网 `ws://` 仍未加密，只用于可信网络。

[发布历史](releases/README.md)

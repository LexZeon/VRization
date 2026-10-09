# 🥽 VRization v0.3.0-alpha — release notes / 发布说明

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

This release adds visual headset fitting and saved phone profiles to the Windows / Android / iOS viewer. The GPU capture, USB transports and latency work were published separately in [v0.2.0-alpha](releases/v0.2.0-alpha.md); its verified downloads and local archive are retained. The local Windows / Android checks, physical Huawei acceptance, API 23 emulator checks and final iOS Simulator CI passed within the exact scope in [validation](VALIDATION.md). The new Windows GUI, physical iPhone USB, headset optics and real FPS game input remain unverified.

### New in v0.3.0-alpha

- Visual headset fitting is first in each application's settings: Windows **Headset editor**, Android **Fit headset visually**, and iOS **Visual headset fit editor**. Drag either eye horizontally for linked spacing, vertically to move both, or a corner to resize both with aspect ratio preserved and centers normally fixed. The PC offers an approximate phone-shaped preview with a selectable aspect ratio.
- Linked mirrored eye spacing works on all three applications: left-eye left / right-eye right widens, left-eye right / right-eye left narrows. Smaller images continue inward until seam contact; shared X is retained while space permits, then recenters. Vertical motion remains direct, corners keep centers fixed unless contact requires adjustment, and FPS mouse mapping is unchanged. Connected Save synchronizes PC ↔ phone through normal validated settings / acknowledgments / broadcasts and preserves committed profiles on both sides; offline Save stays local until a valid connection.
- **Save / Discard:** the editor is a local draft. Preview dragging sends no host setting updates and writes no preferences. Phone Save commits the complete draft; PC Save updates only the fit fields into current host settings, preserving other concurrent changes; Discard restores the entry snapshot. A flat, undistorted preview preserves the actual viewing mode and other optical values. Editing pauses phone pose messages and sends disarm-only hello metadata on entry; it never arms mouse control. The PC preview reuses existing JPEGs without starting another capture.
- **Persistent phone profiles:** committed VR settings survive restarts and offline changes. After a validated host hello, a saved phone profile is restored through one normal settings update with a fresh client sequence. Subsequent host changes retain revision / acknowledgment synchronization. Pairing secrets are not saved.
- **Reset all settings:** restore VR defaults, English and USB. Windows restores low-latency capture defaults (640 / 60 / Q45) and automatic USB choice, while preserving the explicitly chosen capture display / rectangle and ADB executable path. Phone reset clears its preferences / pairing field and disconnects without immediately reconnecting; a fresh launch resumes normal initial USB discovery / listening.
- The original reusable Python geometry / transaction module and matching Android / Swift geometry use the same normalized coordinates, proportional corner projection and resolved seam bounds. Signed eye separation uses −1…0.2 on the wire, with an aspect-dependent inward limit; existing nonnegative profiles and the 0.03 default remain valid. Update both ends: v0.2 does not understand negative values. The seam guarantee is for the flat preview / undistorted full or FPS view, not cinema perspective or lens distortion. See [the behavior and integration contract](EDITING.md).

### Verification and inherited limits

The original Python geometry / transaction has 28 automated checks for aspect fit, both-eye spacing, all four corners, all four selected-eye drag directions, clamp limits, remaining-gap X limits, small-image seam contact, resize contact correction, negative-profile commit / discard, gesture-start deltas, invalid inputs and commit / discard. These are pure checks with no screen capture, OS mouse input or physical headset. Application and device acceptance must be recorded separately; inherited v0.2 performance numbers are not new v0.3 measurements.

Final local checks passed: **152 Windows tests plus 36 subcases**, **70 Android JVM tests** and lint with zero errors / eight warnings. The local EXE audit matched 15 project modules, 44 notice files and all 38 recorded native components. The final APK's installed hash matched on the physical Huawei. Actual Huawei gestures / seam contact, Save / Discard, committed profile restart, PC ↔ phone persistence, language and reset passed, as did 14 real UI checks on the Google-free API 23 emulator. PC handlers were tested headlessly; **the new Windows GUI has not been accepted through actual interaction**. Final [CI 37897738507](https://github.com/LexZeon/VRization/actions/runs/37897738507) passed 65 Swift core tests and three real Simulator UI cases, both iOS SDK builds, LAN / simulated-USB reception, both-eye colors and signed-seam boundary checks, with no failures or skips. See [the precise validation](VALIDATION.md) and [unmodified editor screenshots](EDITING.md#physical-android-examples).

A separate 30.02-second v0.3 AW → Huawei USB run averaged **60.00 host sent FPS**; distinct JPEG reads were **53.70/s**. The phone retained a final-window **59.7 FPS / 9.7 ms receive-to-texture-call mean** after video stopped; individual ping observations were **8–11 ms**. These stages are not whole-session phone averages or end-to-end delay. See [performance](PERFORMANCE.md).

Targets remain Windows 10 / 11 x64, Android 6.0+ with GLES 2.0, and iOS / iPadOS 15+ with Metal. The iOS USB bridge has native Simulator / simulated-usbmux evidence; **physical iPhone USB, physical headset optics and real FPS game input remain unverified**. iPhone installation still needs a Mac, Xcode and your Apple signing. The Simulator download is arm64 for an Apple Silicon Mac, not an iPhone IPA or Windows app.

Capture profiles remain longest edge / target FPS / JPEG quality: low **640 / 60 / Q45**, stable **640 / 30 / Q50**, quality **960 / 30 / Q60**, plus custom. Both eyes receive the same 2D image. No audio, hardware video encoding, native game stereo or 6DoF position tracking is supplied. FPS targets, link RTT and phone-local texture-submission times are not end-to-end video-latency guarantees. See [performance boundaries](PERFORMANCE.md).

### Downloads and setup

The asset names remain `VRization-Windows-x64.zip`, `VRization-Android-debug.apk`, `VRization-vr-core-alpha.aar`, `VRization-iOS-source.zip`, `VRization-iOS-Simulator.zip`, `VRization-Licenses.zip` and `SHA256SUMS.txt`. Completely extract Windows, keep its license / documentation folders and use the separate Microsoft Visual C++ v14 x64 runtime. The APK remains test-signed; preserving application data on upgrade requires a matching certificate. iOS source is editable, not pre-signed for your phone.

Follow [quick start](QUICKSTART.md), [USB setup](USB.md), [iOS signing](IOS.md) and [verified download / local archive instructions](DOWNLOADS.md). Select the intended display before starting capture. USB connection, profile restore, Save and Reset never authorize PC mouse input; FPS needs explicit PC arming and **F8** remains the stop key. LAN `ws://` remains unencrypted and should be used only on trusted networks.

[Release history](releases/README.md)

---

<!-- vrization:chinese -->
## 简体中文

本版在 Windows / Android / iOS 观看端加入可视盒子适配与手机本地配置。GPU 采集、USB 传输和延迟优化已先独立发布为 [v0.2.0-alpha](releases/v0.2.0-alpha.md)，已校验下载与本地归档继续保留。v0.3 本地 Windows / Android 检查、华为真机验收、API 23 模拟器及最终 iOS 模拟器 CI 已在 [验证记录](VALIDATION.md) 明确范围内通过；新 Windows 界面、真实 iPhone USB、盒子镜片和真实 FPS 游戏输入仍未验证。

### v0.3.0-alpha 新增

- 三端设置首位提供可视适配：Windows **画面编辑**、Android **可视化适配 VR 盒子**、iOS **可视化盒子画面编辑器**。横向拖任一眼联动间距、竖向同步移动，拖角点同步缩放，保持图像比例、通常中心固定；电脑提供可选择宽高比的近似手机形预览。
- 三端镜像联动眼间距：左眼向左 / 右眼向右拉开，左眼向右 / 右眼向左收拢；缩小后仍可收拢到接缝；空间允许时保留共用 X，接近中缝时居中；竖向正常，角点通常中心固定，触发接触约束时必要修正，FPS 鼠标映射不变。已连接的保存经普通合法设置 / 确认 / 广播同步电脑 ↔ 手机，两端保留已提交配置；离线保存先留在本地，等合法连接。
- **保存 / 放弃**：编辑器是本地草稿。预览拖动不向主机更新设置、不保存偏好；手机保存提交完整草稿，电脑只把适配字段合并到当前主机设置并保留其他并发变化；放弃恢复进入快照。平面、无畸变预览保留实际模式与其他光学值。编辑暂停手机姿态，进入时发送仅解除授权的 hello 元数据，不授权鼠标；电脑预览复用已有 JPEG，不新增采集。
- **手机配置持久保存**：已提交 VR 设置在重启和离线更改后保留。合法主机 hello 后，用新客户端序号通过一次普通设置更新恢复手机配置；后续电脑改动仍按 revision / 确认同步。不保存配对秘密。
- **重置全部设置**：恢复 VR 默认、英文和 USB。Windows 恢复低延迟采集默认 640 / 60 / Q45 与 USB 自动选择，但保留明确选择的采集显示器 / 选区及 ADB 程序路径；手机清除偏好 / 配对字段并断线，当前界面不自动重连；全新启动恢复正常初次 USB 发现 / 监听。
- 原创可复用 Python 几何 / 事务模块和对应 Android / Swift 几何共用归一化坐标、等比角点投影与解析接缝边界。有符号眼间距协议范围为 −1…0.2、向内下限按比例计算，旧非负配置与默认 0.03 不变。v0.2 不理解负值，需两端更新。接缝保证只用于平面预览 / 无畸变全屏或 FPS，不含大屏幕透视或镜片畸变。见 [操作行为与集成合同](EDITING.md)。

### 验证与继承限制

原创 Python 几何 / 事务已有 28 项自动检查，覆盖比例适配、双眼间距、四角、选中眼四种横向方向、端点限制、剩余间隙对 X 限位、小画面接缝、接触放大修正、负值保存 / 放弃、手势起点总位移、非法输入及提交 / 放弃。它们不采屏、不发操作系统鼠标输入，也不使用真实盒子；应用与设备验收需另记。v0.2 的性能数字不能当作新的 v0.3 测量。

最终本地检查已通过：**Windows 152 项测试及 36 个子项**、**Android 70 项 JVM 检查**、lint 零错误 / 八警告；本地 EXE 审计匹配 15 个自有模块、44 份许可通知及全部 38 个原生组件，华为真机已安装最终 APK 的哈希一致。真机实际拖动 / 接缝、保存 / 放弃、已提交配置重启、电脑 ↔ 手机持久化、语言和重置均通过，无 Google API 23 模拟器另有 14 项真实界面检查。电脑处理器为无界面调用，**未通过真实交互验收新 Windows 界面**。最终 [CI 37897738507](https://github.com/LexZeon/VRization/actions/runs/37897738507) 通过 65 项 Swift 核心和三项真实模拟器界面用例、两种 iOS SDK 构建、局域网 / 模拟 USB 接收、双眼颜色及有符号接缝边界检查，无失败或跳过，见 [精确验证范围](VALIDATION.md) 与 [未修改的编辑原图](EDITING.md#android-真机示例)。

独立 30.02 秒 v0.3 AW → 华为 USB 会话主机平均 **60.00 发送 FPS**、每秒 **53.70 次不同 JPEG 读取**；视频停止后手机保留最终窗口 **59.7 FPS / 接收到纹理调用均值 9.7 毫秒**，个别 ping 观察 **8–11 毫秒**。这些不是整段手机均值或端到端延迟，见 [性能说明](PERFORMANCE.md)。

目标仍为 Windows 10 / 11 x64、支持 GLES 2.0 的 Android 6.0+，以及支持 Metal 的 iOS / iPadOS 15+。iOS USB 有原生模拟器 / 模拟 usbmux 证据，**真实 iPhone USB、实际盒子镜片与真实 FPS 游戏输入仍未验证**。iPhone 安装仍需 Mac、Xcode 和自己的 Apple 签名；模拟器下载为 Apple Silicon Mac 的 arm64 应用，不是 iPhone IPA 或 Windows 软件。

预设仍按最长边 / 目标 FPS / JPEG 质量表示：低延迟 **640 / 60 / Q45**、稳定 **640 / 30 / Q50**、画质 **960 / 30 / Q60**，另有自定义。两眼接收同一二维图像，没有音频、硬件视频编码、原生游戏立体或 6DoF 位置追踪。目标 FPS、链路 RTT 和手机本地纹理提交耗时都不保证端到端视频延迟，见 [性能边界](PERFORMANCE.md)。

### 下载与安装

产物名称仍为 `VRization-Windows-x64.zip`、`VRization-Android-debug.apk`、`VRization-vr-core-alpha.aar`、`VRization-iOS-source.zip`、`VRization-iOS-Simulator.zip`、`VRization-Licenses.zip` 与 `SHA256SUMS.txt`。Windows 完整解压，保留许可 / 文档文件夹，另行使用 Microsoft Visual C++ v14 x64 运行库。APK 仍为测试签名，保留数据覆盖升级要求签名一致；iOS 源码可编辑，没有替你的手机预先签名。

按 [上手教程](QUICKSTART.md)、[USB 前提](USB.md)、[iOS 签名](IOS.md) 与 [已校验下载 / 本地归档](DOWNLOADS.md) 使用。采集前明确选择画面。USB 连接、配置恢复、保存和重置均不会授权电脑鼠标；FPS 须电脑主动授权，**F8** 仍为停止键。局域网 `ws://` 仍未加密，只用于可信网络。

[发布历史](releases/README.md)

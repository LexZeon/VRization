# 🛤️ Roadmap and scope / 路线与范围

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

This separates existing baseline capabilities from possible future work. Dates are not promised.

### v0.1.0-alpha baseline

- Windows display / rectangular capture and JPEG WebSocket streaming.
- Android APK and reusable Android `vr-core` library.
- Fixed full screen, rotation-tracked cinema and pose-to-mouse First-person modes.
- Phone layout and viewing controls.
- PC saved gyro preference, default-enabled First-person, F8/Resume, disconnect and mode-change boundaries.
- Tutorials, actual UI screenshots, dependency attribution and automated builds.

### v0.1.1-alpha maintenance

Selectable English / Simplified Chinese, bilingual public pages, regression checks for settings / reconnect behavior, complete offline documentation packaging and the core AAR's original MIT notice.

### v0.2.0-alpha USB, iOS and Windows integration

Native iOS / iPadOS client with UIKit, Metal, Core Motion, all three modes, English / Chinese selection and a reusable Foundation-based Swift protocol / math package. The same Windows 10 / 11 x64 host remains compatible with Android and iOS through protocol v1; actual local desktop checks use Windows 11.

USB is now the default preference: Android discovers an authorized physical device through official ADB reverse, while iOS uses a native loopback listener and an original Windows relay through Apple's USB service. LAN remains explicitly selectable. Either endpoint's explicit Connect can request streaming. Windows defaults First-person gyro control to enabled, with latched F8/editor/failure/Stop pauses and explicit PC Resume. Foreground detection is one initial attempt; backgrounding, phone language changes and disconnects require explicit reconnection. USB discovery protects existing reverse mappings and reads Apple pairing records without creating trust or exposing keys.

New GUI users get the 640 / 60 FPS / Q45 low-latency preset; stable, quality and custom presets are available, and saved capture choices remain effective. Latest-frame work, on-demand Android rendering and received-FPS / ping-RTT diagnostics help inspection; these are not an end-to-end latency benchmark or guaranteed game frame rate.

Cloud builds compile simulator and device SDKs and exercise the native iOS Simulator over a synthetic stream and simulated usbmux service. Physical iPhone installation still needs Apple signing, and real iPhone USB / motion remains unverified. Huawei Android hardware checks are tracked separately in [validation](VALIDATION.md); neither path establishes headset optics, game compatibility or measured motion-to-photon latency.

### Next candidates

1. Broader physical Android derivative / phone-viewer tests and the first real iPhone USB / motion checks; improved sensor mapping.
2. Hardware codecs, timestamps and reproducible end-to-end latency measurements.
3. Encryption / stronger authentication, clearer USB prerequisite recovery and explicit reconnect behavior.
4. Audio sync, lens presets and configuration import / export.
5. Additional transport / WebRTC adapters and better platform driver compatibility, building on the current USB routes.
6. Unity / Unreal samples, in-game camera interfaces and stable SDK boundaries around the existing Swift core / Android AAR.
7. Independent per-eye rendering where the engine supports it, rather than presenting 2D duplication as native stereo.

### Outside current scope

This is not an OpenXR runtime or SteamVR driver. It does not provide 6DoF tracking, universal game injection, anti-cheat bypass, or automatic conversion of ordinary games into native VR.

### v0.3.0-alpha visual fitting and local profiles

The next release follows the separately published / archived v0.2 GPU / latency work. Windows, Android and iOS receive a first-position flat headset editor with synchronized eye movement, proportional corners with contact constraints, explicit Save / Discard, Reset all settings and persistent committed phone VR profiles. Drafts stay local; phones restore their saved profile only after a validated hello, using normal settings synchronization. Local input preference/pause latch, explicit reconnects and the selected PC capture output remain protected. See [editor scope](EDITING.md), [release history](releases/README.md) and [actual validation](VALIDATION.md).

---

<!-- vrization:chinese -->
## 简体中文

此文件区分已经提供的基础功能与后续方向，不承诺日期。

### v0.1.0-alpha 基础

- Windows 桌面 / 矩形选区采集与 JPEG WebSocket 串流。
- Android APK 与可复用 Android `vr-core` library。
- 固定全屏、旋转追踪虚拟大屏幕、姿态到鼠标三种模式。
- 手机端画面布局与观看参数调节。
- 电脑保存的陀螺仪偏好、默认启用第一人称、F8／恢复、断线和模式切换边界。
- 中文教程、界面截图、依赖来源与许可记录、自动构建配置。

### v0.1.1-alpha 维护改进

可选英文 / 简体中文界面、双语公共页面、设置 / 重连回归检查、完整离线文档打包和核心 AAR 原创 MIT 声明。

### v0.2.0-alpha USB、iOS 与 Windows 集成

原生 iOS / iPadOS 客户端使用 UIKit、Metal、Core Motion，包含三模式、中英选择及可复用的 Foundation Swift 协议 / 数学包。同一 Windows 10 / 11 x64 主机通过协议 v1 兼容 Android / iOS；本地实际桌面检查使用 Windows 11。

USB 已是默认偏好：Android 经官方 ADB reverse 发现已授权真实设备，iOS 使用原生回环监听及经 Apple USB 服务的原创 Windows 中继；局域网仍可显式选择。任一端主动连接可请求串流；Windows 默认启用第一人称陀螺仪控制，F8／编辑器／故障／Stop 锁定暂停，须电脑主动恢复。首次前台只尝试一次，进入后台、手机切语言、断线后需显式重连。发现过程保护已有 reverse 映射，只读 Apple 配对记录，不创建信任或暴露密钥。

新界面用户默认低延迟 640 / 60 FPS / 质量 45，另有稳定、画质和自定义预设；已有捕获配置继续生效。最新帧处理、Android 按需渲染及接收帧率 / ping RTT 便于诊断，不代表端到端延迟基准或保证游戏帧率。

云端编译模拟器 / 真机 SDK，并经合成串流与模拟 usbmux 服务运行原生 iOS 模拟器。真实 iPhone 安装仍须 Apple 签名，真实 iPhone USB / 姿态尚未验证。华为 Android 实机检查另见 [验证记录](VALIDATION.md)；两条路径均不证明盒子镜片、游戏兼容或运动到光子延迟已经通过。

### 下一阶段候选

1. 扩展 Android 衍生系统 / 手机盒子实测及首次真实 iPhone USB / 姿态检查，改进传感器映射。
2. 硬件视频编码与解码，时间戳和可复现的端到端延迟测量。
3. 加密 / 更强身份认证、更清晰的 USB 前提恢复与显式重连策略。
4. 音频同步、镜片参数预设与配置导入导出。
5. 在现有 USB 基础上加入其他传输 / WebRTC 适配器，改善平台驱动兼容。
6. 围绕已有 Swift 核心 / Android AAR 提供 Unity / Unreal 示例、游戏内部相机接口与稳定 SDK 边界。
7. 在引擎明确支持的场景加入左右眼独立渲染；不会把二维桌面伪装成原生立体画面。

### 暂无的能力

当前不是 OpenXR 运行时或 SteamVR 驱动，没有 6DoF 位置追踪、通用游戏注入、反作弊绕过或一键将普通游戏转换成原生 VR 的功能。


### v0.3.0-alpha 可视适配与本地配置

本版在独立发布 / 归档的 v0.2 GPU / 延迟工作之后推进：Windows、Android 与 iOS 加入设置首位平面编辑器、双眼同步移动、受接触约束的等比角点、主动保存 / 放弃、全部重置和手机已提交 VR 配置持久化。草稿只在本地，合法 hello 后才用普通同步恢复已保存配置；保留本地输入偏好／暂停锁、显式重连及选定电脑画面的边界。见 [编辑范围](EDITING.md)、[发布历史](releases/README.md) 与 [实际验证](VALIDATION.md)。

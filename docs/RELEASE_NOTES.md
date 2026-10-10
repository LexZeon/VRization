# 🎯 VRization v0.3.4-alpha — release notes / 发布说明

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

Windows, Android and iOS applications are **0.3.4**, mobile build **7**; the reusable Android core AAR is unchanged. Published **2026-10-10 UTC** as [v0.3.4-alpha](https://github.com/LexZeon/VRization/releases/tag/v0.3.4-alpha). Protocol v1/settings schema 2 are unchanged. The [v0.3.3 notes](releases/v0.3.3-alpha.md) preserve the connection repair's earlier checks.

### Default-enabled continuous gyro mouse control

Windows enables First-person gyro mouse control by default. A validated connection, First-person mode, available capture and fresh valid rotation data are required; the first pose sets a baseline before movement. Control works on the desktop, ordinary applications, games and VRization's own window regardless of foreground-window changes, with no five-second target-window deadline. A temporary sensor gap stops output and rebaselines on fresh poses before continuing. **F8**, the PC emergency stop, editor entry, PC Reset all settings, capture-region selection, capture/input failure and stream Stop latch a pause: late poses, settings and reconnecting cannot clear it. Click **Resume gyro control** on the PC, or explicitly turn the control checkbox off and on, to resume. Full screen and Cinema stop mouse output. The PC saves only the enabled preference, never the live armed state or pause latch.

The PC checkbox is **Gyro mouse control in First-person (default on)**. Turning it off disables automatic input; turning it on is an explicit local resume. The saved `gyro_control_enabled` boolean lives in `input.json`, separate from VR settings and phone profiles. Existing valid saved off preferences remain off. PC Reset all settings latches input paused and restores the enabled preference and Full screen, without starting capture. Selecting a capture region also latches a pause. Use PC Resume when ready.

### Stopping and compatibility

- Cable detection alone does not start capture/control. Explicit Connect on either USB endpoint still coordinates streaming; Disconnect closes its owned transport and stops video/pose output.
- Full screen/Cinema do not drive the mouse. A reconnect must not clear an existing F8/editor/failure/Stop pause.
- Reusable `HostServer`/`PoseController` constructors retain `auto_control=False`; the GUI opts into the saved default-enabled policy. Integrations use host-local policy/resume APIs, without a new remote arm/resume message.
- Android/iOS notices explain the Windows default and F8/PC Resume. Existing phone 0.3.3 remains protocol-compatible. Stabilization stays at 0% by default and its slider cannot clear a pause latch.
- Games may reject ordinary injected mouse input; this release does not bypass game protections or add native game stereo.

### Verification and update scope

Source `101174317613520c7d98375332c2a3bd9032cb2d` passed **318 Windows tests** and **116 clean Android tests (67 app + 49 core)**, with no failures/ignored cases. Android APK/AAR/instrumentation builds and lint passed: zero lint errors, nine CI warnings (eight existing local warnings plus OldTargetApi from the CI SDK inventory), with no warning suppression. The frozen EXE source/native/license audit and clean-profile Windows ZIP runtime smoke check passed. Huawei installed **0.3.4 / build 7** with the existing public certificate; its pulled installed APK matches the release APK hash. All four [CI jobs](https://github.com/LexZeon/VRization/actions/runs/38081097956) passed; iOS passed 80 Swift core tests with zero failures, five genuine native UI cases with zero failures/skips, and both Simulator/unsigned device-target SDK builds. Independent screenshot decoding passed 12 color pixel checks and two seam checks; all 12 host checkpoints recorded no mouse moves. The tested app is 0.3.4/build 7/arm64/minimum iOS 15 on an iPhone 17 Pro Max Simulator running iOS 26.2 (Xcode 26.3/macOS 15.7.9); USB was simulated. See [the complete versioned record](VALIDATION.md).

The advanced Windows GUI check stopped after the user physically pressed Escape; actual GUI Resume/F8 is not claimed. New-version physical gyro control, game feel, video delivery, physical iPhone USB and latency were not tested. Historical performance results retain their own versions and configurations.

Close the old host, extract the complete Windows archive and retain separately installed USB tools. Android matching-signer updates preserve application data; verify with the official public certificate gate and release manifest. iOS source requires Xcode and the owner's Apple signing; the Mac Simulator archive cannot install on an iPhone. Existing published binaries and historical checksums remain immutable.

[Quick start](QUICKSTART.md) · [Security](../SECURITY.md) · [Stabilization](STABILIZATION.md) · [AI handoff](../AI_HANDOFF.md) · [Changelog](../CHANGELOG.md)

---

<!-- vrization:chinese -->
## 简体中文

Windows、Android 与 iOS 应用为 **0.3.4**、手机构建号 **7**；可复用 Android 核心 AAR 不变。按 **UTC 2026-10-10** 发布为 [v0.3.4-alpha](https://github.com/LexZeon/VRization/releases/tag/v0.3.4-alpha)。协议 v1／配置 schema 2 不变，[v0.3.3 说明](releases/v0.3.3-alpha.md) 保留此前连接修复的检查。

### 默认开启且持续响应的陀螺仪鼠标

Windows 默认开启第一人称陀螺仪鼠标控制。必须有通过校验的连接、第一人称模式、可用采集与新的合法旋转姿态；首条姿态先建立基准，再产生移动。桌面、普通应用、游戏和 VRization 自身窗口均可控制，不受前台窗口切换影响，也不要求五秒内切到目标窗口。传感器短暂间断时停止输出，新姿态先重建基准再继续。**F8**、电脑紧急停止、进入编辑器、电脑重置全部设置、选择采集区域、采集／输入故障和停止串流会锁定暂停；迟到姿态、设置与重连都不能解除。需要在电脑点“**恢复陀螺仪控制**”，或主动关闭再开启控制复选框。全屏和大屏幕停止鼠标输出。电脑只保存启用偏好，不保存实时授权状态或暂停锁。

电脑复选框为“**第一人称陀螺仪鼠标控制（默认开启）**”。关闭停用自动输入，主动开启相当于电脑明确恢复；`gyro_control_enabled` 布尔值单独保存在 `input.json`，与 VR 设置和手机配置分开。已有合法的关闭偏好仍保持关闭；电脑一键重置锁定输入暂停，恢复启用偏好并选择全屏，不开始采集；选择采集区域也锁定暂停，准备好后在电脑点恢复。

### 停止与兼容性

- 单纯插线／发现设备不启动采集或控制；任一 USB 端主动连接仍协调开始串流，断开关闭自有传输并停止视频／姿态输出。
- 全屏／大屏幕不控制鼠标；重连不能解除已有 F8／编辑器／故障／Stop 暂停锁。
- 可复用 `HostServer`／`PoseController` 构造器保留 `auto_control=False`，界面采用保存的默认启用策略；集成通过电脑本地策略／恢复 API 操作，不增加远程授权／恢复消息。
- Android／iOS 提示解释电脑默认启用及 F8／电脑恢复；已有手机 0.3.3 协议仍兼容。防抖默认仍为 0%，滑块不能解除暂停锁。
- 游戏可能拒绝普通模拟鼠标，本版不绕过游戏保护，也不新增原生游戏立体画面。

### 验证与更新范围

源码 `101174317613520c7d98375332c2a3bd9032cb2d` 通过 **318 项 Windows** 和 **116 项干净 Android 测试（应用 67＋核心 49）**，无失败／忽略。Android APK／AAR／测试工具构建及 lint 通过：零 lint 错误、九项 CI 警告（八项既有本地警告，加 CI SDK 清单产生的 OldTargetApi），未抑制警告。冻结 EXE 源码／原生／许可审计与新偏好 Windows ZIP 运行 smoke 通过；华为使用原公开证书安装 **0.3.4／构建 7**，拉取的已安装 APK 与发布哈希一致。[四项 CI 任务](https://github.com/LexZeon/VRization/actions/runs/38081097956) 通过，iOS 通过 80 项 Swift 核心（零失败）、五项真实原生界面（零失败／跳过）及模拟器／未签名真机目标两种 SDK 构建；独立解码截图通过 12 项颜色像素及两项接缝检查，12 个电脑检查点均无鼠标移动。测试应用为 0.3.4／构建 7／arm64／最低 iOS 15，环境为 iPhone 17 Pro Max 模拟器 iOS 26.2（Xcode 26.3／macOS 15.7.9），USB 为模拟。完整按版本证据见 [验证记录](VALIDATION.md)。

高级 Windows 界面检查因用户实际按 Escape 而停止，不宣称实际界面 Resume／F8 已验收。新版真机陀螺仪控制、游戏手感、视频传输、真实 iPhone USB 和延迟未测试；历史性能结果仍对应原版本与配置。

关闭旧主机，完整解压 Windows 包并保留另行安装的 USB 工具；同签名 Android 覆盖升级保留应用数据，按官方公开证书门槛及清单验证。iOS 源码需 Xcode 与自己的 Apple 签名，Mac 模拟器包不能安装到 iPhone；已发布二进制和历史校验值保持不变。

[快速开始](QUICKSTART.md) · [安全](../SECURITY.md) · [防抖](STABILIZATION.md) · [AI 接手](../AI_HANDOFF.md) · [版本日志](../CHANGELOG.md)

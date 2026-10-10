# 🎯 VRization v0.3.4-alpha — release notes / 发布说明

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

**Development candidate: validation and publication are pending.** Windows, Android and iOS application versions target **0.3.4**, mobile build **7**. Protocol v1 and settings schema 2 are unchanged. The [v0.3.3 notes](releases/v0.3.3-alpha.md) preserve the connection repair's published checks.

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

New-version synthetic, package, signing/build and native Simulator acceptance is pending in [validation](VALIDATION.md). Historical Huawei/Windows/iOS results remain scoped to their published versions. No new physical iPhone USB, real-game compatibility, unique-frame-rate or end-to-end latency result is claimed.

Close the old host, extract the complete Windows archive and retain separately installed USB tools. Android matching-signer updates preserve application data; verify with the official public certificate gate and release manifest. iOS source requires Xcode and the owner's Apple signing; the Mac Simulator archive cannot install on an iPhone. Existing published binaries and historical checksums remain immutable.

[Quick start](QUICKSTART.md) · [Security](../SECURITY.md) · [Stabilization](STABILIZATION.md) · [AI handoff](../AI_HANDOFF.md) · [Changelog](../CHANGELOG.md)

---

<!-- vrization:chinese -->
## 简体中文

**开发候选：验证与发布尚待完成。** Windows、Android 和 iOS 应用目标版本为 **0.3.4**、手机构建号 **7**；协议 v1 与配置 schema 2 不变。[v0.3.3 说明](releases/v0.3.3-alpha.md) 保留连接修复的已发布检查。

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

新版合成、打包、签名／构建与原生模拟器验收仍待完成，见 [验证记录](VALIDATION.md)。历史华为／Windows／iOS 结果仍对应发布版本，不新增真实 iPhone USB、实际游戏兼容、不同帧率或端到端延迟结论。

关闭旧主机，完整解压 Windows 包并保留另行安装的 USB 工具；同签名 Android 覆盖升级保留应用数据，按官方公开证书门槛及清单验证。iOS 源码需 Xcode 与自己的 Apple 签名，Mac 模拟器包不能安装到 iPhone；已发布二进制和历史校验值保持不变。

[快速开始](QUICKSTART.md) · [安全](../SECURITY.md) · [防抖](STABILIZATION.md) · [AI 接手](../AI_HANDOFF.md) · [版本日志](../CHANGELOG.md)

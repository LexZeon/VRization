# 📝 Version changelog / 版本日志

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

User-visible changes are listed newest first. Dates are GitHub publication dates in **UTC**. Each version links to its detailed release notes, downloads and verification limits. An FPS target or a successful build is not a hardware-performance guarantee.

### Unreleased

- **Documentation:** Added this bilingual changelog covering every published version, with README links and a requirement to keep it updated for future changes.

### [v0.3.2-alpha](https://github.com/LexZeon/VRization/releases/tag/v0.3.2-alpha) — 2026-10-09

Windows, Android and iOS applications: **0.3.2**.

- **Added:** First-person gyro stabilization slider, **0–100%, default 0%** to preserve earlier input behavior. Accepted settings synchronize between PC and phone, persist locally and migrate older profiles.
- **Fixed:** USB tools lookup for ordinary downloaded Windows apps; portable SDK locations, scoped launcher settings and a manual official-tools importer. Android discovery retries within a bounded 30-second attempt. Public Windows ZIPs now receive an independent startup check without a developer SDK.
- **Changed:** Visible “FPS” mode renamed **First person**. Saved per-eye display bounds apply to every mode, including Cinema and lens distortion.
- **Improved:** High-resolution pose timing and adaptive host-side smoothing; optimization ideas and the One Euro Filter reference are credited. Mouse input still needs explicit PC arming.
- **Checked:** Huawei slider synchronization, saved settings after restart, all-mode offscreen display masks and phone-first USB startup. The user also confirmed ordinary-launch streaming and repeated close / reopen. iOS core, both SDK builds and native Simulator UI checks passed; physical iPhone USB remains untested.

### [v0.3.1-alpha](https://github.com/LexZeon/VRization/releases/tag/v0.3.1-alpha) — 2026-10-09

Windows application: **0.3.1**. Android / iOS applications and their existing phone installations remain **0.3.0**.

- **Fixed:** Background ADB commands no longer depend on a missing or invalid standard-input handle inherited from a Windows launcher. Official tool discovery also checks the managed SDK installation.
- **Added:** **USB connection…** shortcut on the PC connection card, plus USB status in the activity log and clearer setup instructions.
- **Checked:** Ordinary Windows launch, authorized Huawei USB forwarding and visible streaming. This patch introduced no new measured FPS or end-to-end latency claim.

### [v0.3.0-alpha](https://github.com/LexZeon/VRization/releases/tag/v0.3.0-alpha) — 2026-10-09

Windows, Android and iOS applications: **0.3.0**.

- **Added:** Visual headset fitting as the first settings entry: proportional corner resizing, vertical placement and linked eye spacing. The inner edges can meet even when the displayed images are small.
- **Added:** **Save / Discard** editing, PC / phone synchronization and locally saved committed phone profiles restored after reopening.
- **Added:** **Reset all settings** with documented defaults and reusable Python / Android / Swift geometry and editing components.
- **Changed:** Signed eye separation supports moving the eyes inward, with aspect-dependent contact limits. Both endpoints need this version for negative separation.
- **Checked:** Physical Huawei editing / persistence, Android emulator behavior and native iOS Simulator editing / seam tests. GPU capture and USB latency work from v0.2.0 are retained.

### [v0.2.0-alpha](https://github.com/LexZeon/VRization/releases/tag/v0.2.0-alpha) — 2026-10-09

Windows / Android updated to **0.2.0**; native iOS client introduced at **0.2.0**.

- **Added:** Native iOS / iPadOS 15+ viewer with Metal, Core Motion and a reusable Swift core. Source and Mac Simulator downloads are supplied; physical iPhone installation needs Xcode and Apple signing.
- **Added:** **USB as the default** on PC and both phone platforms, authorized physical Android detection / forwarding and an iOS USB relay. Explicit LAN connection remains available.
- **Improved:** Original Windows DXGI / D3D11 GPU capture, cropping, rotation and downscaling before CPU JPEG encoding, with GDI / MSS compatibility fallback.
- **Improved:** Latest-frame handoff and phone texture reuse, with frame / round-trip diagnostics that remain separate from end-to-end latency measurements.
- **Added:** Adjustable performance presets: low latency **640 / 60 / Q45**, stable **640 / 30 / Q50**, quality **960 / 30 / Q60** (long edge / target FPS / JPEG quality).
- **Added:** Illustrated USB / iOS guides and a verified local archive tool preserving each version's download checksums, historical releases and a runnable latest Windows copy. Real Huawei USB streaming was tested; iOS USB evidence was software / simulated-device testing.

### [v0.1.1-alpha](https://github.com/LexZeon/VRization/releases/tag/v0.1.1-alpha) — 2026-10-09

Windows and Android applications: **0.1.1**.

- **Changed:** English became the default and primary interface language; selectable Simplified Chinese and local language persistence were added to both apps.
- **Documentation:** Standardized public pages and existing illustrated usage / build guides as complete English-first / Chinese-below documents.
- **Fixed:** Delayed settings acknowledgments and stale session callbacks. Android 6.0 / Android 16 emulator checks covered same-signer updates, saved preferences and sensor-less fallback.
- **Packaging:** Completed offline documentation and embedded the original MIT license in the Android core library.

### [v0.1.0-alpha](https://github.com/LexZeon/VRization/releases/tag/v0.1.0-alpha) — 2026-10-09

First Windows / Android preview.

- **Added:** Desktop or rectangular-region streaming over LAN to an Android phone, with side-by-side viewing for a phone VR box.
- **Added:** Fixed Full screen, head-tracked Cinema and gyro-to-mouse FPS viewing modes, with explicit PC input authorization and **F8** stop.
- **Added:** Scale, position, eye spacing, field of view, screen distance, distortion, recentering and mouse sensitivity controls.
- **Added:** Runnable Windows package, Android 6.0+ APK, reusable Android core and open-source license / attribution records. Both eyes show the same 2D source; this does not create native stereoscopic game rendering.

---

<!-- vrization:chinese -->
## 简体中文

按从新到旧记录用户能感受到的变化。日期使用 GitHub 发布日期，时区为 **UTC**。每个版本都链接到详细发布说明、下载与验证范围。目标帧率或构建成功不等于硬件性能保证。

### 未发布

- **文档：** 新增覆盖全部已发布版本的中英双语日志、README 入口及今后持续更新日志的项目要求。

### [v0.3.2-alpha](https://github.com/LexZeon/VRization/releases/tag/v0.3.2-alpha) — 2026-10-09

Windows、Android 与 iOS 应用均为 **0.3.2**。

- **新增：** 第一人称陀螺仪防抖滑块，**0–100%，默认 0%** 保留此前操作效果。接受的设置在电脑与手机之间同步、本地保存，并兼容旧配置迁移。
- **修复：** 普通下载 Windows 程序的 USB 工具查找，增加便携 SDK 位置、只作用于子程序的启动配置和手动官方工具导入器。Android 检测在最长 30 秒的有限尝试内重试。公开 Windows ZIP 新增脱离开发 SDK 的独立启动检查。
- **调整：** 界面“FPS”改名为“**第一人称**”。保存的每眼显示范围适用于所有模式，包括大屏幕与镜片畸变。
- **优化：** 高精度姿态计时及电脑端自适应平滑；优化思路与 One Euro Filter 参考保留鸣谢。鼠标控制仍需电脑主动授权。
- **验证：** 华为真机滑块同步、重启保存、全部模式离屏显示范围及手机先启动的 USB 连接；用户还确认普通启动可见画面，反复关闭 / 重开仍可连接。iOS 核心、两种 SDK 构建及原生模拟器界面检查通过，真实 iPhone USB 尚未实测。

### [v0.3.1-alpha](https://github.com/LexZeon/VRization/releases/tag/v0.3.1-alpha) — 2026-10-09

Windows 应用为 **0.3.1**；Android / iOS 应用及已有手机安装仍为 **0.3.0**。

- **修复：** 后台 ADB 命令不再依赖 Windows 启动环境传入的缺失或无效标准输入句柄；官方工具查找加入已管理 SDK 安装位置。
- **新增：** 电脑连接卡片的“**USB 连接…**”入口、活动日志中的 USB 状态及更清楚的设置教程。
- **验证：** 普通 Windows 启动、已授权华为 USB 转发和可见串流。本补丁没有新增帧率或端到端延迟测量结论。

### [v0.3.0-alpha](https://github.com/LexZeon/VRization/releases/tag/v0.3.0-alpha) — 2026-10-09

Windows、Android 与 iOS 应用均为 **0.3.0**。

- **新增：** 设置第一项的画面可视编辑：拖角点等比缩放、上下移动及双眼间距联动。即使画面很小，内侧边缘也能相接。
- **新增：** “**保存 / 放弃**”编辑、电脑 / 手机同步，以及本地保存的手机已提交配置，重开后恢复。
- **新增：** “**一键重置全部设置**”、明确的默认值，以及可复用的 Python / Android / Swift 几何与编辑组件。
- **调整：** 有符号眼间距支持向内靠近，接触边界按图像比例计算；使用负间距需要两端都更新到该版。
- **验证：** 华为真机编辑 / 保存、Android 模拟器行为、iOS 原生模拟器编辑 / 接缝检查；保留 v0.2.0 的 GPU 采集和 USB 延迟优化。

### [v0.2.0-alpha](https://github.com/LexZeon/VRization/releases/tag/v0.2.0-alpha) — 2026-10-09

Windows / Android 更新为 **0.2.0**；新增的原生 iOS 客户端为 **0.2.0**。

- **新增：** 原生 iOS / iPadOS 15+ 客户端，使用 Metal、Core Motion 与可复用 Swift 核心。提供源码与 Mac 模拟器下载，真实 iPhone 安装需要 Xcode 和 Apple 签名。
- **新增：** 电脑和两种手机端都**默认 USB**，自动检测 / 转发已授权 Android 真机，并提供 iOS USB 中继；保留显式局域网连接。
- **优化：** 原创 Windows DXGI / D3D11 GPU 采集，在 CPU JPEG 编码前裁切、旋转和缩小，保留 GDI / MSS 兼容回退。
- **优化：** 最新帧交接与手机纹理复用，提供帧处理 / 链路往返诊断，并与端到端延迟测量区分。
- **新增：** 可调性能预设：低延迟 **640 / 60 / Q45**、稳定 **640 / 30 / Q50**、画质 **960 / 30 / Q60**，依次表示最长边 / 目标帧率 / JPEG 质量。
- **新增：** 双语图文 USB / iOS 教程和带校验的本地归档工具，保存各版下载校验值、历史版与可直接运行的最新版 Windows。华为真实 USB 串流已测试；iOS USB 当时属于软件 / 模拟设备验证。

### [v0.1.1-alpha](https://github.com/LexZeon/VRization/releases/tag/v0.1.1-alpha) — 2026-10-09

Windows 与 Android 应用均为 **0.1.1**。

- **调整：** 英文成为默认和优先界面语言，两端新增可选简体中文并在本地保存语言选择。
- **文档：** 公共页面和已有图文使用 / 构建教程统一完善为同页先完整英文、再完整中文。
- **修复：** 迟到的设置确认与旧会话回调；Android 6.0 / Android 16 模拟器检查覆盖同签名升级、偏好保存及无传感器回退。
- **打包：** 补齐离线文档，在 Android 核心库内嵌原创 MIT 许可。

### [v0.1.0-alpha](https://github.com/LexZeon/VRization/releases/tag/v0.1.0-alpha) — 2026-10-09

首个 Windows / Android 预览版。

- **新增：** 通过局域网将电脑桌面或矩形选区串流到 Android 手机，以双眼并排画面用于手机 VR 盒子。
- **新增：** 固定全屏、头部追踪大屏幕、陀螺仪转鼠标的 FPS 三种模式，电脑主动授权输入并可用 **F8** 停止。
- **新增：** 缩放、位置、双眼间距、视野角度、屏幕距离、畸变、回正与鼠标灵敏度设置。
- **新增：** 可运行 Windows 程序包、Android 6.0+ APK、可复用 Android 核心及开源许可 / 鸣谢记录。两眼显示相同二维来源，不会自动生成游戏原生立体深度。

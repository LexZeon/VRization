# 📝 Version changelog / 版本日志

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

User-visible changes are listed newest first. Dates are GitHub publication dates in **UTC**. Each version links to its detailed release notes, downloads and verification limits. An FPS target or a successful build is not a hardware-performance guarantee.

### Unreleased

- **Release management:** The ordinary-channel archive now selects only public releases containing the exact `VRization-Windows-x64.zip` asset. Separate SteamVR preview releases are excluded from automatic and explicit ordinary `latest` selection. This changes release tooling; no application runtime behavior is changed.

### [v0.5.0-steamvr-preview](https://github.com/LexZeon/VRization/releases/tag/v0.5.0-steamvr-preview) — 2026-10-10

**Separate preview; documentation-only discovery entry on `main`.** Windows and Android preview applications use **0.5.0-steamvr-preview**, mobile build **1**; iOS uses **0.5.0**, build **1**, with its own preview identity. Stable **v0.4.0-alpha**, all existing files and historical downloads are preserved.

- **Independent routes:** Original direct-phone streaming with the four existing modes; a phone as a rotation-only **3DOF SteamVR HMD** receiving independent compositor eye images; a desktop overlay on an already connected SteamVR headset. The preview uses separate mobile installs, settings and USB endpoints.
- **Verification limits:** Software/build evidence is recorded on the experimental branch. Real phone/PCVR acceptance, achieved hardware FPS and physical latency remain deferred to the next hardware session. This documentation entry adds no experimental implementation to `main`.
- **Guides:** [Illustrated tutorial](https://github.com/LexZeon/VRization/blob/codex/steamvr-experimental/experimental/steamvr/docs/TUTORIAL.md), [verification record](https://github.com/LexZeon/VRization/blob/codex/steamvr-experimental/experimental/steamvr/docs/VALIDATION.md) and [AI handoff](https://github.com/LexZeon/VRization/blob/codex/steamvr-experimental/experimental/steamvr/docs/AI_HANDOFF.md).

### [v0.4.0-alpha](https://github.com/LexZeon/VRization/releases/tag/v0.4.0-alpha) — 2026-10-10

Windows, Android and iOS applications **0.4.0**, mobile build **8**; the reusable Android core AAR is updated. Older evidence below remains scoped to its named release.

- **Added:** Fourth **Enhanced first person** mode (`fps_enhanced`), fixed physical 1:1 square per eye, original Android GLES/iOS Metal inverse angular warp and pure reusable projection helpers. Existing FOV controls the warp span; black border samples remain explicit.
- **Added:** Proportional square editor/viewer fit with existing scale, offsets, mirrored spacing, Save/Discard, local committed profiles and connected synchronization. Enhanced preview keeps the warp; Windows uses an approximate mesh over the existing latest frame, without additional capture.
- **Compatibility:** Explicit `enhanced-first-person` negotiation, per-message `enhancedFirstPerson` confirmation and old-version ordinary `fps` fallback, with protocol v1/settings schema 2 unchanged. Enhanced viewing remains available without a rotation sensor; gyro control still needs valid poses. Both first-person modes share the saved default-enabled gyro policy and latched F8/PC Resume boundaries.
- **Packaging:** The Windows freeze explicitly excludes optional developer packages `numpy`, `dxcam` and `comtypes`, keeping their incidental presence on a build machine from changing the portable runtime. VRization's own DXGI capture remains included; this does not remove GPU capture or add a performance claim.
- **Checked:** Local Windows **334 tests plus 204 subtests**, a separate **22 script unit cases**, Android **133 cases (75 app + 58 core)**, APK/release AAR builds and canonical APK signature passed. Android instrumentation compiled but did not run. All four CI jobs passed. Independent iOS review passed **95 Swift tests, seven native UI cases with zero failures/skips, both SDK builds, 38 enhanced pixel checks and 16 older-mode color/two seam checks**. Final EXE/source/native/notice audit and a complete prepublication ZIP clean-profile check passed. Huawei/PCVR hardware tests are deferred to the next chat.
- **Checked GUI:** Actual isolated Windows preview on ASUS passed enhanced selection, square corner resize, inward eye contact, Save/reopen and draft Discard. The tutorial preserves an unmodified synthetic-grid editor screenshot; no capture, phone/pose connection or OS mouse output ran in that check.
- **Documentation only:** Added the bilingual projection tutorial, exact OpenCV 4.12.0 mathematics-only credit, module/handoff updates and archived v0.3.4 release notes. No OpenCV code/runtime or user reference image is incorporated; existing files/releases are retained.

Separate planned work: a SteamVR experimental version after preserving existing files; no SteamVR driver/package is implemented by this entry. See [current notes](docs/RELEASE_NOTES.md), [verification](docs/VALIDATION.md) and [roadmap](docs/ROADMAP.md).

### [v0.3.4-alpha](https://github.com/LexZeon/VRization/releases/tag/v0.3.4-alpha) — 2026-10-10

Windows, Android and iOS applications: **0.3.4**, mobile build **7**. The reusable Android core AAR is unchanged.

- **Changed default:** Windows enables First-person gyro mouse control by default and saves `gyro_control_enabled` separately from VR settings. Phone v0.3.3 protocol messages remain compatible; v0.3.4 mobile wording explains the new default.
- **Improved:** Fresh valid First-person poses start control automatically. The desktop, ordinary applications, games and VRization's own window remain controllable across foreground changes. Short sensor gaps stop output/rebaseline, then resume; this GUI policy has no five-second target-window deadline.
- **Kept:** F8, PC emergency stop, editor entry, PC Reset, capture-region selection, capture/input failure and stream Stop latch input paused. Late poses, settings and reconnect cannot resume it; use PC Resume or explicitly re-enable the checkbox. Full screen/Cinema never drive the mouse. Live armed/pause state is not saved; reusable constructors retain `auto_control=False`.
- **Checked:** 318 Windows tests, 116 clean Android tests, package/source/native audits, matching-signer Huawei 0.3.4/build 7 installation and all four CI jobs passed. iOS passed 80 Swift core tests, five genuine native UI cases with zero failures/skips, both SDK builds and 12 color/two seam pixel checks. Physical new gyro/game/video/latency and advanced Windows GUI Resume/F8 remain unverified; see [exact validation](docs/VALIDATION.md).

### [v0.3.3-alpha](https://github.com/LexZeon/VRization/releases/tag/v0.3.3-alpha) — 2026-10-10

Windows, Android and iOS applications: **0.3.3**, mobile build **6**.

- **Fixed:** Actual phone Disconnect and PC Stop; sockets, late frames, statistics, pose authorization and renderer output are released. Closed host sessions are revoked before asynchronous sender cleanup; old cleanup cannot affect a new connection.
- **Added:** Explicit USB Connect from either endpoint, with separate foreground control/video. PC connection requests preserve an already connected phone's session. iOS Stop acknowledgment and device/generation guards prevent stale readiness from restarting capture.
- **Fixed:** Bounded ADB startup/recovery and reverse-map ownership retained through temporary failures, allowing reuse without unplugging the cable.
- **Fixed:** Windows DXGI continues streaming the surface already masked by the OS; protected regions remain black and genuine layout/access/resource failures still stop capture.
- **Added:** Installed version/build display on both phone clients; reusable connection modules, a complete [module catalogue](docs/MODULES.md) and bilingual [AI handoff](AI_HANDOFF.md).
- **Fixed:** iOS LAN connection has a 15-second pre-open deadline; cancelled or expired upgrades cannot restore an old session or picture.
- **Checked:** 80 Swift core tests, five genuine native Simulator UI cases, both iOS SDK builds and color / seam checks passed. Physical iPhone USB remains untested.
- **Publishing:** The canonical Android certificate gate rejects unrelated CI debug signatures; ordinary-launch and public-ZIP checks supplement source tests.

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

- **发布管理：** 原版通道归档现仅选择包含准确资产名 `VRization-Windows-x64.zip` 的公开发布；独立 SteamVR 实验发布不会被自动或显式选为原版 `latest`。这是发布工具改动，应用运行行为没有变化。

### [v0.5.0-steamvr-preview](https://github.com/LexZeon/VRization/releases/tag/v0.5.0-steamvr-preview) — 2026-10-10

**独立实验版；`main` 仅新增说明入口。** Windows 与 Android 实验应用版本为 **0.5.0-steamvr-preview**、手机构建号 **1**；iOS 为 **0.5.0**、构建号 **1**，使用独立实验版标识。原版通道的 **v0.4.0-alpha**、所有现有文件与历史下载继续保留。

- **独立入口：** 保留原有四种模式的手机直连串流；手机作为只有旋转的 **3DOF SteamVR 头显**，接收合成器独立双眼画面；已有 SteamVR 头显观看桌面悬浮层。实验版使用独立手机安装、设置与 USB 端点。
- **验证范围：** 实验分支记录软件／构建证据；真实手机／PCVR 验收、实际硬件帧率及物理延迟留到下次硬件会话。本条文档不会将实验实现加入 `main`。
- **指南：** [图文教程](https://github.com/LexZeon/VRization/blob/codex/steamvr-experimental/experimental/steamvr/docs/TUTORIAL.md)、[验证记录](https://github.com/LexZeon/VRization/blob/codex/steamvr-experimental/experimental/steamvr/docs/VALIDATION.md)及 [AI 接手指南](https://github.com/LexZeon/VRization/blob/codex/steamvr-experimental/experimental/steamvr/docs/AI_HANDOFF.md)。

### [v0.4.0-alpha](https://github.com/LexZeon/VRization/releases/tag/v0.4.0-alpha) — 2026-10-10

Windows、Android 与 iOS 应用 **0.4.0**、手机构建号 **8**，可复用 Android 核心 AAR 已更新；以下旧证据仍对应其明确版本。

- **新增：** 第四种“**加强第一人称**”（`fps_enhanced`），每眼固定物理 1:1 正方形，原创 Android GLES／iOS Metal 逆角度变形及纯数学可复用辅助；已有 FOV 控制变形范围，明确处理黑边采样。
- **新增：** 正方形编辑器／观看器等比适配，沿用缩放、偏移、镜像间距、保存／放弃、本地已提交配置及连接同步；加强预览保留变形，电脑在已有最新帧作近似网格，不额外采集。
- **兼容性：** 显式 `enhanced-first-person` 协商、每条消息的 `enhancedFirstPerson` 确认及旧版本普通 `fps` 回退，协议 v1／配置 schema 2 不变。无旋转传感器仍可加强观看，陀螺仪仍需合法姿态；两种第一人称共用已保存的默认启用策略与锁定 F8／电脑恢复边界。
- **打包：** Windows 冻结打包显式排除可选开发工具 `numpy`、`dxcam` 与 `comtypes`，避免构建电脑偶然安装的软件改变便携运行依赖；仍包含 VRization 自身 DXGI 采集，不移除 GPU 采集，也不据此增加性能结论。
- **检查：** 本地 Windows **334 项及 204 个子测试**、独立 **22 项脚本单元用例**、Android **133 项（75 app＋58 core）**、APK／release AAR 构建及权威 APK 签名通过。Android instrumentation 只编译未运行；四项 CI 全部通过；iOS 独立审核通过 **95 项 Swift、七项原生界面零失败／跳过、两种 SDK、38 项加强像素和 16 项旧模式颜色／两项接缝**，最终 EXE／源码／原生／通知审计及完整预发布 ZIP 新配置检查通过，华为／PCVR 真机测试留到下次聊天。
- **界面检查：** ASUS 上实际隔离配置 Windows 预览通过加强选择、正方形角点缩放、双眼向内接触、保存／重开及草稿放弃；教程保留未经修改的合成网格编辑器截图，此次没有采集、手机／姿态连接或操作系统鼠标输出。
- **纯文档：** 新增双语投影教程、准确 OpenCV 4.12.0 仅数学参考鸣谢、模块／接手更新及 v0.3.4 说明归档；不采用 OpenCV 代码／运行库或用户参考图片，保留已有文件／发布。

单独计划：保留现有文件后另做 SteamVR 实验版本；本条不实现 SteamVR 驱动／安装包，见 [当前说明](docs/RELEASE_NOTES.md)、[验证](docs/VALIDATION.md) 与 [路线](docs/ROADMAP.md)。

### [v0.3.4-alpha](https://github.com/LexZeon/VRization/releases/tag/v0.3.4-alpha) — 2026-10-10

Windows、Android 与 iOS 应用：**0.3.4**，手机构建号 **7**；可复用 Android 核心 AAR 不变。

- **默认变化：** Windows 默认开启第一人称陀螺仪鼠标，`gyro_control_enabled` 与 VR 设置分开保存。手机 v0.3.3 的协议消息继续兼容，v0.3.4 手机说明同步解释新默认。
- **优化：** 新的合法第一人称姿态自动开始控制；桌面、普通应用、游戏和 VRization 自身窗口都可控制，切换前台不解除。传感器短暂间断时停止／重建基准再恢复，此界面策略没有五秒目标窗口限制。
- **保留：** F8、电脑紧急停止、进入编辑器、电脑重置／选区、采集／输入故障和 Stop 锁定暂停。迟到姿态、设置或重连不能恢复，须在电脑恢复或主动重新开启复选框；全屏／大屏幕不输出鼠标。不保存实时授权／暂停状态，可复用构造器保留 `auto_control=False`。
- **检查：** 318 项 Windows、116 项干净 Android 测试、打包／源码／原生审计、同签名华为 0.3.4／构建 7 安装与四项 CI 任务通过；iOS 通过 80 项 Swift 核心、五项真实原生界面（零失败／跳过）、两种 SDK 构建及 12 项颜色／两项接缝像素检查。新版真机陀螺仪／游戏／视频／延迟及高级 Windows 界面 Resume／F8 未验收，见 [准确验证](docs/VALIDATION.md)。

### [v0.3.3-alpha](https://github.com/LexZeon/VRization/releases/tag/v0.3.3-alpha) — 2026-10-10

Windows、Android 与 iOS 应用：**0.3.3**，手机构建号 **6**。

- **修复：** 手机真正断开、电脑真正 Stop；释放 socket、迟到帧、统计、姿态授权和渲染输出。异步发送清理之前撤销已关闭会话，旧清理不能影响新连接。
- **新增：** 任一端主动 USB 连接，前台控制与视频分离；电脑重复连接保留手机既有会话。iOS 停止确认及设备 / 代际保护，阻止旧就绪事件重新启动采集。
- **修复：** 有限 ADB 启动 / 恢复，临时故障时保留映射归属，支持不拔线重新连接。
- **修复：** Windows DXGI 继续串流系统已遮罩的画面；受保护区域保持黑色，真实布局 / 访问 / 资源故障仍停止采集。
- **新增：** 两个手机端显示实际安装版本 / 构建号；可复用连接模块、完整 [模块目录](docs/MODULES.md) 和双语 [AI 接手提示词](AI_HANDOFF.md)。
- **修复：** iOS 局域网连接在打开前有 15 秒等待上限；取消或过期的升级请求不能恢复旧会话或画面。
- **验证：** 80 项 Swift 核心、五项真实原生模拟器界面、两种 iOS SDK 构建及颜色 / 接缝检查通过，真实 iPhone USB 尚未实测。
- **发布：** 固定 Android 证书校验拒绝无关 CI 调试签名；除源码测试外检查普通启动和公开 ZIP。

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

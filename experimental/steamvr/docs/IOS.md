# 📱 iOS SteamVR experimental client / iOS SteamVR 实验客户端

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

### A separate app

The published preview remains **0.5.0/build 1**. Current unpublished source is **0.5.1/build 3**; the verified earlier `cc83978` baseline below is **0.5.1/build 2**, with ordinary **0.4.0/build 8** preserved. Live-video Refresh passed the earlier iOS CI baseline described below; new host-guard CI/final packaging and physical iPhone/recovery acceptance remain pending. The released baseline results below keep their original source/version attribution. Huawei observations belong to Android, not iPhone; see [validation](VALIDATION.md).

The preview app is **VRization SteamVR Experimental**, version **0.5.0, build 1**, bundle identifier `org.vrization.ios.steamvr`. It uses a separate Xcode project and local preferences; the ordinary VRization app and its saved settings remain available. English is the default; select English or 中文 in settings.

This client receives either an ordinary desktop picture or independently rendered left/right SteamVR pictures. Its negotiated session decides the route. The phone HMD route sends full head orientation to the virtual headset; it does not inject mouse movement. Windows setup and driver registration are documented in the [native guide](../native/README.md).

### Build or open the Simulator app

Use macOS with Xcode, its command-line tools and an installed iPhone Simulator runtime. The app deployment target is iOS 15.0; this minimum is a build target, not a claim that every iOS 15 device has been tested. Metal and Core Motion availability are checked at runtime.

Open `ios/VRizationSteamVR.xcodeproj`, select the **VRizationSteamVR** scheme and an iPhone Simulator, then Run. The ordinary project is `ios/VRization.xcodeproj`; choose the experimental project deliberately.

To run the complete automated checks from a repository checkout:

```sh
python3 -m venv .venv-ios-steamvr
source .venv-ios-steamvr/bin/activate
python -m pip install -e desktop
python scripts/build_ios_steamvr.py
```

The script runs the unchanged stable Swift package tests, the separate SteamVR Swift package tests, unsigned iOS Simulator and device SDK builds, and native Simulator UI tests. It starts an isolated synthetic stereo host and simulated USB bridge, then stops them. It does not register a SteamVR driver or send OS mouse input. For core-only checks, run `swift test --package-path ios/SteamVR`.

Successful runs create `artifacts/ios-steamvr/VRization-SteamVR-iOS-Simulator.zip` and `VRization-SteamVR-iOS-source.zip`. Unzip the Simulator package and install its `.app` into a booted compatible Simulator with `xcrun simctl install booted VRizationSteamVRApp.app`. The source package includes the ordinary and experimental projects and reusable cores; use a full checkout for the Python CI fixture.

**Neither archive is a signed iPhone installation package.** For a real iPhone, open the experimental project on a Mac, select your signing team and connected device, and build with your own Apple provisioning. Signing, Developer Mode and device trust may require actions on the phone. No App Store, TestFlight or signed IPA distribution is provided by these unsigned builds.

### Connect an iPhone

USB is the default. Install and start the experimental app, keep it in the foreground and unlock the phone. On Windows, use Apple's device support and approve “Trust This Computer” if prompted. Select the experimental host's phone route and start streaming, or use the phone's Connect button. The device-side preview ports are **18776 for video and 18777 for control**; the ordinary app uses different ports. A charging cable or an entry in Device Manager alone does not verify the complete USB stream.

For LAN, choose **LAN**, enter the host's address, preview port **8766** and current pairing code, then Connect. Use the same trusted network and allow local-network access if iOS asks. The pairing code is not stored locally.

The phone waits for a validated host hello and a complete accepted session snapshot before displaying stereo frames or sending HMD orientation. “Connected” with “Waiting for computer frame” can mean that transport is ready while the computer has no compositor picture yet. Check the host's selected route and capture status. A changed route or session epoch clears the picture and requires reconnecting. An old host remains ordinary mono/mouse streaming; it cannot silently become a virtual headset.

### Refresh without interrupting a live HMD

The 0.5.1 source adds toolbar **Refresh**. A live accepted HMD with `video-refresh` rebuilds video while keeping transport/epoch and saved fit. The independent `VideoRefreshGate` rejects pre-ACK/old decode work until the current epoch/request matches; its paused ACK is status, not independent Resume permission. The user's explicit action now requests guarded host-side tracking recovery after cleanup as described below. A full-reconnect fallback carries that intent once into its new accepted capable HMD session; ordinary Connect/Save, background or Stop never grant it. No separate Resume/Recenter/settings replay is sent. Current build-3 Xcode CI and physical recovery remain pending.

**Startup-header fix: regression passed, bounded phone observations recorded.** A fresh shared-memory mapping briefly exposes an empty header before its first legal publication. The reader now waits only for that initial exact 64-byte all-zero state; malformed or later-zero headers remain strict, and close resets initialization. The earlier startup-header revision passed **506 actual tests plus 435 subtests**, with zero failures/errors/skips. A candidate then retained valid tracking in **94 samples across three phone Refreshes and one PC double-click Refresh**; helper/map replacement was observed and the phone still showed the SteamVR scene. Earlier `cc83978` CI predates this host change. The user subsequently reported gray output again. The later explicit Refresh-recovery contract is not covered by this earlier 506-test result; new full regression/CI/package and physical reboot acceptance remain pending.

### Fit, move and recenter

Long-press the picture to show settings; Hide returns to the view. Open the display editor at the top of settings. Drag a corner to scale proportionally, drag inside an eye to move it, and adjust mirrored eye spacing. Save commits and synchronizes the layout; Discard restores the previous layout. Local preferences survive relaunch. Reset restores this experimental app's defaults without modifying the ordinary app's profile.

SteamVR SBS frames already contain two projected eyes. Each phone eye samples its own half with the correct half-image aspect and a boundary clamp. The viewer and editor bypass the ordinary Cinema projection and Enhanced first person's forced square/warp for these frames, while preserving the selected mode in the profile. Scale, movement, eye spacing and one optional lens-distortion stage still apply. The same saved mode resumes its ordinary meaning when connected to a mono desktop stream.

Field of view and screen distance do not add another projection to SBS. Mouse sensitivity, invert Y and stabilization are stored for direct mouse sessions; virtual HMD orientation does not use those mouse settings.

Double-tap the picture or use Recenter while looking forward. The client resets its local full-rotation baseline and sends the origin control before subsequent poses; pose sequence numbers remain increasing. Opening the editor pauses host tracking. Save, Discard, a mode change or reconnect cannot release an emergency pause: use the computer's explicit Resume control. F8 on the computer pauses tracking.

A phone without available device-motion tracking may still display stereo video, with an honest no-tracking notice and invalid tracking messages. It never invents a quaternion. Backgrounding or disconnecting the app clears video and tracking. This orientation path supplies rotational tracking; it does not create positional room-scale tracking or VR controllers. Audio remains on the computer.

### Raster limits and validation evidence

The preview requires an unrotated JPEG with even packed width and both raster edges no larger than **2048 pixels**. The host should resize each eye before packing. Unsupported packed images are rejected with a reconnect notice instead of thumbnail-resizing across the eye boundary.

The [final verified CI run 38094239121, job 114336723064](https://github.com/LexZeon/VRization/actions/runs/38094239121/job/114336723064), source commit [`a20ba0757dc3b0f45f3ffc16c87f061cc34d64bb`](https://github.com/LexZeon/VRization/commit/a20ba0757dc3b0f45f3ffc16c87f061cc34d64bb), passed **95 unchanged stable core tests, 21 SteamVR core tests, 3 checker/package helper tests and 2 native UI tests**. The native UI summary records zero failures, skipped tests or expected failures. The environment was Xcode 26.3 (17C529) on macOS 15.7.9, arm64 iPhone 17 Pro Max Simulator running iOS 26.2. Both **iOS Simulator 26.2 and device iOS 26.2 SDK builds** succeeded unsigned, with bundle `org.vrization.ios.steamvr`, version 0.5.0/build 1 and deployment target iOS 15.0. The CI Simulator archive's executable matches the built app, and all **69 CI source archive files** match that Git commit byte for byte. The iOS app/core/project and stable tests are unchanged from verified commit `045ae23`; the experimental native UI test alone changed in `979fd61`. [CI 38094098823](https://github.com/LexZeon/VRization/actions/runs/38094098823/job/114336307526), source `979fd618781346ee9805d3fd45c0a78d9c1664e9`, also passed; its entire iOS tree and build/fixture helpers match the final run.

The final original native exports contain **7 PNGs and 50 pixel checks**: 16 eye-color checks, 16 straight-border checks, 8 outside-content masks and 10 disconnected-black checks. Independent verification reran the checker and reread the original pixels. The **6 host checkpoints** cover LAN connection, editor Discard/Save, LAN disconnection, simulated USB connection and USB disconnection. The passed native test waits for the visible editor/handle, performs a slower held real corner drag and strictly requires the actual draft scale to decrease **before Save**; the original host Save assertion and all pixel checks remain strict. The host recorded scale **0.85 → 0.7530025214802623**, preserving `fps_enhanced`; simulated USB reconnect restores exactly **0.7530025214802623**. Discard preserves the previous settings. There were **zero mouse moves**, and all 28 recorded tracking sink updates were invalid with no invented quaternion. No SteamVR driver was registered and no physical iPhone was tested.

The retained [CI 38093072466 failure](https://github.com/LexZeon/VRization/actions/runs/38093072466/job/114333306236), source `550f845`, had one passed and one failed native UI case: a very short corner drag left the real draft at 0.85, and the host correctly saved that unchanged value. Pixel verification and package creation did not run. Revision `979fd61` changes only native test readiness/gesture timing and adds the draft-before-Save assertion; it introduces no production change or settings shortcut. Both later CI runs passed those strict checks. The [illustrated tutorial](TUTORIAL.md) retains its original **CI 38092654893 / `cfaf0c8`** screenshot attribution; those images are not relabeled as final-run exports.

The preserved [ordinary iOS regression](https://github.com/LexZeon/VRization/actions/runs/38092149615/job/114330605939), source `045ae23`, independently passed **95 Swift tests, 7 native UI cases, 26 PNGs, 38 enhanced checks, 16 ordinary color checks, 2 seam checks and 15 host checkpoints**, with zero failed/skipped UI cases and zero mouse moves. Its ordinary bundle is `org.vrization.ios`, version **0.4.0/build 8**. The ordinary app/shared renderer/core/stable tests/project source remains identical through final commit `a20ba075`; this preserves direct-phone regression evidence, not a new hardware test. Published v0.4.0 packages remain preserved.

Evidence is recorded under `artifacts/ios-steamvr/`: `UI.xcresult`, `screenshots/manifest.json`, `screenshots/stereo-check.json`, `host-report.json`, `environment.json` and `fixture.log`. These checks exercise real Swift/UIKit/Metal and real host messages with an original synthetic color card; USB enumeration is simulated. They establish independent eye sampling, aspect/projection behavior, editor synchronization, disconnect clearing and honest unavailable tracking in that Simulator environment. They do not establish physical USB or a running SteamVR compositor. Original screenshot bytes and their orientation metadata remain preserved.

Physical iPhone USB, both landscape orientations on real sensors, game compatibility, SteamVR compositor integration, sustained FPS and end-to-end latency require later hardware testing. The received FPS and ping in the app are stream throughput and round-trip time, not a motion-to-photon measurement. Synthetic screenshots must not be substituted for native UI evidence.

**0.5.1 attempt history:** The earlier full-reconnect candidate `fc607e6` in [CI 38108240331](https://github.com/LexZeon/VRization/actions/runs/38108240331) passed 95 stable/21 preview Swift tests and both unsigned SDK builds, but its native UI had one pass and one failure after simulated USB full-reconnect Refresh (`usbFailed`). Its retained images/checkpoints are partial evidence, not a completed UI or new live-refresh pass. The subsequent [CI 38109367242](https://github.com/LexZeon/VRization/actions/runs/38109367242), source `ad092b0`, passed 95 stable/30 preview Swift tests and both SDKs, but both UI cases failed at the test observer event-count assertion because the synthetic helper omitted `video_refreshed`. Its existing ACK/paused-wait assertions passed; retained partial evidence contains five native PNGs/four checkpoints and 40 independently checked pixels, zero mouse moves and 512 invalid tracking sink records. This is a test-helper failure, not a complete UI or physical recovery pass.

**Verified earlier iOS live-refresh baseline — `cc83978`:** [CI 38110018576, job 114383462034](https://github.com/LexZeon/VRization/actions/runs/38110018576/job/114383462034), exact source `cc8397836fd88e8d8a9e60a3fbaa0cf86b1c0878`, passed **95 stable +30 preview Swift tests, four helper tests and two native UI cases**, zero failures/skips. Independent review checked **nine original PNGs, 70 pixel samples and ten host checkpoints**, zero mouse moves and all **512 tracking records invalid** without sensors. Live LAN Refresh retained epoch 1; simulated USB Refresh retained epoch 2, while actual fixture Disconnect/Reconnect changed 2→3 with pause and all eleven settings preserved. Native editor Save changed scale 0.85→0.7530025214802623. Both unsigned arm64 SDK 26.2 builds identify `org.vrization.ios.steamvr`, **0.5.1/build 2**, minimum iOS 15.0; all **70 source ZIP files** match that commit and the Simulator archive matches the built executable/debug payload/Metal library. Environment: Xcode 26.3.0 (17C529), macOS 15.7.9, iPhone 17 Pro Max Simulator/iOS 26.2. This tests real UIKit/Metal against synthetic SBS and simulated USB, not a physical iPhone, sensor, cable or SteamVR runtime; the newer host startup-header guard is outside this baseline.

### Modules and references

`ios/SteamVR` contains the reusable `VRizationSteamVRCore`: strict transient session negotiation, `VideoRefreshGate` request/ACK and independent decode-generation lifetime and one-shot explicit reconnect recovery intent, independent eye UVs, full quaternion recentering, wire messages and isolated preferences. Shared app adapters compile their extra behavior only with `STEAMVR_PREVIEW`: `MotionSource` reads fused rotations; `StreamClient` binds frames/poses to the accepted session and transport generation; `JPEGDecoder` preserves packed pixels; `StereoRenderer` applies eye sampling; `HeadsetEditorView` uses per-eye geometry; `ViewerController` connects these modules to the normal UI. The transient layout/epoch, pairing code and tracking samples are never saved in the profile. Retain these boundaries when embedding the core in another project.

The quaternion, negotiation and UV implementations and synthetic card are original VRization code under the project's MIT license. API/convention references, checked 2026-10-10: Apple's [CMAttitude rotationMatrix](https://developer.apple.com/documentation/coremotion/cmattitude/rotationmatrix), [CMQuaternion](https://developer.apple.com/documentation/coremotion/cmquaternion) and [xArbitraryZVertical](https://developer.apple.com/documentation/coremotion/cmattitudereferenceframe/xarbitraryzvertical), authored by Apple and subject to Apple's documentation/SDK terms; no Apple sample code or SDK binaries are copied. The OpenVR world-axis contract (+X right, +Y up, −Z forward) follows Valve's [Driver API documentation at v2.15.6 commit 0924064](https://github.com/ValveSoftware/openvr/blob/0924064316de3effbcd1acf1e309182a2deb1c05/docs/Driver_API_Documentation.md#poses), an architecture reference. The iOS app bundles no OpenVR library or driver; the Windows bundle's BSD-3-Clause notices are preserved in the [native license record](../native/licenses/README.md). UIKit, Metal, ImageIO and Core Motion are Apple system frameworks, not redistributable project dependencies.

**Explicit Phone HMD Refresh now also requests tracking recovery.** This user-authorized exception applies only to the accepted, enabled SteamVR Phone HMD route. Only after worker-owned old-video cleanup completes may the host recover a pause that existed when Refresh was requested; that receipt does not guarantee the new Mirror has already published its first frame. Already-active tracking keeps its baseline; recovery of a paused stream follows existing Resume rules and needs fresh valid sensor data, never replayed motion. A captured pause generation makes newer F8/editor pauses or disabling tracking take precedence; Stop, closing the window or replacing the owner/epoch cancels recovery. Stop atomically revokes the active/accepted HMD session and latches pause under the same HMD lock used by refresh recovery, so an in-flight completion cannot restore that stopped session. Repeated PC clicks and an overlapping phone request share one reset/ACK. A user-requested full-reconnect fallback carries one transient intent only into its new accepted capable HMD session; an eight-second fallback may carry it once, not loop indefinitely. Ordinary Connect, automatic reconnect and Save/Discard do not arm that intent. Direct-phone mouse control is unchanged. Earlier ACK paused fields remain status, not standalone recovery authority. The earlier focused regression passed **43 software tests plus 32 subcases**; complete regression after the atomic Stop refinement, build-3 phone/iOS CI, final packaging and physical recovery acceptance are pending. The latest user check still reported gray output after Refresh/editing; no successful gray-screen or reboot fix is claimed.

---

<!-- vrization:chinese -->
## 简体中文

### 独立应用

公开实验版仍为 **0.5.0/build 1**，当前未发布源码为 **0.5.1/build 3**；下文早先已核验的 `cc83978` 基线为 **0.5.1/build 2**，普通 **0.4.0/build 8** 保留。活动视频刷新已通过下文的早先 iOS CI 基线，新电脑保护 CI／最终打包和实体 iPhone／恢复验收尚待；下文保留已发布基线的原源码／版本来源，华为观察属于 Android，不代表 iPhone，通过[验证记录](VALIDATION.md)查看范围。

实验应用名为 **VRization SteamVR Experimental**，版本 **0.5.0，build 1**，Bundle ID 为 `org.vrization.ios.steamvr`。它使用独立 Xcode 项目和本地设置，普通 VRization 应用及其已有设置继续保留。默认语言为英文，可在设置选择 English 或中文。

客户端可接收普通桌面画面，也可接收分别渲染的 SteamVR 左右眼画面，由协商后的会话决定路线。手机头显路线发送完整头部方向给虚拟头显，不注入鼠标移动。Windows 设置与驱动注册见[原生组件指南](../native/README.md)。

### 构建或运行模拟器应用

需要 macOS、Xcode、其命令行工具及已安装的 iPhone 模拟器运行环境。应用部署下限为 iOS 15.0；这是构建目标，不表示所有 iOS 15 设备均已测试。Metal 与 Core Motion 的可用性在运行时检查。

打开 `ios/VRizationSteamVR.xcodeproj`，选择 **VRizationSteamVR** scheme 和 iPhone 模拟器，然后运行。普通版项目为 `ios/VRization.xcodeproj`，请明确选择实验版项目。

在完整仓库中运行全部自动检查：

```sh
python3 -m venv .venv-ios-steamvr
source .venv-ios-steamvr/bin/activate
python -m pip install -e desktop
python scripts/build_ios_steamvr.py
```

脚本执行未修改的正式版 Swift 核心测试、独立 SteamVR Swift 核心测试、未签名的 iOS 模拟器与设备 SDK 构建，以及原生模拟器界面测试。它启动隔离的合成双眼测试服务和模拟 USB 桥接，结束后关闭；不会注册 SteamVR 驱动或发送系统鼠标输入。只检查核心可执行 `swift test --package-path ios/SteamVR`。

成功运行后生成 `artifacts/ios-steamvr/VRization-SteamVR-iOS-Simulator.zip` 和 `VRization-SteamVR-iOS-source.zip`。解压模拟器包，用 `xcrun simctl install booted VRizationSteamVRApp.app` 将其中 `.app` 安装到已启动且兼容的模拟器。源码包包含普通版和实验版项目及可复用核心；运行 Python CI 测试服务需完整仓库。

**两种压缩包都不是已签名的 iPhone 安装包。** 真机需要在 Mac 打开实验项目，选择自己的签名团队和已连接设备，使用自己的 Apple 配置构建。签名、开发者模式和设备信任可能需要在手机操作。未签名构建不提供 App Store、TestFlight 或已签名 IPA 分发。

### 连接 iPhone

默认 USB。安装并启动实验应用，保持前台和手机解锁。Windows 需要 Apple 设备支持；若出现“信任此电脑”，请确认。选择实验电脑端的手机路线并开始串流，或使用手机的连接按钮。手机端实验端口为 **18776 视频、18777 控制**，与普通应用端口不同。仅接入充电线或设备管理器有记录，不等于完整 USB 串流已验证。

使用局域网时选择 **LAN**，填写电脑地址、实验端口 **8766** 和当前配对码，再连接。使用同一可信网络；iOS 请求本地网络权限时允许。配对码不在本地保存。

手机在合法电脑握手和完整、已接受的会话快照到达后，才显示双眼视频和发送头显方向。“已连接”但“等待电脑画面”可能表示传输已准备好，电脑尚无合成器画面；请检查电脑路线及采集状态。路线或会话代际改变后会清除画面，需要重新连接。旧电脑端仅使用普通单图／鼠标路线，不能静默升级为虚拟头显。

### 活动头显刷新时不中断追踪

0.5.1 源码新增工具栏 **刷新**；已接受且具 `video-refresh` 的活动头显保持传输／代际及已保存适配，仅重建视频。独立 `VideoRefreshGate` 在当前代际／请求匹配之前拒绝确认前帧及旧解码；确认的暂停字段仅是状态，不是独立恢复权限。用户显式操作现按下文请求清理后的受保护电脑追踪恢复；完整重连回退只携带一次意图到其新的已接受能力头显会话，普通连接／保存、后台或停止不授权。不另发恢复／居中／设置重播；当前build3 Xcode CI及真机恢复仍待。

**启动头修复：回归已通过，记录有限手机观察。** 新共享内存映射在首次合法发布前短暂暴露空头；读端现只等待启动时准确64字节全零状态，损坏头及合法头之后再归零仍严格，关闭读端才重置初始化。早先启动头修订完整回归通过 **506 个实际测试加 435 个子检查**，零失败／错误／跳过。随后候选版三次手机刷新及一次电脑双击刷新共 **94 个姿态样本保持有效**，观察到工具／映射确实替换，手机仍显示 SteamVR 场景。用户随后再次报告灰屏；后来的显式刷新恢复契约不属于此前506测试范围，新完整回归／CI／打包及实体重启仍待验收。

### 调整、移动和回正

长按画面打开设置，隐藏按钮返回观看。设置顶部打开显示编辑器，拖动顶点等比缩放、拖动画面内部移动，并调整镜像双眼间距。保存提交并同步布局，弃用恢复此前布局。本地设置会在重启应用后沿用；重置只恢复实验应用默认值，不修改普通版配置。

SteamVR SBS 已包含两只投影后的眼睛。手机每只眼只采样对应半幅，使用半幅比例与边界钳制。观看器与编辑器对这种画面跳过普通大屏幕投影及加强第一人称的强制正方形／弯曲，同时保留配置中的所选模式。缩放、移动、眼间距及一次可选镜头畸变仍生效；重新连接单图桌面串流后，所选模式恢复普通含义。

视野角度和屏幕距离不会对 SBS 再投影。鼠标灵敏度、反转 Y 和防抖保存供直接鼠标会话使用；虚拟头显方向不使用这些鼠标设置。

面向前方时双击画面或点击回正。客户端重置本地完整旋转基准，在后续姿态前发送回正控制，姿态序号继续递增。打开编辑器会暂停电脑追踪。保存、弃用、模式切换或重连不能解除紧急暂停，可使用电脑明确的恢复按钮或受保护的显式头显刷新恢复例外；电脑 F8 暂停追踪。

没有可用设备动作追踪时，手机仍可显示双眼视频，同时明确提示无追踪，并发送无效追踪消息，不伪造四元数。应用退到后台或断开后清除视频与追踪。这一路线只提供旋转方向，不生成房间级位置追踪或 VR 控制器；音频继续留在电脑。

### 图像限制与验证证据

实验版要求 JPEG 未旋转、拼接总宽为偶数，宽高均不超过 **2048 像素**。电脑应先分眼缩小再拼接；不支持的拼接图像会拒绝并提示重连，避免整图缩略处理跨越眼睛边界。

[最终已核验 CI 38094239121，job 114336723064](https://github.com/LexZeon/VRization/actions/runs/38094239121/job/114336723064)、源码 commit [`a20ba0757dc3b0f45f3ffc16c87f061cc34d64bb`](https://github.com/LexZeon/VRization/commit/a20ba0757dc3b0f45f3ffc16c87f061cc34d64bb)，通过 **95 项未修改的正式版核心测试、21 项 SteamVR 核心测试、3 项校验／打包辅助测试及 2 项原生界面测试**；原生界面摘要中失败、跳过和预期失败均为零。环境为 macOS 15.7.9、Xcode 26.3（17C529）、arm64 iPhone 17 Pro Max 模拟器、iOS 26.2。**iOS Simulator 26.2 与设备 iOS 26.2 SDK** 均成功完成未签名构建，Bundle ID 为 `org.vrization.ios.steamvr`，版本 0.5.0/build 1，部署目标 iOS 15.0。CI 模拟器压缩包中的可执行文件与构建应用一致，**CI 源码包 69 个文件**逐字节匹配该 Git commit。iOS 应用／核心／项目配置及正式版测试与已核验 `045ae23` 相同，只有实验版原生 UI 测试在 `979fd61` 中改变。[CI 38094098823](https://github.com/LexZeon/VRization/actions/runs/38094098823/job/114336307526)、源码 `979fd618781346ee9805d3fd45c0a78d9c1664e9` 也已通过；其完整 iOS 目录与构建／测试服务辅助工具与最终构建相同。

最终原生导出保留 **7 张 PNG 和 50 项像素检查**：16 项分眼颜色、16 项直线边框、8 项画面外黑色遮罩、10 项断开后黑屏。独立审核重跑校验器，并重新读取原始像素。**6 个电脑端检查点**覆盖局域网连接、编辑器弃用／保存、局域网断开、模拟 USB 连接和模拟 USB 断开。通过的原生测试等待可见编辑器／顶点就绪，执行放慢并保持的真实顶点拖动，严格要求实际草稿比例在**保存之前**缩小；原电脑保存断言与所有像素检查继续严格执行。电脑实际记录比例 **0.85 → 0.7530025214802623**，并保留 `fps_enhanced`；模拟 USB 重连恢复完全相同的 **0.7530025214802623**。弃用保留此前设置。记录到 **零次鼠标移动**，28 条追踪接收记录全部为无效状态，没有伪造四元数；未注册 SteamVR 驱动，未测试实体 iPhone。

保留的 [CI 38093072466 失败记录](https://github.com/LexZeon/VRization/actions/runs/38093072466/job/114333306236)、源码 `550f845`，原生 UI 一项通过、一项失败：过短的顶点拖动令实际草稿保持 0.85，电脑正确保存原值，像素校验和打包未执行。修订 `979fd61` 只改变原生测试的就绪等待／拖动时间，并增加保存前草稿断言，没有修改生产代码或使用设置捷径；后续两轮 CI 均通过严格检查。[图文教程](TUTORIAL.md)继续标注原始截图来自 **CI 38092654893／`cfaf0c8`**，不把它们改标为最终构建的导出。

保留的[普通 iOS 回归](https://github.com/LexZeon/VRization/actions/runs/38092149615/job/114330605939)、源码 `045ae23`，独立核验通过 **95 项 Swift、7 项原生 UI、26 张 PNG、38 项加强模式、16 项普通颜色、2 项接缝及 15 个电脑检查点**，UI 零失败／跳过、零鼠标移动。普通应用标识为 `org.vrization.ios`，版本 **0.4.0/build 8**。普通应用／共享渲染器／核心／正式版测试／项目配置源码到最终 `a20ba075` 仍完全一致，保留直连手机的回归证据，不代表新增硬件测试；已发布 v0.4.0 包继续保留。

证据位于 `artifacts/ios-steamvr/`：`UI.xcresult`、`screenshots/manifest.json`、`screenshots/stereo-check.json`、`host-report.json`、`environment.json` 和 `fixture.log`。这些检查使用真实 Swift/UIKit/Metal 和电脑协议消息，视频源是项目原创合成色卡，USB 枚举是模拟的。它们证明该模拟器环境中的分眼采样、比例／投影、编辑器同步、断开清屏及如实无追踪行为，不证明实体 USB 或已运行的 SteamVR 合成器。截图原始字节与方向元数据均保留。

实体 iPhone USB、真传感器下两种横屏方向、游戏兼容性、SteamVR 合成器集成、持续帧率及端到端延迟需要后续硬件测试。应用接收 FPS 与 ping 分别代表传输吞吐和往返时间，不是动作到显示的延迟测量。不能用合成截图替代原生界面证据。

**0.5.1 尝试历史：** 早先完整重连候选源码 `fc607e6` 的 [CI 38108240331](https://github.com/LexZeon/VRization/actions/runs/38108240331) 通过 95 项正式／21 项实验 Swift 与双 SDK 未签名构建，但原生 UI 一项通过、一项在模拟 USB 完整重连刷新后失败（`usbFailed`）；保留的图像／检查点仅是部分证据，不是完整 UI 或新活动刷新通过。后来 [CI 38109367242](https://github.com/LexZeon/VRization/actions/runs/38109367242)、源码 `ad092b0` 通过95正式／30实验Swift及双SDK，但两项UI均在测试观察器事件数量断言失败，因合成服务漏记`video_refreshed`；其确认／暂停等待断言已通过，部分证据保留5原生PNG／4检查点、40独立核对像素、零鼠标及512无效追踪记录。这是测试服务失败，不是完整UI或物理恢复通过。

**已核验的早先 iOS 活动刷新基线——`cc83978`：** [CI 38110018576、job 114383462034](https://github.com/LexZeon/VRization/actions/runs/38110018576/job/114383462034)，准确源码 `cc8397836fd88e8d8a9e60a3fbaa0cf86b1c0878`，通过 **95 项正式＋30 项实验 Swift、四项辅助测试、两项原生 UI**，零失败／跳过。独立审查核对 **九张原始 PNG、70 个像素样本和十个电脑检查点**，零鼠标移动，无传感器下 **512 条追踪记录全部无效**。活动 LAN 刷新保持代际1，模拟 USB 刷新保持代际2；真实测试服务断开／重连令2→3，同时保留暂停与完整11项设置。原生编辑器保存令大小0.85→0.7530025214802623。双未签名 arm64 SDK26.2 构建标识 `org.vrization.ios.steamvr`、**0.5.1/build 2**、最低 iOS15.0；**源码 ZIP 全部70文件**逐字节匹配该 commit，模拟器包匹配构建的可执行文件／调试载荷／Metal 库。环境为 Xcode26.3.0（17C529）、macOS15.7.9、iPhone17ProMax模拟器／iOS26.2。范围为真实 UIKit／Metal、合成 SBS 与模拟 USB，不代表实体 iPhone、传感器、线缆或 SteamVR 运行环境；新的电脑启动头保护不属于该基线。

### 模块与来源

`ios/SteamVR` 的可复用 `VRizationSteamVRCore` 包含严格临时会话协商、`VideoRefreshGate` 请求／确认与独立解码代际生命周期及一次显式重连恢复意图、独立双眼 UV、完整四元数回正、协议消息及隔离设置。共享应用适配层只有编译条件 `STEAMVR_PREVIEW` 才启用额外行为：`MotionSource` 读取融合旋转；`StreamClient` 将帧／姿态绑定已接受的会话及传输代际；`JPEGDecoder` 保留拼接像素；`StereoRenderer` 分眼采样；`HeadsetEditorView` 使用分眼几何；`ViewerController` 将模块连接到正常界面。临时布局／代际、配对码和追踪样本不写入配置。移植到其他项目时保留这些边界。

四元数、协商、UV 实现及合成色卡是 VRization 原创代码，适用项目 MIT 许可。API／约定参考于 2026-10-10 核对：Apple 编写的 [CMAttitude rotationMatrix](https://developer.apple.com/documentation/coremotion/cmattitude/rotationmatrix)、[CMQuaternion](https://developer.apple.com/documentation/coremotion/cmquaternion)、[xArbitraryZVertical](https://developer.apple.com/documentation/coremotion/cmattitudereferenceframe/xarbitraryzvertical)，适用 Apple 文档／SDK 条款；没有复制 Apple 示例代码或 SDK 二进制。OpenVR 世界坐标约定（+X 向右、+Y 向上、−Z 向前）参考 Valve 的 [v2.15.6 commit 0924064 驱动 API 文档](https://github.com/ValveSoftware/openvr/blob/0924064316de3effbcd1acf1e309182a2deb1c05/docs/Driver_API_Documentation.md#poses)，属于架构参考。iOS 应用不附带 OpenVR 库或驱动，Windows 包的 BSD-3-Clause 声明保存在[原生许可记录](../native/licenses/README.md)。UIKit、Metal、ImageIO、Core Motion 是 Apple 系统框架，不是项目可再分发依赖。

**显式手机头显刷新现在也请求恢复追踪。** 该用户授权的例外只适用于已接受、已启用的 SteamVR 手机头显路线。仅在所属工作线程完成旧视频清理后，电脑才可恢复刷新请求时已有的暂停；该回执不保证新Mirror已经发布第一帧。原本活动的追踪保留基准，暂停流按既有恢复规则等待新的有效传感器数据，绝不重放旧动作。捕获暂停代际令事务期间新按 F8／进入编辑器或禁用追踪优先；停止、关闭窗口或替换所有者／会话代际取消恢复。停止与刷新恢复使用同一头显锁，原子撤销active／accepted会话并锁定暂停，处理中完成不能恢复已停止会话。电脑重复点击及重叠手机请求共用一次重置／确认。用户要求的完整重连回退只携带一次临时意图到其新的已接受且支持能力的头显会话；八秒超时回退最多携带一次，不无限循环。普通连接、自动重连及保存／弃用不设置该意图，手机直连鼠标控制不变；确认中的暂停字段仍只是状态，不能单独授权恢复。早先针对性回归通过 **43 项软件测试加 32 个子检查**；原子停止细化后的完整回归、手机／iOS build3 CI、最终打包和真机恢复仍待验收。最近用户检查仍报告刷新／编辑后灰屏，不声称灰屏或实体重启已经修好。

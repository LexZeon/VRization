# 📱 iOS SteamVR experimental client / iOS SteamVR 实验客户端

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

### A separate app

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

### Modules and references

`ios/SteamVR` contains the reusable `VRizationSteamVRCore`: strict transient session negotiation, independent eye UVs, full quaternion recentering, wire messages and isolated preferences. Shared app adapters compile their extra behavior only with `STEAMVR_PREVIEW`: `MotionSource` reads fused rotations; `StreamClient` binds frames/poses to the accepted session and transport generation; `JPEGDecoder` preserves packed pixels; `StereoRenderer` applies eye sampling; `HeadsetEditorView` uses per-eye geometry; `ViewerController` connects these modules to the normal UI. The transient layout/epoch, pairing code and tracking samples are never saved in the profile. Retain these boundaries when embedding the core in another project.

The quaternion, negotiation and UV implementations and synthetic card are original VRization code under the project's MIT license. API/convention references, checked 2026-10-10: Apple's [CMAttitude rotationMatrix](https://developer.apple.com/documentation/coremotion/cmattitude/rotationmatrix), [CMQuaternion](https://developer.apple.com/documentation/coremotion/cmquaternion) and [xArbitraryZVertical](https://developer.apple.com/documentation/coremotion/cmattitudereferenceframe/xarbitraryzvertical), authored by Apple and subject to Apple's documentation/SDK terms; no Apple sample code or SDK binaries are copied. The OpenVR world-axis contract (+X right, +Y up, −Z forward) follows Valve's [Driver API documentation at v2.15.6 commit 0924064](https://github.com/ValveSoftware/openvr/blob/0924064316de3effbcd1acf1e309182a2deb1c05/docs/Driver_API_Documentation.md#poses), an architecture reference. The iOS app bundles no OpenVR library or driver; the Windows bundle's BSD-3-Clause notices are preserved in the [native license record](../native/licenses/README.md). UIKit, Metal, ImageIO and Core Motion are Apple system frameworks, not redistributable project dependencies.

---

<!-- vrization:chinese -->
## 简体中文

### 独立应用

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

### 调整、移动和回正

长按画面打开设置，隐藏按钮返回观看。设置顶部打开显示编辑器，拖动顶点等比缩放、拖动画面内部移动，并调整镜像双眼间距。保存提交并同步布局，弃用恢复此前布局。本地设置会在重启应用后沿用；重置只恢复实验应用默认值，不修改普通版配置。

SteamVR SBS 已包含两只投影后的眼睛。手机每只眼只采样对应半幅，使用半幅比例与边界钳制。观看器与编辑器对这种画面跳过普通大屏幕投影及加强第一人称的强制正方形／弯曲，同时保留配置中的所选模式。缩放、移动、眼间距及一次可选镜头畸变仍生效；重新连接单图桌面串流后，所选模式恢复普通含义。

视野角度和屏幕距离不会对 SBS 再投影。鼠标灵敏度、反转 Y 和防抖保存供直接鼠标会话使用；虚拟头显方向不使用这些鼠标设置。

面向前方时双击画面或点击回正。客户端重置本地完整旋转基准，在后续姿态前发送回正控制，姿态序号继续递增。打开编辑器会暂停电脑追踪。保存、弃用、模式切换或重连不能解除紧急暂停，须使用电脑明确的恢复按钮；电脑 F8 暂停追踪。

没有可用设备动作追踪时，手机仍可显示双眼视频，同时明确提示无追踪，并发送无效追踪消息，不伪造四元数。应用退到后台或断开后清除视频与追踪。这一路线只提供旋转方向，不生成房间级位置追踪或 VR 控制器；音频继续留在电脑。

### 图像限制与验证证据

实验版要求 JPEG 未旋转、拼接总宽为偶数，宽高均不超过 **2048 像素**。电脑应先分眼缩小再拼接；不支持的拼接图像会拒绝并提示重连，避免整图缩略处理跨越眼睛边界。

[最终已核验 CI 38094239121，job 114336723064](https://github.com/LexZeon/VRization/actions/runs/38094239121/job/114336723064)、源码 commit [`a20ba0757dc3b0f45f3ffc16c87f061cc34d64bb`](https://github.com/LexZeon/VRization/commit/a20ba0757dc3b0f45f3ffc16c87f061cc34d64bb)，通过 **95 项未修改的正式版核心测试、21 项 SteamVR 核心测试、3 项校验／打包辅助测试及 2 项原生界面测试**；原生界面摘要中失败、跳过和预期失败均为零。环境为 macOS 15.7.9、Xcode 26.3（17C529）、arm64 iPhone 17 Pro Max 模拟器、iOS 26.2。**iOS Simulator 26.2 与设备 iOS 26.2 SDK** 均成功完成未签名构建，Bundle ID 为 `org.vrization.ios.steamvr`，版本 0.5.0/build 1，部署目标 iOS 15.0。CI 模拟器压缩包中的可执行文件与构建应用一致，**CI 源码包 69 个文件**逐字节匹配该 Git commit。iOS 应用／核心／项目配置及正式版测试与已核验 `045ae23` 相同，只有实验版原生 UI 测试在 `979fd61` 中改变。[CI 38094098823](https://github.com/LexZeon/VRization/actions/runs/38094098823/job/114336307526)、源码 `979fd618781346ee9805d3fd45c0a78d9c1664e9` 也已通过；其完整 iOS 目录与构建／测试服务辅助工具与最终构建相同。

最终原生导出保留 **7 张 PNG 和 50 项像素检查**：16 项分眼颜色、16 项直线边框、8 项画面外黑色遮罩、10 项断开后黑屏。独立审核重跑校验器，并重新读取原始像素。**6 个电脑端检查点**覆盖局域网连接、编辑器弃用／保存、局域网断开、模拟 USB 连接和模拟 USB 断开。通过的原生测试等待可见编辑器／顶点就绪，执行放慢并保持的真实顶点拖动，严格要求实际草稿比例在**保存之前**缩小；原电脑保存断言与所有像素检查继续严格执行。电脑实际记录比例 **0.85 → 0.7530025214802623**，并保留 `fps_enhanced`；模拟 USB 重连恢复完全相同的 **0.7530025214802623**。弃用保留此前设置。记录到 **零次鼠标移动**，28 条追踪接收记录全部为无效状态，没有伪造四元数；未注册 SteamVR 驱动，未测试实体 iPhone。

保留的 [CI 38093072466 失败记录](https://github.com/LexZeon/VRization/actions/runs/38093072466/job/114333306236)、源码 `550f845`，原生 UI 一项通过、一项失败：过短的顶点拖动令实际草稿保持 0.85，电脑正确保存原值，像素校验和打包未执行。修订 `979fd61` 只改变原生测试的就绪等待／拖动时间，并增加保存前草稿断言，没有修改生产代码或使用设置捷径；后续两轮 CI 均通过严格检查。[图文教程](TUTORIAL.md)继续标注原始截图来自 **CI 38092654893／`cfaf0c8`**，不把它们改标为最终构建的导出。

保留的[普通 iOS 回归](https://github.com/LexZeon/VRization/actions/runs/38092149615/job/114330605939)、源码 `045ae23`，独立核验通过 **95 项 Swift、7 项原生 UI、26 张 PNG、38 项加强模式、16 项普通颜色、2 项接缝及 15 个电脑检查点**，UI 零失败／跳过、零鼠标移动。普通应用标识为 `org.vrization.ios`，版本 **0.4.0/build 8**。普通应用／共享渲染器／核心／正式版测试／项目配置源码到最终 `a20ba075` 仍完全一致，保留直连手机的回归证据，不代表新增硬件测试；已发布 v0.4.0 包继续保留。

证据位于 `artifacts/ios-steamvr/`：`UI.xcresult`、`screenshots/manifest.json`、`screenshots/stereo-check.json`、`host-report.json`、`environment.json` 和 `fixture.log`。这些检查使用真实 Swift/UIKit/Metal 和电脑协议消息，视频源是项目原创合成色卡，USB 枚举是模拟的。它们证明该模拟器环境中的分眼采样、比例／投影、编辑器同步、断开清屏及如实无追踪行为，不证明实体 USB 或已运行的 SteamVR 合成器。截图原始字节与方向元数据均保留。

实体 iPhone USB、真传感器下两种横屏方向、游戏兼容性、SteamVR 合成器集成、持续帧率及端到端延迟需要后续硬件测试。应用接收 FPS 与 ping 分别代表传输吞吐和往返时间，不是动作到显示的延迟测量。不能用合成截图替代原生界面证据。

### 模块与来源

`ios/SteamVR` 的可复用 `VRizationSteamVRCore` 包含严格的临时会话协商、独立双眼 UV、完整四元数回正、协议消息及隔离设置。共享应用适配层只有编译条件 `STEAMVR_PREVIEW` 才启用额外行为：`MotionSource` 读取融合旋转；`StreamClient` 将帧／姿态绑定已接受的会话及传输代际；`JPEGDecoder` 保留拼接像素；`StereoRenderer` 分眼采样；`HeadsetEditorView` 使用分眼几何；`ViewerController` 将模块连接到正常界面。临时布局／代际、配对码和追踪样本不写入配置。移植到其他项目时保留这些边界。

四元数、协商、UV 实现及合成色卡是 VRization 原创代码，适用项目 MIT 许可。API／约定参考于 2026-10-10 核对：Apple 编写的 [CMAttitude rotationMatrix](https://developer.apple.com/documentation/coremotion/cmattitude/rotationmatrix)、[CMQuaternion](https://developer.apple.com/documentation/coremotion/cmquaternion)、[xArbitraryZVertical](https://developer.apple.com/documentation/coremotion/cmattitudereferenceframe/xarbitraryzvertical)，适用 Apple 文档／SDK 条款；没有复制 Apple 示例代码或 SDK 二进制。OpenVR 世界坐标约定（+X 向右、+Y 向上、−Z 向前）参考 Valve 的 [v2.15.6 commit 0924064 驱动 API 文档](https://github.com/ValveSoftware/openvr/blob/0924064316de3effbcd1acf1e309182a2deb1c05/docs/Driver_API_Documentation.md#poses)，属于架构参考。iOS 应用不附带 OpenVR 库或驱动，Windows 包的 BSD-3-Clause 声明保存在[原生许可记录](../native/licenses/README.md)。UIKit、Metal、ImageIO、Core Motion 是 Apple 系统框架，不是项目可再分发依赖。

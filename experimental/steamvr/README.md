# 🧪 VRization SteamVR experiment / SteamVR 实验版

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

This is the separate **0.5.0-steamvr-preview** experiment, based on the released v0.4.0 code. Keep ordinary VRization and all historical downloads. Its three entries connect different frame/input paths; they are not additional direct-phone display modes. English is the default, with selectable Simplified Chinese. Hardware testing with Huawei and PCVR is deferred to the next session: no real SteamVR HMD, physical cable, headset optics, gyro axes, FPS or end-to-end latency pass is claimed here.

| Entry | What it does | What to use |
| --- | --- | --- |
| 📱 Original direct phone | Captures a desktop/display region; retains Full screen, Big screen, First person and Enhanced first person. First-person gyro can control the Windows mouse under the existing local input policy. | Preview Windows host + separate preview phone app; original apps remain available separately |
| 🥽 Phone as SteamVR HMD | Full phone orientation drives a virtual 3DOF HMD; the compositor supplies independent left/right images. This route never moves the Windows mouse. | SteamVR installed separately, explicit registration of this preview's driver, and preview Android/iOS client |
| 🎮 Existing SteamVR headset | Adds a desktop screen overlay 3 m wide, 2 m ahead of an already connected native headset. SteamVR games continue using that headset and its existing controllers/tracking. | Existing PCVR or standalone-to-PC SteamVR transport; no phone app required |

A standalone headset must already connect to SteamVR through a compatible transport. This preview does not supply an Android standalone OpenXR app, tracked controllers or a replacement vendor driver. It does not overwrite DPVR, remove other drivers, or edit `forceDriver` or global SteamVR configuration. Phone virtual-display/headless behavior and switching between virtual/physical HMDs remain hardware acceptance items; a SteamVR restart may be needed.

### 📦 Separate installation and connection

Extract the complete experimental Windows package and run its launcher. Keep that folder in place after manually registering its driver. The ordinary `Start-Windows.bat` and stable app install are independent; this experiment does not refresh stable `latest`.

The launcher provides **Register Phone HMD**, **Remove this driver** and **Open SteamVR** as explicit user actions. Registration calls the installed runtime's `vrpathreg adddriver` for only this package's driver directory; removal uses `removedriver` for that same directory. Opening the launcher or its diagnostics performs none of these actions and starts no capture. Do not register or launch a runtime during unattended source/fixture checks.

USB remains the first connection preference, with explicit LAN support. Preview endpoints are isolated:

| Component | Preview identity / endpoints |
| --- | --- |
| Windows | `%LOCALAPPDATA%/VRizationSteamVR/Windows`; each route has a separate child preference directory |
| HTTP/WebSocket host | TCP 8766; ordinary host retains 8765 |
| Android | `org.vrization.steamvr`, version `0.5.0-steamvr-preview` / build 1; preferences `vrization_steamvr`; USB control 18774, video/bootstrap 18775 |
| iOS | `org.vrization.ios.steamvr`, version 0.5.0 / build 1; preference key `steamvrPhonePreferencesV1`; USB video 18776, control 18777 |

Use the matching preview app for preview USB endpoints. Preview clients can retain the legacy mono/mouse protocol when no stereo session is negotiated; this never silently turns a direct-phone session into a virtual HMD. Android APK builds are separate install identities. iOS source and Simulator output are not a signed, directly installable iPhone app; physical installation requires the user's Apple signing setup.

For the phone HMD route, explicitly register its driver, start SteamVR, choose the phone entry and start streaming, then connect the preview phone. The host waits for the phone's `stereo-sbs` and `hmd-orientation` capabilities and a complete accepted session snapshot before sending stereo frames. An old client that cannot handle this pairing is rejected with an explanation instead of receiving stereo it cannot render.

### 🎛️ Fit, tracking and Stop

SBS uses each eye's half of the source image and its own aspect ratio. Fit scale, movement, mirrored eye spacing, corner editing, Save/Discard and synchronized local settings remain usable. SteamVR already owns perspective: Cinema and Enhanced square/fisheye projection are bypassed for SBS rendering while the user's saved direct-phone mode is retained. The phone applies its lens correction once; eye UV clamps prevent sampling across the center seam.

The phone sends full normalized XYZW orientation, not a quaternion reconstructed from Euler mouse angles. This is **3DOF rotation only**, with fixed 1.6 m height and no tracked translation/controllers. No sensor or invalid/stale data produces unavailable tracking, not a fabricated valid identity pose.

**F8, opening the fit editor, Stop and disconnect invalidate HMD tracking.** F8/editor/Stop emergency pause stays latched through reconnect, mode change and Save/Discard. Recenter changes the baseline but does not release that latch. Only **Resume HMD tracking on the PC** releases it, after local conditions allow it. Tracking enabled/paused state is separate from persistent display settings and from the ordinary mouse-control route.

Stop closes the current host session and owned native helper, clears old frames and invalidates pose data. Helpers observe a unique host Stop event and clean up their own resources; a bounded termination fallback exists for a stuck child. The existing-headset overlay hides/clears on inactive or stale frames and destroys only its own overlay. It does not shut down SteamVR or another app.

### 🛠️ Build, attribution and next test

Native Windows targets are built on a Windows x64 MSVC runner:

The four native targets and 365 runtime-independent fixture checks passed in [CI 38093072466](https://github.com/LexZeon/VRization/actions/runs/38093072466/job/114333306286), source `550f845f5b551f2c52c36491e3d0c37f313b0ff9`; its complete native bundle was independently audited against exact SDK/asset hashes. An earlier build of identical native source also passed a local software-WARP replay. Local Windows/Python 387 cases plus 312 subtests, 40 script cases and Android 176 cases passed; iOS preview passed both SDK builds, 95+21 Swift cases, two UI cases and 50 pixel samples. The complete Windows ZIP's isolated startup/owned IPC passed and now runs in future preview CI. See [verification and limits](docs/VALIDATION.md) and the [illustrated connection tutorial](docs/TUTORIAL.md). These results do not validate real SteamVR or physical phones.

```powershell
python scripts/build_steamvr_native.py --configuration Release --test
python -m unittest discover -s scripts -p test_build_steamvr_native.py -v
python scripts/check_docs.py
```

Android preview tasks are `:steamvr-app:assembleSteamvrDebug`, `:steamvr-app:testSteamvrDebugUnitTest` and `:steamvr-app:lintSteamvrDebug`; instrumentation is compiled separately and must be executed on a device before a hardware pass is recorded. The separate iOS Xcode project is `ios/VRizationSteamVR.xcodeproj`, with its reusable Swift package in `ios/SteamVR`. Native fixtures use Windows mappings, Stop events, software WARP pixels and the driver factory ABI without registering a driver or starting SteamVR. Simulator/software fixtures establish only their stated scope.

Valve OpenVR v2.15.6 is pinned to commit `0924064316de3effbcd1acf1e309182a2deb1c05`, with five exact SHA256 files and its original **BSD-3-Clause** license. VRization's IPC, tracking gate, frame packing and overlay implementation are original MIT code; official HMD/overlay lifecycle ideas are credited even without copying sample code. See [native provenance](native/licenses/README.md), [architecture](docs/ARCHITECTURE.md) and [AI handoff](docs/AI_HANDOFF.md).

Next hardware session must verify repeated USB connect/Stop/reconnect without cable replug, both-eye source isolation and optics on the phone, yaw/pitch/roll and recenter across phone orientation, F8/editor latch and local Resume, SteamVR virtual HMD initialization/compositor frame availability, existing native-headset overlay cleanup, and measured FPS/round-trip versus separately measured motion-to-photon latency. Preserve the existing DPVR setup throughout.

---

<!-- vrization:chinese -->
## 简体中文

这是基于已发布 v0.4.0 的独立 **0.5.0-steamvr-preview** 实验版，保留普通 VRization 及全部历史下载。三个入口分别连接不同的画面／输入通路，不是新增直连手机显示模式。软件默认英文，可选择简体中文。华为与 PCVR 真机测试留到下一次：本页不声称真实 SteamVR 头显、实体线缆、头显光学、陀螺仪坐标、帧率或端到端延迟已经通过。

| 入口 | 功能 | 使用条件 |
| --- | --- | --- |
| 📱 原版手机直连 | 采集桌面／选区，保留全屏、大屏幕、第一人称、加强第一人称。第一人称陀螺仪按既有本地输入规则控制 Windows 鼠标。 | 实验版电脑端和独立实验版手机端；原版应用另外保留 |
| 🥽 手机作为 SteamVR 头显 | 手机完整方向驱动虚拟三自由度头显，合成器提供独立左右眼图像；此路线不移动 Windows 鼠标。 | 另装 SteamVR、显式注册本实验版驱动、实验版 Android／iOS 手机端 |
| 🎮 现有 SteamVR 头显 | 在已连接实体头显前方 2 米添加宽 3 米的桌面覆盖层；SteamVR 游戏仍使用原有头显、控制器和追踪。 | 已有 PCVR 或一体机连接电脑的 SteamVR 通路；不需要手机应用 |

一体机必须已通过兼容通路连接 SteamVR。本实验不提供 Android 一体机 OpenXR 应用、追踪控制器或替代厂商驱动，不覆盖 DPVR、不移除其他驱动，也不修改 `forceDriver` 或 SteamVR 全局配置。手机虚拟显示／无实体显示运行、虚拟与实体头显切换都留待实机验收，可能需要重启 SteamVR。

### 📦 独立安装与连接

完整解压实验版 Windows 包，运行其中的启动器；手动注册驱动后保留该目录。普通 `Start-Windows.bat` 和正式应用安装相互独立；本实验不刷新正式 `latest`。

启动器的“注册手机头显”“移除此驱动”“打开 SteamVR”均是用户显式操作。注册只用已安装运行环境的 `vrpathreg adddriver` 添加本包驱动路径，移除只用 `removedriver` 删除同一路径。仅打开启动器或运行诊断不会执行这些动作，也不会开始采集；无人值守源码／测试检查时不要注册或启动运行环境。

USB 仍为优先连接方式，另保留显式局域网；实验版端点独立：

| 组件 | 实验版标识／端点 |
| --- | --- |
| Windows | `%LOCALAPPDATA%/VRizationSteamVR/Windows`；每条路线有独立子设置目录 |
| HTTP／WebSocket 电脑服务 | TCP 8766，原版仍为 8765 |
| Android | `org.vrization.steamvr`、版本 `0.5.0-steamvr-preview`／build 1；设置 `vrization_steamvr`；USB 控制 18774，视频／发现 18775 |
| iOS | `org.vrization.ios.steamvr`、版本 0.5.0／build 1；设置键 `steamvrPhonePreferencesV1`；USB 视频 18776，控制 18777 |

实验版 USB 端点使用对应实验版应用。未协商双眼会话时，实验版手机可保留旧的 mono／mouse 协议，不会把直连会话悄悄变成虚拟头显。Android APK 使用独立安装标识；iOS 源码／模拟器产物不是已签名、可直接安装的 iPhone 应用，真机安装需要用户的 Apple 签名环境。

手机头显路线需显式注册其驱动、启动 SteamVR、选择手机入口并开始串流，再连接实验版手机。电脑端收到 `stereo-sbs` 和 `hmd-orientation` 能力，发送完整的已接受会话快照后，才发双眼帧。不能处理此组合的旧手机会明确收到拒绝说明，不会收到无法正确渲染的双眼画面。

### 🎛️ 适配、追踪与停止

SBS 为每眼使用各自半幅源图及自身比例，仍可缩放、移动、镜像调整眼间距、拖顶点、保存／弃用并同步本地设置。SteamVR 已决定透视，所以双眼渲染绕过大屏幕和加强正方形／鱼眼投影，但保留用户存储的直连模式。手机镜片补偿只做一次，分眼 UV 边界防止采样穿过中缝。

手机发送完整归一化 XYZW 方向，不从鼠标用的欧拉角重建四元数。它只有 **3DOF 旋转**，固定 1.6 米高度，没有位置追踪／控制器。缺传感器或无效／旧数据只产生不可用追踪，不伪造有效恒等姿态。

**F8、打开适配编辑器、停止和断开都会令头显追踪无效。** F8／编辑器／停止的紧急暂停在重连、切模式和保存／弃用后仍锁定；重新居中只改基准，不解除锁定。只有电脑本地条件允许后的“恢复头显追踪”可以解除。追踪启用／暂停状态与持久显示设置、原版鼠标路线相互独立。

停止会关闭当前电脑会话和自身原生子进程，清除旧帧并令姿态无效。工具检查独立 Stop 事件，清理自己的资源；对子进程卡死保留限时结束后备方式。已有头显覆盖层在数据停用／过期时隐藏、清空，只销毁自己覆盖层，不关闭 SteamVR 或其他应用。

### 🛠️ 构建、鸣谢及下次测试

原生 Windows 目标在 Windows x64 MSVC runner 构建：

四个原生目标及 365 项不依赖运行环境的检查在 [CI 38093072466](https://github.com/LexZeon/VRization/actions/runs/38093072466/job/114333306286) 通过，源码 `550f845f5b551f2c52c36491e3d0c37f313b0ff9`；完整原生包另核对 SDK／文件固定哈希，相同源码的较早构建也通过本地软件 WARP 复跑。本机 Windows／Python 387 项加 312 子检查、40 脚本测试、Android 176 项通过；iOS 实验版通过双 SDK、95+21 Swift、2 UI、50 像素采样。完整 Windows ZIP 的独立启动／自有 IPC 通过，并纳入未来实验 CI。见[验证及范围](docs/VALIDATION.md)和[连接图文教程](docs/TUTORIAL.md)。这些结果不验证真实 SteamVR 或实体手机。

```powershell
python scripts/build_steamvr_native.py --configuration Release --test
python -m unittest discover -s scripts -p test_build_steamvr_native.py -v
python scripts/check_docs.py
```

Android 实验版任务为 `:steamvr-app:assembleSteamvrDebug`、`:steamvr-app:testSteamvrDebugUnitTest`、`:steamvr-app:lintSteamvrDebug`；仪器测试另行编译，设备真正运行后才能记录实机通过。独立 iOS 工程为 `ios/VRizationSteamVR.xcodeproj`，可复用 Swift 包在 `ios/SteamVR`。原生测试使用 Windows 映射、Stop 事件、软件 WARP 像素及驱动工厂 ABI，不注册驱动或启动 SteamVR；模拟器／软件测试只证明其明确覆盖的范围。

Valve OpenVR v2.15.6 锁定 commit `0924064316de3effbcd1acf1e309182a2deb1c05`，五个文件校验准确 SHA256，并保留 **BSD-3-Clause** 原许可。VRization 的 IPC、追踪门控、帧拼接和覆盖层是 MIT 原创代码；即使未复制示例源码，也记录官方头显／覆盖层生命周期思路。参见[原生来源](native/licenses/README.md)、[架构](docs/ARCHITECTURE.md)、[AI 接手](docs/AI_HANDOFF.md)。

下次真机需验证：USB 反复连接／停止／重连不拔线、手机双眼源隔离与镜片、不同持机方向的 yaw／pitch／roll 与居中、F8／编辑器锁定及电脑恢复、SteamVR 虚拟头显初始化与合成帧是否可得、现有头显覆盖层清理；测量真实帧率／往返时间，另测运动到显示延迟，保持现有 DPVR 配置。

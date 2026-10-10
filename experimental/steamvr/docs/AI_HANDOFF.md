# AI/developer handoff / AI 与开发者交接

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

Use this prompt to continue the separate SteamVR preview. Read repository `AGENTS.md`, this page, [architecture](ARCHITECTURE.md), [experiment guide](../README.md) and [native guide/credits](../native/README.md) before editing. Preserve ordinary v0.4.0 and all historical files/downloads. Keep every project-owned public page complete English first and complete Chinese below; the software defaults to English and offers both languages. Root CHANGELOG must record each visible change in both languages.

> Continue VRization's separate 0.5.0-steamvr-preview. Keep three explicit routes: direct phone with existing four modes; phone as a 3DOF SteamVR HMD using full orientation and independent SBS compositor eyes; already connected native SteamVR headset with a desktop overlay. Preserve the stable app, isolated preview identities/settings/ports, local emergency-pause ownership, and all historical files. Complete tests within their true scope. Hardware Huawei and PCVR verification was deferred to the next chat; do not claim it already passed or activate attached hardware merely because it is detected.

The implemented source has real driver/pose, compositor mirror and overlay paths. Native binaries alone are not evidence that a virtual phone display works headlessly. Startup/diagnostics must not capture, send mouse input, register a driver, edit SteamVR configuration or launch SteamVR. Explicit user registration adds/removes only this package's path. Keep DPVR and every existing headset driver; never set `forceDriver` or terminate another application's process to make this preview work.

Work at the correct boundary:

1. Read `app.py` for launcher/route/local profile behavior and `runtime.py` for explicit runtime/driver actions, helper ownership and diagnostics.
2. Read `host.py`/`session.py` for HostServer extension hooks and strict video/input pairing. SBS is allowed only after both capabilities and an accepted full snapshot. Descriptor absence stays legacy mono/mouse. Never silently translate HMD orientation into Windows mouse motion.
3. Read `pose.py` for epoch, monotonic counters, accepted data, recenter and tracking pause. F8/editor/Stop latch survives reconnect/Save/mode/recenter. Only PC-local Resume clears it; absent/stale/invalid sensor data cannot become valid identity tracking.
4. Read Python/native IPC together. Keep exact 128-byte `VRP1` pose and 64-byte `VRF1` frame headers, readonly readers, one writer, seqlock barriers, bounded dimensions and Windows uptime. Only phone route owns the fixed pose map; every frame session gets a fresh unique map. Invalidate old data before closing.
5. Read native driver/mirror/overlay lifetimes before changing C++. Match OpenVR adapter; release mirror SRVs through OpenVR; hide/clear/destroy overlay before texture/context release; observe the owned Stop event and keep termination fallback limited to that owned child.
6. Read Android `StreamSession`, `OrientationMath`, `StereoProjection` and iOS `StreamSession`, `HMDQuaternion`, `StereoSampling`. Preserve full quaternion/landscape/recenter conventions, per-eye source aspect/UV clamps, one phone lens stage, saved mode restoration and independent app preferences. Pure math goldens do not establish real phone-axis correctness.
7. Use [module table](ARCHITECTURE.md#module-boundaries-and-replacement-points) when substituting capture, encoder, transport or pose sinks. Maintain direct-phone behavior and its enhanced capability fallback; do not copy logic into unrelated platform screens.

Preview identity checklist: Windows `%LOCALAPPDATA%/VRizationSteamVR/Windows` and route child profiles; host8766; Android `org.vrization.steamvr`, preferences `vrization_steamvr`, control18774/video18775; iOS `org.vrization.ios.steamvr`, `steamvrPhonePreferencesV1`, video18776/control18777. Pairing/session acceptance, pause latch and input arming must never become persistent display-setting fields. iOS Simulator/source packages are not installable signed iPhone apps.

Build/test commands:

```powershell
python scripts/build_steamvr_native.py --configuration Release --test
python -m unittest discover -s scripts -p test_build_steamvr_native.py -v
python -m unittest discover -s experimental/steamvr/tests -v
python scripts/check_docs.py
# Android from android/:
.\gradlew.bat :steamvr-app:testSteamvrDebugUnitTest :steamvr-app:assembleSteamvrDebug :steamvr-app:lintSteamvrDebug
```

The native build uses five exact SDK pins, original upstream license bytes, x64 MSVC `/MD`, software WARP pixel tests and factory ABI without runtime `Init`. Never retry an installation rejected by approval review or pretend a failed runtime initialization is an ABI pass. Use the configured Windows CI runner when local MSVC/SDK are absent. The separate iOS workflow builds `VRizationSteamVR.xcodeproj` for both SDKs and uses Simulator/native Metal tests with generated calibration fixtures. Android instrumentation must run on real/emulated Android before executed results are recorded; compilation alone is not execution. Record final source commit, build hashes, test counts, actual runner/device/runtime and failed checks accurately.

OpenVR pinned commit is `0924064316de3effbcd1acf1e309182a2deb1c05`, v2.15.6, **BSD-3-Clause**. Preserve native `OpenVR-LICENSE.txt` byte-for-byte and `.gitattributes` protection. Do not describe it as MIT. Record upstream authors, exact references, bundled SDK files, lifecycle-only sample ideas, and original VRization rewrites in both languages. SteamVR/vendor-driver terms are separate. No user reference photograph is copied or redistributed.

Next chat's hardware acceptance plan:

- First confirm ordinary v0.4.0 remains available, then use the preview install identity. Repeated USB connect from either side, Stop from either side, disconnect/reconnect and restart should work without replug; verify actual blanking and peer state.
- Phone route: explicitly register only the preview path, verify serial `VRizationPhone`, real compositor eye textures, adapter match and headless/debug-display behavior. Prove different left/right calibration colors are preserved, physical per-eye source aspect/optics fit, no center-eye bleed, gyro yaw/pitch/roll and recenter in both landscape directions. No-sensor and stale data must show unavailable tracking.
- Exercise F8, editor Save/Discard, mode change, disconnect and Stop while moving the phone. Verify pause stays latched until local PC Resume and no OS mouse movement occurs on HMD route.
- Native-headset route: retain the existing driver and connection, verify the head-relative desktop overlay and native game/controllers, then Stop/close/route change; no leftover overlay or process, and no tracking/config modification.
- Measure sustained delivered frames and round-trip independently of end-to-end latency. Inspect CPU JPEG and GPU readback cost before choosing a new encoder; report measurements, not advertised 90 Hz or configured60 FPS as achieved performance.

After any release, preserve old verified assets and save a new independent experimental archive; do not refresh ordinary stable `latest` with an experimental bundle. Update actual release date/version/assets only after successful publication. If blocked hardware is deliberately deferred, finish code/fixtures/docs and describe those precise limits instead of manufacturing results.

---

<!-- vrization:chinese -->
## 简体中文

用下列提示继续独立 SteamVR 实验版。修改前读仓库 `AGENTS.md`、本页、[架构](ARCHITECTURE.md)、[实验教程](../README.md)、[原生教程／来源](../native/README.md)。保留普通 v0.4.0 及所有历史文件／下载。项目自有公共页保持完整英文在前、完整中文在后，软件默认英文并支持两种语言；根 CHANGELOG 双语记录每次用户可见改变。

> 继续 VRization 独立 0.5.0-steamvr-preview，保持三个显式路线：保留四模式的手机直连；完整姿态与独立 SBS 合成器双眼的手机 3DOF SteamVR 头显；已有实体 SteamVR 头显的桌面覆盖层。保留正式应用、实验版独立标识／设置／端口、本地紧急暂停所有权及全部历史文件。按真实覆盖范围完成测试。华为与 PCVR 真机验证已经安排下次聊天，不得宣称已通过，也不因检测到设备就自行激活硬件。

源码已包含真实驱动／姿态、合成器镜像及覆盖层通路；原生二进制本身不能证明手机虚拟显示能无实体显示运行。启动／诊断不得采集、注入鼠标、注册驱动、修改 SteamVR 配置或启动 SteamVR。用户显式注册只添加／移除本包路径，保留 DPVR 和所有既有头显驱动；不得设置 `forceDriver` 或结束别的应用进程来让实验工作。

在正确边界修改：

1. 读 `app.py` 的启动器／路线／本地设置，以及 `runtime.py` 的显式运行环境／驱动动作、自有工具与诊断。
2. 读 `host.py`／`session.py` 的 HostServer 钩子及严格视频／输入配对。必须两种能力和完整已接受快照后才发 SBS；无描述符仍为旧 mono／mouse，不得悄悄将头显方向改成 Windows 鼠标。
3. 读 `pose.py` 的代际、递增序号、合法数据、居中和暂停。F8／编辑器／停止锁定在重连／保存／切模式／居中后保留，只有电脑恢复解除；缺失／旧／无效传感器不能伪造有效恒等姿态。
4. 同时读 Python 和原生 IPC，保持准确 128 字节 `VRP1` 姿态、64 字节 `VRF1` 帧头、只读读端、单写入者、seqlock 屏障、有边界尺寸和 Windows 开机时间。仅手机头显拥有固定姿态映射，每个帧会话新建独立映射，关闭前令旧数据失效。
5. 改 C++ 前读驱动／Mirror／Overlay 生命周期：匹配 OpenVR 显卡，通过 OpenVR 释放 SRV，在纹理／上下文释放前隐藏／清空／销毁覆盖层，检查自有 Stop 事件，后备结束操作仅限自己的子进程。
6. 读 Android `StreamSession`、`OrientationMath`、`StereoProjection` 和 iOS `StreamSession`、`HMDQuaternion`、`StereoSampling`，保留完整四元数／横屏／居中约定、分眼源比例／UV 边界、一次手机镜片处理、持久模式恢复与独立设置。纯数学 golden 不证明实体手机坐标正确。
7. 换采集、编码器、传输或姿态输出时参照[模块表](ARCHITECTURE.md#module-boundaries-and-replacement-points)，保持直连及其加强模式能力回退，不在无关平台界面复制逻辑。

独立标识：Windows `%LOCALAPPDATA%/VRizationSteamVR/Windows` 及各路线子设置；电脑服务8766；Android `org.vrization.steamvr`、`vrization_steamvr`、控制18774／视频18775；iOS `org.vrization.ios.steamvr`、`steamvrPhonePreferencesV1`、视频18776／控制18777。配对／接受状态、暂停锁定和输入启用不得成为持久显示设置字段。iOS 模拟器／源码不是可安装签名 iPhone 应用。

构建／测试命令：

```powershell
python scripts/build_steamvr_native.py --configuration Release --test
python -m unittest discover -s scripts -p test_build_steamvr_native.py -v
python -m unittest discover -s experimental/steamvr/tests -v
python scripts/check_docs.py
# 在 android/ 运行：
.\gradlew.bat :steamvr-app:testSteamvrDebugUnitTest :steamvr-app:assembleSteamvrDebug :steamvr-app:lintSteamvrDebug
```

原生构建采用五个准确 SDK 锁定、完整上游许可字节、x64 MSVC `/MD`、软件 WARP 像素及不调用运行环境 `Init` 的工厂 ABI。不得重试审批拒绝的安装，也不得把运行环境初始化失败冒充 ABI 通过；本地无 MSVC／SDK 时使用配置好的 Windows CI。独立 iOS 工作流为 `VRizationSteamVR.xcodeproj` 构建双 SDK，并以原创校准图做模拟器／原生 Metal 测试。Android 仪器测试必须在真实／模拟 Android 运行后才记录执行，编译不等于运行。准确记录最终源码 commit、构建哈希、测试数量、实际 runner／设备／运行环境与失败检查。

OpenVR v2.15.6 锁定 `0924064316de3effbcd1acf1e309182a2deb1c05`，为 **BSD-3-Clause**，保持 `OpenVR-LICENSE.txt` 字节及 `.gitattributes` 保护，不能称作 MIT。双语记录上游作者、准确引用、打包 SDK 文件、仅生命周期参考的示例思路及 VRization 原创重写。SteamVR／厂商驱动条款独立，不复制或再分发用户参考照片。

下次聊天的真机验收：

- 先确认普通 v0.4.0 仍可使用，再安装独立实验版；测试两端发起 USB 连接、两端停止、断开／重连和重启均不需拔线，核实真正清屏与对端状态。
- 手机路线显式注册本实验路径，验证 `VRizationPhone` 序列号、真实合成器双眼纹理、显卡匹配和无实体显示／debug-display 行为；独立左右校准色不串眼、实体每眼比例／镜片可适配、中缝不漏眼；横屏两个方向验证 yaw／pitch／roll 和居中。缺传感器／旧数据必须显示不可用。
- 移动手机时测试 F8、编辑保存／弃用、切模式、断开、停止：电脑本地恢复前仍锁定，头显路线不发生系统鼠标移动。
- 实体头显路线保留原驱动和连接，验证随头桌面覆盖层与原生游戏／控制器，再停止／关闭／切路线，无残留覆盖层或进程，不改追踪／配置。
- 分别测持续送达帧率、往返和端到端延迟；选择新编码器前检查 CPU JPEG 与 GPU 读回成本，不把声明 90 Hz 或配置60 FPS 当作实测。

发布后保留已验证旧产物，并另存独立实验版归档，不用实验包更新正式 `latest`。成功发布后才写实际日期／版本／产物；硬件已明确延期时完成代码／自动检查／文档，准确报告边界而不伪造结果。

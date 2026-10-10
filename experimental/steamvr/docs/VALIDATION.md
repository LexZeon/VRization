# 🔬 Preview verification / 测试版验证

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

This page records software/build evidence for **0.5.0-steamvr-preview**. Huawei phone and PCVR acceptance is deferred at the user's request. A configured 60 FPS target, a Simulator screenshot or a successful native build does not establish achieved hardware FPS, cable reliability or physical motion-to-photon latency.

| Check | Actual evidence and scope |
| --- | --- |
| Windows/Python | **387 cases plus 312 subtests** passed locally, including the previous host tests, real local WebSocket acceptance ordering, session ownership, full quaternion gates, Stop/reconnect and real owned Windows map/event checks. **40 script cases** passed separately. |
| Native Windows | Four Release targets and **365** runtime-independent CTest fixtures passed in [CI 38093072466](https://github.com/LexZeon/VRization/actions/runs/38093072466/job/114333306286), source `550f845f5b551f2c52c36491e3d0c37f313b0ff9`. Independently audited all 11 payload files plus build report, five AMD64 PE assets, ABI exports, five SDK pins and unchanged native sources. An earlier build of the same native code also passed a local software-WARP replay. No runtime or driver was started. |
| Android | **133 original +43 new =176** local unit cases passed; both variants' APK, core AAR, lint and instrumentation compilation completed. The separate preview APK retains the canonical release certificate, application ID `org.vrization.steamvr`, `0.5.0-steamvr-preview` / build 1. Instrumentation and GPU pixels have not run on a physical device. |
| iOS preview | [CI 38092654893](https://github.com/LexZeon/VRization/actions/runs/38092654893) passed **95 original +21 new Swift cases, three helper cases and two native UI cases**, zero failed/skipped UI cases, both unsigned arm64 SDK builds, **7 original PNGs /50 pixel samples /6 connection checkpoints**. Independent source archive and application identity audits passed. iOS code is unchanged at `550f845`. See [iOS details](IOS.md). |
| Original release regression | All four build jobs in [CI 38092149615](https://github.com/LexZeon/VRization/actions/runs/38092149615) passed for this branch's shared source. Ordinary package startup, Android, Swift/both SDKs and the seven native UI cases retain their own direct-phone scope. The published v0.4.0 files are preserved. |
| Final Windows executable | **28** included project modules and its launcher match current source bytecode; **38** bundled native runtime files match their installed origins and the released v0.4.0 baseline; **47** project/runtime notice files match exact source bytes. Optional numpy/dxcam/comtypes, ADB and Windows graphics DLLs are excluded. This is an executable audit, not a live SteamVR test. |
| Complete Windows ZIP | Clean-profile extraction and the actual windowed EXE's diagnostics passed without developer SDK environment. Routes, version, isolated ports, native paths and software-only flags are checked. The ZIP's own atomic IPC DLL preserved original BGRA bytes, rejected a duplicate writer, invalidated closed frames and signaled an owned Stop event. Shared source lookup under the extracted EXE identity rejected a fake CWD/PATH ADB; frozen diagnostics do not expose an `adb_found` claim. This check runs in future preview CI through `scripts/smoke_steamvr_package.py`. |

The two phone-HMD UI fixtures use original synthetic per-eye color grids and invalid tracking when a Simulator has no sensor. Recorded input count is zero. A later [CI 38093072466 iOS attempt](https://github.com/LexZeon/VRization/actions/runs/38093072466/job/114333306236) failed one of two UI cases: a very short native corner drag left the draft unchanged, and the host correctly saved that unchanged value. Its pixel/package steps did not run. The test-only revision `979fd61` waits for the actual editor/handle, uses a slower held native drag and strictly verifies decreased draft scale before keeping the original host Save assertion. No production iOS change or settings shortcut was used. Real Windows preview GUI capture could not be visually confirmed because the automation surface returned black frames and activation failures; it is not recorded as a GUI pass. The ordinary v0.4.0 enhanced-editor check remains separate evidence for that earlier release.

OpenVR's original BSD-3-Clause license is byte-preserved, with v2.15.6 and exact commit/file pins; native code is original MIT with credited reference ideas. No SDK headers/import libraries, private signing keys, ADB binaries or system graphics DLLs are redistributed in the Windows runtime package. Native targets need a current **Microsoft Visual C++ v14 x64 runtime at least as new as their build toolset**; see the [official requirement](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist). The audited CI used MSVC 19.51. [Source credits](../native/licenses/README.md) distinguish SDK distribution, rewritten ideas and separately installed SteamVR/vendor software.

### 📋 Next physical-device session

1. Check ordinary and preview installs coexist; cold launch and repeated USB connect/Stop/Disconnect/reconnect must work without cable replug. Verify both devices agree on the current session and clear live frames on either endpoint's Stop.
2. On Huawei, confirm distinct eye sources, optical fit, source aspect, saved display bounds, mirrored spacing, inward edge contact and Save/Discard synchronization in direct and SteamVR routes.
3. Test real phone yaw, pitch and roll in both landscape orientations, recenter, stale tracking, F8/editor pause and local PC Resume. HMD route must produce zero OS mouse events; direct first-person behavior remains independently testable.
4. Verify SteamVR recognizes only the explicitly registered Phone HMD, initializes without a physical display, and supplies real compositor textures; preserve DPVR/native drivers and test switching back to the physical headset. Test the existing-headset overlay and its resource cleanup using the existing transport/controllers.
5. Record achieved capture/delivery/display FPS, missed frames and software stage timings; measure motion-to-photon separately with physical equipment. FPS and timestamp age alone are not an end-to-end latency measurement. Improve bottlenecks after this measurement.

Use [AI handoff](AI_HANDOFF.md) and [architecture](ARCHITECTURE.md) to continue in another chat; follow the [illustrated tutorial](TUTORIAL.md) for each route. Keep all old packages and app preferences.

---

<!-- vrization:chinese -->
## 简体中文

本页记录 **0.5.0-steamvr-preview** 的软件／构建证据。按用户安排，华为和 PCVR 验收留到下一次。目标 60 FPS、模拟器截图或原生构建成功不能证明真实硬件帧率、线缆可靠性或运动到显示的物理延迟。

| 检查 | 实际证据与范围 |
| --- | --- |
| Windows／Python | 本机 **387 项加 312 个子检查**通过，涵盖旧电脑端、真实本地 WebSocket 接受顺序、会话所有权、完整四元数门控、停止／重连和真正的自有 Windows 映射／事件；另有 **40 项脚本测试**通过。 |
| Windows 原生 | 四个 Release 目标和 **365** 项无需运行环境的 CTest 在 [CI 38093072466](https://github.com/LexZeon/VRization/actions/runs/38093072466/job/114333306286) 通过，源码 `550f845f5b551f2c52c36491e3d0c37f313b0ff9`；独立核对 11 个有效载荷文件及构建报告、5 个 AMD64 PE、ABI、5 个 SDK 固定哈希及相同原生源码。相同原生代码的较早构建也通过本机软件 WARP 复跑；未启动运行环境或驱动。 |
| Android | 本机 **133 项原有 +43 项新增 =176** 单元测试通过；两个版本 APK、核心 AAR、lint、仪器测试编译完成。独立实验 APK 使用既有发布证书、`org.vrization.steamvr` 和 `0.5.0-steamvr-preview`／build 1。尚未在实体设备执行仪器测试或 GPU 像素测试。 |
| iOS 实验版 | [CI 38092654893](https://github.com/LexZeon/VRization/actions/runs/38092654893) 通过 **95 项原有 +21 项新增 Swift、3 项辅助脚本和 2 项原生 UI**，UI 零失败／跳过；两个 SDK 未签名 arm64 构建、**7 张原始 PNG／50 个像素采样／6 个连接检查点**通过。独立源码包和应用标识核对通过，`550f845` 的 iOS 代码不变；见 [iOS 详情](IOS.md)。 |
| 原版回归 | [CI 38092149615](https://github.com/LexZeon/VRization/actions/runs/38092149615) 的四个构建任务均通过，检查本分支共享源码中的普通压缩包启动、Android、Swift／双 SDK 和 7 项原生 UI，各自保留手机直连的验证范围；已发布 v0.4.0 文件保留。 |
| 最终 Windows EXE | 内嵌 **28** 个项目模块及启动入口字节码与当前源码一致；**38** 个原生运行库与安装来源及 v0.4.0 发布基准一致；**47** 份项目／运行库许可原文一致。排除可选 numpy／dxcam／comtypes、ADB、Windows 图形 DLL；这属于 EXE 核对，不是真实 SteamVR 测试。 |
| 完整 Windows ZIP | 全新设置目录解压、实际无控制台 EXE 诊断通过，不使用开发 SDK 环境；检查路线、版本、独立端口、原生路径和纯软件标记。包内自身原子 IPC DLL 保留原创 BGRA 字节、拒绝重复写入者、关闭时令旧帧无效，并触发自有 Stop 事件。以已解压 EXE 标识调用共享源码查找，排除假 CWD／PATH ADB；冻结版诊断没有声称 `adb_found` 结果。未来实验 CI 运行 `scripts/smoke_steamvr_package.py` 完成此检查。 |

两个手机头显 UI 测试使用原创合成分眼色块；模拟器无传感器时记录无效追踪，鼠标输入计数为零。较后的 [CI 38093072466 iOS 尝试](https://github.com/LexZeon/VRization/actions/runs/38093072466/job/114333306236) 两项 UI 中一项失败：过短的原生顶点拖动没有改变草稿，电脑正确保存原值，像素／打包步骤未执行。纯测试修订 `979fd61` 等待真实编辑器／顶点就绪，放慢并保持原生拖动，在保留原电脑保存断言前严格验证草稿缩小；没有修改 iOS 生产代码或用设置捷径。Windows 实验版 GUI 自动化返回黑色画面和激活失败，尚不能确认其实际可视界面，因此没有记录 GUI 通过；原 v0.4.0 加强编辑器检查仍只证明较早版本。

OpenVR 的 BSD-3-Clause 原许可逐字保留，固定 v2.15.6、commit 和文件哈希；原生代码为 MIT 原创，记录参考思路。Windows 运行包不再分发 SDK 头文件／导入库、签名私钥、ADB 或系统图形 DLL。原生目标需要**至少与构建工具版本一样新的 Microsoft Visual C++ v14 x64 运行库**，见[官方要求](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)；核验 CI 使用 MSVC 19.51。[来源记录](../native/licenses/README.md)区分 SDK 分发、重写思路、另装 SteamVR／厂商软件。

### 📋 下次实体设备测试

1. 验证原版与实验版安装共存；冷启动和 USB 多次连接／停止／断开／重连不拔线，两端认可同一当前会话，任一端停止都清掉实时帧。
2. 华为测试分眼源、盒子光学适配、源比例、已保存显示范围、镜像间距、向内边缘接触、保存／弃用同步；覆盖直连和 SteamVR 路线。
3. 两个横屏方向测试真实 yaw／pitch／roll、居中、追踪过期、F8／编辑器暂停和电脑恢复。头显路线系统鼠标事件必须为零；直连第一人称另外测试。
4. 确认 SteamVR 只识别显式注册的手机头显，无实体显示可初始化并提供真实合成器纹理；保留 DPVR／原生驱动并测试切回实体头显。用既有连接方式／控制器测试已有头显覆盖层及资源清理。
5. 记录真实采集／传输／显示帧率、漏帧和软件各阶段耗时；用实体设备另测运动到显示延迟。仅凭 FPS 或时间戳年龄不能等同端到端延迟，再按测量结果优化瓶颈。

新聊天用 [AI 接手](AI_HANDOFF.md)和[架构](ARCHITECTURE.md)继续，各路线操作见[图文教程](TUTORIAL.md)，保留旧包与应用设置。

# SteamVR native bridge / SteamVR 原生桥接

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

This directory implements the native part of the separate SteamVR experiment. It preserves the ordinary VRization app and its four direct-phone display modes. Native source implementation is available; compilation, fixture results and hardware acceptance are separate claims. A later authorized Huawei session observed Phone HMD activation, undistorted Mirror eyes and real sensor/background delivery; [validation](../docs/VALIDATION.md) records the precise versions and limits. Complete axes, real VR games, physical iPhone/PCVR and stable lifecycle/latency acceptance remain pending. A packaged DLL or passing WARP test does not establish that SteamVR can render to this phone HMD without a physical display.

The previously published four native targets compiled with x64 MSVC 19.51.36260.0 on source `045ae23745f47b41ce3542a69f1f4edc17f31fd1`. The native build/CTest step in [CI run 38092149008](https://github.com/LexZeon/VRization/actions/runs/38092149008/job/114330601507) passed **365 fixture checks**, and the same CI binaries passed an independent local software-WARP replay. This establishes the native fixture scope only; whole-package and phone/runtime hardware checks are separate.

The later `fc607e6` candidate in [CI run 38108240331](https://github.com/LexZeon/VRization/actions/runs/38108240331) also compiled and passed **365 native checks plus 48 owned-timer cadence checks = 413 fixtures**. Its extracted Windows ZIP passed isolated diagnostics without GUI, runtime, capture or input. The timer is therefore compiled/fixture-tested in that candidate; fresh physical publication FPS and the later live-refresh source/package remain unverified.

The newer `ad092b0` code freeze in [CI 38109367242](https://github.com/LexZeon/VRization/actions/runs/38109367242) also passed the same **413 fixtures**, including the owned high-resolution timer, and the extracted Windows ZIP/owned-IPC diagnostic gate. Independent verification checked all staged and ZIP native hashes, SDK pins and report/CTest identity. That iOS attempt later failed its fixture event-count assertion; the corrected earlier `cc83978` iOS baseline passed. Current physical recovery/performance acceptance remains limited; see validation.

The experiment has three host entries: original direct phone streaming; phone as a SteamVR HMD with phone orientation; and desktop viewing on an already connected SteamVR headset. The direct-phone entry uses the original stream path. These native targets implement the other two entries:

| Target | Data path | Ownership |
| --- | --- | --- |
| `driver_vrization_phone.dll` | Validated phone XYZW quaternion → shared pose → `TrackedDevicePoseUpdated` | SteamVR loads the provider only after explicit driver registration; the provider discovers the host map from `RunFrame` and adds serial `VRizationPhone` once |
| `VRization-SteamVR-Mirror.exe` | Two undistorted compositor eye SRVs → D3D11 per-eye resize → SBS BGRA → shared frame → host encoder → phone | Mirror owns the unique frame map and OpenVR SRVs; the host reads |
| `VRization-SteamVR-Overlay.exe` | Host desktop BGRA → shared frame → D3D11 texture → `SetOverlayTexture` | Host owns the unique frame map; overlay reads and owns only its overlay handle |
| `VRization-SteamVR-IPC.dll` | Explicit x64 `VRizationSequenceIncrement` / `VRizationMemoryBarrier` exports for Python ctypes | Original Windows-intrinsic bridge; no OpenVR dependency or runtime activation |

The mirror verifies active HMD serial `VRizationPhone`. It refuses to silently stream another headset. Its explicit `--allow-native-headset` option is reserved for deliberate alternate integrations; the phone host route does not use it. The overlay requires an existing native HMD and refuses the phone serial. Neither native program moves the Windows mouse. The overlay leaves the existing headset's tracking and driver in control.

The latest `cc83978` freeze in [CI 38110018576](https://github.com/LexZeon/VRization/actions/runs/38110018576) passed 413 native fixtures and the complete 171-file Windows ZIP gate. Independent verification matched SDK pins, native/ZIP/report/CTest hashes and owned IPC checks with zero runtime/GUI/device actions. A separate bounded Huawei passive sample observed 900 publications /14.9987184 seconds =60.005127 publication FPS with invalid/paused pose flags 5; [validation](../docs/VALIDATION.md) records delivery/GLES/lifecycle scope. Normal-gyro Refresh, display latency and sustained hardware acceptance remain pending.

**Startup-header race fixed in source; complete physical recovery is still under review.** New mapping creation can expose an exact 64-byte zero header before the writer publishes its first legal inactive header. `FrameReader` waits only for that initial all-zero state. After any legal header, a zero header still fails; nonzero malformed data remains rejected, and close resets initialization. This neither fabricates frames/tracking nor clears pause. The focused runtime regression passed **13 software tests**, including a real Windows mapping read before first publication and two new tests with six subcases. The subsequent complete suite for that startup-header revision passed **460 desktop/preview tests plus 368 subtests** (51.81s) and **46 script tests plus 67 subtests** (7.67s): **506 actual tests plus 435 subtests**, zero failures/errors/skips; all 114 audited source hashes stayed unchanged during testing. Before the guard, phone Refresh produced `Invalid frame header` and paused tracking after repeated PC Refresh retained 31 valid samples. The new candidate then retained advancing phone sequence and valid flags 3 across **three phone Refreshes (31+21+21 samples) and one PC double-click Refresh (21 samples), totaling 94 samples**. A replaced helper/map confirmed an actual rebuild, the PC footer showed no new invalid-header error and the phone still displayed the SteamVR scene. These are bounded observations, not a complete subjective gray-screen, physical-axis, cold-start or reboot pass. The user subsequently reported gray output again after Refresh/editing. The earlier `cc83978` compiled CI baseline predates this guard, and the 506-test guard revision predates the later explicit Refresh-recovery contract; new full regression/CI/package and complete physical recovery remain pending.

### Build and staged files

Use a Windows x64 MSVC runner with CMake ≥3.21 and the Windows SDK. The build never installs a compiler, registers a driver, starts SteamVR or changes existing headset configuration.

```powershell
python scripts/build_steamvr_native.py --configuration Release --test
# Dependency verification only, also available without a compiler:
python scripts/build_steamvr_native.py --fetch-only
```

The script fetches only five SHA256-pinned OpenVR SDK files from Valve at commit `0924064316de3effbcd1acf1e309182a2deb1c05` (v2.15.6), verifies the verbatim license, runs CMake/CTest, and stages `artifacts/steamvr/native-bundle`. It preserves and rejects an existing mismatched SDK cache file. `native-build-report.json` records binary hashes and whether fixture tests actually ran. No production release is replaced.

```text
native/
  VRization-SteamVR-Mirror.exe
  VRization-SteamVR-Overlay.exe
  VRization-SteamVR-IPC.dll
  openvr_api.dll
  README.md
  licenses/{README.md,OpenVR-LICENSE.txt,VRization-MIT.txt}
drivers/vrization_phone/
  driver.vrdrivermanifest
  bin/win64/driver_vrization_phone.dll
  resources/settings/default.vrsettings
```

The native targets use `/MD`; the target PC needs the **Microsoft Visual C++ v14 x64 Redistributable at least as new as the build toolset**, including the Visual Studio 2026 toolset used here. Use Microsoft's [current supported runtime guidance](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist); an old 2015–2022 package alone is not a sufficient version check. Windows D3D11, DXGI and D3DCompiler remain system components and are not bundled. OpenVR's redistributable SDK DLL is bundled with its BSD-3-Clause license; SteamVR itself must be installed separately under its own terms. See [native provenance and licenses](licenses/README.md).

### Runtime and Stop boundaries

Host-owned processes accept `--frame-map Local\<unique-name>` and optional `--stop-event Local\<unique-name>`. The mirror also accepts `--width 640 --fps 60`. Both helpers wait up to 60 seconds for the selected runtime/HMD and report `waiting`; timeout or incompatible HMD exits with an explicit error. A runtime can start before the phone session: the driver repeats map discovery from `RunFrame`. Manual registration may still require a SteamVR restart; one observed Phone HMD activation does not establish reliable cold-start/restart behavior.

The mirror creates its D3D11 device on the adapter returned by OpenVR `GetDXGIOutputInfo`. It acquires both eye SRVs once per session, downsamples on the GPU before CPU readback, and releases them with `ReleaseMirrorTextureD3D11` while the OpenVR context is alive. Readback is tight BGRA at the resized resolution, never a full-resolution intermediate. Each source eye's aspect determines output height; the total SBS width is even and dimensions are bounded by 1920×1080. The source is compositor stereo, not a duplicated desktop frame. Typed sRGB views are reencoded once when producing encoded BGRA bytes.

The phone driver advertises 1024×1024 per eye, 2048×1024 virtual output bounds, 90° symmetric projection, 0.064 m IPD and nominal 90 Hz. This advertised display frequency is not measured stream FPS. Identity driver distortion leaves phone lens processing to the phone renderer once. Phone tracking is orientation-only: the host supplies a fixed 1.6 m position and no physical translation, controllers, prediction or fabricated angular velocity. Missing sensors, invalid quaternions, pause or data older than 500 ms produce invalid tracking, never a synthesized valid identity pose.

The existing-headset overlay is 3 m wide and 2 m ahead of the HMD, using a tracked-device-relative transform. Inactive, missing or stale frame data hides and clears its texture; a fresh frame can show it again. It owns a unique overlay key and destroys only that overlay. Its head-relative screen intentionally follows head motion.

The host signals the unique manual-reset Stop event; each loop polls it without blocking. Normal mirror shutdown marks its frame inactive; overlay shutdown hides, clears and destroys its overlay before texture/context teardown. Console Ctrl+C also requests cleanup. A killed/crashed writer cannot refresh the 500 ms timestamp; readers fail closed. Native GPU/runtime calls can stall independently of polling, so the host retains a bounded owned-process termination fallback. The native helper never kills SteamVR or another application's process.

### Shared-memory contract for integrations

All maps are `Local\` with Windows' normal user security descriptor. A second writer refuses an already existing map. Readers open read-only. Seqlock at byte 12 is odd while writing, even when complete; Windows Interlocked operations and memory barriers publish complete snapshots. Readers retry at most four times and validate bounds before payload access. Tick timestamps use Windows `GetTickCount64`, not wall clock or Python `perf_counter`.

The Python writer/reader uses the original `VRization-SteamVR-IPC.dll` to expose Windows compiler intrinsics. `InterlockedIncrement` is not assumed to be a callable `kernel32` export. CTest loads this real DLL and checks odd/even mapped publication and its explicit ABI without starting a VR runtime.

| Map / field | Layout |
| --- | --- |
| `Local\VRizationPhonePoseV1` | 128 bytes; little-endian `<4sIIIQQ4d3dI36s` |
| Pose header | magic `VRP1`, version 1, header size 128, seqlock at 12 |
| Pose body | uptime ms at 16; negotiated pose sequence at 24 (zero allowed); XYZW doubles at 32; XYZ metres at 64 |
| Pose flags | uint32 at 88: active 1, tracking valid 2, paused 4; 36 reserved zero bytes |
| Unique frame map | capacity 64 + 1920×1080×4 bytes; little-endian `<4sIIIIIIIQ24s` |
| Frame header | magic `VRF1`, version 1, header size 64, seqlock at 12 |
| Frame body | width 16, height 20, stride 24, active flag 28; uptime ms 32; 24 reserved zero bytes |
| Frame pixels | tight BGRA8 begins at 64; stride = width×4; SBS mirror width even, overlay mono may have odd width |

Pose coordinates use OpenVR world axes: +X right, +Y up, −Z forward. Phone-to-world coordinate conversion and session-generation checks belong to the host/client contract, not a second conversion in the driver. The driver's ABI reorders XYZW into WXYZ and normalizes only a finite quaternion already close to unit length. Frames use unique per-session map names; Stop invalidates old maps before their writer closes. These boundaries keep stale sessions from becoming a new stream.

### Fixture scope and module handoff

`native_tests.cpp` exercises real Windows readonly mappings, exact layout and payload, writer conflicts, odd seqlocks, inactive/old generation clearing, mono odd-width frames, stale/future ticks, malformed quaternion/position/flags, XYZW→WXYZ conversion, and sequence zero. A real named Windows event checks nonblocking host Stop, latching and handle cleanup. WARP D3D11 renders independent red/blue eyes plus a gradient, checking all borders and the center seam, channel order, orientation, downsample samples and sRGB behavior. `LoadLibrary` checks the exported factory and pinned provider/display ABI without calling `Init` on a fake runtime context. CTest success must be recorded only after CI executes it. Six offline Python SDK tests have passed locally: exact license/pins, unchanged verified cache, preservation/rejection of corrupt cache, verified atomic download, wrong download rejection and oversized download rejection.

For another developer or AI: `ipc.hpp` defines bounded ownership/snapshots; `pose.hpp` validates and converts tracking; `phone_driver.cpp` implements provider/display lifecycle; `gpu.hpp` owns GPU eye packing; `stop.hpp` observes the owned event; `timing.hpp` owns QPC cadence and Stop-cancellable high-resolution one-shot waits, with the prior candidate's build/timer fixtures passed and fresh physical performance still pending; `runtime.hpp` parses arguments and owns OpenVR lifetime; `mirror.cpp` bridges compositor frames; `overlay.cpp` displays host frames; `native_tests.cpp` is runtime-independent evidence; `CMakeLists.txt` stages redistributable targets. Keep the pose map exclusive to the phone-HMD route, native overlay isolated from OS input, and direct-phone streaming independent. Preserve upstream notices, pin updates deliberately, and distinguish build/fixture evidence from real SteamVR, physical USB, gyro axes, latency and FPS measurements.

**Explicit Phone HMD Refresh now also requests tracking recovery.** This user-authorized exception applies only to the accepted, enabled SteamVR Phone HMD route. Only after worker-owned old-video cleanup completes may the host recover a pause that existed when Refresh was requested; that receipt does not guarantee the new Mirror has already published its first frame. Already-active tracking keeps its baseline; recovery of a paused stream follows existing Resume rules and needs fresh valid sensor data, never replayed motion. A captured pause generation makes newer F8/editor pauses or disabling tracking take precedence; Stop, closing the window or replacing the owner/epoch cancels recovery. Stop atomically revokes the active/accepted HMD session and latches pause under the same HMD lock used by refresh recovery, so an in-flight completion cannot restore that stopped session. Repeated PC clicks and an overlapping phone request share one reset/ACK. A user-requested full-reconnect fallback carries one transient intent only into its new accepted capable HMD session; an eight-second fallback may carry it once, not loop indefinitely. Ordinary Connect, automatic reconnect and Save/Discard do not arm that intent. Direct-phone mouse control is unchanged. Earlier ACK paused fields remain status, not standalone recovery authority. The earlier focused regression passed **43 software tests plus 32 subcases**; complete regression after the atomic Stop refinement, build-3 phone/iOS CI, final packaging and physical recovery acceptance are pending. The latest user check still reported gray output after Refresh/editing; no successful gray-screen or reboot fix is claimed.

---

<!-- vrization:chinese -->
## 简体中文

本目录实现独立 SteamVR 实验版的原生部分，保留普通 VRization 及其四种直连手机显示模式。已经编写原生源码，但编译结果、自动化测试和硬件验收是分别需要证据的事项。后来获授权的华为会话已观察手机头显激活、Mirror 未畸变双眼及真实传感器／背景交付，[验证](../docs/VALIDATION.md)注明准确版本和边界；完整坐标、真实 VR 游戏、实体 iPhone／PCVR、稳定生命周期和延迟验收仍待完成；打包出 DLL 或通过 WARP 测试，不代表 SteamVR 已能在没有实体显示器时为手机头显渲染。

之前已发布的四个原生目标已用 x64 MSVC 19.51.36260.0 编译，源码为 `045ae23745f47b41ce3542a69f1f4edc17f31fd1`；[CI run 38092149008](https://github.com/LexZeon/VRization/actions/runs/38092149008/job/114330601507) 的原生构建／CTest 步骤通过 **365 项测试**，相同 CI 二进制的本地独立软件 WARP 复跑也通过。这只证明原生自动检查范围，完整包与手机／运行环境真机检查另行验收。

后来 `fc607e6` 候选版的 [CI run 38108240331](https://github.com/LexZeon/VRization/actions/runs/38108240331) 也完成编译并通过 **365 个原生检查加 48 个自有定时器节奏检查，合计 413 个夹具检查**。解压 Windows ZIP 通过独立诊断，没有启动界面、运行环境、采集或输入；因此该候选版定时器已实际编译／测试，但新真机发布 FPS 和后来活动刷新源码／打包仍未验收。

更新冻结源码 `ad092b0` 的 [CI 38109367242](https://github.com/LexZeon/VRization/actions/runs/38109367242) 同样通过 **413 个夹具检查**，含自有高分辨率定时器，以及解压 Windows ZIP／自有 IPC 诊断门控；独立核对暂存及 ZIP 内全部原生哈希、SDK 固定值和报告／CTest 身份。该轮iOS后来因测试服务事件计数断言失败，修正后的早先 `cc83978` iOS基线已通过；当前真机恢复／性能验收仍有边界，见验证。

实验版电脑端有三个入口：原版手机直连串流、手机作为 SteamVR 头显并提供方向、已连接 SteamVR 头显观看桌面。直连入口沿用原有串流；以下原生组件实现另外两个入口：

| 组件 | 数据通路 | 所有权 |
| --- | --- | --- |
| `driver_vrization_phone.dll` | 已校验的手机 XYZW 四元数 → 共享姿态 → `TrackedDevicePoseUpdated` | 显式注册驱动后 SteamVR 加载提供器；提供器从 `RunFrame` 发现电脑端映射，只添加一次序列号 `VRizationPhone` |
| `VRization-SteamVR-Mirror.exe` | 两只眼未畸变合成纹理 → D3D11 分眼缩小 → SBS BGRA → 共享帧 → 电脑编码 → 手机 | Mirror 拥有独立帧映射及 OpenVR SRV；电脑端只读 |
| `VRization-SteamVR-Overlay.exe` | 电脑桌面 BGRA → 共享帧 → D3D11 纹理 → `SetOverlayTexture` | 电脑端拥有独立帧映射；Overlay 只读并只拥有自己的覆盖层句柄 |
| `VRization-SteamVR-IPC.dll` | 为 Python ctypes 显式导出 x64 `VRizationSequenceIncrement`／`VRizationMemoryBarrier` | 原创 Windows intrinsic 桥接，无 OpenVR 依赖，不激活运行环境 |

Mirror 检查当前头显序列号必须为 `VRizationPhone`，不会悄悄串流另一台头显。显式 `--allow-native-headset` 参数保留给有意选择的其他集成，手机路线不用它。Overlay 要求已有实体头显，并拒绝手机序列号。两个原生程序都不移动 Windows 鼠标；Overlay 保留原头显的追踪与驱动。

最新 `cc83978` 的 [CI 38110018576](https://github.com/LexZeon/VRization/actions/runs/38110018576) 通过413原生夹具及完整171文件Windows ZIP门控；独立核对SDK固定值、原生／ZIP／报告／CTest哈希与自有IPC检查，运行环境／界面／设备动作均为零。另一个有限华为被动样本在无效／暂停姿态标志5时，14.9987184秒观察900次发布＝60.005127发布FPS，交付／GLES／生命周期范围见[验证](../docs/VALIDATION.md)；正常陀螺仪刷新、显示延迟及持续硬件验收仍待。

**源码已修复启动头竞态，完整真机恢复仍在验收。** 新映射创建后、写入者首次发布合法停用头之前，可能读到准确64字节全零头；`FrameReader` 仅对首次合法头之前这一全零状态等待。见过任何合法头之后，全零头仍报错；非零损坏数据仍严格拒绝，关闭读端才重置初始化。不伪造帧／追踪，也不解除暂停。针对性运行回归通过 **13 项软件测试**，包含首次发布前读取真实 Windows 映射，以及两项新增测试的六个子检查；该启动头修订随后完整套件通过 **460 项桌面／实验版加 368 个子检查**（51.81秒）及 **46 项脚本加 67 个子检查**（7.67秒），合计 **506 个实际测试加 435 个子检查**，零失败／错误／跳过，测试期间114份受审源码哈希不变。保护加入之前，电脑重复刷新保持31个有效样本后，手机刷新触发 `Invalid frame header` 并暂停；新候选版随后 **三次手机刷新（31＋21＋21个样本）及一次电脑双击刷新（21个样本），合计94个样本** 均保持标志3有效、手机序号持续增长。观察到工具／映射替换证明确实重建，电脑页脚没有新头信息错误，手机仍显示 SteamVR 场景。这是有限观察，不代表完整主观灰屏、物理坐标、冷启动或重启通过；用户随后报告刷新／编辑后仍灰屏；早先 `cc83978` 编译CI基线早于保护，506测试的保护修订也早于后来的显式刷新恢复契约，新完整回归／CI／打包及完整真机恢复仍待。

### 构建及暂存目录

使用带 CMake ≥3.21、Windows SDK 的 Windows x64 MSVC runner。构建不会安装编译器、注册驱动、启动 SteamVR 或更改已有头显配置。

```powershell
python scripts/build_steamvr_native.py --configuration Release --test
# 只验证依赖，没有编译器也可运行：
python scripts/build_steamvr_native.py --fetch-only
```

脚本只下载 Valve OpenVR v2.15.6、commit `0924064316de3effbcd1acf1e309182a2deb1c05` 中五个锁定 SHA256 的文件，验证完整许可证，执行 CMake/CTest，再暂存到 `artifacts/steamvr/native-bundle`。已有缓存的哈希不匹配时会保留文件并拒绝继续。`native-build-report.json` 记录二进制哈希及是否实际运行测试；不会替换正式发布。

```text
native/
  VRization-SteamVR-Mirror.exe
  VRization-SteamVR-Overlay.exe
  VRization-SteamVR-IPC.dll
  openvr_api.dll
  README.md
  licenses/{README.md,OpenVR-LICENSE.txt,VRization-MIT.txt}
drivers/vrization_phone/
  driver.vrdrivermanifest
  bin/win64/driver_vrization_phone.dll
  resources/settings/default.vrsettings
```

原生目标采用 `/MD`，目标电脑需要 **不旧于构建工具链的 Microsoft Visual C++ v14 x64 Redistributable**，包括本次 Visual Studio 2026 工具链。按 Microsoft 的[当前支持运行库说明](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)检查；仅有旧 2015–2022 安装包不足以证明版本满足。D3D11、DXGI、D3DCompiler 属于 Windows 系统组件，不随包复制。可再分发的 OpenVR SDK DLL 携带 BSD-3-Clause 许可证；SteamVR 本身需另外安装并遵守自己的条款。参见[原生来源与许可证](licenses/README.md)。

### 运行与停止边界

电脑端拥有的子进程接收 `--frame-map Local\<独立名称>`，可选 `--stop-event Local\<独立名称>`；Mirror 另接收 `--width 640 --fps 60`。两种工具最多等待选定运行环境／头显 60 秒并输出 `waiting`；超时或头显不匹配时明确报错退出。运行环境可先于手机会话启动：驱动从 `RunFrame` 重复发现映射。手动注册仍可能需要重启 SteamVR；一次已观察手机头显激活不证明可靠冷启动／重启行为。

Mirror 使用 OpenVR `GetDXGIOutputInfo` 指定的显卡创建设备，每次会话只获取一次两只眼的 SRV，先在 GPU 缩小，再读回 CPU，并在 OpenVR 上下文存活时调用 `ReleaseMirrorTextureD3D11` 释放。读回的是已缩小分辨率的紧密 BGRA，没有完整分辨率中间读回；输出高度由每只眼的源比例决定，SBS 总宽为偶数，最大 1920×1080。输入是合成器的真实双眼纹理，不是复制两份桌面帧。对于带类型的 sRGB 视图，输出编码 BGRA 时只重新编码一次。

手机驱动声明每眼 1024×1024、虚拟输出 2048×1024、对称 90° 投影、0.064 米瞳距和标称 90 Hz。声明刷新率不是实测串流帧率。驱动采用恒等畸变，由手机渲染器只做一次镜片处理。手机仅追踪方向，电脑端提供固定 1.6 米高度，不提供真实平移、控制器、预测或捏造角速度。缺传感器、四元数无效、暂停或超过 500 毫秒的旧数据均产生无效追踪，不会伪造有效的恒等姿态。

已有头显覆盖层宽 3 米，位于头显前方 2 米，以头显相对变换定位。帧未启用、缺失或过期时隐藏并清空纹理；新鲜帧可重新显示。工具使用独立覆盖层标识，只销毁自己的覆盖层；这个跟随头部的屏幕会随头部移动。

电脑端发出独立手动重置 Stop 事件，各循环非阻塞检查。Mirror 正常退出会标记帧无效；Overlay 会在纹理／上下文销毁前隐藏、清空、销毁自身覆盖层。Ctrl+C 同样请求清理。崩溃或被终止的写入者不能更新时间戳，读端在 500 毫秒后拒绝旧数据。GPU／运行库调用可能独立于轮询发生停滞，因此电脑端保留限时结束自己子进程的后备操作；原生工具不会结束 SteamVR 或其他应用进程。

### 共享内存集成约定

映射均处于 `Local\`，采用 Windows 普通用户安全描述符；第二个写入者遇到同名现存映射会拒绝接管。读端只读打开。第 12 字节的 seqlock 在写入中为奇数、完成后为偶数，Windows Interlocked 与内存屏障发布完整快照；读端最多重试四次，先校验边界再读取载荷。时间戳使用 Windows `GetTickCount64`，不使用墙上时间或 Python `perf_counter`。

Python 写／读端通过原创 `VRization-SteamVR-IPC.dll` 暴露 Windows 编译器 intrinsic，不假设 `InterlockedIncrement` 是可调用的 `kernel32` 导出。CTest 加载这个真实 DLL，验证映射奇／偶发布及显式 ABI，不启动 VR 运行环境。

| 映射／字段 | 布局 |
| --- | --- |
| `Local\VRizationPhonePoseV1` | 128 字节，小端 `<4sIIIQQ4d3dI36s` |
| 姿态头 | `VRP1`、版本 1、头长 128，seqlock 偏移 12 |
| 姿态内容 | 开机毫秒偏移 16；协议姿态序号偏移 24（允许零）；XYZW 双精度偏移 32；XYZ 米偏移 64 |
| 姿态标记 | uint32 偏移 88：启用 1、追踪有效 2、暂停 4；保留 36 个零字节 |
| 独立帧映射 | 容量 64 + 1920×1080×4 字节，小端 `<4sIIIIIIIQ24s` |
| 帧头 | `VRF1`、版本 1、头长 64，seqlock 偏移 12 |
| 帧内容 | 宽偏移 16、高 20、行距 24、启用标记 28；开机毫秒 32；保留 24 个零字节 |
| 像素 | 紧密 BGRA8 从偏移 64 开始；行距 = 宽×4；Mirror SBS 宽为偶数，Overlay 单画面可为奇数 |

姿态采用 OpenVR 世界坐标：+X 向右、+Y 向上、−Z 向前。手机到世界的坐标转换与会话代际校验属于电脑端／手机协议，驱动不重复转换。驱动只将 XYZW 重排为 ABI 的 WXYZ，并只归一化已经接近单位长度的有限四元数。帧映射每会话采用独立名称；停止后先令旧映射失效，再关闭写入者，防止旧会话被当作新串流。

### 测试范围与模块交接

`native_tests.cpp` 检查真实 Windows 只读映射、准确布局及载荷、写入者冲突、奇数 seqlock、停用／旧代际清空、单画面奇数宽、过期／未来时间戳、异常四元数／位置／标记、XYZW→WXYZ 和零序号。真实 Windows 命名事件检查非阻塞电脑端 Stop、锁定状态及句柄清理。WARP D3D11 渲染分开的红蓝眼和渐变，检查所有边界及中缝、通道顺序、方向、缩小采样与 sRGB 行为。`LoadLibrary` 检查导出的工厂和锁定的提供器／显示 ABI，不在伪运行环境上调用 `Init`。只有 CI 实际运行后才能记录 CTest 通过。六项离线 Python SDK 测试已在本机通过：准确许可／锁定数据、合格缓存不修改、损坏缓存保留并拒绝、校验后原子下载、拒绝错误下载及拒绝超大下载。

交给后续开发者或 AI：`ipc.hpp` 定义有边界的所有权与快照；`pose.hpp` 验证并转换追踪；`phone_driver.cpp` 实现提供器／显示生命周期；`gpu.hpp` 管理 GPU 双眼拼接；`stop.hpp` 观察自有事件；`timing.hpp` 管理 QPC 节奏及 Stop 可取消高分辨率单次等待，先前候选版构建／定时器测试已通过，新真机性能仍待完成；`runtime.hpp` 解析参数并管理 OpenVR 生命周期；`mirror.cpp` 桥接合成器帧；`overlay.cpp` 显示电脑端帧；`native_tests.cpp` 提供不依赖运行环境的证据；`CMakeLists.txt` 暂存可再分发目标。保持姿态映射只属于手机头显路线、原生覆盖层不触发系统输入、直连手机路线独立。保留上游声明，有意更新锁定版本，并区分构建／测试证据和真实 SteamVR、实体 USB、陀螺仪坐标、延迟及帧率测量。

**显式手机头显刷新现在也请求恢复追踪。** 该用户授权的例外只适用于已接受、已启用的 SteamVR 手机头显路线。仅在所属工作线程完成旧视频清理后，电脑才可恢复刷新请求时已有的暂停；该回执不保证新Mirror已经发布第一帧。原本活动的追踪保留基准，暂停流按既有恢复规则等待新的有效传感器数据，绝不重放旧动作。捕获暂停代际令事务期间新按 F8／进入编辑器或禁用追踪优先；停止、关闭窗口或替换所有者／会话代际取消恢复。停止与刷新恢复使用同一头显锁，原子撤销active／accepted会话并锁定暂停，处理中完成不能恢复已停止会话。电脑重复点击及重叠手机请求共用一次重置／确认。用户要求的完整重连回退只携带一次临时意图到其新的已接受且支持能力的头显会话；八秒超时回退最多携带一次，不无限循环。普通连接、自动重连及保存／弃用不设置该意图，手机直连鼠标控制不变；确认中的暂停字段仍只是状态，不能单独授权恢复。早先针对性回归通过 **43 项软件测试加 32 个子检查**；原子停止细化后的完整回归、手机／iOS build3 CI、最终打包和真机恢复仍待验收。最近用户检查仍报告刷新／编辑后灰屏，不声称灰屏或实体重启已经修好。

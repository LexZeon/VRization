# 📝 Version changelog / 版本日志

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

User-visible changes are listed newest first. Dates are GitHub publication dates in **UTC**. Each version links to its detailed release notes, downloads and verification limits. An FPS target or a successful build is not a hardware-performance guarantee.

### Unreleased

Current unpublished source versions are **Windows 0.5.1-steamvr-preview, Android 0.5.1-steamvr-preview/build 3 and iOS 0.5.1/build 3**. Ordinary VRization remains **0.4.0/build 8**; historical 0.5.0 preview downloads stay preserved. The earlier `cc83978` build-2 baseline passed independently verified Windows, Android and iOS CI. The startup-header revision separately passed 506 actual tests plus 435 subtests; the later explicit HMD Refresh-recovery contract has focused tests only so far. New complete regression/CI/final packaging and subjective/reboot acceptance remain pending after the user reported gray output again.

- **Fixed Android USB bootstrap:** Loopback Host validation now uses the explicitly configured reverse-video endpoint for each app: ordinary **18765**, preview **18775**. This corrects the preview APK's USB handshake being rejected with HTTP 403. The reusable host validates the configured ports while retaining authenticated session, Origin and Stop guards; physical acceptance of the corrected preview is recorded separately.
- **Fixed:** The Phone HMD manifest now uses an explicit empty `hmd_presence` list instead of treating its serial as a USB VID.PID pattern. Native build, packaging and ZIP checks reject the invalid serial and always-present wildcards, even when payload hashes match. The existing C++ registration and tracking behavior is unchanged; [pinned Valve references](experimental/steamvr/native/licenses/README.md) record the configuration source.
- **Fixed paused Phone HMD presence:** An accepted, connected session refreshes invalid tracking status while editing, paused, without a sensor or after a stale pose. This prevents a one-time paused header from expiring into a native disconnect/Mirror exit; it never refreshes old valid tracking or clears the PC Resume latch. Stop immediately closes the accepted/active gate. Earlier heartbeat regression passed **416 Windows/Python cases plus 314 subtests**; a physical editor interval over six seconds kept Mirror publishing, Save retained pause, and local Resume plus movement restored viewing. Static Resume and complete physical-axis/stability acceptance remain incomplete; published downloads are unchanged.

- **Explicit Phone HMD Refresh now also requests tracking recovery.** This user-authorized exception applies only to the accepted, enabled SteamVR Phone HMD route. Only after worker-owned old-video cleanup completes may the host recover a pause that existed when Refresh was requested; that receipt does not guarantee the new Mirror has already published its first frame. Already-active tracking keeps its baseline; recovery of a paused stream follows existing Resume rules and needs fresh valid sensor data, never replayed motion. A captured pause generation makes newer F8/editor pauses or disabling tracking take precedence; Stop, closing the window or replacing the owner/epoch cancels recovery. Stop atomically revokes the active/accepted HMD session and latches pause under the same HMD lock used by refresh recovery, so an in-flight completion cannot restore that stopped session. Repeated PC clicks and an overlapping phone request share one reset/ACK. A user-requested full-reconnect fallback carries one transient intent only into its new accepted capable HMD session; an eight-second fallback may carry it once, not loop indefinitely. Ordinary Connect, automatic reconnect and Save/Discard do not arm that intent. Direct-phone mouse control is unchanged. Earlier ACK paused fields remain status, not standalone recovery authority. The earlier focused regression passed **43 software tests plus 32 subcases**; complete regression after the atomic Stop refinement, build-3 phone/iOS CI, final packaging and physical recovery acceptance are pending. The latest user check still reported gray output after Refresh/editing; no successful gray-screen or reboot fix is claimed.
- **Current Android build-3 software scope:** Local Gradle passed **75 ordinary +58 core +71 preview =204 unit tests**, including nine new explicit-recovery intent cases, with zero failures/errors/skips; lint had zero errors/eight existing warnings. Preview APK and instrumentation compiled and verified the canonical signer; ordinary APK was not rebuilt. This does not establish current CI, installation or physical gray-screen/reboot acceptance.
- **Fault under diagnosis:** The user also reported a gray phone view after the former full-reconnect Refresh; the new video-only path awaits physical recovery acceptance. The reported PC black screen is SteamVR's **Headset Window**. An exited Mirror was separately observed while the phone was connected and waiting for video; that does not establish the cause of every black Headset Window.
- **Added Phone HMD quality profiles:** Balanced **1280 total stereo width /Q75 /60 FPS target** is the new-user/Reset default; Sharper **1920/Q80/60** and Low latency **640/Q45/60** remain selectable. Saved capture choices and direct-phone defaults are retained. Width labels distinguish total SBS width from per-eye pixels, custom combinations remain Custom, and Reset preserves tracking pause. Huawei UI receive counts near 58 FPS included repeated frame delivery; the measured 1920×960 native baseline was **481 publications /14.9744952 seconds =32.121283 publication FPS**. Native pacing passed compilation/fixtures and bounded physical publication sampling; sustained active-tracking/display/latency checks remain pending; no achieved unique/display FPS or latency guarantee is claimed.
- **Implemented frame deduplication and native pacing:** Mirror delivery skips the same coherent header publication sequence/tick at unchanged JPEG quality, retains quality-change re-encoding, and preserves new sequences even at the same coarse tick. Pure decoder output and native ABI are unchanged. Original owned QPC deadlines and a high-resolution one-shot waitable timer wait with Stop cancellation, without global timer changes. The earlier complete revision before live-video Refresh passed **445 desktop/preview tests plus 330 subtests** and **45 script tests plus 67 subtests**: **490 tests plus 397 subtests**, zero failures/errors/skips. The prior `fc607e6` candidate compiled and passed **413 native fixtures** (365 IPC/pose/WARP/factory plus 48 timer), and its extracted Windows ZIP passed isolated diagnostics. The corrected earlier iOS baseline passed; new-source CI, final release packaging and sustained active-tracking/display/latency checks remain pending. The earlier native baseline remains unchanged, with no higher achieved unique/display FPS claim.
- **Earlier code-freeze software/build scope:** Code freeze `ad092b0` passed **503 actual Python/script tests +429 subtests**, zero failures/errors/skips. [CI 38109367242](https://github.com/LexZeon/VRization/actions/runs/38109367242) Windows passed **413 native fixtures** and the complete extracted ZIP startup/owned-IPC gate; Android passed **195 unit tests**, both variants/instrumentation compilation and lint with zero errors/nine CI warnings. That iOS attempt later failed its fixture event-count assertion; corrected `cc83978` iOS evidence is recorded below. Final release package and physical live-refresh/reboot acceptance remain incomplete. Earlier counters/failed attempts stay preserved; no achieved higher unique/display FPS or physical recovery pass is inferred.
- **Coalesced repeated PC Refresh:** Repeated taps, including during a phone request, reuse only the pending current owner/epoch and do not fall through to full reconnect/pause. Two real-loopback fixtures retain receipt/close count, ACK, epoch and baseline. The iOS fixture now records video refresh completion; a real subprocess/loopback test checks two consecutive events. Earlier `cc83978` coalesced-refresh regression: **458 desktop/preview +362 subtests**, **46 scripts +67 subtests =504 actual +429 subtests**, zero failures/errors/skips.
- **Verified earlier iOS live-refresh baseline — `cc83978`:** [CI 38110018576, job 114383462034](https://github.com/LexZeon/VRization/actions/runs/38110018576/job/114383462034), exact source `cc8397836fd88e8d8a9e60a3fbaa0cf86b1c0878`, passed **95 stable +30 preview Swift tests, four helper tests and two native UI cases**, zero failures/skips. Independent review checked **nine original PNGs, 70 pixel samples and ten host checkpoints**, zero mouse moves and all **512 tracking records invalid** without sensors. Live LAN Refresh retained epoch 1; simulated USB Refresh retained epoch 2, while actual fixture Disconnect/Reconnect changed 2→3 with pause and all eleven settings preserved. Native editor Save changed scale 0.85→0.7530025214802623. Both unsigned arm64 SDK 26.2 builds identify `org.vrization.ios.steamvr`, **0.5.1/build 2**, minimum iOS 15.0; all **70 source ZIP files** match that commit and the Simulator archive matches the built executable/debug payload/Metal library. Environment: Xcode 26.3.0 (17C529), macOS 15.7.9, iPhone 17 Pro Max Simulator/iOS 26.2. This tests real UIKit/Metal against synthetic SBS and simulated USB, not a physical iPhone, sensor, cable or SteamVR runtime; the newer host startup-header guard is outside this baseline.
- **Bounded updated Huawei evidence:** Preview 0.5.1/build 2 passed real GLES (576 masks/108 enhanced/512 stereo/five lifecycle/12 synthetic orientation/three context-recreation cases) and passive live-video Refresh with retained epoch/fit/gate, fresh frames, two USB Disconnect/blanking cycles and unchanged preferences. At 1920/Q80/60, delivery was **1618/30.009s =53.917158 decoded FPS**; native sampling counted **900/14.9987184s =60.005127 publication FPS**, with invalid/paused tracking during the probe. No physical display FPS, end-to-end latency or final normal-gyro/black-window recovery pass is inferred; [validation](experimental/steamvr/docs/VALIDATION.md) separates every stage.
- **Startup-header race fixed in source; complete physical recovery is still under review.** New mapping creation can expose an exact 64-byte zero header before the writer publishes its first legal inactive header. `FrameReader` waits only for that initial all-zero state. After any legal header, a zero header still fails; nonzero malformed data remains rejected, and close resets initialization. This neither fabricates frames/tracking nor clears pause. The focused runtime regression passed **13 software tests**, including a real Windows mapping read before first publication and two new tests with six subcases. The subsequent complete suite for that startup-header revision passed **460 desktop/preview tests plus 368 subtests** (51.81s) and **46 script tests plus 67 subtests** (7.67s): **506 actual tests plus 435 subtests**, zero failures/errors/skips; all 114 audited source hashes stayed unchanged during testing. Before the guard, phone Refresh produced `Invalid frame header` and paused tracking after repeated PC Refresh retained 31 valid samples. The new candidate then retained advancing phone sequence and valid flags 3 across **three phone Refreshes (31+21+21 samples) and one PC double-click Refresh (21 samples), totaling 94 samples**. A replaced helper/map confirmed an actual rebuild, the PC footer showed no new invalid-header error and the phone still displayed the SteamVR scene. These are bounded observations, not a complete subjective gray-screen, physical-axis, cold-start or reboot pass. The user subsequently reported gray output again after Refresh/editing. The earlier `cc83978` compiled CI baseline predates this guard, and the 506-test guard revision predates the later explicit Refresh-recovery contract; new full regression/CI/package and complete physical recovery remain pending.
- **Test tooling:** Connection instrumentation protects the application's original preference file throughout Activity startup, callbacks and teardown. Optional bounded frame-rate sampling counts decoded frames delivered to the view with pose output disabled; it neither changes the production input defaults nor measures displayed FPS or motion-to-photon latency.
- **Checked on one physical Huawei:** Ordinary public **0.4.0/build 8** passed repeated USB connection/Disconnect and PC Stop/reconnect, real GLES masks and enhanced projection; public preview **0.5.0-steamvr-preview/build 1** passed additional stereo rendering/lifecycle fixtures. A 15.005-second ordinary USB sample delivered **879 decoded frames /58.58047 FPS** at 640 long edge, Q45 and a 60 FPS target. An **unpublished host candidate** additionally observed active Phone HMD, undistorted Mirror eye acquisition, real sensor packets and SteamVR background SBS on the phone. After paused editing, PC Resume plus physical movement restored viewing; the user reported normal recentering. Complete physical-axis/game/PCVR/stability acceptance and display FPS/motion-to-photon remain unverified; see [exact scope](experimental/steamvr/docs/VALIDATION.md).
- **Documentation only:** Added bilingual root and experiment README diagrams explaining the SteamVR phone-HMD pose/video loop and existing-headset game/desktop-overlay paths, including component roles, GPU/CPU stages and pending hardware verification. That documentation-only update did not change application versions or published downloads.

### [v0.5.0-steamvr-preview](https://github.com/LexZeon/VRization/releases/tag/v0.5.0-steamvr-preview) — 2026-10-10

Separate **0.5.0-steamvr-preview** branch and download channel. Stable **v0.4.0-alpha** and local stable `latest` remain preserved. Android and iOS preview installs use independent application identities and settings.

- **Added:** Separate Windows launcher with direct-phone, phone SteamVR HMD and existing SteamVR headset routes; independent mobile installs, USB endpoints and preferences.
- **Added:** Original 3DOF virtual HMD driver, full gyro quaternions, capability/epoch-gated stereo, GPU compositor packing and existing-headset desktop overlay. Native Stop cleans owned resources; HMD never moves the mouse, and F8/editor/Stop require local PC Resume.
- **Compatibility:** Original direct-phone modes remain. SBS viewer/editor use independent source halves, native aspect/projection and synchronized fit. Experimental archives cannot replace stable `latest`.
- **Polish and regression:** Preview window titles/footer text follow the selected language; the native iOS drag test now waits for the real handle and verifies the draft actually shrinks before checking Save synchronization.
- **Checked:** 387 Windows/Python cases plus 312 subtests, 40 script cases, 176 Android cases, 365 native fixtures, iOS 95+21 Swift/two UI/50 pixel samples and dual SDK builds passed. The full public Windows package receives fresh-profile diagnostics and real owned IPC checks in future CI. See [exact evidence](experimental/steamvr/docs/VALIDATION.md), [illustrated tutorial](experimental/steamvr/docs/TUTORIAL.md) and [pinned BSD-3-Clause OpenVR attribution](experimental/steamvr/native/licenses/README.md). Huawei/PCVR hardware, achieved FPS and physical latency remain unverified until next chat; all previous files/releases are retained.

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

当前未发布源码版本为 **Windows 0.5.1-steamvr-preview、Android 0.5.1-steamvr-preview/build 3、iOS 0.5.1/build 3**。普通版保持 **0.4.0/build 8**，历史0.5.0实验版下载原样保留；此前 `cc83978` build2 基线的 Windows、Android 与 iOS CI 均已独立核验通过。启动头修订另通过506实际加435子检查；之后显式头显刷新恢复契约目前只有针对性测试。用户再次报告灰屏，新完整回归／CI／最终打包及主观／重启验收仍待完成。

- **修复 Android USB 引导：** 回环 Host 校验按各应用显式配置的反向视频端点判断：普通版 **18765**、实验版 **18775**，修正实验 APK 的 USB 握手被 HTTP 403 拒绝。可复用电脑端校验配置端口，同时保留已授权会话、Origin 及停止边界；修复后实验版的真机验收单独记录。
- **修复：** 手机头显 manifest 改用显式空 `hmd_presence` 列表，不再把设备序列号误当 USB VID.PID 匹配。原生构建、打包和 ZIP 检查拒绝错误序列号及永久存在通配符，即使有效载荷哈希相符也不接受。原有 C++ 注册和追踪行为保持原样；[锁定 Valve 来源](experimental/steamvr/native/licenses/README.md)记录配置参考。
- **修复暂停手机头显的存在状态：** 已接受、已连接会话在编辑／暂停／无传感器或姿态过期时刷新无效追踪状态，避免一次性暂停头信息过期而被原生驱动判为断联、Mirror 退出；不刷新旧有效追踪、不解除电脑本地恢复锁，停止立即关闭 accepted／active 门控。早先心跳回归 **416 项 Windows／Python 加 314 个子检查**通过；真机超过六秒编辑时 Mirror 持续发布，保存保留暂停，电脑恢复加实际移动令画面恢复。静止恢复及完整物理坐标／稳定性尚未验收，已发布下载保持原样。

- **显式手机头显刷新现在也请求恢复追踪。** 该用户授权的例外只适用于已接受、已启用的 SteamVR 手机头显路线。仅在所属工作线程完成旧视频清理后，电脑才可恢复刷新请求时已有的暂停；该回执不保证新Mirror已经发布第一帧。原本活动的追踪保留基准，暂停流按既有恢复规则等待新的有效传感器数据，绝不重放旧动作。捕获暂停代际令事务期间新按 F8／进入编辑器或禁用追踪优先；停止、关闭窗口或替换所有者／会话代际取消恢复。停止与刷新恢复使用同一头显锁，原子撤销active／accepted会话并锁定暂停，处理中完成不能恢复已停止会话。电脑重复点击及重叠手机请求共用一次重置／确认。用户要求的完整重连回退只携带一次临时意图到其新的已接受且支持能力的头显会话；八秒超时回退最多携带一次，不无限循环。普通连接、自动重连及保存／弃用不设置该意图，手机直连鼠标控制不变；确认中的暂停字段仍只是状态，不能单独授权恢复。早先针对性回归通过 **43 项软件测试加 32 个子检查**；原子停止细化后的完整回归、手机／iOS build3 CI、最终打包和真机恢复仍待验收。最近用户检查仍报告刷新／编辑后灰屏，不声称灰屏或实体重启已经修好。
- **当前Android build3软件范围：** 本地Gradle通过 **75普通＋58核心＋71实验＝204项单元测试**，包含九项新增显式恢复意图，零失败／错误／跳过；lint零错误／八个既有警告。实验APK／仪器包已编译并核验标准签名，普通APK未重建；这不代表当前CI、安装或实体灰屏／重启验收通过。
- **正在定位的故障：** 用户另报告旧完整重连刷新后手机灰屏，新的视频单独刷新仍待真机恢复验收。用户报告的电脑黑屏是 SteamVR 的 **Headset Window**。另已观察手机连接却等视频时 Mirror 退出，不能据此认定全部 Headset Window 黑屏的原因。
- **新增手机头显画质预设：** 新用户／重置默认均衡 **双眼总宽 1280／Q75／目标 60 FPS**，另可选更清晰 **1920／Q80／60**、低延迟 **640／Q45／60**；保留已保存采集选择及直连默认值。宽度文案区分 SBS 总宽与每眼像素，自定义组合仍为自定义，重置保持追踪暂停。华为界面约 58 个接收 FPS 包含重复交付；1920×960 原生基线为 **481 次发布／14.9744952 秒＝32.121283 发布 FPS**。原生节奏已通过编译／测试及有限真机发布采样，持续活动追踪／显示／延迟仍待验收，不声称实际不同帧／显示帧率或保证延迟。
- **已实现帧去重及原生节奏：** Mirror 在 JPEG 质量不变时跳过同一一致性帧头发布序号／tick，保留质量变更重新编码，且保留粗粒度 tick 相同的新序号；纯解码器结果和原生 ABI 不变。原创自有 QPC 截止时间及高分辨率单次可等待定时器支持 Stop 取消，不改全局定时器。活动视频刷新前的完整修订通过 **445 项桌面／实验版测试加 330 个子检查**及 **45 项脚本加 67 个子检查**，合计 **490 项加 397 个子检查**，零失败／错误／跳过；先前 `fc607e6` 候选版编译并通过 **413 个原生夹具检查**（365 个 IPC／姿态／WARP／工厂加 48 个定时器），解压 Windows ZIP 通过独立诊断。修正后的早先iOS基线已通过，新源码CI、最终发布打包和持续活动追踪／显示／延迟仍待验收，之前原生基线原样保留，不声称实际不同帧／显示帧率提高。
- **早先冻结源码的软件／构建范围：** 冻结源码 `ad092b0` 通过 **503 个实际 Python／脚本测试＋429 个子检查**，零失败／错误／跳过；[CI 38109367242](https://github.com/LexZeon/VRization/actions/runs/38109367242) 的 Windows 通过 **413 个原生夹具检查**与完整解压 ZIP 启动／自有 IPC 门控，Android 通过 **195 项单元测试**、两变体／仪器包编译及 lint 零错误／九个 CI 警告。该轮iOS后来因测试服务事件计数断言失败，修正 `cc83978` iOS证据见下文；最终发布包及活动刷新／重启真机最终验收仍未完成；此前计数／失败尝试保留，不据此声称实际不同帧／显示帧率提高或真机恢复通过。
- **合并电脑重复刷新：** 重复点击，包括手机请求待完成时，仅合并当前所有者／代际的事务，不退回完整重连／暂停；两项真实回环夹具核对回执／关闭次数、确认、代际和基准保留。iOS测试服务现记录视频刷新完成，真实子进程／回环检查连续两次事件。此前 `cc83978` 合并刷新修订回归为 **458桌面／实验版＋362子检查**、**46脚本＋67子检查＝504实际＋429子检查**，零失败／错误／跳过。
- **已核验的早先 iOS 活动刷新基线——`cc83978`：** [CI 38110018576、job 114383462034](https://github.com/LexZeon/VRization/actions/runs/38110018576/job/114383462034)，准确源码 `cc8397836fd88e8d8a9e60a3fbaa0cf86b1c0878`，通过 **95 项正式＋30 项实验 Swift、四项辅助测试、两项原生 UI**，零失败／跳过。独立审查核对 **九张原始 PNG、70 个像素样本和十个电脑检查点**，零鼠标移动，无传感器下 **512 条追踪记录全部无效**。活动 LAN 刷新保持代际1，模拟 USB 刷新保持代际2；真实测试服务断开／重连令2→3，同时保留暂停与完整11项设置。原生编辑器保存令大小0.85→0.7530025214802623。双未签名 arm64 SDK26.2 构建标识 `org.vrization.ios.steamvr`、**0.5.1/build 2**、最低 iOS15.0；**源码 ZIP 全部70文件**逐字节匹配该 commit，模拟器包匹配构建的可执行文件／调试载荷／Metal 库。环境为 Xcode26.3.0（17C529）、macOS15.7.9、iPhone17ProMax模拟器／iOS26.2。范围为真实 UIKit／Metal、合成 SBS 与模拟 USB，不代表实体 iPhone、传感器、线缆或 SteamVR 运行环境；新的电脑启动头保护不属于该基线。
- **有限华为新证据：** 实验0.5.1/build2通过真实GLES（576遮罩／108加强／512立体／5生命周期／12合成方向／3上下文重建）及被动活动视频刷新，保留代际／适配／门控，收到新帧，两次USB断开／清黑、偏好不变；1920／Q80／60交付 **1618／30.009秒＝53.917158解码FPS**，原生采样为 **900／14.9987184秒＝60.005127发布FPS**，工具期间追踪无效／暂停。不据此推断物理显示帧率、端到端延迟或正常陀螺仪／黑窗恢复的最终通过，见[分阶段范围](experimental/steamvr/docs/VALIDATION.md)。
- **源码已修复启动头竞态，完整真机恢复仍在验收。** 新映射创建后、写入者首次发布合法停用头之前，可能读到准确64字节全零头；`FrameReader` 仅对首次合法头之前这一全零状态等待。见过任何合法头之后，全零头仍报错；非零损坏数据仍严格拒绝，关闭读端才重置初始化。不伪造帧／追踪，也不解除暂停。针对性运行回归通过 **13 项软件测试**，包含首次发布前读取真实 Windows 映射，以及两项新增测试的六个子检查；该启动头修订随后完整套件通过 **460 项桌面／实验版加 368 个子检查**（51.81秒）及 **46 项脚本加 67 个子检查**（7.67秒），合计 **506 个实际测试加 435 个子检查**，零失败／错误／跳过，测试期间114份受审源码哈希不变。保护加入之前，电脑重复刷新保持31个有效样本后，手机刷新触发 `Invalid frame header` 并暂停；新候选版随后 **三次手机刷新（31＋21＋21个样本）及一次电脑双击刷新（21个样本），合计94个样本** 均保持标志3有效、手机序号持续增长。观察到工具／映射替换证明确实重建，电脑页脚没有新头信息错误，手机仍显示 SteamVR 场景。这是有限观察，不代表完整主观灰屏、物理坐标、冷启动或重启通过；用户随后报告刷新／编辑后仍灰屏；早先 `cc83978` 编译CI基线早于保护，506测试的保护修订也早于后来的显式刷新恢复契约，新完整回归／CI／打包及完整真机恢复仍待。
- **测试工具：** 连接仪器测试在 Activity 启动、回调和销毁全程保护应用原有偏好文件。可选限时帧率采样关闭姿态输出，只计数交付观看器的已解码帧；不更改生产版输入默认值，也不测量实际显示帧率或运动到显示延迟。
- **单台华为真机检查：** 普通公开 **0.4.0/build 8** 通过多次 USB 连接／断开、电脑停止／重连及真实 GLES 范围遮罩／加强投影；公开实验 **0.5.0-steamvr-preview/build 1** 另通过双眼渲染／生命周期测试。普通 USB 在最长边 640、Q45、目标 60 FPS 时，15.005 秒交付 **879 个已解码帧／58.58047 FPS**。**未发布电脑端候选版**另观察活动手机头显、未畸变 Mirror 双眼获取、真实传感器消息及手机显示 SteamVR 背景 SBS。暂停编辑后，电脑恢复加实际移动手机令画面恢复，用户报告回正正常。完整物理坐标／游戏／PCVR／稳定性及显示帧率／运动到显示延迟仍未验收，见[准确范围](experimental/steamvr/docs/VALIDATION.md)。
- **纯文档：** 根目录与实验版 README 新增双语流程图，解释 SteamVR 手机头显的姿态／视频循环及已有头显的游戏／桌面覆盖层通路，注明组件职责、GPU／CPU 环节和待完成硬件验证。该次纯文档更新没有改变应用版本或已发布下载。

### [v0.5.0-steamvr-preview](https://github.com/LexZeon/VRization/releases/tag/v0.5.0-steamvr-preview) — 2026-10-10

独立 **0.5.0-steamvr-preview** 分支和下载通道，正式 **v0.4.0-alpha** 及本地正式 `latest` 继续保留；Android／iOS 实验版使用独立应用标识和设置。

- **新增：** 独立 Windows 启动器，提供直接连手机、手机 SteamVR 头显、现有 SteamVR 头显三条路线；手机安装身份、USB 端点及设置独立。
- **新增：** 原创三自由度虚拟头显驱动、完整陀螺仪四元数、能力／epoch 协商双眼协议、GPU 合成器拼接和真实头显桌面悬浮层。停止会清理本程序资源；HMD 不移动鼠标，F8／编辑／停止暂停后需要电脑本地恢复。
- **兼容：** 保留原来的直连手机模式。SBS 查看器／编辑器使用独立源图像、原生比例／投影和同步适配。实验归档不能替换正式 `latest`。
- **完善及回归：** 实验版窗口标题／页脚随所选语言显示；iOS 原生拖动测试等待真实顶点，在检查保存同步前确认草稿确实缩小。
- **检查：** Windows／Python 387 项加 312 子检查、40 脚本、176 Android、365 原生、iOS 95+21 Swift／2 UI／50 像素及双 SDK 通过。未来 CI 为完整 Windows 发布包执行全新设置目录诊断和真实自有 IPC 检查。见[准确证据](experimental/steamvr/docs/VALIDATION.md)、[图文教程](experimental/steamvr/docs/TUTORIAL.md)及[固定 BSD-3-Clause OpenVR 来源](experimental/steamvr/native/licenses/README.md)。华为／PCVR、真实帧率和物理延迟留到下次，全部旧文件／发布保留。

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

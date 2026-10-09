# 🧪 Validation record / 验证记录

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

Recorded 2026-10-08. Automated checks, desktop capture and emulator observations are distinguished from hardware capabilities that remain untested.

### Completed for the first release

| Check | Environment and result | What it establishes |
| --- | --- | --- |
| Host core | Windows x64, local CPython 3.12.14; 12 checks passed. | Listed settings, protocol, input authorization, long-edge scaling and module behavior. |
| Android core | JDK 17, Gradle 8.9, AGP 8.7.3; 6 tests passed. | Pose math, angle handling and arbitrary tilted recentering. |
| Android build / lint | Latest first-release APK assembled and linted successfully. | APK generation, not universal device compatibility. |
| Windows EXE | Local build succeeded with 40 license files; no Microsoft `VCRUNTIME140*.dll`. | Packaging and bundled notices were checked; Microsoft runtime is a system prerequisite. |
| Display capture | ASUS PA279 portrait source 2160 × 3840; limit 1280 produced 720 × 1280. | Portrait capture, aspect preservation and longest-edge bound. |
| Desktop screenshot | 1054 × 963 crop of this project's GUI, selecting that ASUS display. | Actual controls, modes, display selection and stream settings. |
| Android installation / display | Google-free Android 6.0 / API 23 emulator received the original animated card. | Startup, JPEG / WebSocket reception and both-eye display in that environment. |
| Actual desktop stream | Latest first-release APK received ASUS desktop frames at 720 × 1280 and stayed connected. | Real Windows capture → network → Android rendering beyond synthetic frames. |
| Settings UI | Scale, offsets, separation and distortion visible; hidden controls leave the image visible. | Settings and viewing flow work in the emulator. |
| Endpoint round trip | Real Android controls sent offsetX 0.3 and separation 0.2; host accepted, echoed and saved them without disconnecting. | Float serialization did not incorrectly reject these boundary values. |
| No-sensor fallback | Emulator has no usable rotation sensor; full screen works. | Fixed viewing without sensor support. |

The older emulator screenshot files show the final v0.1.1 English interface and show the original [calibration example](../examples/embedded_host.py). Receive-FPS readings describe those sessions, **not end-to-end latency measurements or performance benchmarks**. The emulator uses software graphics; readings from actual desktop reception likewise do not predict physical phones, viewers or Wi-Fi. No game-FPS guarantee follows from them. The table above remains the historical first-release record.

### v0.1.1-alpha follow-up checks

- Windows host: **20 automated tests passed**, including concurrent settings updates and language handling.
- Android: **15 tests passed** (6 core math tests and 9 app settings-order / session-dispatch regression tests); the v0.1.1 APK assembled and linted.
- Actual Windows 11 build 26200 / ASUS display: English default, Chinese switching, persistence after reopen, language switching while streaming, and 1060 × 680 scrolling checked. Switching language disarms mouse control.
- Documentation: all 20 project-owned pages pass language-order / section / local-file checks. Windows and Android license ZIPs were actually packaged with offline-link validation. Six checker smoke cases and discovery of a temporary nested Markdown page also passed; these checks do not judge translation quality.
- The final packaged Windows EXE also started on the actual ASUS display with English UI and responded normally.

#### Android 16 / API 36 — final v0.1.1 APK

Tested on a Google-free AOSP emulator. The v0.1.0 APK upgraded in place to v0.1.1 (version code 2). English was the default; switching to Chinese persisted after force-stop / reopen, then switching back to English worked.

The actual client received the original 1280 × 720 calibration card over WebSocket and rendered both eyes with OpenGL. Host-selected cinema / FPS modes remained selected and Game Rotation Vector registration was observed in Android's sensor service; returning to full screen unregistered it. This does **not** establish physical gyro axes or real FPS input.

Hiding controls and restoring with Back passed. Entering the background changed the host's connected state to false, with no mouse output. After a language change, Home / background transition, and server close code `1001`, explicitly tapping Connect restored reception. No AndroidRuntime, OpenGLRenderer or libEGL errors were observed during these checks. Receive-FPS readings are not benchmarks.

#### Android 6.0 / API 23 — final v0.1.1 APK

The same local debug signature upgraded v0.1.0 to v0.1.1 in place, preserving host, port and saved settings. On a Chinese-system fresh configuration, English was still the default. Both English and Chinese choices persisted after force-stop / reopen. APK v1 / v2 signature verification passed, and the locally built old / new certificate SHA-256 matched; this does not guarantee another machine's debug key matches.

The actual client rendered the original 1280 × 720 card in both eyes. Hiding controls / Back recovery passed. Dragging scale to `1.0` and offsetX to `-0.3` remained stable after two seconds. Without a rotation sensor, host-selected cinema actively returned to full screen, and selecting FPS also remained in full screen. Home / background disconnected the host; explicit Connect restored reception after foreground return or a host close. The test `FakeInput.moves` list stayed empty.

No FATAL, native-fatal or out-of-memory errors were observed. One `EGL_BAD_SURFACE` appeared while the old PopupWindow was recreated during a Chinese language selection; the new Activity continued rendering normally afterward, with no persistent GL failure. This is recorded as a nonblocking lifecycle observation, not a claim of an entirely empty GL error log.

### v0.2.0-alpha checks

- Windows host: **107 automated tests passed**, including USB discovery / mapping ownership, iOS relay framing / pairing checks, loopback bootstrap restrictions, Windows DPI fallback, actual WebSocket wire messages, capture pacing, original GPU resources and fallback / cache integration. Local Windows builds use CPython 3.12.14.
- Android: **36 tests passed** (8 core and 28 app), APK / AAR build and lint passed after the final latency improvements. The same local debug certificate upgraded the attached HUAWEI Pura 70 Ultra from version code 1 to code 3 without uninstalling.
- Physical phone: HUAWEI Pura 70 Ultra, reporting Android 12 / API 31 compatibility, received the original **960 × 540** calibration card over an actual data cable. USB and English were default. Authorized discovery, fresh-launch automatic connection, both-eye rendering and hidden controls / Back recovery passed. No manual IP or pairing code was entered in USB mode.
- Chinese persisted after force-stop / reopen; switching language disconnected the host and required an explicit reconnect. A new process launch made its documented one-time USB connection attempt. In FPS mode the host received **877 real sensor pose messages** during the observed interval. No operating-system mouse input was armed; the fake sink remained empty. These observations do not verify physical gyro axes or real-game control.
- USB detection encountered a real Huawei difference: ADB did not return a usable USB path. The final Windows implementation verifies the physical USB serial through native SetupAPI enumeration. Emulators and network ADB remain excluded.
- The same phone also received actual ASUS PA279 portrait desktop frames over USB at **540 × 960**. Home / background disconnected the host, and returning to the foreground did not silently reconnect. Full desktop capture performance is measured separately below.
- New screenshots show this phone and its USB reception; the source is an original calibration card, not a game. The phone's observed ping round trip of **4–7 ms** is a connection diagnostic, **not end-to-end video latency**.

The final calibration USB session, at 960 × 540 / target 60 FPS / JPEG 60, recorded **60 consecutive host-send samples averaging 59.99 FPS (59.74–60.22)** after the Windows pacing fix. The phone UI showed approximately 60 FPS received. This is a synthetic-content diagnostic on the physical USB path, not desktop-capture performance or an end-to-end latency benchmark. The earlier Windows tick-based pacing fluctuated around 32–64 FPS. Different content / capture costs require separate measurement.

The actual ASUS desktop USB session used the native GDI backend and produced **540 × 960** frames. Its **24 host-send FPS samples averaged 11.05, ranging from 8.2 to 12.11**. When the display layout later changed, the layout guard stopped producing new frames; no operating-system mouse input was emitted. This establishes the observed capture / USB path and fail-closed behavior, not a 60 FPS desktop guarantee or end-to-end video latency.

CS2 and Discord remained running as requested. GPU 3D utilization was observed near full load, while Discord used approximately one CPU core. These are concurrent-load observations, not a controlled performance comparison, and do not establish which application caused the capture limit. The local native / MSS timing trials likewise ran on the busy desktop; their results must not be presented as controlled backend benchmarks.

After the user reported exiting Discord, the first short retest stopped on another real display-layout change. A fresh **540 × 960** USB session on the new layout then recorded **14 host-send samples averaging 8.62 FPS (7.87–9.54)**, no capture errors and no operating-system mouse moves. Discord background processes remained but used approximately 0% of one CPU core in a two-second sample. The primary display resolution differed from the earlier session, so these observations cannot isolate Discord as a cause. Both test hosts were stopped and their owned USB mappings removed.

The pre-optimization EXE started on the actual ASUS display in English with USB discovery. Its clean preference profile selected 960 / 60 / 60; existing capture settings remained Custom. The desktop preview automation tool later failed to capture its window during a changed display-resolution / scaling layout, so further GUI interaction was not counted as passing.

#### Original GPU capture follow-up

The production `MssCaptureSource` selected the original DXGI / D3D11 backend on the ASUS PA279, performed rotation / resize on the GPU and streamed its actual **2160 × 3840 desktop as 360 × 640 / Q45 / target 60 FPS** over USB. The HUAWEI phone's decoded-frame UI readings were **59.9 and 57.7 FPS**, with link round trips of **2 and 7 ms**. The host recorded **41 send-stat samples averaging 59.66 FPS**, range **45.97 startup–60.14**; excluding the initial startup sample, mean send FPS was **60.00**. There were **2,338 distinct JPEGs, 173 repeated / static reads, zero empty reads and zero capture errors**. Repeated packets are not distinct desktop updates. Mean production read / resize / JPEG time was **4.06 ms**. No operating-system mouse input was emitted. DXcam, NumPy and comtypes were absent from the production runtime.

The stable preset captured an original **1280 × 720** animation window on ASUS as **640 × 360 / Q50 / target 30 FPS**. The phone read **30.2 FPS**; 13 send-stat samples averaged **29.43 FPS including startup**, or **30.00** after the startup sample. All **391 JPEGs differed**, with no repeats or capture errors. An owned calibration image had red / green / blue / yellow in the correct four corners, verifying crop, portrait-source rotation and channel order. The quality preset captured the full portrait display as **540 × 960 / Q60 / target 30 FPS**: the phone read **30.0 FPS**; 14 host samples averaged **29.56 including startup**, or **30.00** afterward, with 417 distinct JPEGs and five repeated reads. Mean read times were **4.26 ms stable / 7.71 ms quality**.

These are bounded sessions on one GPU / display / phone setup, with an original moving window on the desktop. They establish an actual desktop-to-phone path above 30 FPS for the default, without a controlled same-resolution comparison to the earlier GDI tests. **Capture time plus ping RTT is not end-to-end video latency.** Decode, render scheduling, screen scanout and input-to-photon latency require separate measurement. Current defaults are 640 / 60 / Q45, stable 640 / 30 / Q50, quality 960 / 30 / Q60. See [performance and attribution](PERFORMANCE.md).

The final latency-improved APK upgraded this Huawei phone in place with the same signing certificate. Its UI showed **59.9 decoded FPS**, **7 ms link RTT** and **11.3 ms mean phone-local processing from complete-JPEG reception to texture submission**. That phone metric excludes PC capture, link transport and physical display. In the bounded final host session, 39 send samples averaged **59.68 FPS**; after startup, host capture averaged **4.06 ms**, latest-frame queue **0.30 ms** and submission to the local transport **0.11 ms**. The original moving window started partway through: there were 1,117 distinct JPEGs and 1,280 repeated / static reads, so the whole session is not a 60-distinct-update benchmark. No capture errors or operating-system mouse moves occurred. Phone decoding now hands frames directly to the renderer through a session gate, and same-size / same-format uploads reuse the texture. These independently measured components must not be added and labelled end-to-end latency.

A later bounded test used only the **Alienware AW2726DL**, after the user changed the selected test display. Actual **2560 × 1440** desktop capture became **640 × 360 / Q45 / target 60** using the final pre/post-layout validation. There were **34 host send samples, mean 59.59 FPS**, 1,889 distinct JPEGs and 212 repeated reads; distinct updates were approximately **53.59 per second** over the instrumented source interval. After startup, host capture averaged **2.96 ms**, queue **0.36 ms**, local send submission **0.12 ms**. After the bounded run ended, the phone retained its final-window readings of **56.7 decoded FPS, 7 ms RTT and 10.8 ms phone processing**. These retained readings are not live values or session-wide phone averages. No capture errors or OS mouse output occurred; ASUS was not used in this run.

The release retains the previous API 23 / 36 results above as historical evidence; they are not fresh coverage of every v0.2.0 change. GitHub Actions run [37889266302](https://github.com/LexZeon/VRization/actions/runs/37889266302) passed the iOS checks: 40 reusable-core tests, both Simulator / unsigned device builds, two native UI cases using real slider and precision-button touches, LAN / simulated USB reception, settings echo, and original-image color / orientation validation. These are Simulator results, not physical iPhone USB or a signed IPA.

### Still needs physical testing

- Other phones / Android derivatives, Wi-Fi, heat and battery life.
- Real rotation sensors: axes, stability, recentering and cinema tracking.
- Viewer optics: alignment, field of view, distortion and comfort.
- Real FPS games: input acceptance, control feel and compatibility.
- Other GPUs, display layouts, Windows scaling, protected / exclusive content.
- Quality, throughput, dropped frames and end-to-end latency with specified hardware and network conditions.

Screenshots and unit tests must not be presented as passing these untested cases.

### Build provenance

The first locally verified release used CPython 3.12.14 and has the recorded native inventory. Windows CI uses 3.12.10; its embedded DLL versions must be inspected separately. Check actual Actions status for remote build outcomes and audit a concrete binary before redistributing it.

Microsoft Visual C++ v14 x64 runtime is installed by the system, not shipped inside the EXE. See [build](BUILD.md) and [third-party notices](../THIRD_PARTY_NOTICES.md).

### v0.3.0-alpha — current work, separate acceptance

The original Python headset-fit geometry / local transaction has **20 pure tests passing**: landscape / portrait fit, symmetric eye spacing, unclipped valid bounds, all four center-fixed corners, pan / scale / separation clamps, all four selected-eye directions with global X preserved, gesture-start rather than accumulated deltas, invalid numeric snapshots and one-shot commit / discard. They perform no capture, GUI automation, USB operation or OS mouse injection.

Before the final linked-spacing correction, the complete local Windows suite passed **132 tests plus 20 language-catalog subcases**, including the original geometry cases and nine headless editor / reset integration cases. They cover draft isolation, entry disarm, blocking desktop arming while editing, saving only fit fields into current settings, full reset / persistence, English / automatic USB defaults, and preservation of explicit display / region / ADB path. They do not exercise the new Windows GUI through real user interactions. That interim x64 EXE's static package audit matched 15 project modules, 44 notice files and all 38 recorded native DLL / PYD hashes, without bundled research libraries or Windows system D3D DLLs; final-direction builds require their own checks.

The local Android build, before the linked-spacing correction, passed **61 JVM tests (46 app / 15 core)**, APK / AAR compilation and lint with **zero errors / eight warnings**. It targets min API 23 / target 35 with version 0.3.0, code 4, and uses the same local debug certificate as the preceding installed APK. These are automated / build checks, not physical-phone editor acceptance.

Phone UI / device acceptance and the new iOS build checks are still being completed. This paragraph does **not** claim new phone UI, physical-device, Windows GUI or end-to-end acceptance. Record those checks here only after they run; retain the completed v0.2 evidence and [original release notes](releases/v0.2.0-alpha.md) as historical records.

---

<!-- vrization:chinese -->
## 简体中文

记录日期：2026-10-08。这里区分自动检查、电脑采集和模拟器观察；未验证的硬件能力不以截图或单元测试代替。

### 首发已完成

| 项目 | 环境与结果 | 能说明什么 |
| --- | --- | --- |
| 电脑端核心检查 | Windows x64，本机 CPython 3.12.14，12 项检查通过。 | 设置 / 协议校验、姿态输入授权、长边缩放和模块行为通过所列检查。 |
| Android 核心检查 | JDK 17、Gradle 8.9、AGP 8.7.3，6 项单元检查通过。 | 姿态数学、角度处理与任意倾斜回正等逻辑通过检查。 |
| Android 构建与静态检查 | 首发 APK 的 `assembleDebug`、`lintDebug` 成功。 | 能生成 APK；不等于所有设备兼容性验证。 |
| Windows 最终程序 | 本机 EXE 打包成功，附带 40 份许可文件；不包含 Microsoft `VCRUNTIME140*.dll`。 | 打包与许可随附已检查；微软运行库由系统安装提供。 |
| Windows 显示器采集 | ASUS PA279，2160 × 3840 纵向显示器；最长输出边设为 1280，确认输出为 720 × 1280。 | 纵向整屏可采集，按原始比例缩放并限制最长边。 |
| 电脑教程截图 | 1054 × 963，截取本项目电脑端界面；截图选择上述 ASUS 显示器。 | 展示真实按钮、模式、显示器选择与串流设置。 |
| Android 安装、连接和显示 | 无 Google 服务的 Android 6.0 / API 23 模拟器，安装首发 APK，接收原创动态校准卡。 | APK 可在该环境启动，JPEG / WebSocket 接收与双眼显示可运行。 |
| 实际桌面到 Android 串流 | 首发 APK 在上述模拟器接收实际 ASUS 桌面采集，确认帧尺寸为 720 × 1280，连接保持。 | 除示例帧外，真实 Windows 采集 → 网络 → Android 显示路径也已连接验证。 |
| 设置操作 | 模拟器显示缩放、位置、双眼间距、畸变控制；隐藏操作区后仍显示双眼画面。 | 界面与观看流程可操作。 |
| 设置边界值往返 | 实际 Android 界面把水平位置设为 0.3、双眼间距设为 0.2，主机接受、回传并保存，连接保持。 | 浮点边界值不会因序列化误差被主机误拒绝。 |
| 无传感器回退 | 模拟器没有可用旋转传感器，客户端可使用全屏模式。 | 无传感器设备的固定画面路径可运行。 |

较早的模拟器截图文件展示最终 v0.1.1 英文界面，对应 [examples/embedded_host.py](../examples/embedded_host.py) 的原创校准卡，未用真实游戏画面冒充实机测试。接收帧率是当次连接状态，**没有测量端到端延迟，也不构成性能基准**；上表仍保留首发的历史记录。

上述模拟器使用软件图形渲染；实际桌面连接测试的接收读数同样不能代表 Android 真机、手机盒子或真实无线网络的性能。没有根据这些读数承诺游戏帧率。

### v0.1.1-alpha 补充检查

- 电脑端 **20 项自动检查通过**，涵盖并发设置同步与语言处理。
- Android **15 项检查通过**（6 项核心数学、9 项应用设置顺序 / 会话分发回归），v0.1.1 APK 构建与 lint 通过。
- 真实 Windows 11 build 26200 / ASUS 显示器检查默认英文、中文切换、重开后保留、串流中切换与 1060 × 680 小窗滚动；切换语言会解除鼠标授权。
- 20 个自有公共页面的语言顺序、分区与本地文件链接检查通过；Windows 与 Android 许可 ZIP 已实际打包并通过离线链接检查。6 个检查器烟雾用例和临时嵌套 Markdown 的发现检查通过；这些检查不判断翻译质量。
- 最终打包 Windows EXE 已在真实 ASUS 显示器以英文启动，界面响应正常。

#### Android 16 / API 36 — 最终 v0.1.1 APK

在不含 Google 服务的 AOSP 模拟器测试，v0.1.0 可覆盖升级到 v0.1.1（version code 2）。默认英文，切换中文后强制停止再打开仍保留中文，再切回英文成功。

实际客户端经 WebSocket 接收 1280 × 720 原创校准卡并通过 OpenGL 显示双眼画面。电脑切大屏幕 / FPS 后客户端保留相应模式，Android 传感器服务注册 Game Rotation Vector；回到全屏后注销。这**不代表**真实陀螺仪轴向或真实 FPS 输入已经通过。

隐藏操作区与返回键恢复通过。进入后台后主机连接状态变为 false，没有鼠标输出。切换语言、Home 进入后台、服务端 `1001` 关闭之后，均显式点击连接即可恢复接收。这些检查期间未观察到 AndroidRuntime、OpenGLRenderer 或 libEGL 错误；接收帧率读数不作为性能基准。

#### Android 6.0 / API 23 — 最终 v0.1.1 APK

相同本地 debug 签名从 v0.1.0 原地升级到 v0.1.1，保留 host、port 与设置。系统中文的首次配置仍默认英文，English / 中文各自选择后强制停止再开均保留。APK v1 / v2 签名验证通过，本机构建旧新版证书 SHA-256 一致；这不保证其他机器的 debug key 相同。

实际客户端显示 1280 × 720 原创卡的双眼画面，隐藏 / 返回恢复通过。拖到 scale `1.0`、offsetX `-0.3` 并等待两秒后值保持稳定。没有旋转传感器时，主机推大屏幕会主动回全屏，选择 FPS 也保持全屏。Home 进入后台后主机断开，回前台或主机关闭后显式点击连接均恢复接收；测试 `FakeInput.moves` 始终为空。

未观察到 FATAL、原生 fatal 或内存不足错误。中文语言选择重建旧 PopupWindow 时出现过一次 `EGL_BAD_SURFACE`，随后新 Activity 持续正常渲染，没有持续 GL 失败。这里如实记录为非阻塞生命周期观察，不声称该环境的 GL 错误日志完全为空。

### v0.2.0-alpha 检查

- Windows 电脑端 **107 项自动检查通过**，包含 USB 识别 / 映射归属、iOS 中继分帧 / 配对、回环 bootstrap 限制、Windows DPI 回退、实际 WebSocket 报文、采集节奏、原创 GPU 资源及回退 / 缓存接入。本地 Windows 使用 CPython 3.12.14 构建。
- Android **36 项检查通过**（核心 8、应用 28），最终延迟优化后的 APK / AAR 构建与 lint 通过。同一本地 debug 证书在接入的 HUAWEI Pura 70 Ultra 从 version code 1 覆盖升级到 code 3，无需卸载。
- 真机 HUAWEI Pura 70 Ultra 报告 Android 12 / API 31 兼容层，经真实数据线接收 **960 × 540** 原创校准卡。默认 USB 和英文，授权发现、新启动自动连接、双眼渲染、隐藏设置 / 返回恢复通过，USB 未手填 IP 或配对码。
- 中文在强制停止 / 重开后保留；切换语言会断开并要求显式重连。新进程启动进行了文档约定的一次 USB 自动尝试。FPS 模式的观察区间收到 **877 条真实传感器姿态消息**，未授权操作系统鼠标，假接收器保持为空。这不代表陀螺仪实际轴向或真实游戏控制已经验证。
- 真机测试发现华为差异：ADB 未提供可用 USB 路径。最终 Windows 实现通过原生 SetupAPI 枚举确认真实 USB 序列号，继续排除模拟器与网络 ADB。
- 同一手机还经 USB 接收真实 ASUS PA279 竖屏桌面，尺寸 **540 × 960**。Home 进入后台后主机断开，回到前台不会悄悄重连；整屏采集性能另行记录如下。
- 新截图展示此手机的 USB 接收，来源是原创校准卡而非游戏。手机观察到 **4–7 ms** ping 往返仅作连接诊断，**不是端到端视频延迟**。

最终 960 × 540 / 目标 60 FPS / JPEG 60 校准 USB 会话在 Windows 节奏修复后，连续 **60 个电脑发送样本均值 59.99 FPS（59.74–60.22）**，手机接收读数约 60 FPS。这是实际 USB 路径上的合成内容诊断，不是桌面采集成绩或端到端延迟基准。此前 Windows tick 等待的读数约在 32–64 FPS 间波动；其他内容 / 采集负担需要分别测量。

实际 ASUS 桌面 USB 会话使用原生 GDI 后端，输出 **540 × 960** 帧；**24 个电脑发送 FPS 样本均值 11.05，范围 8.2–12.11**。随后显示布局改变，布局保护停止产生新帧，没有发出操作系统鼠标输入。这说明当次实际采集 / USB 路径与异常停止行为，不代表桌面可保证 60 FPS，也没有测量端到端视频延迟。

按用户要求，CS2 和 Discord 保持运行。观察到 GPU 3D 利用率接近满载，Discord 约占用一个 CPU 核心。这些只是同时运行负载的观察，不是受控性能对比，也不能确定哪个应用造成采集限制。本地原生后端 / MSS 计时试验同样在忙碌桌面运行，不把读数作为受控后端性能基准。

用户报告退出 Discord 后，第一次短复测因另一次实际显示布局变化停止。按新布局重新启动 **540 × 960** USB 会话后，**14 个电脑发送样本均值 8.62 FPS（7.87–9.54）**，没有采集错误，没有操作系统鼠标移动。Discord 后台进程仍存在，但两秒采样约占一个 CPU 核心的 0%。主显示器分辨率与之前不同，因此这些观察无法单独确定 Discord 是否造成问题。两个测试主机均已停止，并移除了各自建立的 USB 映射。

优化前的 EXE 在实际 ASUS 显示器以英文启动并识别 USB，当时全新偏好选中 960 / 60 / 60，已有采集设置保留为自定义。桌面分辨率 / 缩放布局变化期间，界面预览自动化工具随后无法捕获窗口，因此不把后续 GUI 操作计为通过。

#### 原创 GPU 采集补充检查

正式 `MssCaptureSource` 在 ASUS PA279 选择原创 DXGI / D3D11 后端，在 GPU 完成旋转和缩放，把真实 **2160 × 3840 桌面以 360 × 640 / Q45 / 目标 60 FPS** 经 USB 发送。华为手机解码帧率读数为 **59.9、57.7 FPS**，链路往返分别为 **2、7 ms**。电脑 **41 个发送样本均值 59.66 FPS**，范围 **启动阶段 45.97–60.14**；去掉首个启动样本后均值 **60.00**。统计到 **2,338 张不同 JPEG、173 次重复 / 静态读取、零空读取、零采集错误**；重复发送不算新的桌面更新。正式采集 / 缩放 / JPEG 平均 **4.06 ms**，没有发出操作系统鼠标输入。正式运行环境没有 DXcam、NumPy 或 comtypes。

稳定预设在 ASUS 采集原创 **1280 × 720** 动画窗口，输出 **640 × 360 / Q50 / 目标 30 FPS**。手机读数 **30.2 FPS**；电脑 13 个发送样本含启动均值 **29.43 FPS**，去掉首个启动样本后 **30.00**。**391 张 JPEG 均不同**，无重复、无采集错误。原创校准画面的红 / 绿 / 蓝 / 黄四角位置正确，验证了选区、竖屏来源旋转与颜色通道。画质预设采集竖屏全屏，输出 **540 × 960 / Q60 / 目标 30 FPS**，手机 **30.0 FPS**；电脑 14 个样本含启动均值 **29.56**，之后 **30.00**，417 张不同 JPEG、五次重复读取。平均读取时间分别为稳定 **4.26 ms** / 画质 **7.71 ms**。

这是同一 GPU / 显示器 / 手机上的限时会话，桌面包含原创动态窗口。默认预设的真实桌面到手机路径超过 30 FPS，但与此前 GDI 测试没有做相同分辨率的严格对照。**采集耗时加 ping 往返不是端到端视频延迟。** 解码、渲染调度、屏幕扫描和输入到显示仍需分别测量。当前默认 640 / 60 / Q45，稳定 640 / 30 / Q50，画质 960 / 30 / Q60。见 [性能与来源说明](PERFORMANCE.md)。

最终低延迟 APK 用相同签名在此华为手机覆盖安装。界面显示 **59.9 解码 FPS**、**7 ms 链路往返**，以及从完整 JPEG 接收到纹理提交的 **11.3 ms 手机本地平均处理耗时**；该手机指标不含电脑采集、链路和物理屏幕显示。最终限时电脑会话 39 个发送样本均值 **59.68 FPS**；启动之后电脑采集平均 **4.06 ms**、最新帧排队 **0.30 ms**、提交给本地连接 **0.11 ms**。原创动态窗口在会话中途启动，统计 1,117 张不同 JPEG、1,280 次重复 / 静态读取，因此整个会话不能当作每秒 60 次不同桌面更新的基准。没有采集错误或操作系统鼠标移动。手机解码通过会话门直接把帧交给渲染器，相同尺寸 / 格式上传复用纹理。这些独立测得的环节不能相加并称为端到端延迟。

用户改变测试显示器后，后续限时测试只使用 **Alienware AW2726DL**，以最终采集前后布局校验采集真实 **2560 × 1440** 桌面，输出 **640 × 360 / Q45 / 目标 60**。电脑 **34 个发送样本均值 59.59 FPS**，1,889 张不同 JPEG、212 次重复读取；仪表记录区间的不同更新约 **53.59 次每秒**。启动后电脑采集平均 **2.96 ms**、排队 **0.36 ms**、本地发送提交 **0.12 ms**。限时会话结束后，手机保留的末次统计窗口读数为 **56.7 解码 FPS、7 ms RTT、10.8 ms 手机本地处理**；这不是当时仍在串流的实时值，也不是整段手机平均。没有采集错误或系统鼠标输出，此轮没有使用 ASUS。

上面的 API 23 / 36 结果保留为历史证据，不代表重新覆盖 v0.2.0 的所有改动。GitHub Actions [37889266302](https://github.com/LexZeon/VRization/actions/runs/37889266302) 的 iOS 检查通过：40 项可复用核心测试、模拟器 / 未签名真机目标构建、两个通过实际滑条与精确按钮触摸的原生界面用例、局域网 / 模拟 USB 接收、设置回传，以及原创图像颜色 / 方向校验。这些是模拟器结果，不代表 iPhone 真机 USB 或已签名 IPA。

### 仍需实机验证

- 其他 Android 手机 / 衍生系统、无线网络、发热与续航。
- 真实陀螺仪 / 旋转传感器的方向、稳定性、回正和大屏幕转头体验。
- 手机 VR 盒子的镜片对齐、视场角、畸变与佩戴舒适度。
- FPS 游戏实际接收鼠标输入的行为、头部控制手感与兼容性。
- 不同 GPU、显示器组合、Windows 缩放和受保护 / 独占全屏内容。
- 硬件与网络条件明确的画质、帧率、丢帧、流量和端到端延迟测量。

这些未完成项不影响已有源码、自动检查与模拟器串流记录的真实性，也不应被描述为已经通过。

### 构建来源与审计范围

首发本机构建使用 CPython 3.12.14，仓库原生运行时清单对应该产物。Windows CI 固定 CPython 3.12.10，不能据此宣称两个构建的内置 DLL 版本相同。重新发布时对具体产物核查许可与运行组件；以 GitHub Actions 的实际运行状态判断远程构建是否成功。

Windows 程序使用系统安装的 Microsoft Visual C++ v14 x64 运行库，不在 EXE 中分发 `VCRUNTIME140*.dll`。完整说明见 [构建指南](BUILD.md) 与 [第三方声明](../THIRD_PARTY_NOTICES.md)。


### v0.3.0-alpha — 当前工作与独立验收

原创 Python 盒子适配几何 / 本地事务已有 **20 项纯检查通过**：横竖比例、对称双眼间距、合法边界不偷偷裁切、四个中心固定角点、平移 / 缩放 / 间距限制、选中眼四种方向与整体 X 保留、手势起点而非重复累加、非法数字快照及一次提交 / 放弃。检查不采屏、不做界面自动化、不操作 USB、不注入系统鼠标。

在最终联动间距修正前，本地完整 Windows 套件 **132 项测试及 20 个语言词条子项通过**，包含原有几何检查及九项无真实界面的编辑 / 重置集成检查：草稿隔离、进入解除授权、电脑编辑期间禁止授权、只将适配字段合并到当前设置、全部重置 / 保存、英文 / USB 自动默认，以及保留明确显示器 / 选区 / ADB 路径。它们没有通过真实用户操作验收新的 Windows 界面。该中间版 x64 EXE 静态审计匹配 15 个自有模块、44 份许可通知及全部 38 个原生 DLL / PYD 哈希，没有附带研究库或 Windows 系统 D3D DLL；最终方向构建须另行检查。

联动间距修正前的本地 Android 构建**61 项 JVM 检查通过（应用 46 / 核心 15）**，APK / AAR 编译及 lint 通过，**零错误 / 八条警告**。最低 API 23、target 35、版本 0.3.0 / code 4，沿用此前已安装 APK 的本地 debug 证书；这是自动化 / 构建检查，不是手机实机编辑器验收。

手机界面 / 设备验收及新 iOS 构建检查仍在完成。本段**不宣称**新手机界面、实机、Windows 界面或端到端验收通过；实际执行后再记录，保留 v0.2 已完成证据和 [原发布说明](releases/v0.2.0-alpha.md) 作为历史。

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

- Windows host: **69 automated tests passed**, including USB discovery / mapping ownership, iOS relay framing / pairing checks, loopback bootstrap restrictions, Windows DPI fallback, actual WebSocket wire messages and capture pacing. A new local Windows EXE was built with CPython 3.12.14.
- Android: **27 tests passed** (6 core and 21 app), APK build / lint passed. The same local debug certificate upgraded the attached HUAWEI Pura 70 Ultra from version code 1 to code 3 without uninstalling.
- Physical phone: HUAWEI Pura 70 Ultra, reporting Android 12 / API 31 compatibility, received the original **960 × 540** calibration card over an actual data cable. USB and English were default. Authorized discovery, fresh-launch automatic connection, both-eye rendering and hidden controls / Back recovery passed. No manual IP or pairing code was entered in USB mode.
- Chinese persisted after force-stop / reopen; switching language disconnected the host and required an explicit reconnect. A new process launch made its documented one-time USB connection attempt. In FPS mode the host received **877 real sensor pose messages** during the observed interval. No operating-system mouse input was armed; the fake sink remained empty. These observations do not verify physical gyro axes or real-game control.
- USB detection encountered a real Huawei difference: ADB did not return a usable USB path. The final Windows implementation verifies the physical USB serial through native SetupAPI enumeration. Emulators and network ADB remain excluded.
- The same phone also received actual ASUS PA279 portrait desktop frames over USB at **540 × 960**. Home / background disconnected the host, and returning to the foreground did not silently reconnect. Full desktop capture performance is measured separately below.
- New screenshots show this phone and its USB reception; the source is an original calibration card, not a game. The phone's observed ping round trip of **4–7 ms** is a connection diagnostic, **not end-to-end video latency**.

The final calibration USB session, at 960 × 540 / target 60 FPS / JPEG 60, recorded **60 consecutive host-send samples averaging 59.99 FPS (59.74–60.22)** after the Windows pacing fix. The phone UI showed approximately 60 FPS received. This is a synthetic-content diagnostic on the physical USB path, not desktop-capture performance or an end-to-end latency benchmark. The earlier Windows tick-based pacing fluctuated around 32–64 FPS. Different content / capture costs require separate measurement.

The actual ASUS desktop USB session used the native GDI backend and produced **540 × 960** frames. Its **24 host-send FPS samples averaged 11.05, ranging from 8.2 to 12.11**. When the display layout later changed, the layout guard stopped producing new frames; no operating-system mouse input was emitted. This establishes the observed capture / USB path and fail-closed behavior, not a 60 FPS desktop guarantee or end-to-end video latency.

CS2 and Discord remained running as requested. GPU 3D utilization was observed near full load, while Discord used approximately one CPU core. These are concurrent-load observations, not a controlled performance comparison, and do not establish which application caused the capture limit. The local native / MSS timing trials likewise ran on the busy desktop; their results must not be presented as controlled backend benchmarks.

The new EXE started on the actual ASUS display in English with USB discovery. A clean preference profile selected 960 / 60 / 60 automatically; existing capture settings remained Custom. The desktop preview automation tool later failed to capture its window during a changed display-resolution / scaling layout, so further GUI interaction was not counted as passing.

The release retains the previous API 23 / 36 results above as historical evidence; they are not fresh coverage of every v0.2.0 change. The complete iOS validation result remains pending; it is not recorded as passed. Physical iPhone USB remains untested.

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

- Windows 电脑端 **69 项自动检查通过**，包含 USB 识别 / 映射归属、iOS 中继分帧 / 配对、回环 bootstrap 限制、Windows DPI 回退、实际 WebSocket 报文与采集节奏。本地使用 CPython 3.12.14 重新构建 Windows EXE。
- Android **27 项检查通过**（核心 6、应用 21），APK 构建 / lint 通过。同一本地 debug 证书在接入的 HUAWEI Pura 70 Ultra 从 version code 1 覆盖升级到 code 3，无需卸载。
- 真机 HUAWEI Pura 70 Ultra 报告 Android 12 / API 31 兼容层，经真实数据线接收 **960 × 540** 原创校准卡。默认 USB 和英文，授权发现、新启动自动连接、双眼渲染、隐藏设置 / 返回恢复通过，USB 未手填 IP 或配对码。
- 中文在强制停止 / 重开后保留；切换语言会断开并要求显式重连。新进程启动进行了文档约定的一次 USB 自动尝试。FPS 模式的观察区间收到 **877 条真实传感器姿态消息**，未授权操作系统鼠标，假接收器保持为空。这不代表陀螺仪实际轴向或真实游戏控制已经验证。
- 真机测试发现华为差异：ADB 未提供可用 USB 路径。最终 Windows 实现通过原生 SetupAPI 枚举确认真实 USB 序列号，继续排除模拟器与网络 ADB。
- 同一手机还经 USB 接收真实 ASUS PA279 竖屏桌面，尺寸 **540 × 960**。Home 进入后台后主机断开，回到前台不会悄悄重连；整屏采集性能另行记录如下。
- 新截图展示此手机的 USB 接收，来源是原创校准卡而非游戏。手机观察到 **4–7 ms** ping 往返仅作连接诊断，**不是端到端视频延迟**。

最终 960 × 540 / 目标 60 FPS / JPEG 60 校准 USB 会话在 Windows 节奏修复后，连续 **60 个电脑发送样本均值 59.99 FPS（59.74–60.22）**，手机接收读数约 60 FPS。这是实际 USB 路径上的合成内容诊断，不是桌面采集成绩或端到端延迟基准。此前 Windows tick 等待的读数约在 32–64 FPS 间波动；其他内容 / 采集负担需要分别测量。

实际 ASUS 桌面 USB 会话使用原生 GDI 后端，输出 **540 × 960** 帧；**24 个电脑发送 FPS 样本均值 11.05，范围 8.2–12.11**。随后显示布局改变，布局保护停止产生新帧，没有发出操作系统鼠标输入。这说明当次实际采集 / USB 路径与异常停止行为，不代表桌面可保证 60 FPS，也没有测量端到端视频延迟。

按用户要求，CS2 和 Discord 保持运行。观察到 GPU 3D 利用率接近满载，Discord 约占用一个 CPU 核心。这些只是同时运行负载的观察，不是受控性能对比，也不能确定哪个应用造成采集限制。本地原生后端 / MSS 计时试验同样在忙碌桌面运行，不把读数作为受控后端性能基准。

新 EXE 在实际 ASUS 显示器以英文启动并识别 USB。全新偏好默认选中 960 / 60 / 60，已有采集设置保留为自定义。桌面分辨率 / 缩放布局变化期间，界面预览自动化工具随后无法捕获窗口，因此不把后续 GUI 操作计为通过。

上面的 API 23 / 36 结果保留为历史证据，不代表重新覆盖 v0.2.0 的所有改动。完整 iOS 验证结果仍待定，不记为已经通过。真实 iPhone USB 仍未验证。

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

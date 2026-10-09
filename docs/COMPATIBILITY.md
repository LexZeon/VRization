# 🧭 Compatibility / 兼容性

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

Support targets and observed tests are separate. Passing an emulator test does not establish support for every OS version, ARM phone, vendor derivative or VR viewer.

### Targets

| Component | Target and requirements | Evidence / limits |
| --- | --- | --- |
| Windows host | Windows 10 / 11 x64; Microsoft Visual C++ v14 x64 runtime | Local physical machine runs Windows 11 build 26200. Windows 10 has not been physically tested. |
| Android client | Android 6.0 / API 23 or later, OpenGL ES 2.0, APK-compatible system | Java application with no bundled ABI-specific native library. v0.2.0 was installed and streamed over USB on a physical HUAWEI Pura 70 Ultra reporting Android 12 / API 31 compatibility; other derivatives require device testing. |
| iOS client | iOS / iPadOS 15+, landscape, Metal, local-network permission | Native Swift / UIKit client. Xcode on macOS builds and signs it; the Windows host serves both phone platforms. See [iOS guide](IOS.md) for exact installation / test limits. |
| Google services | Not required | First-release API 23 emulator uses no Google services. |
| Full screen | Network and graphics support | No rotation sensor required; verified on the sensor-less API 23 emulator. |
| Cinema / FPS | Compatible Android rotation sensor or iOS Core Motion | Real gyro axes, drift and headset tracking still need a physical phone. |
| FPS game input | Game accepts ordinary relative mouse input; PC authorization and F8 | Real FPS games and anti-cheat / raw-input combinations remain unverified. |

### Interface language

All applications offer **English / 简体中文**; English is the default and the choice is saved locally. The PC stores language in `language.json` independently of `preferences.json`. Changing the PC language keeps streaming active but disarms mouse control. Changing the phone language disconnects the stream and requires reconnecting (Android recreates its Activity; iOS rebuilds its controls). Language choice is independent on each device.

### What has actually been checked

The first release and final v0.1.1 APK were installed and streamed on a Google-free Android 6.0 / API 23 emulator. The same-signer upgrade retained settings; English remained the default even on a Chinese system, and both language choices persisted after restart. Both-eye rendering, hidden controls / Back recovery, boundary sliders, no-sensor cinema / FPS fallback, background disconnect and explicit reconnect passed. One transient `EGL_BAD_SURFACE` occurred during old language-popup recreation; subsequent rendering was normal. See the exact observation in [validation](VALIDATION.md).

A physical ASUS portrait display was captured from Windows 11; 2160 × 3840 became 720 × 1280 at longest-edge limit 1280. The desktop language controls were tested on the actual ASUS display: English default, Chinese selection, persistence after reopen, switching during streaming, and scrolling at 1060 × 680.

The final v0.1.1 APK also upgraded the Google-free Android 16 / API 36 AOSP emulator from v0.1.0, started with English UI, retained Chinese after force-stop / reopen, and switched back to English. It received the original 1280 × 720 card over a real WebSocket and rendered both eyes. Host-selected cinema / FPS modes remained selected; sensor-service Game Rotation Vector registration and full-screen unregistration were observed. Hidden controls / Back recovery, disconnecting on background, and explicit reconnection after language changes, background or server close `1001` passed. No AndroidRuntime / OpenGLRenderer / libEGL errors were observed. These are emulator observations, not physical-gyro, real-game or latency tests. See [validation](VALIDATION.md).

### v0.2.0 physical Android USB check

A HUAWEI Pura 70 Ultra reporting Android 12 / API 31 compatibility upgraded in place from the previous local APK to v0.2.0 (code 3). English and USB were the defaults. Authorized USB host discovery, automatic connection on a fresh launch, reception of the original 960 × 540 calibration stream and both-eye rendering passed. The phone transmitted rotation poses in FPS mode; the test used a fake input sink, with no operating-system mouse output. Chinese persisted after force-stop / reopen, and switching language disconnected the stream as designed. This does not establish its marketing OS version, every Huawei model, gyro axes or headset comfort. See [the complete validation record](VALIDATION.md).

USB support requires official Platform Tools / Android debugging authorization, or Apple's Windows device software / Trust for iOS. Neither driver stack is bundled. The iOS relay is tested with simulated USB devices; there is no real-iPhone USB result. See [USB prerequisites](USB.md).

### Still unverified

Other Android phones / derivatives, physical iPhones / iPads including the oldest target iOS 15, actual viewer optics, gyro-axis accuracy / drift / comfort, real FPS games, Windows 10 hardware and measured end-to-end video latency. Windows ARM64 / x86 native builds are not supplied. Please submit device results with version, settings and measurement method through [contributing](../CONTRIBUTING.md).

---

<!-- vrization:chinese -->
## 简体中文

支持目标与已经观察到的测试结果分开记录。模拟器通过不代表全部系统版本、ARM 手机、厂商衍生系统与 VR 盒子都兼容。

### 支持目标

| 部分 | 目标与要求 | 已有证据 / 限制 |
| --- | --- | --- |
| Windows 电脑端 | Windows 10 / 11 x64；Microsoft Visual C++ v14 x64 运行库 | 本机实际运行 Windows 11 build 26200；未在 Windows 10 实机测试。 |
| Android 手机端 | Android 6.0 / API 23+、OpenGL ES 2.0、可安装 APK 的兼容系统 | Java 应用，不附带 ABI 专用原生库。v0.2.0 已在报告 Android 12 / API 31 兼容层的 HUAWEI Pura 70 Ultra 真机安装并经 USB 串流；其他衍生系统需分别实测。 |
| iOS 手机端 | iOS / iPadOS 15+、横屏、Metal、本地网络权限 | 原生 Swift / UIKit 客户端，macOS 用 Xcode 构建和签名；Windows 主机同时服务两类手机。安装与实测边界见 [iOS 教程](IOS.md)。 |
| Google 服务 | 不需要 | 首版 API 23 模拟器不含 Google 服务。 |
| 全屏模式 | 网络与图形支持 | 无需旋转传感器，已在无传感器 API 23 模拟器检查。 |
| 大屏幕 / FPS | 兼容 Android 旋转传感器或 iOS Core Motion | 真实轴向、漂移与头部追踪仍需手机实测。 |
| FPS 游戏输入 | 游戏接受普通相对鼠标；电脑主动授权与 F8 | 真实 FPS、反作弊与原始输入组合尚未验证。 |

### 界面语言

所有客户端可选 **English / 简体中文**，默认英文，分别在本地保存。电脑语言存于 `language.json`，独立于 `preferences.json`。电脑切换语言保持串流但解除鼠标授权；手机切换语言断开串流，需要重新连接（Android 重建 Activity，iOS 重建控件）。各设备语言独立选择。

### 实际检查范围

首版与最终 v0.1.1 APK 均在无 Google 的 Android 6.0 / API 23 模拟器安装并串流。同签名升级保留设置，系统中文时仍默认英文，两种语言重开均保留。双眼显示、隐藏 / 返回恢复、边界滑块、无传感器大屏幕 / FPS 回退、后台断开与显式重连通过。旧语言弹窗重建期间有一次临时 `EGL_BAD_SURFACE`，随后渲染正常，具体见 [验证记录](VALIDATION.md)。

Windows 11 采集真实 ASUS 竖屏，2160 × 3840 在最长边 1280 时输出 720 × 1280。电脑语言界面已在真实 ASUS 显示器检查默认英文、切换中文、重开后保留、串流中切换及 1060 × 680 小窗滚动。

最终 v0.1.1 APK 已在无 Google 的 Android 16 / API 36 AOSP 模拟器从 v0.1.0 升级，默认英文，切中文后强制停止再开仍保留中文，可切回英文。真实 WebSocket 接收 1280 × 720 原创卡并显示双眼画面。电脑切大屏幕 / FPS 后客户端保留对应模式，传感器服务注册 Game Rotation Vector、全屏时注销；隐藏 / 返回恢复、后台断开，以及语言切换 / 后台 / 服务端 `1001` 关闭后的显式重连均通过。未观察到 AndroidRuntime / OpenGLRenderer / libEGL 错误。这些是模拟器观察，不是实机陀螺仪、真实游戏或延迟测试。详见 [验证记录](VALIDATION.md)。

### v0.2.0 Android 真机 USB 检查

报告 Android 12 / API 31 兼容层的 HUAWEI Pura 70 Ultra 从此前本地 APK 覆盖升级到 v0.2.0（code 3）。默认英文和 USB，授权后的 USB 服务发现、新启动自动连接、960 × 540 原创校准串流接收与双眼渲染通过。FPS 模式手机可发送旋转姿态；测试使用假输入接收器，没有操作系统鼠标输出。中文在强制停止 / 重开后保留，切换语言按设计断开串流。这不推断其营销系统版本，也不代表全部华为型号、陀螺仪轴向或盒子舒适度。详见 [完整验证记录](VALIDATION.md)。

USB 需要官方 Platform Tools / Android 调试授权，或 iOS 的 Apple Windows 设备软件 / 信任，均不在包内附带。iOS 中继通过模拟 USB 设备测试，尚无 iPhone 真机 USB 结果。详见 [USB 前提](USB.md)。

### 仍未验证

其他 Android 手机 / 衍生系统、真实 iPhone / iPad（包括最低目标 iOS 15）、真实盒子镜片、陀螺仪轴向 / 漂移 / 舒适度、真实 FPS 游戏、Windows 10 硬件及端到端视频延迟测量。未提供 Windows ARM64 / x86 原生构建。欢迎按 [贡献说明](../CONTRIBUTING.md) 提交版本、设置与测量方法完整的设备结果。

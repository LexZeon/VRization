# 🚀 Quick start / 快速开始

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

v0.2.0-alpha sends one Windows desktop / rectangular region to both eyes of an Android or iOS phone viewer. **USB is the default**; trusted LAN is optional. The image is the same 2D source in both eyes, with no audio or native game stereo. English is the default software language; choose Simplified Chinese independently on each device.

### 1. Get the applications

Download from [GitHub Releases](https://github.com/LexZeon/VRization/releases) using [the download guide](DOWNLOADS.md). Completely extract the Windows x64 ZIP, then run `VRization-Host.exe`. Windows 10 / 11 x64 is the target; local desktop evidence is Windows 11. Keep the included documentation / license files. If Windows reports a missing Visual C++ runtime, follow [build prerequisites](BUILD.md) for Microsoft's official v14 x64 installer.

- **Android:** install the APK on an Android 6.0 / API 23+ device with OpenGL ES 2.0 and APK installation support. No Google services are required; OEM derivatives need their own validation.
- **iPhone / iPad:** the app targets iOS / iPadOS 15+ with Metal. Follow [Xcode build and signing](IOS.md) on a Mac. The source ZIP needs your signing; the Simulator ZIP cannot be installed on a phone. There is no universal unsigned IPA.

### 2. Connect by USB

On Windows select the intended display / region, leave automatic USB detection enabled and click **Start streaming**. A cable connection never starts capture or mouse control by itself.

- **Android:** install Google's official Platform Tools, enable USB debugging, connect a data cable, unlock the phone and approve this computer. Select the official SDK's `adb.exe` in PC USB settings if needed. With several Android USB devices, select the intended one. Open the app with **USB cable · default** selected; if its first attempt has ended, tap **Detect USB and connect**. No IP or code entry is needed.
- **iPhone / iPad:** install official Apple Devices / Apple Mobile Device support on Windows. Connect one device, unlock it and **Trust This Computer**. Open the signed app with USB selected. Its initial foreground attempt waits for the PC; use **Connect** to retry. No hotspot or USB tethering is used.

Detailed menus, prerequisites and port-conflict recovery are in [the USB guide](USB.md). Huawei Android hardware evidence is separate from the current iOS simulated-usbmux / native-Simulator checks; a real iPhone USB connection remains unverified. See [compatibility](COMPATIBILITY.md) and [validation](VALIDATION.md).

### 3. Fit the image and choose a mode

Start with **Full screen**, confirm both eye images are complete, then adjust scale, horizontal / vertical offset and eye spacing before placing the phone in the viewer. Long-press the picture to restore hidden controls; Android also supports Back. Double-tap to recenter.

| Mode | Behavior |
| --- | --- |
| Full screen | Fixed side-by-side images; no gyro needed. |
| Cinema | Rotation-tracked virtual screen. Recenter after placing the phone. |
| FPS game | Fixed side-by-side view, sending phone rotation to the host. PC authorization is required for mouse control. |

For FPS, select the mode with a working rotation sensor, enable **Allow phone head tracking to control the game mouse** on the PC, then switch to the game within five seconds. **F8 stops control.** Disconnects, stale pose and focus changes also stop it; re-arm manually. Games using raw input or protection may ignore system mouse input. Actual game / headset comfort is not established by the automated checks.

### 4. Choose a performance profile

In **Stream → Performance profile**, use low latency `960 / 60 FPS / Q60`, stable `1280 / 30 / Q65`, quality `1920 / 30 / Q80` or custom. New users default to low latency; previous saved choices stay effective. The size limits the longest edge and preserves aspect ratio. Target FPS is not a guarantee. Received FPS and link ping RTT help troubleshooting; neither is end-to-end video latency.

### Alternative: trusted LAN

Choose **LAN / Wi-Fi · manual pairing** on the phone. Join the same trusted network, start the PC stream, enter its displayed LAN host, port (default `8765`) and current six-digit code, keeping leading zeroes. Enter a host only, without a URL or path. Allow only the needed private-network firewall access; iOS may also require Local Network permission. `ws://` is unencrypted; do not expose the port publicly. USB does not require an inbound LAN firewall rule.

After backgrounding, changing phone language or disconnecting, use the connection button explicitly. The phone does not silently resume the session. Desktop language changes keep streaming running but stop mouse authorization. Finish by stopping PC streaming. Read [security](../SECURITY.md) before sharing private content.

---

<!-- vrization:chinese -->
## 简体中文

v0.2.0-alpha 把 Windows 桌面 / 矩形区域发给 Android 或 iOS 手机盒子的两眼。**默认 USB**，可信局域网为可选项。两眼是相同二维源画面，没有声音或原生游戏立体深度。软件默认英文，每台设备可独立选择简体中文。

### 1. 安装应用

按 [下载指南](DOWNLOADS.md) 从 [GitHub Releases](https://github.com/LexZeon/VRization/releases) 下载。完整解压 Windows x64 ZIP，再运行 `VRization-Host.exe`。目标为 Windows 10 / 11 x64，本地桌面证据来自 Windows 11；保留附带文档与许可。若 Windows 提示缺少 Visual C++ 运行库，按 [构建前提](BUILD.md) 安装 Microsoft 官方 v14 x64 运行库。

- **Android：**安装 APK，最低 Android 6.0 / API 23、OpenGL ES 2.0，并能安装 APK。不要求 Google 服务，OEM 衍生系统需独立验证。
- **iPhone / iPad：**目标 iOS / iPadOS 15+、Metal，按 [Xcode 构建与签名](IOS.md) 在 Mac 上安装。源码 ZIP 需要自己的签名，模拟器 ZIP 不能安装到手机；没有通用免签 IPA。

### 2. USB 连接

Windows 选择目标显示器 / 选区，保持自动检测 USB，点击**开始串流**。插线不会自动开始采集或授权鼠标。

- **Android：**安装 Google 官方 Platform Tools，启用 USB 调试，接数据线、解锁并授权此电脑。需要时在电脑 USB 设置选择官方 SDK 的 `adb.exe`；多台 Android USB 设备时明确选择目标。手机保持“**USB 数据线 · 默认**”；首次尝试结束后点“**检测 USB 并连接**”，无需填写 IP / 配对码。
- **iPhone / iPad：**Windows 安装官方 Apple Devices / Apple Mobile Device 支持，只接一台设备，解锁并**信任此电脑**。前台打开已签名应用并选 USB；首次会等待电脑，点 **Connect / 连接**可重试。不使用热点或 USB 网络共享。

具体菜单、前提和端口冲突排查见 [USB 教程](USB.md)。华为 Android 硬件证据与现有 iOS 模拟 usbmux / 原生模拟器检查分开；真实 iPhone USB 仍未验证。参见 [兼容性](COMPATIBILITY.md)、[验证记录](VALIDATION.md)。

### 3. 适配画面与模式

先用**全屏**确认两眼画面完整，再调整缩放、水平 / 垂直偏移和双眼间距，随后装入盒子。长按画面恢复隐藏操作区，Android 也支持返回键；双击回正。

| 模式 | 行为 |
| --- | --- |
| 全屏 | 固定双眼图像，不需要陀螺仪。 |
| 大屏幕 | 随旋转观察虚拟屏幕，装入盒子后回正。 |
| FPS 游戏 | 固定双眼图像，向主机发送手机旋转；控制鼠标需电脑主动授权。 |

FPS 使用可用旋转传感器，在手机选择模式，在电脑勾选“**允许手机陀螺仪控制当前游戏鼠标**”，五秒内切换到游戏。**F8 停止控制**；断线、姿态超时和焦点变化也会停止，需手动重新授权。原始输入或游戏保护可能忽略系统鼠标。自动检查不证明真实游戏 / 盒子舒适度已经通过。

### 4. 性能预设

在“**串流设置 → 性能预设**”选择低延迟 `960 / 60 FPS / 质量 60`、稳定 `1280 / 30 / 65`、画质 `1920 / 30 / 80` 或自定义。新用户默认低延迟，已有保存选择继续生效。尺寸限制最长边并保持比例，目标帧率不是保证。接收帧率与链路 ping RTT 用于排查，均不是端到端视频延迟。

### 可选：可信局域网

手机选择“**局域网 / Wi-Fi · 手动配对**”。两端同一可信网络，电脑开始串流，手机填显示的电脑局域网主机、端口（默认 `8765`）及六位码，保留开头的零；主机栏不填 URL 或路径。防火墙只开放必要的专用网络访问，iOS 可能需要允许本地网络。`ws://` 未加密，不向公网暴露；USB 不需要开放局域网入站防火墙端口。

进入后台、手机切语言或断线后须主动点连接，不会悄悄恢复。电脑切语言会保持串流，但停止鼠标授权。使用结束停止电脑串流，共享私密内容前阅读 [安全说明](../SECURITY.md)。

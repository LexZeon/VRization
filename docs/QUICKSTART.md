# 🚀 Quick start / 快速开始

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

VRization sends one Windows desktop / rectangular region to both eyes of an Android or iOS phone viewer. **USB is the default**; trusted LAN is optional. The image is the same 2D source in both eyes, with no audio or native game stereo. English is the default software language; choose Simplified Chinese independently on each device.

### 1. Get the applications

Download from [GitHub Releases](https://github.com/LexZeon/VRization/releases) using [the download guide](DOWNLOADS.md). Completely extract the Windows x64 ZIP, then run `VRization-Host.exe`. Windows 10 / 11 x64 is the target; local desktop evidence is Windows 11. Keep the included documentation / license files. If Windows reports a missing Visual C++ runtime, follow [build prerequisites](BUILD.md) for Microsoft's official v14 x64 installer.

- **Android:** install the APK on an Android 6.0 / API 23+ device with OpenGL ES 2.0 and APK installation support. No Google services are required; OEM derivatives need their own validation.
- **iPhone / iPad:** the app targets iOS / iPadOS 15+ with Metal. Follow [Xcode build and signing](IOS.md) on a Mac. The source ZIP needs your signing; the Simulator ZIP cannot be installed on a phone. There is no universal unsigned IPA.

### 2. Connect by USB

On Windows select the intended display / region and leave automatic USB detection enabled. With both apps open, click **Connect / Start streaming** on the PC **or Connect on the phone**. Either explicit action coordinates streaming; detection or plugging in a cable alone never starts capture or mouse control.

- **Android:** install Google's official Platform Tools, enable USB debugging, connect a data cable, unlock the phone and approve this computer. Select the official SDK's `adb.exe` in PC USB settings if needed. With several Android USB devices, select the intended one. Open the app with **USB cable · default** selected; tap **Detect USB and connect** to start explicitly, including during automatic waiting. No IP or code entry is needed.
- **iPhone / iPad:** install official Apple Devices / Apple Mobile Device support on Windows. Connect one device, unlock it and **Trust This Computer**. Open the signed app with USB selected. It keeps a foreground control listener ready; click **Connect** on either endpoint to begin video. Keep the app foregrounded; Windows cannot launch a background iOS application. No hotspot or USB tethering is used.

Detailed menus, prerequisites and port-conflict recovery are in [the USB guide](USB.md). Huawei Android hardware evidence is separate from the current iOS simulated-usbmux / native-Simulator checks; a real iPhone USB connection remains unverified. See [compatibility](COMPATIBILITY.md) and [validation](VALIDATION.md).

### 3. Fit the image and choose a mode

Start with **Full screen**, confirm both eye images are complete, then adjust scale, horizontal / vertical offset and eye spacing before placing the phone in the viewer. Long-press the picture to restore hidden controls; Android also supports Back. Double-tap to recenter.

| Mode | Behavior |
| --- | --- |
| Full screen | Fixed side-by-side images; no gyro needed. |
| Cinema | Rotation-tracked virtual screen. Recenter after placing the phone. |
| First person | Fixed side-by-side view, sending phone rotation to the host. The Windows gyro mouse preference defaults to enabled; F8 pauses it and PC Resume clears that pause. |

Windows enables First-person gyro mouse control by default. A validated connection, First-person mode, available capture and fresh valid rotation data are required; the first pose sets a baseline before movement. Control works on the desktop, ordinary applications, games and VRization's own window regardless of foreground-window changes, with no five-second target-window deadline. A temporary sensor gap stops output and rebaselines on fresh poses before continuing. **F8**, the PC emergency stop, editor entry, PC Reset all settings, capture-region selection, capture/input failure and stream Stop latch a pause: late poses, settings and reconnecting cannot clear it. Click **Resume gyro control** on the PC, or explicitly turn the control checkbox off and on, to resume. Full screen and Cinema stop mouse output. The PC saves only the enabled preference, never the live armed state or pause latch. Games using raw input or protection may ignore system mouse input. Automated checks do not establish actual game or headset comfort.

### 4. Choose a performance profile

In **Stream → Performance profile**, use low latency `640 / 60 FPS / Q45`, stable `640 / 30 / Q50`, quality `960 / 30 / Q60` or custom. New users default to low latency; previous saved choices stay effective. The size limits the longest edge and preserves aspect ratio. The Windows GPU backend crops, rotates and scales before smaller readback; explicitly unsupported initial capture can use the same selected rectangle through GDI / MSS. Target FPS is not a guarantee. Received FPS and link ping RTT help troubleshooting; neither is end-to-end video latency. See [measured performance and delay](PERFORMANCE.md).

### Alternative: trusted LAN

Choose **LAN / Wi-Fi · manual pairing** on the phone. Join the same trusted network, start the PC stream, enter its displayed LAN host, port (default `8765`) and current six-digit code, keeping leading zeroes. Enter a host only, without a URL or path. Allow only the needed private-network firewall access; iOS may also require Local Network permission. `ws://` is unencrypted; do not expose the port publicly. USB does not require an inbound LAN firewall rule.

After backgrounding, changing phone language or disconnecting, use the connection button explicitly. The phone does not silently resume the session. Desktop language changes keep streaming running and retain the existing input preference/pause latch. Finish by stopping PC streaming. Read [security](../SECURITY.md) before sharing private content.

### 5. Edit and keep your headset fit

Open the editor from the first settings action: Windows **Headset editor → Open visual headset editor**, Android **Fit headset visually**, or iOS **Visual headset fit editor**. On all three, left-eye left / right-eye right widens the linked spacing, and left-eye right / right-eye left narrows it. Smaller images can move inward until their inner edges meet; shared X remains while space allows, then recenters. Vertical motion stays normal, and proportional corner resizing obeys the same seam limit. Update both ends to v0.3 for signed separation; only flat, undistorted display has this contact guarantee. Then choose **Save** or **Discard**; the draft preview sends no settings, and phone entry pauses new poses and sends disarm-only metadata. A connected Save synchronizes through the validated host and retains the committed settings on both sides. Offline Save stays local until a valid connection. **Reset all settings** returns product defaults; Windows preserves the intended capture display / region and ADB tool path, while phone reset disconnects without immediately reconnecting. A fresh phone-app launch resumes normal initial USB discovery / listening. Follow [the complete editor guide](EDITING.md) for restoration priority, geometry, reset scope and safety boundaries.

### 🎯 Tune First-person stabilization

Use the PC or phone **First-person stabilization** slider. Its default 0% keeps the previous input behavior; increase it gradually to smooth small unwanted movements and lower it if turns feel delayed. Mouse sensitivity is separate. The Windows host filters once; the phone keeps sending ordinary poses. Connected values synchronize and committed phone values persist offline. Older hosts cannot apply this setting, so use v0.3.2 on both ends. Read [the stabilization guide](STABILIZATION.md).

The complete Windows ZIP includes a launcher and needs no Python or development tools to run the app. Android USB still needs separately obtained official Platform Tools: use the PC USB controls to open Google's download page and import the downloaded tools ZIP, or select an installed official `adb.exe`. Drivers and Google's acceptance steps remain separate. See [USB setup](USB.md).

---

<!-- vrization:chinese -->
## 简体中文

VRization 把 Windows 桌面 / 矩形区域发给 Android 或 iOS 手机盒子的两眼。**默认 USB**，可信局域网为可选项。两眼是相同二维源画面，没有声音或原生游戏立体深度。软件默认英文，每台设备可独立选择简体中文。

### 1. 安装应用

按 [下载指南](DOWNLOADS.md) 从 [GitHub Releases](https://github.com/LexZeon/VRization/releases) 下载。完整解压 Windows x64 ZIP，再运行 `VRization-Host.exe`。目标为 Windows 10 / 11 x64，本地桌面证据来自 Windows 11；保留附带文档与许可。若 Windows 提示缺少 Visual C++ 运行库，按 [构建前提](BUILD.md) 安装 Microsoft 官方 v14 x64 运行库。

- **Android：**安装 APK，最低 Android 6.0 / API 23、OpenGL ES 2.0，并能安装 APK。不要求 Google 服务，OEM 衍生系统需独立验证。
- **iPhone / iPad：**目标 iOS / iPadOS 15+、Metal，按 [Xcode 构建与签名](IOS.md) 在 Mac 上安装。源码 ZIP 需要自己的签名，模拟器 ZIP 不能安装到手机；没有通用免签 IPA。

### 2. USB 连接

Windows 选择目标显示器 / 选区，保持自动检测 USB。两端应用都打开后，点击电脑“**连接 / 开始串流**”或手机“**连接**”，任一主动操作都可协调开始串流；单纯检测或插线不会开始采集或授权鼠标。

- **Android：**安装 Google 官方 Platform Tools，启用 USB 调试，接数据线、解锁并授权此电脑。需要时在电脑 USB 设置选择官方 SDK 的 `adb.exe`；多台 Android USB 设备时明确选择目标。手机保持“**USB 数据线 · 默认**”；点“**检测 USB 并连接**”主动开始，自动等待期间也能点，无需填写 IP / 配对码。
- **iPhone / iPad：**Windows 安装官方 Apple Devices / Apple Mobile Device 支持，只接一台设备，解锁并**信任此电脑**。前台打开已签名应用并选 USB，会保留前台控制监听；任一端点“**连接**”开始视频。请保持手机应用在前台，Windows 不能启动后台 iOS 应用；不使用热点或 USB 网络共享。

具体菜单、前提和端口冲突排查见 [USB 教程](USB.md)。华为 Android 硬件证据与现有 iOS 模拟 usbmux / 原生模拟器检查分开；真实 iPhone USB 仍未验证。参见 [兼容性](COMPATIBILITY.md)、[验证记录](VALIDATION.md)。

### 3. 适配画面与模式

先用**全屏**确认两眼画面完整，再调整缩放、水平 / 垂直偏移和双眼间距，随后装入盒子。长按画面恢复隐藏操作区，Android 也支持返回键；双击回正。

| 模式 | 行为 |
| --- | --- |
| 全屏 | 固定双眼图像，不需要陀螺仪。 |
| 大屏幕 | 随旋转观察虚拟屏幕，装入盒子后回正。 |
| 第一人称 | 固定双眼图像，向主机发送手机旋转；Windows 默认启用陀螺仪鼠标；F8 锁定暂停，电脑恢复按钮解除。 |

Windows 默认开启第一人称陀螺仪鼠标控制。必须有通过校验的连接、第一人称模式、可用采集与新的合法旋转姿态；首条姿态先建立基准，再产生移动。桌面、普通应用、游戏和 VRization 自身窗口均可控制，不受前台窗口切换影响，也不要求五秒内切到目标窗口。传感器短暂间断时停止输出，新姿态先重建基准再继续。**F8**、电脑紧急停止、进入编辑器、电脑重置全部设置、选择采集区域、采集／输入故障和停止串流会锁定暂停；迟到姿态、设置与重连都不能解除。需要在电脑点“**恢复陀螺仪控制**”，或主动关闭再开启控制复选框。全屏和大屏幕停止鼠标输出。电脑只保存启用偏好，不保存实时授权状态或暂停锁。 原始输入或游戏保护可能忽略系统鼠标，自动检查不证明真实游戏／盒子舒适度。

### 4. 性能预设

在“**串流设置 → 性能预设**”选择低延迟 `640 / 60 FPS / 质量 45`、稳定 `640 / 30 / 50`、画质 `960 / 30 / 60` 或自定义。新用户默认低延迟，已有保存选择继续生效。尺寸限制最长边并保持比例；Windows GPU 后端先裁切、旋转和缩小，再回读较少像素，初始化时明确不支持的采集可对同一选区采用 GDI / MSS。目标帧率不是保证，接收帧率与链路 ping RTT 用于排查，均不是端到端视频延迟。详见 [实测性能与延迟](PERFORMANCE.md)。

### 可选：可信局域网

手机选择“**局域网 / Wi-Fi · 手动配对**”。两端同一可信网络，电脑开始串流，手机填显示的电脑局域网主机、端口（默认 `8765`）及六位码，保留开头的零；主机栏不填 URL 或路径。防火墙只开放必要的专用网络访问，iOS 可能需要允许本地网络。`ws://` 未加密，不向公网暴露；USB 不需要开放局域网入站防火墙端口。

进入后台、手机切语言或断线后须主动点连接，不会悄悄恢复。电脑切语言保持串流与原输入偏好／暂停锁。使用结束停止电脑串流，共享私密内容前阅读 [安全说明](../SECURITY.md)。


### 5. 编辑并保存盒子适配

从设置首位打开编辑器：Windows **画面编辑 → 打开可视画面编辑器**、Android **可视化适配 VR 盒子**、iOS **可视化盒子画面编辑器**。三端左眼向左 / 右眼向右都拉开联动间距，左眼向右 / 右眼向左收拢；缩小后仍可向内拖到内边相接，空间允许时保留共用 X，接近中缝时居中；竖向正常，等比角点缩放也遵守接缝限位。负间距需两端都更新至 v0.3，相接保证仅用于无畸变平面画面。之后选**保存**或放弃 / 弃用；草稿预览不发设置，手机进入时暂停新姿态并发送仅解除授权的元数据。已连接的保存通过合法主机同步，两端保留已提交配置；离线保存先留在本地，等合法连接。**重置全部设置**恢复产品默认；Windows 保留采集显示器 / 选区与 ADB 工具路径，手机重置后当前界面断线且不自动重连，全新启动恢复正常初次 USB 发现 / 监听。恢复优先规则、几何、重置范围与输入边界见 [完整编辑教程](EDITING.md)。

### 🎯 调整 第一人称防抖

使用电脑或手机的“**第一人称防抖强度**”滑块。默认 0% 保留此前输入；细小非自主移动明显时逐步提高，转头跟随迟缓时降低。鼠标灵敏度单独调整。Windows 主机只滤波一次，手机仍发送普通姿态。连接时值同步，手机已提交值也离线保存。旧电脑端无法应用此设置，请把两端都更新至 v0.3.2，见 [防抖教程](STABILIZATION.md)。

完整 Windows ZIP 包含启动器，运行应用无需 Python 或开发环境；Android USB 仍需另行获取官方 Platform Tools。在电脑 USB 控件打开 Google 下载页，按其步骤下载后导入工具 ZIP，或选择已安装的官方 `adb.exe`。驱动与 Google 的条款确认仍是独立步骤，见 [USB 设置](USB.md)。

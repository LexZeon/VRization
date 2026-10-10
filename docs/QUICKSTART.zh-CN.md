# 🚀 Quick-start link and illustrated reference / 快速入口与图示参考

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

This older tutorial URL is preserved for existing links. **Start with the current [quick start](QUICKSTART.md)**, then use [USB setup](USB.md) for platform-specific installation and authorization. Windows, Android and iOS now prefer USB; LAN is an explicit alternative.

### USB first

1. Extract and run the Windows 10 / 11 x64 host, choose your intended display / region, and click **Start streaming**. Windows 11 is the locally tested desktop environment; Windows 10 is a support target.
2. **Android:** install the APK, install Google's official Platform Tools, enable USB debugging, connect a data cable and approve this PC. If needed choose the SDK's `adb.exe` in PC USB settings. Keep USB selected on the phone and use **Detect USB and connect** after an unsuccessful initial attempt.
3. **iPhone / iPad:** install a signed iOS 15+ app using [the Xcode guide](IOS.md). Install Apple Devices / Apple Mobile Device support on Windows, connect one phone, unlock it and **Trust This Computer**. Keep the signed app foreground with USB selected, using **Connect** to wait again if necessary. The Simulator ZIP cannot be installed on a phone.
4. USB does not need an IP, six-digit code, hotspot or shared Wi-Fi. Use explicit Connect on either endpoint to start streaming; Windows defaults First-person gyro mouse control to enabled. **F8 stops control**. Backgrounding, phone language changes and disconnects require explicit reconnection.

Profiles use longest edge / target FPS / JPEG quality: low latency `640 / 60 / Q45` for new users, stable `640 / 30 / Q50`, quality `960 / 30 / Q60`, or custom. Previously saved capture settings are retained. Windows prefers original GPU crop / rotation / scaling before smaller readback, with compatible same-region GDI / MSS paths. Received FPS and ping RTT are not end-to-end video latency; see [performance](PERFORMANCE.md). Physical Huawei Android evidence and iOS simulated-usbmux / Simulator evidence are separate; real iPhone USB, actual FPS games and viewer optics remain unverified. Consult [validation](VALIDATION.md) for concrete results.

### Illustrated controls

- [Windows host](images/desktop.png): choose the current display name rather than copying the example's monitor number.
- [Android connection screen](images/android.png), [viewer-fit controls](images/android-settings.png), and [hidden-controls side-by-side view](images/android-vr.png): these Android illustrations document the earlier v0.1.1 Google-free API 23 emulator / original calibration-card session. They are UI references, not current USB button layouts or hardware-performance proof.

Start in **Full screen**. Shrink scale and adjust offsets / eye spacing for your viewer, then try **Cinema** with recentering. First-person mode needs a rotation sensor and the enabled PC preference. It controls the desktop, ordinary applications, games and VRization's own window across foreground changes; F8 requires the PC Resume action. Long-press restores hidden controls; Android also supports Back. Double-tap recenters. Both eyes show the same 2D source, without native game stereo or audio.

### LAN and troubleshooting

For manual LAN, explicitly choose LAN on the phone, join the same trusted network, enter the PC's displayed LAN host / port / current six-digit code, preserving leading zeroes. Do not enter a URL in the host field. The historical emulator address `10.0.2.2` is not a physical phone's PC address. Phone loopback `127.0.0.1:18765` is used only through the configured Android USB reverse tunnel.

Allow necessary private-network firewall access for LAN only; do not disable the firewall. For missing runtime DLLs, use Microsoft's official installer linked in [build prerequisites](BUILD.md). APK debug-signature conflicts may require uninstalling the older app, which clears its settings. USB port conflicts must be resolved without stealing another program's mapping. See [USB troubleshooting](USB.md), [compatibility](COMPATIBILITY.md), [security](../SECURITY.md) and [contributing](../CONTRIBUTING.md).

### Visual fit in v0.3

The first settings action is the headset-fit editor, with a local preview and explicit Save / Discard. Phones retain committed profiles; Reset restores defaults without granting input permission. See [the editor guide](EDITING.md).

### Current first-person controls

The mode is now named **First person**; its wire identifier stays `fps`. v0.3.2 adds a stabilization slider defaulting to 0%, with host-only filtering and normal sync / persistence. Stronger smoothing may add following lag. Update both apps for this feature and read [stabilization](STABILIZATION.md); the earlier pictured UI retains its original labels. Windows runs without Python; official USB tools remain a separate manual download / import in [USB setup](USB.md).

---

<!-- vrization:chinese -->
## 简体中文

保留此旧教程地址以兼容已有链接。**请先阅读最新 [快速开始](QUICKSTART.md)**，再按 [USB 教程](USB.md) 完成平台安装和授权。Windows、Android、iOS 现在都优先 USB，局域网为显式可选项。

### 优先 USB

1. 完整解压并运行 Windows 10 / 11 x64 主机，选目标显示器 / 选区，点击**开始串流**。本地桌面实测为 Windows 11，Windows 10 是支持目标。
2. **Android：**安装 APK 与 Google 官方 Platform Tools，开启 USB 调试，接数据线并授权此电脑。需要时在电脑 USB 设置选择 SDK 的 `adb.exe`。手机保持 USB，首次尝试未成功后点“**检测 USB 并连接**”。
3. **iPhone / iPad：**按 [Xcode 教程](IOS.md) 安装已签名 iOS 15+ 应用。Windows 安装 Apple Devices / Apple Mobile Device 支持，只接一台手机，解锁并**信任此电脑**。已签名应用保持前台 USB，需要时点 **Connect / 连接**重新等待；模拟器 ZIP 不能装到手机。
4. USB 不需要填写 IP、六位码、热点或同一 Wi-Fi。任一端主动连接可开始串流，Windows 默认启用第一人称陀螺仪鼠标，**F8 停止控制**。手机进入后台、切语言或断线后需显式重连。

预设按最长边 / 目标 FPS / JPEG 质量表示：新用户默认低延迟 `640 / 60 / Q45`，稳定 `640 / 30 / Q50`，画质 `960 / 30 / Q60`，或自定义；已有捕获设置继续保留。Windows 优先原创 GPU 裁切 / 旋转 / 缩放再回读小画面，保留同区域 GDI / MSS 兼容路径。接收帧率与 ping RTT 不是端到端视频延迟，见 [性能](PERFORMANCE.md)。华为 Android 真机与 iOS 模拟 usbmux / 模拟器证据分开；真实 iPhone USB、真实 FPS 游戏和盒子镜片仍未验证。具体结果见 [验证记录](VALIDATION.md)。

### 操作图示

- [Windows 主机](images/desktop-zh.png)：按自己当前显示器名称选择，不照抄示例编号。
- [Android 连接界面](images/android.png)、[盒子适配设置](images/android-settings.png)、[隐藏操作区的双眼画面](images/android-vr.png)：这些 Android 图示来自较早 v0.1.1、无 Google 的 API 23 模拟器及原创校准卡，只供界面参考，不表示当前 USB 按钮布局或真机性能。

先用**全屏**，缩小画面并调整偏移 / 眼间距，再试**大屏幕**并回正。第一人称需要旋转传感器与已启用电脑偏好；桌面、普通应用、游戏和 VRization 自身窗口都可控制，切换前台不解除；F8 后须电脑恢复。长按恢复隐藏操作区，Android 也支持返回键；双击回正。两眼同一二维源画面，没有原生游戏立体深度或声音。

### 局域网与排查

手动局域网需在手机显式选择 LAN，两端同一可信网络，填电脑显示的局域网主机 / 端口 / 当前六位码，保留开头的零；主机栏不填 URL。旧截图的 `10.0.2.2` 是模拟器专用地址，不是真实手机的电脑地址。手机回环 `127.0.0.1:18765` 仅通过已配置的 Android USB reverse 隧道使用。

只有局域网连接需要必要的专用网络防火墙放行，不要关闭防火墙。缺运行库 DLL 时用 [构建前提](BUILD.md) 中的 Microsoft 官方安装器。APK 调试签名冲突可能需卸载旧应用，这会清空其设置。USB 端口冲突不能靠抢占其他软件映射解决。参见 [USB 排查](USB.md)、[兼容性](COMPATIBILITY.md)、[安全说明](../SECURITY.md)、[贡献指南](../CONTRIBUTING.md)。


### v0.3 可视适配

设置第一个操作是盒子适配编辑器，本地预览后明确保存 / 放弃；手机保存已提交配置，重置恢复默认，不授予输入权限。见 [编辑教程](EDITING.md)。

### 当前第一人称控制

模式现称“**第一人称**”，协议标识仍为 `fps`。v0.3.2 防抖滑块默认 0%，只在主机滤波、正常同步保存；更强平滑可能增加跟随迟滞。使用时更新两端，见 [防抖](STABILIZATION.md)，较早截图保留对应原始名称。Windows 运行无需 Python，官方 USB 工具仍按 [USB 设置](USB.md) 另行手动下载 / 导入。

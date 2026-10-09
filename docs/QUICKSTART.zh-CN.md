# 🚀 Quick start / 上手教程

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

[Home](../README.md) · [Build from source](BUILD.md)

You need Windows 10 / 11 x64, an Android 6.0+ phone or a system with Android APK compatibility, and a phone VR viewer. Full-screen mode works without a gyroscope; cinema and FPS need a compatible rotation sensor. Google Play services are not required.

### 📦 1. Install matching versions

Download the Windows archive and Android APK from [GitHub Releases](https://github.com/LexZeon/VRization/releases). Extract the entire Windows archive before launching `VRization-Host.exe`.

The host requires Microsoft Visual C++ v14 x64 runtime; Microsoft runtime DLLs are not bundled. Most PCs already have it. If startup reports missing `VCRUNTIME140*.dll`, failure to load the Python DLL, or error 126, follow [Microsoft's official guide](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist/) and install the [current x64 runtime](https://aka.ms/vc14/vc_redist.x64.exe), then restart VRization. The first local build used MSVC 14.44 and requires that runtime version or later.

Transfer the APK to the phone and open it. If Android blocks installation from this source, allow the current file manager / browser to install it. Menus differ by vendor. Systems without an Android APK compatibility layer cannot install it directly.

The alpha APK uses a test signature, not a store release signature. Another computer or CI may generate a different debug key. A signature conflict requires uninstalling the previous app, which clears its saved settings. Do not publish this test APK as a store release.

### 📡 2. Put both devices on the same network

Use the same router. Prefer Ethernet for the PC and a strong 5 GHz / 6 GHz Wi-Fi connection for the phone. Start near the router. Guest networks often isolate devices even when their Wi-Fi name is identical.

Enter the PC's LAN IP, usually `192.168.x.x` or `10.x.x.x`. `127.0.0.1` on a phone means the phone itself. With VPNs or multiple adapters, choose the address on the phone's subnet.

Traffic is unencrypted. Use a trusted LAN, do not forward the port to the internet, and do not treat the pairing code as encryption.

### 🖥️ 3. Select the PC image

![Windows control panel](images/desktop.png)

1. Select a display. Start with the entire display to avoid an invalid capture region.
2. For a rectangular region, enter its top-left coordinates, width and height. These are Windows desktop coordinates; monitors left of the primary display can use negative coordinates.
3. Set the **longest output edge**, FPS and JPEG quality. Aspect ratio is preserved for landscape and portrait sources. Start with modest values, then increase them.
4. Start streaming and note the displayed IP, port (default `8765`) and six-digit pairing code.

Allow a Windows firewall prompt only on a trusted private network. You do not need to disable the firewall or run as administrator to view an ordinary desktop.

The screenshot's `2 · ASUS PA279 2160 × 3840` is the display used for development validation. Select your own intended screen; your number and name need not match. See the [validation record](VALIDATION.md).

A region follows coordinates, not a window. Update it after moving the window. Protected video, some exclusive-fullscreen games and the secure desktop can appear black; test an ordinary desktop first, then try windowed / borderless game mode.

### 🌐 Choose an interface language

Both applications default to English. Select **English / 简体中文** in the PC header or the phone's **Language / 语言** setting; the choice is saved independently on each device. PC switching leaves the stream running but disarms mouse control. Phone switching recreates the screen, disconnects and requires connecting again. Desktop illustrations show the corresponding language; phone screenshots show the final v0.1.1 English UI.

### 📱 4. Connect the phone

![Android client](images/android.png)

Enter the PC IP, port and pairing code, then tap **连接电脑 / Connect to PC**. Start with **全屏模式 / Full screen**. **显示设置 / Show settings** opens controls and **隐藏设置 / Hide settings** hides them. **Long-press the image** or press **Back** to restore controls; **double-tap** to recenter. **关于与开源许可 / About and licenses** shows bundled notices. Button language follows the app's selected interface language when available.

These final v0.1.1 screenshots use a Google-free Android 6.0 / API 23 emulator receiving this project's original animated calibration card. **`10.0.2.2` is the emulator's special address for its development PC**; a physical phone must use the PC's LAN IP. Receive-FPS readings describe that session, not physical-device performance or end-to-end latency.

This emulator has no usable rotation sensor and falls back to full screen. It verifies installation and UI flow, not real phone sensors, optics, heat or wireless performance.

### 🥽 5. Align the image with the lenses

Hold the phone in landscape before inserting it. Scroll the settings panel to **Viewer fit / 盒子适配**.

![Scale, offsets, eye separation and lens distortion](images/android-settings.png)

| Setting | Adjustment |
| --- | --- |
| Scale | Shrink the image if a large phone's edges are hidden by the lenses. |
| Horizontal / vertical offset | Move each eye's visible image toward the lens center. |
| Eye separation | Adjust image positions; this is not an automatic interpupillary-distance measurement. |
| Field of view | Change the virtual camera's visible angle. |
| Screen distance | Change the cinema screen's position and apparent size. |
| Distortion | Start at zero and adjust gently for your particular lenses. |

Change one setting at a time and keep a comfortable baseline. Hide the controls when ready.

![The same 2D card in both eye regions with controls hidden](images/android-vr.png)

Both eyes receive the same image; the card does not demonstrate native stereoscopic depth. If you experience double vision, dizziness or eye discomfort, remove the viewer, rest, and return to smaller images and gentler settings.

### 🎬 6. Cinema mode

Choose **Cinema / 大屏幕模式**, face your intended viewing direction, and tap **Recenter / 视角回正**. Turn slowly to check the screen's position.

This places the same 2D desktop image on a virtual plane and tracks head rotation. It does not track room position or create stereoscopic depth. Devices with only an accelerometer or incomplete sensor support can use full screen instead.

### 🎯 7. FPS mode

1. Test on the desktop or an offline game first, with low sensitivity.
2. Choose **FPS game / FPS 游戏模式**, look forward and recenter.
3. On the PC, enable **Allow phone gyro to control the current game's mouse / 允许手机陀螺仪控制当前游戏鼠标** and switch to the game within **5 seconds**. The first external foreground window is locked; changing focus stops control and requires arming again.
4. Turn slowly, check horizontal / vertical directions, then adjust sensitivity or invert Y.
5. Press **F8** on the PC at any time to stop mouse control. Disconnecting, switching modes or stopping streaming requires fresh authorization.

This sends ordinary relative mouse movement; some games reject it. It does not inject into games, bypass anti-cheat, or render native stereo. Follow each game's input and mod rules.

### 🔧 Troubleshooting

| Symptom | Check first |
| --- | --- |
| Cannot connect | Streaming started, correct IP / port / code, guest Wi-Fi isolation, VPN, private-network firewall rule. |
| Pairing error | Use the current six-digit host code; restarting can change it. |
| Connected but black | Capture an ordinary desktop, check region / display, then try windowed game mode. |
| Stuttering | Lower longest edge, FPS and quality; move nearer the router; check CPU load and phone temperature. |
| Double image | Center the phone, then adjust scale, offsets and eye separation for those lenses. |
| No head response | Full screen intentionally ignores pose; cinema / FPS require a supported rotation sensor. |
| Drift | Recenter and move away from magnetic objects; sensor fusion differs by device. |
| FPS mouse does not move | Check PC arming, focus and mode; test the desktop before game input compatibility. |
| APK cannot install | Check Android version, APK compatibility and debug-signature conflicts. Avoid repackaged APKs. |
| Missing DLL / error 126 | Install or repair the current official Microsoft Visual C++ v14 x64 runtime linked above. |

Include version, device, mode and reproduction steps in an Issue. Remove pairing codes and private screen content. See [contributing](../CONTRIBUTING.md).

---

<!-- vrization:chinese -->
## 简体中文

[返回首页](../README.md) · [构建源码](BUILD.md) · [排查问题](#-遇到问题时)

准备一台 Windows 10 / 11 x64 电脑、一部 Android 6.0+ 或兼容 Android APK 的手机，以及一个手机 VR 盒子。全屏模式可以在没有陀螺仪的设备上使用；大屏幕与 FPS 需要设备提供兼容的旋转传感器。此 Alpha 不依赖 Google Play 服务。

### 📦 1. 安装同一版本的两端

打开 [GitHub Releases](https://github.com/LexZeon/VRization/releases)，下载 Windows 压缩包与 Android APK。Windows 端先完整解压再启动其中的程序，不要只从压缩包拖出单个文件。

Windows 端需要 Microsoft Visual C++ v14 x64 运行库，项目包内不附带微软运行库 DLL。电脑通常已具备该组件；如果启动报缺少 `VCRUNTIME140*.dll`、无法加载 Python DLL 或错误 126，再按 [微软官方说明](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist/) 下载并安装 [当前 x64 运行库](https://aka.ms/vc14/vc_redist.x64.exe)，然后重新启动 VRization。首发本机构建使用 MSVC 14.44，运行库应为相同或更新版本；使用微软当前受支持版本即可。

将 APK 传到手机，点击安装。Android 如提示“此来源不允许安装”，只为当前文件管理器 / 浏览器允许安装来源，然后继续。不同品牌和衍生系统的菜单位置可能不同。没有 Google 服务不影响使用；不提供 Android APK 兼容层的系统无法直接安装。

Alpha APK 使用测试签名，不是应用商店发布签名。不同电脑或 CI 构建生成的测试签名可能不同；覆盖安装报签名冲突时，需要先卸载旧版再安装，这会清除旧版保存的设置。不要把测试 APK 当作正式商店包发布。

### 📡 2. 让手机找到电脑

电脑与手机接同一路由器。建议电脑使用网线、手机使用信号良好的 5 GHz / 6 GHz Wi-Fi；首轮测试靠近路由器。访客网络通常开启设备隔离，即使 Wi-Fi 名称相同也可能互相连不上。

电脑端显示的局域网 IP 通常形如 `192.168.x.x` 或 `10.x.x.x`。手机上的 `127.0.0.1` 指手机自己，不能用来连接另一台电脑。如果电脑有 VPN、虚拟网卡或多个网卡，选择与手机处于同一网段的地址。

当前连接是明文局域网串流。只在可信网络上使用，不做公网端口转发。配对码不能替代加密。

### 🖥️ 3. 在电脑端选画面

![电脑控制台](images/desktop-zh.png)

电脑控制台的使用顺序：

1. 选择显示器。首次连接先用完整显示器，避免把选区设到屏幕之外。
2. 如只想显示某个区域，填写矩形的左上角坐标和宽高。坐标属于 Windows 桌面坐标，多显示器左侧屏幕可能使用负坐标。
3. 选择 **最长输出边**、帧率与 JPEG 质量。输出保持原画面比例，无论横屏还是竖屏都限制最长边；先用较低尺寸和帧率确认连接，再逐步提高。
4. 开始串流，记录显示的 IP、端口（默认 `8765`）和六位配对码。

Windows 如弹出防火墙窗口，仅在你信任的专用网络上允许访问。无需关闭整个防火墙，也无需管理员权限来观看普通桌面。

截图中的 `2 · ASUS PA279 2160 × 3840` 是本次开发验证的显示器；请在自己的电脑上选择准备串流的屏幕，编号和名称无需与截图一致。验证环境与范围见 [首版记录](VALIDATION.md)。

矩形选区按坐标采集，不会自动跟随窗口。窗口移动后应重新设置区域。受保护视频、某些游戏的独占全屏或系统安全桌面可能显示黑屏；先试普通桌面，再试游戏的窗口 / 无边框窗口模式。

### 🌐 选择界面语言

两端默认英文。在电脑顶部或手机 **Language / 语言** 设置中选 **English / 简体中文**，两端各自保存。电脑切换保持串流，但解除鼠标授权；手机切换重建界面并断线，需要重新连接。电脑图展示对应语言，手机图采用最终 v0.1.1 默认英文界面。

### 📱 4. 在手机端连接

![Android 客户端](images/android.png)

填写电脑 IP、端口与配对码，点击 **连接电脑**。连接后先选择 **全屏模式**；点击 **显示设置** 调整画面，点击 **隐藏设置** 收起控制区。隐藏后**长按画面**或按**返回键**恢复操作区，**双击画面**可以回正。手机端的 **关于与开源许可** 可查看附带的许可文本。

最终 v0.1.1 截图来自不含 Google 服务的 Android 6.0 / API 23 模拟器，正在接收本项目的原创动态校准卡。**`10.0.2.2` 是 Android 模拟器访问开发电脑的专用地址**；真实手机应填写电脑在同一局域网中的 IP。接收帧率只描述当时连接，不是实机性能或端到端延迟测量。

该模拟器没有可用的旋转传感器，客户端可回退到全屏模式。模拟器能验证安装与界面流程，不能代替手机传感器、盒子镜片、发热和无线网络的实机检查。

### 🥽 5. 让镜片里的画面对齐

先将手机横屏拿在手上调整，再放入盒子。设置面板向下滚动可找到 **盒子适配**：

![盒子适配设置：缩放、水平与垂直位置、双眼间距、镜片畸变](images/android-settings.png)

| 设置 | 怎样调 |
| --- | --- |
| 画面缩放 | 大手机被镜片遮住边缘时，先缩小画面。 |
| 水平 / 垂直偏移 | 将两眼的有效画面移到镜片中心。 |
| 眼间距 | 微调左右眼画面的位置；这是显示参数，不是自动测量瞳距。 |
| 视场角 | 改变虚拟相机的可见范围。 |
| 屏幕距离 | 在大屏幕模式中改变虚拟屏幕的位置和视觉尺寸。 |
| 畸变 | 从零开始微调；不同盒子镜片需要不同数值。 |

每次只改一项。保留一个舒适的基础布局，再逐步调整。完成后点击 **隐藏设置**：

![隐藏设置后，左右眼显示同一张二维校准卡](images/android-vr.png)

左右眼复制同一张图像，方便通过手机 VR 盒子观看；图中的二维卡片不代表原生立体游戏深度。出现重影、眩晕或眼部不适时取下盒子休息，恢复较小画面和较温和设置。

### 🎬 6. 大屏幕模式

选择 **大屏幕模式**，正对准备观看的方向，点击 **视角回正**。缓慢转头检查屏幕是否保持在预期方向。

此模式把同一张二维电脑图像放到虚拟屏幕上，追踪头部旋转；没有房间位置追踪，也不会生成桌面内容的立体深度。某些手机只有加速度计或不完整的传感器实现，这时可退回全屏模式。

### 🎯 7. FPS 游戏模式

1. 先在普通桌面或离线游戏中测试，把鼠标灵敏度设低一些。
2. 手机切到 **FPS 游戏模式**，正视前方并点击 **视角回正**。
3. 在电脑端勾选 **允许手机陀螺仪控制当前游戏鼠标**，在 **5 秒内**切到游戏窗口。控制会锁定第一个外部前台窗口，之后切换焦点会停止控制，需要重新授权。
4. 缓慢转头，检查左右、上下方向；按需要调节灵敏度与 Y 轴反转。
5. 随时按电脑键盘 **F8** 停止鼠标控制；断开连接、切换模式或停止串流后需要重新授权。

此功能映射普通鼠标移动，不能保证所有 FPS 游戏接受。没有注入游戏进程、绕过反作弊或原生双目渲染功能。请遵守游戏的输入和模组规则。

### 🔧 遇到问题时

| 现象 | 先检查 |
| --- | --- |
| 连不上电脑 | 是否开始串流、IP / 端口 / 配对码是否正确、是否为访客 Wi-Fi、VPN 是否隔离、专用网络防火墙规则。 |
| 密码或配对错误 | 使用当前电脑端显示的六位码；重新启动后码可能改变。 |
| 已连接但黑屏 | 先采集普通桌面；检查矩形范围、显示器编号，再把游戏改为窗口模式。 |
| 画面卡顿 | 降低最长输出边、FPS 和 JPEG 质量，靠近路由器，检查电脑 CPU 与手机温度。 |
| 画面看起来有双影 | 检查手机是否居中，再调缩放、偏移和眼间距；不同镜片不共享同一套参数。 |
| 转头无反应 | 检查模式；全屏本来不使用姿态。大屏幕 / FPS 需要兼容旋转传感器。 |
| 转头漂移 | 回正，远离磁性物体；不同设备的传感器融合质量不同。 |
| FPS 鼠标不动 | 确认电脑端授权、游戏焦点和模式；先用桌面验证，再检查游戏是否接受模拟输入。 |
| APK 安装失败 | 检查 Android 版本、APK 兼容能力及测试签名冲突；不要从未知网站下载改包。 |
| 电脑程序报缺少 DLL / 错误 126 | 先安装或修复微软当前受支持的 Visual C++ v14 x64 运行库，参考上方官方链接。 |

提交 Issue 时附上版本、设备、模式与复现步骤。不要公开配对码或私密屏幕内容。反馈模板见 [贡献指南](../CONTRIBUTING.md)。

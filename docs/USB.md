# 🔌 USB connection guide / USB 连接指南

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

USB is the default connection preference in the Windows host, Android app and iOS app. A data cable and the platform's authorization are required. Native USB transport does not require a hotspot, USB tethering or a shared Wi-Fi network. Use one phone at a time; the host accepts one viewer.

The host detects authorized USB devices automatically when its USB option is enabled. **You must click Start streaming on the PC.** A new phone app launch starts one foreground USB connection attempt; Android v0.3.2 retries bootstrap discovery within a bounded 30-second window including its handshake, while iOS opens its local listener and waits for the PC. If it fails, use the phone's connection button to retry. Returning from the background or changing the phone's language disconnects and requires a manual connection; neither action silently reconnects. USB never enables first-person mouse control: explicitly allow control on the PC, switch to the game within five seconds, and press **F8** to stop it.

### Find the PC's USB controls and status

Click **USB connection…** in the PC's top connection card to open the USB controls directly. Alternatively, select the **Stream** tab and scroll down to the **USB connection** group. Keep **Detect authorized USB phones automatically (recommended)** checked; the device selector and **Choose official SDK adb.exe…** button are in the same group.

Read the USB status in the top connection card, below the PC address and connection hint; status changes also appear in the bottom activity log. **Waiting for phone** only means the streaming server is waiting for a viewer, and does not establish that USB is ready. After starting streaming, look for **Android USB ready: …**, then retry **Detect USB and connect** on Android if its initial attempt has ended. If the PC reports USB off, unavailable, waiting or a port conflict, follow that message before repeatedly retrying on the phone.

### Android: first setup

1. Install the release's Android APK on the phone. Android 6.0 / API 23 or newer is the application's minimum; actual derivative / device results are listed in [compatibility records](COMPATIBILITY.md).
2. Open **USB connection… → Download official Android USB tools…**, read / accept Google's terms and download the official [Windows Platform Tools](https://developer.android.com/tools/releases/platform-tools). Use **Import downloaded USB tools ZIP…** to choose the downloaded verified **37.0.1** ZIP and a separate installation folder. Import verifies the package, keeps its complete NOTICE and preserves existing installations; it does not download or accept terms for you. Alternatively, extract official tools yourself and use **Choose official SDK adb.exe…**. Keep the whole tools folder. VRization bundles no `adb.exe`, SDK or USB driver; the packaged app itself needs no Python / development environment.
3. Enable the phone's Developer options and **USB debugging**, connect a data cable, unlock the phone and approve USB debugging for this computer. OEM menu names and driver requirements vary; use the manufacturer's USB driver if Windows does not recognize its debugging interface. Google's [ADB setup guide](https://developer.android.com/tools/adb#Enabling) explains device authorization.
4. Keep **Detect authorized USB phones automatically (recommended)** enabled on the PC. With one authorized Android USB device it is selected automatically. With several, choose the intended serial number in the USB device list. Emulators and wireless ADB are excluded from this USB discovery.
5. Select the screen / region, then click **Start streaming** on the PC. Open VRization on the phone with **USB cable · default** selected. If its first attempt has already ended, tap **Detect USB and connect**. You do not enter an IP address or six-digit code in USB mode.

For later sessions, connect and unlock the phone, start PC streaming, and open the phone app or use its USB connection button. If another program already owns phone port `18765`, VRization reports the conflict and leaves that mapping untouched; close the owning program or choose LAN. It removes only the reverse mapping that it created and still owns.

### Portable tools and different Windows launch environments

If USB works only when launched from a development / packaged app, check the PC's displayed official tool path. An SDK inside a packaged application's virtualized AppData can be invisible to an ordinary double-clicked process. Use the importer or manually select an official installation in an ordinary folder. The default is `tools/android-sdk` beside a standalone EXE, or at the managed archive root outside `latest`; launchers conditionally set SDK variables only for their child. Keep that separately installed folder when updating. This changes tool discovery, not device trust; the phone must still authorize USB debugging. See [download / archive layout](DOWNLOADS.md).

The packaged v0.3.2 EXE was checked with SDK environment variables cleared and fresh preferences: it selected separately installed portable tools, found an authorized physical device and completed diagnostics without errors. Tool discovery does not repair a dropped ADB session or phone authorization. Both were separately observed during development; no old-host GUI or port collision was found, and not every historical failure is attributed to AppData virtualization. If Windows sees the USB interface but the app reports no authorized phone, check the phone's current debugging approval and data connection; avoid restarting a shared ADB server that other tools may use.

A bounded phone-first test on the Huawei succeeded when PC streaming started 6.08 seconds after the phone attempt: connection arrived at 7.67 seconds from phone startup. This verifies that startup order in one run, not a persistent background retry or long-duration guarantee. See [version-scoped validation](VALIDATION.md).

### iPhone / iPad: first setup and present limits

**The iOS USB path currently has software bridge / fake-device tests, not a successful real-iPhone USB test.** A Simulator, unsigned device build or connected charging cable does not establish hardware compatibility. Check [iOS build and signing](IOS.md) and [compatibility records](COMPATIBILITY.md) for the current evidence.

1. Build and sign the iOS app for your device using Xcode on a Mac, following [the iOS guide](IOS.md). The source ZIP needs your Apple signing. A Simulator ZIP runs in the matching Mac Simulator and cannot be installed on an iPhone. The app requires iOS / iPadOS 15 or newer.
2. On Windows, install Apple's **Apple Devices** app and its Apple Mobile Device support. Connect one iPhone / iPad with a data cable, unlock it, approve **Trust This Computer**, and confirm that Apple Devices recognizes it. See Apple's [Windows device guide](https://support.apple.com/guide/devices-windows/welcome/windows) and [USB recognition / Trust instructions](https://support.apple.com/en-us/108643).
3. Leave automatic USB detection enabled and click **Start streaming** on the PC. Open the signed VRization app in the foreground with USB selected. Its first launch opens the USB listener; otherwise tap its USB connection button. The PC connects through Apple's local USB service. No hotspot or USB tethering is used, and no IP / six-digit code is entered on the phone.
4. Keep the app visible and unlocked. After backgrounding, changing language or a disconnect, use the phone's connection button again. Automatic iOS selection supports **one attached iPhone / iPad**; unplug other Apple mobile devices rather than relying on an arbitrary selection.

VRization reads an existing local Apple pairing record to check that trust was established. It does not create pairing records or display / save their keys. Apple software and signing services remain separately supplied under Apple's terms.

### LAN remains available

Choose **LAN / Wi-Fi · manual pairing** on the phone. Join the same trusted network, enter the PC's LAN host address, server port (default `8765`) and current six-digit pairing code, preserving leading zeroes. Enter a host only, without a URL scheme, path or query. Allow the PC port on the private network if Windows Firewall blocks it. USB setup does not require opening an inbound LAN firewall port. Current LAN HTTP / WebSocket traffic is unencrypted; use a trusted local network. See [the protocol](PROTOCOL.md).

### Performance and measurements

Use the host's **Performance profile** selector. The new-user default is low latency; existing saved settings remain in effect until changed.

| Profile | Maximum long edge | Capture target | JPEG quality |
| --- | --- | --- | --- |
| Low latency — default for new users | 640 pixels | 60 FPS | 45 |
| Stable | 640 pixels | 30 FPS | 50 |
| Quality | 960 pixels | 30 FPS | 60 |
| Custom | Your selection | Your selection | Your selection |

The long-edge bound preserves aspect ratio. A profile changes capture size, FPS target and JPEG quality, leaving your monitor / region selection intact. Smaller frames can reduce encoding, transfer and phone decoding work. The actual rate depends on the PC, cable, USB service, phone decoder and display; 60 FPS is a target, not a guarantee. The phone reports received-frame FPS and link ping round-trip time. **Neither is end-to-end video / motion-to-photon latency**: ping does not include desktop capture, JPEG encoding, image decode or display presentation. Audio stays on the computer.

### Transport details and troubleshooting

Android uses official ADB reverse forwarding, with the phone's `127.0.0.1:18765` mapped to the PC's configured host port (default `8765`). The phone requests `GET http://127.0.0.1:18765/usb-bootstrap`, validates the version, identity, port and six-digit token, then connects to `ws://127.0.0.1:18765/ws?token=…`. An advertised PC port is informational; the phone keeps using its fixed forwarded port. The bootstrap endpoint returns a token only to a loopback request while the host has an authorized physical Android USB mapping; it is disabled for ordinary embedding by default. Tokens are not saved in phone preferences or bootstrap logs. A stopped host usually refuses the connection; HTTP 403 means the host rejected USB bootstrap, while 503 indicates a reachable but stopped host. Debugging approval on the phone alone does not establish a usable reverse mapping. For 403 or “not detected”, first check the PC's USB status, automatic-detection checkbox and official `adb.exe` path, then the cable, selected device, debugging approval and streaming state. Retry on the phone after the PC reports **Android USB ready: …**. Reverse syntax is documented in Google's [ADB manual](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/user/adb.1.md).

iOS uses a native Network-framework listener at phone loopback `127.0.0.1:18766`. The Windows relay uses Apple's local USB multiplexing service to reach it, then bridges the existing host session. Frames have a four-byte big-endian length including a one-byte kind: `1` for UTF-8 protocol JSON, `2` for JPEG, with length `1…8 MiB`; phone-to-host messages are JSON only, up to 16 KiB. This is VRization's framing inside the USB tunnel, separate from the usbmux service's own plist framing. If detection fails, first check Apple Devices, trust, a single attached device and the foreground signed app. Source and protocol-reference credit is in [third-party notices](../THIRD_PARTY_NOTICES.md).

### Saved view profiles and Reset (v0.3)

USB discovery / authorization is unchanged. A saved phone VR profile is applied only after the valid host hello and uses normal settings synchronization; it neither starts capture nor arms input. Editor drafts stay local. Phone reset returns English / USB and disconnects without an immediate automatic attempt in the reset screen; use Connect there explicitly. A fresh phone-app launch resumes the normal initial USB discovery / listening policy. PC reset preserves the selected capture display / region and ADB path, returns USB device selection to automatic and leaves platform authorization / installed tools intact. See [editing](EDITING.md).

---

<!-- vrization:chinese -->
## 简体中文

Windows 电脑端、Android 端和 iOS 端都默认优先 USB。需要支持数据传输的线缆以及相应平台授权。原生 USB 传输不要求开启热点、USB 网络共享或连接同一 Wi-Fi。每次使用一部手机，电脑端同时接受一个观看端。

电脑启用 USB 选项后会自动检测已授权的 USB 设备。**电脑必须由你点击“开始串流”。** 手机软件新启动时在前台发起一次 USB 连接：Android v0.3.2 在含握手的最长 30 秒窗口内重试 bootstrap 发现，iOS 打开本地监听并等待电脑连接。失败后用手机连接按钮重试。手机进入后台或切换语言会断开，回来后需要手动连接，不会悄悄重连。USB 不会自动开启第一人称鼠标控制：仍须在电脑主动允许控制、五秒内切换到游戏，并可随时按 **F8** 停止。

### 找到电脑端 USB 控件与状态

点击电脑顶部连接卡片的“**USB 连接…**”可直接打开 USB 控件；也可以选择“**串流设置**”页，向下滚动到“**USB 连接**”区域。保持勾选“**自动检测已授权的 USB 手机（推荐）**”；设备选择框与“**选择官方 SDK 中的 adb.exe…**”按钮也在这里。

USB 状态位于顶部连接卡片、电脑地址和连接提示下方，状态变化也会显示在底部活动日志。“**等待手机连接**”只代表串流服务在等待观看端，不表示 USB 已经就绪。开始串流后，先确认电脑显示“**安卓 USB 已就绪：…**”；若手机首次尝试已结束，再点“**检测 USB 并连接**”。如果电脑提示 USB 已关闭、不可用、等待中或端口冲突，先按该提示排查，再在手机重试。

### Android：首次设置

1. 在手机安装发布版 Android APK。软件最低支持 Android 6.0 / API 23；实际衍生系统和设备验证见 [兼容性记录](COMPATIBILITY.md)。
2. 点“**USB 连接… → 下载官方安卓 USB 工具…**”，在 Google 阅读 / 接受条款，下载官方 [Windows Platform Tools](https://developer.android.com/tools/releases/platform-tools)。点“**导入已下载的 USB 工具 ZIP…**”，选择已校验的 **37.0.1** ZIP 和另行安装目录；导入核对包、保留完整 NOTICE 与已有安装，不替你下载或接受条款。也可自行解压官方工具，再“**选择官方 SDK 中的 adb.exe…**”，保留整个工具文件夹。VRization 不附带 `adb.exe`、SDK 或驱动，打包应用本身无需 Python / 开发环境。
3. 在手机启用开发者选项和 **USB 调试**，接入数据线，解锁手机并允许此电脑进行 USB 调试。不同厂商的菜单和驱动要求不同；若 Windows 未识别调试接口，使用该厂商的 USB 驱动。Google 的 [ADB 设置指南](https://developer.android.com/tools/adb#Enabling) 说明了设备授权。
4. 电脑保持勾选“**自动检测已授权的 USB 手机（推荐）**”。只有一台已授权 Android USB 设备时自动选择；多台时在 USB 设备列表选择目标序列号。此 USB 检测排除模拟器和无线 ADB。
5. 选择屏幕 / 选区，在电脑点“**开始串流**”。手机打开 VRization，保持选择“**USB 数据线 · 默认**”。若首次尝试已经结束，点“**检测 USB 并连接**”。USB 模式无需手填 IP 或六位配对码。

以后使用时接线、解锁、开始电脑串流，再打开手机软件或点 USB 连接按钮。如果其他软件已占用手机端口 `18765`，VRization 会报告冲突并保留已有映射；请关闭占用软件或选择局域网。VRization 只移除由自己建立且仍属于自己的反向映射。

### 便携工具与不同 Windows 启动环境

若只有从开发 / 打包应用内启动才能连接 USB，先看电脑显示的官方工具路径。打包应用虚拟化 AppData 内的 SDK 可能不被普通双击进程看到；用导入器或手动选择普通文件夹中的官方安装。独立 EXE 默认用旁边 `tools/android-sdk`，已管理归档放根目录、在 `latest` 之外；启动器只为子应用有条件设置 SDK 变量。更新时保留另装工具目录。这改的是工具发现，不是设备信任，手机仍需授权 USB 调试，见 [下载 / 归档结构](DOWNLOADS.md)。

打包 v0.3.2 EXE 已在清空 SDK 环境变量、使用新偏好时检查：选中另行安装的便携工具，识别已授权真实设备，诊断完成且无错误。工具发现不会修复掉线的 ADB 会话或手机授权；开发期间两种问题另有实际观察，未发现旧电脑端界面或端口冲突，不能把全部历史故障归因于 AppData 虚拟化。Windows 能看到 USB 接口而软件没有已授权手机时，核对手机当前调试批准和数据连接；避免重启其他工具共用的 ADB 服务。

华为一次有限的手机先启动检查通过：手机尝试后 6.08 秒才开始电脑串流，手机启动后 7.67 秒连接成功。这验证该次启动顺序，不是持续后台重试或长期连接保证。见 [按版本记录的验证](VALIDATION.md)。

### iPhone / iPad：首次设置与当前限制

**目前 iOS USB 仅有软件桥接 / 假设备测试，尚无真实 iPhone USB 成功测试。** 模拟器、未签名真机 SDK 构建或接上充电线都不等于硬件兼容性验证。当前证据见 [iOS 构建与签名](IOS.md) 和 [兼容性记录](COMPATIBILITY.md)。

1. 按 [iOS 教程](IOS.md) 在 Mac 上用 Xcode 为设备构建并签名。源码 ZIP 需要使用自己的 Apple 签名。模拟器 ZIP 只用于匹配的 Mac 模拟器，不能安装到 iPhone。应用要求 iOS / iPadOS 15 及以上。
2. Windows 安装 Apple 的 **Apple Devices** 软件及其 Apple Mobile Device 支持。只接一台 iPhone / iPad，使用数据线、解锁并允许“**信任此电脑**”，确认 Apple Devices 能识别设备。参见 Apple 的 [Windows 设备指南](https://support.apple.com/guide/devices-windows/welcome/windows) 与 [USB 识别 / 信任说明](https://support.apple.com/en-us/108643)。
3. 电脑保持自动 USB 检测，点“**开始串流**”。手机前台打开已经签名的 VRization，选择 USB。首次启动会打开 USB 监听；否则点 USB 连接按钮。电脑通过 Apple 的本地 USB 服务连接，不使用热点或 USB 网络共享，手机无需填写 IP / 六位配对码。
4. 保持软件在前台且手机已解锁。进入后台、切换语言或断线后，再点手机连接按钮。iOS 自动选择仅支持**连接一台 iPhone / iPad**；请拔掉其他 Apple 移动设备，避免任意选择。

VRization 读取已有的本地 Apple 配对记录来确认已建立信任，不创建配对记录，也不显示 / 保存其中的密钥。Apple 软件与签名服务按 Apple 条款另行提供。

### 仍可使用局域网

手机选择“**局域网 / Wi-Fi · 手动配对**”。两端加入同一可信网络，输入电脑局域网主机地址、服务端口（默认 `8765`）和当前六位配对码，保留前导零。只填主机，不填 URL 协议头、路径或查询参数。若 Windows 防火墙拦截，允许私人网络上的电脑端口。USB 设置无需开放局域网入站防火墙端口。当前局域网 HTTP / WebSocket 未加密，请在可信本地网络使用。参见 [协议](PROTOCOL.md)。

### 性能与指标

在电脑“**性能预设**”中选择。新用户默认低延迟；已有保存设置继续生效，直到主动更改。

| 预设 | 最大长边 | 捕获目标 | JPEG 质量 |
| --- | --- | --- | --- |
| 低延迟 — 新用户默认 | 640 像素 | 60 FPS | 45 |
| 稳定 | 640 像素 | 30 FPS | 50 |
| 清晰 | 960 像素 | 30 FPS | 60 |
| 自定义 | 自行选择 | 自行选择 | 自行选择 |

长边限制保持画面比例。预设修改捕获大小、目标帧率和 JPEG 质量，保留显示器 / 选区。较小画面可减少编码、传输和手机解码工作。实际帧率取决于电脑、线缆、USB 服务、手机解码与屏幕；60 FPS 是目标而非保证。手机显示接收帧率和链路 ping 往返时间。**两者都不是端到端视频 / 运动到光子延迟**：ping 不包括桌面采集、JPEG 编码、图像解码或显示呈现。声音仍留在电脑。

### 传输细节与排查

Android 使用官方 ADB 反向端口映射，把手机 `127.0.0.1:18765` 转发到电脑配置的服务端口（默认 `8765`）。手机请求 `GET http://127.0.0.1:18765/usb-bootstrap`，校验版本、软件标识、端口和六位 token 后连接 `ws://127.0.0.1:18765/ws?token=…`。响应中的电脑端口仅用于说明，手机始终使用固定转发端口。bootstrap 只在电脑拥有已授权的真实 Android USB 映射、请求来自回环地址时返回 token；普通嵌入服务默认关闭此接口。token 不写入手机偏好或 bootstrap 日志。电脑服务停止时通常连接被拒绝；HTTP 403 表示电脑拒绝了 USB bootstrap，503 表示服务可达但串流已停止。手机已批准调试不等于电脑已经建立可用的反向映射。遇到 403 或“未检测到”，先检查电脑 USB 状态、自动检测开关与官方 `adb.exe` 路径，再检查数据线、所选设备、调试批准与串流状态。电脑显示“**安卓 USB 已就绪：…**”后再在手机重试。反向映射语法见 Google 的 [ADB 手册](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/user/adb.1.md)。

iOS 使用原生 Network 框架在手机回环地址 `127.0.0.1:18766` 监听。Windows 中继通过 Apple 本地 USB 多路复用服务访问此端口，桥接已有电脑会话。帧头为四字节大端长度，长度包含一字节类型：`1` 为 UTF-8 协议 JSON，`2` 为 JPEG，长度 `1…8 MiB`；手机发向电脑只允许 JSON，最大 16 KiB。这是 USB 隧道内的 VRization 分帧，独立于 usbmux 服务自己的 plist 分帧。未检测到时先检查 Apple Devices、信任、是否只接一台设备，以及已签名软件是否在前台。源码与协议参考贡献见 [第三方声明](../THIRD_PARTY_NOTICES.md)。


### 保存观看配置与重置（v0.3）

USB 发现 / 授权不变。手机保存配置只在合法主机 hello 后经普通设置同步恢复，不开始采集、不授权输入；编辑草稿只在本地。手机重置恢复英文 / USB 并断线，当前重置后的页面不立即自动尝试，可主动点连接；全新启动手机软件时恢复正常首次 USB 发现 / 监听策略。电脑保留采集显示器 / 选区及 ADB 路径，USB 设备选择恢复自动，不改变平台授权或已安装工具。见 [编辑文档](EDITING.md)。

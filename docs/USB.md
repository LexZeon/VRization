# 🔌 USB connection guide / USB 连接指南

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

USB is the default connection preference in the Windows host, Android app and iOS app. A data cable and the platform's authorization are required. Native USB transport does not require a hotspot, USB tethering or a shared Wi-Fi network. Use one phone at a time; the host accepts one viewer.

**v0.3.3 candidate behavior:** Automatic detection finds authorized devices and never starts capture by itself. After setup, select the screen / region, then press **Connect / Start streaming** on the PC or **Detect USB and connect** on Android / **Connect** in a foreground iOS app. Either explicit action can request host startup; an existing active session is retained. Fresh Android startup can wait for an existing stream, while iOS startup opens control only. Returning from the background or changing language requires explicit connection. This candidate awaits final native / device validation; historical behavior is recorded in [validation](VALIDATION.md). USB never arms first-person mouse control: explicitly allow it on the PC and use **F8** to stop.

### Find the PC's USB controls and status

Click **USB connection…** in the PC's top connection card to open the USB controls directly. Alternatively, select the **Stream** tab and scroll down to the **USB connection** group. Keep **Detect authorized USB phones automatically (recommended)** checked; the device selector and **Choose official SDK adb.exe…** button are in the same group.

Read the USB status in the top connection card, below the PC address and connection hint; status changes also appear in the bottom activity log. **Waiting for phone** only means the streaming server is waiting for a viewer, and does not establish that USB is ready. After starting streaming, look for **Android USB ready: …**, then retry **Detect USB and connect** on Android if its initial attempt has ended. If the PC reports USB off, unavailable, waiting or a port conflict, follow that message before repeatedly retrying on the phone.

### Android: first setup

1. Install the release's Android APK on the phone. Android 6.0 / API 23 or newer is the application's minimum; actual derivative / device results are listed in [compatibility records](COMPATIBILITY.md).
2. Open **USB connection… → Download official Android USB tools…**, read / accept Google's terms and download the official [Windows Platform Tools](https://developer.android.com/tools/releases/platform-tools). Use **Import downloaded USB tools ZIP…** to choose the downloaded verified **37.0.1** ZIP and a separate installation folder. Import verifies the package, keeps its complete NOTICE and preserves existing installations; it does not download or accept terms for you. Alternatively, extract official tools yourself and use **Choose official SDK adb.exe…**. Keep the whole tools folder. VRization bundles no `adb.exe`, SDK or USB driver; the packaged app itself needs no Python / development environment.
3. Enable the phone's Developer options and **USB debugging**, connect a data cable, unlock the phone and approve USB debugging for this computer. OEM menu names and driver requirements vary; use the manufacturer's USB driver if Windows does not recognize its debugging interface. Google's [ADB setup guide](https://developer.android.com/tools/adb#Enabling) explains device authorization.
4. Keep **Detect authorized USB phones automatically (recommended)** enabled on the PC. With one authorized Android USB device it is selected automatically. With several, choose the intended serial number in the USB device list. Emulators and wireless ADB are excluded from this USB discovery.
5. Select the screen / region and open Android with **USB cable · default** selected. Press **Connect / Start streaming** on the PC, or tap **Detect USB and connect** on Android. The candidate connects either way without entering an IP address or six-digit code.

For later sessions, connect and unlock the phone, then use either side’s explicit Connect with the cable left in place. Disconnect must clear the phone image and stop live frames; button text alone is insufficient. Conflicts on phone video `18765` or control `18764` are reported and existing mappings are preserved. VRization removes only mappings it created and still owns.

### Portable tools and different Windows launch environments

If USB works only when launched from a development / packaged app, check the PC's displayed official tool path. An SDK inside a packaged application's virtualized AppData can be invisible to an ordinary double-clicked process. Use the importer or manually select an official installation in an ordinary folder. The default is `tools/android-sdk` beside a standalone EXE, or at the managed archive root outside `latest`; launchers conditionally set SDK variables only for their child. Keep that separately installed folder when updating. This changes tool discovery, not device trust; the phone must still authorize USB debugging. See [download / archive layout](DOWNLOADS.md).

The packaged v0.3.2 EXE was checked with SDK environment variables cleared and fresh preferences: it selected separately installed portable tools, found an authorized physical device and completed diagnostics without errors. Tool discovery does not repair a dropped ADB session or phone authorization. Both were separately observed during development; no old-host GUI or port collision was found, and not every historical failure is attributed to AppData virtualization. If Windows sees the USB interface but the app reports no authorized phone, check the phone's current debugging approval and data connection; avoid restarting a shared ADB server that other tools may use.

A bounded phone-first test on the Huawei succeeded when PC streaming started 6.08 seconds after the phone attempt: connection arrived at 7.67 seconds from phone startup. This verifies that startup order in one run, not a persistent background retry or long-duration guarantee. See [version-scoped validation](VALIDATION.md).

### iPhone / iPad: first setup and present limits

**The iOS USB path currently has software bridge / fake-device tests, not a successful real-iPhone USB test.** A Simulator, unsigned device build or connected charging cable does not establish hardware compatibility. Check [iOS build and signing](IOS.md) and [compatibility records](COMPATIBILITY.md) for the current evidence.

1. Build and sign the iOS app for your device using Xcode on a Mac, following [the iOS guide](IOS.md). The source ZIP needs your Apple signing. A Simulator ZIP runs in the matching Mac Simulator and cannot be installed on an iPhone. The app requires iOS / iPadOS 15 or newer.
2. On Windows, install Apple's **Apple Devices** app and its Apple Mobile Device support. Connect one iPhone / iPad with a data cable, unlock it, approve **Trust This Computer**, and confirm that Apple Devices recognizes it. See Apple's [Windows device guide](https://support.apple.com/guide/devices-windows/welcome/windows) and [USB recognition / Trust instructions](https://support.apple.com/en-us/108643).
3. Keep automatic USB detection enabled and open the matching signed iOS app in the foreground. Select the screen / region, then press **Connect / Start streaming** on the PC or **Connect** on iOS. Startup opens foreground control only; an explicit action opens video and sends readiness through the paired Apple USB tunnel before host startup. Use the matching candidate viewer and PC relay, which add this pre-handshake. No IP / six-digit code is entered.
4. Keep the app visible and unlocked. Disconnect stops video and clears its texture; foreground control remains for a later PC Connect. Backgrounding stops both listeners. Return and connect explicitly; Windows cannot launch a background iOS app. Automatic selection supports **one attached iPhone / iPad**.

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

iOS separates foreground control at phone loopback `127.0.0.1:18767` from explicitly opened video at `127.0.0.1:18766`. PC Connect sends one framed JSON `{v:1,type:"connect"}` to control; detection never sends wake requests. After video accept the unique phone peer sends the same readiness before host hello. The relay requires and consumes readiness within two seconds, then can request the host coordinator and waits up to eight seconds for that same request to succeed. TCP acceptance without readiness cannot restart a stopped host. PC Stop gates old attempts and sends one stop control; the phone closes video and clears output before acknowledging stopped. Only that ACK or paired explicit port refusal clears the gate; timeout/service failure cannot. New PC Connect replaces it. Frames use a four-byte big-endian length including one-byte kind: `1` JSON, `2` JPEG, length `1…8 MiB`; JSON is at most 16 KiB. This framing is separate from usbmux plist messages. See [protocol](PROTOCOL.md) and [third-party notices](../THIRD_PARTY_NOTICES.md).

### Saved view profiles and Reset (v0.3)

A saved phone VR profile applies only after valid host hello through normal synchronization; it neither starts capture nor arms input. Drafts stay local. Reset returns English / USB and disconnects; connect explicitly. Android fresh startup can wait for an existing stream, while iOS fresh startup opens foreground control only. PC reset preserves the screen / region and ADB path, returns USB selection to automatic and preserves platform authorization / tools. See [editing](EDITING.md).

---

<!-- vrization:chinese -->
## 简体中文

Windows 电脑端、Android 端和 iOS 端都默认优先 USB。需要支持数据传输的线缆以及相应平台授权。原生 USB 传输不要求开启热点、USB 网络共享或连接同一 Wi-Fi。每次使用一部手机，电脑端同时接受一个观看端。

**v0.3.3 候选行为：** 自动检测只寻找已授权设备，不主动开始采集。完成设置后先选屏幕／选区，再在电脑点“**连接 / 开始串流**”，或 Android 点“**检测 USB 并连接**”／前台 iOS 点“**连接**”；任一明确动作都可请求主机启动，已有活动会话保持。全新 Android 启动可等待已有串流，iOS 初次仅开放控制。后台返回或切换语言后需主动连接。候选仍待最终原生／设备验证，旧版行为见[验证记录](VALIDATION.md)。USB 不自动授权第一人称鼠标，仍需电脑主动允许，并可按 **F8** 停止。

### 找到电脑端 USB 控件与状态

点击电脑顶部连接卡片的“**USB 连接…**”可直接打开 USB 控件；也可以选择“**串流设置**”页，向下滚动到“**USB 连接**”区域。保持勾选“**自动检测已授权的 USB 手机（推荐）**”；设备选择框与“**选择官方 SDK 中的 adb.exe…**”按钮也在这里。

USB 状态位于顶部连接卡片、电脑地址和连接提示下方，状态变化也会显示在底部活动日志。“**等待手机连接**”只代表串流服务在等待观看端，不表示 USB 已经就绪。开始串流后，先确认电脑显示“**安卓 USB 已就绪：…**”；若手机首次尝试已结束，再点“**检测 USB 并连接**”。如果电脑提示 USB 已关闭、不可用、等待中或端口冲突，先按该提示排查，再在手机重试。

### Android：首次设置

1. 在手机安装发布版 Android APK。软件最低支持 Android 6.0 / API 23；实际衍生系统和设备验证见 [兼容性记录](COMPATIBILITY.md)。
2. 点“**USB 连接… → 下载官方安卓 USB 工具…**”，在 Google 阅读 / 接受条款，下载官方 [Windows Platform Tools](https://developer.android.com/tools/releases/platform-tools)。点“**导入已下载的 USB 工具 ZIP…**”，选择已校验的 **37.0.1** ZIP 和另行安装目录；导入核对包、保留完整 NOTICE 与已有安装，不替你下载或接受条款。也可自行解压官方工具，再“**选择官方 SDK 中的 adb.exe…**”，保留整个工具文件夹。VRization 不附带 `adb.exe`、SDK 或驱动，打包应用本身无需 Python / 开发环境。
3. 在手机启用开发者选项和 **USB 调试**，接入数据线，解锁手机并允许此电脑进行 USB 调试。不同厂商的菜单和驱动要求不同；若 Windows 未识别调试接口，使用该厂商的 USB 驱动。Google 的 [ADB 设置指南](https://developer.android.com/tools/adb#Enabling) 说明了设备授权。
4. 电脑保持勾选“**自动检测已授权的 USB 手机（推荐）**”。只有一台已授权 Android USB 设备时自动选择；多台时在 USB 设备列表选择目标序列号。此 USB 检测排除模拟器和无线 ADB。
5. 选屏幕／选区，Android 打开应用并选“**USB 数据线 · 默认**”；电脑点“**连接 / 开始串流**”，或 Android 点“**检测 USB 并连接**”。候选支持任一端主动连接，无需 IP 或六位码。

以后接线、解锁，用任一端主动连接即可，数据线可以一直插着。断开后应清画面并停止实时帧，不能只看按钮文字。手机视频 `18765` 或控制 `18764` 被占用会报告冲突并保留映射；只移除本项目创建且仍拥有的映射。

### 便携工具与不同 Windows 启动环境

若只有从开发 / 打包应用内启动才能连接 USB，先看电脑显示的官方工具路径。打包应用虚拟化 AppData 内的 SDK 可能不被普通双击进程看到；用导入器或手动选择普通文件夹中的官方安装。独立 EXE 默认用旁边 `tools/android-sdk`，已管理归档放根目录、在 `latest` 之外；启动器只为子应用有条件设置 SDK 变量。更新时保留另装工具目录。这改的是工具发现，不是设备信任，手机仍需授权 USB 调试，见 [下载 / 归档结构](DOWNLOADS.md)。

打包 v0.3.2 EXE 已在清空 SDK 环境变量、使用新偏好时检查：选中另行安装的便携工具，识别已授权真实设备，诊断完成且无错误。工具发现不会修复掉线的 ADB 会话或手机授权；开发期间两种问题另有实际观察，未发现旧电脑端界面或端口冲突，不能把全部历史故障归因于 AppData 虚拟化。Windows 能看到 USB 接口而软件没有已授权手机时，核对手机当前调试批准和数据连接；避免重启其他工具共用的 ADB 服务。

华为一次有限的手机先启动检查通过：手机尝试后 6.08 秒才开始电脑串流，手机启动后 7.67 秒连接成功。这验证该次启动顺序，不是持续后台重试或长期连接保证。见 [按版本记录的验证](VALIDATION.md)。

### iPhone / iPad：首次设置与当前限制

**目前 iOS USB 仅有软件桥接 / 假设备测试，尚无真实 iPhone USB 成功测试。** 模拟器、未签名真机 SDK 构建或接上充电线都不等于硬件兼容性验证。当前证据见 [iOS 构建与签名](IOS.md) 和 [兼容性记录](COMPATIBILITY.md)。

1. 按 [iOS 教程](IOS.md) 在 Mac 上用 Xcode 为设备构建并签名。源码 ZIP 需要使用自己的 Apple 签名。模拟器 ZIP 只用于匹配的 Mac 模拟器，不能安装到 iPhone。应用要求 iOS / iPadOS 15 及以上。
2. Windows 安装 Apple 的 **Apple Devices** 软件及其 Apple Mobile Device 支持。只接一台 iPhone / iPad，使用数据线、解锁并允许“**信任此电脑**”，确认 Apple Devices 能识别设备。参见 Apple 的 [Windows 设备指南](https://support.apple.com/guide/devices-windows/welcome/windows) 与 [USB 识别 / 信任说明](https://support.apple.com/en-us/108643)。
3. 电脑保持自动 USB 检测，前台打开匹配版本、已签名的 iOS 应用。先选屏幕／选区，再在电脑点“**连接 / 开始串流**”或 iOS 点“**连接**”。应用初次只开放控制，明确动作才开放视频，经已配对 Apple USB 隧道发送就绪消息后请求主机启动。新增预握手需匹配候选观看端与电脑中继，无需 IP／六位码。
4. 保持前台和解锁。断开停止视频并清纹理，保留前台控制供下一次电脑连接；后台停止两个监听。回前台后主动连接，Windows 不能启动后台 iOS 应用。自动选择只支持**连接一台 iPhone／iPad**。

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

iOS 在手机回环 `127.0.0.1:18767` 监听前台控制，在 `127.0.0.1:18766` 监听明确开放的视频。电脑主动连接对控制发送一次 framed JSON `{v:1,type:"connect"}`，检测不发送唤醒。视频接受唯一连接后，手机在 host hello 前发送同样就绪；中继两秒内校验消费，再请求主机协调器，最多等待八秒使同一身份成功。仅 TCP 接受而无就绪不能恢复已停止主机。电脑停止门控旧尝试、发送一次 stop；手机关视频并清画面后才确认 stopped。仅该确认或已配对端口明确拒绝解除门控，超时／服务失败不能；新电脑主动连接可替代它。四字节大端长度包含一字节类型：`1` JSON、`2` JPEG，长度 `1…8 MiB`，JSON 最多 16 KiB；与 usbmux plist 分帧不同。见[协议](PROTOCOL.md)和[鸣谢](../THIRD_PARTY_NOTICES.md)。


### 保存观看配置与重置（v0.3）

保存 VR 配置仅在合法 host hello 后正常同步，不启动采集或授权输入；草稿仅本地。重置恢复英文／USB 并断线，随后主动连接。全新 Android 可等待已有串流，iOS 全新启动仅开放控制。电脑重置保留屏幕／选区和 ADB 路径，设备选择恢复自动并保留平台授权／工具。见[编辑](EDITING.md)。

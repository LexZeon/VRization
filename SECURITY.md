# 🔒 Security / 安全说明

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

v0.3.0-alpha defaults to authorized USB connections, with a trusted-LAN alternative. The host sends its selected display / region to one connected viewer, and First-person mode can move the PC mouse only after local authorization. USB pairing does not start PC streaming or grant mouse control.

### Connection boundaries

- Android USB requires a data cable, USB debugging and the phone's approval of this PC. Use official Platform Tools and an appropriate OEM driver; VRization does not install a driver, root a phone or change debugging authorization. It excludes emulator / wireless transports, uses `--no-rebind`, and removes only its own still-matching reverse mapping.
- Android bootstrap returns a code only while an authorized physical USB mapping is owned. It requires a loopback peer, a single loopback Host / allowed port, no Origin header, and a running host. Replies use `no-store` / `nosniff`; there is no CORS permission. It is disabled by default in embedded hosts. These checks do not protect against malicious software already running on the PC with local access.
- iOS USB requires Apple Mobile Device support and an existing local trust pairing record. The app listens only on phone loopback while foreground; Windows checks USB connection type and reads the pairing record before connecting. VRization does not send Pair / Trust / SavePairRecord, request Apple credentials or save / display pairing-record keys. This is not a claim of an independently audited cryptographic trust protocol.
- USB uses the platform's authorized tunnel, without adding application-level encryption. The GUI host still listens on its configured network interface (default `0.0.0.0:8765`); selecting USB on the phone does not disable the LAN listener. USB requires no inbound LAN firewall rule. Keep unnecessary LAN access blocked.
- LAN WebSockets are unencrypted (`ws://`); network attackers can potentially read images, settings and the code.
- A six-digit pairing code is basic access control, not TLS, strong authentication or a trusted network.
- Do not forward ports, expose the host to the internet or use public Wi-Fi.
- Allow only necessary private-network firewall access and stop streaming when finished.
- Close private windows before sharing. A capture region can reveal other content after windows move.

Do not publish authenticated WebSocket URLs, pairing codes, device serials, Apple pairing records, signing certificates or provisioning profiles in diagnostics. The iOS relay reports safe HTTP status / connection failures without including its authenticated URL. Bounded USB frames and v1 message validation reduce malformed-input exposure; they do not replace review of a concrete build. See [USB setup](docs/USB.md), [protocol](docs/PROTOCOL.md) and [validation](docs/VALIDATION.md).

### Input control

The phone cannot arm mouse input. First-person mode, a valid connection, live pose and explicit PC authorization are required together. After arming, switch to the game within five seconds. **F8** stops control. Mode changes, disconnects, host stop and desktop language changes require fresh authorization; stale pose or a foreground-window change also disarms. Phone backgrounding / language changes end the session and require explicit reconnection. Test directions, sensitivity and the stop key on a desktop / offline application first. Games may reject system mouse input; VRization does not bypass game protection.

The Windows target is 10 / 11 x64. Recorded local tests use Windows 11. Huawei Android hardware evidence and the iOS fake-usbmux / Simulator evidence are separate; no physical iPhone, real FPS game or viewer-optics security / compatibility pass is implied.

### Reporting

Use Issues for ordinary bugs. For pairing bypass, unauthorized input, code execution or screen leakage, prefer **Security → Report a vulnerability** when the maintainer enables private reporting. If unavailable, open an Issue requesting a private contact only; do not publish exploits, private data or pairing codes.

This alpha has no formal security-maintenance SLA. Include version, OS, minimal reproduction conditions and possible impact, with real IP addresses, codes and private screens removed.

### Editor / reset and local preference boundaries

Editor dragging sends no settings and writes no preferences. Phone poses pause; editor entry stops new poses and drops application-pending pose work (already submitted transport bytes cannot be recalled) and sends one disarm-only hello with `editing: true`, while video / ping may continue. Desktop entry also disarms input. Leaving / saving never re-arms it. Discard restores the entry snapshot. Committed local phone profiles are restored only after a validated hello through ordinary bounded settings messages; pairing secrets remain excluded. Reset does not grant control or platform trust. The PC preserves the explicitly selected capture display / region and configured ADB path to avoid sharing an unintended output or changing installed tools. Phone reset disconnects without automatic reconnection. See [editor scope](docs/EDITING.md).

---

<!-- vrization:chinese -->
## 简体中文

v0.3.0-alpha 默认已授权 USB 连接，也可选择可信局域网。服务器把电脑选定显示器 / 区域发给一个观看端；第一人称鼠标功能须电脑主动授权。USB 配对不自动开始电脑串流，也不授予鼠标控制。

### 连接边界

- Android USB 要求数据线、USB 调试及手机对电脑的授权。使用官方 Platform Tools 和合适的 OEM 驱动；VRization 不安装驱动、不 root 手机、不改变调试授权。排除模拟器 / 无线连接，使用 `--no-rebind`，只移除仍匹配的自有 reverse 映射。
- Android bootstrap 只在主机拥有已授权真实 USB 映射时返回配对码；要求回环来源、单个回环 Host / 允许端口、无 Origin 及主机运行。响应使用 `no-store` / `nosniff`，不授予 CORS；嵌入主机默认关闭。这些检查不防御已经在电脑本地运行、具备本机访问能力的恶意软件。
- iOS USB 要求 Apple Mobile Device 支持及已有本地信任配对记录。手机只在前台监听回环，Windows 检查 USB 类型并读取配对记录后连接。VRization 不发送 Pair / Trust / SavePairRecord，不索取 Apple 凭据，不保存 / 显示配对记录密钥；这不代表一个已独立审计的密码学信任协议。
- USB 使用平台授权隧道，没有额外应用层加密。界面主机仍监听已配置网络接口（默认 `0.0.0.0:8765`）；手机选择 USB 不会关闭局域网监听。USB 无需开放局域网入站防火墙端口，保持不必要的网络访问被阻止。
- 局域网使用明文 WebSocket (`ws://`)；画面、设置和配对码可能被同网段攻击者读取。
- 六位配对码是基础访问控制，不能替代 TLS、强身份认证或可信网络。
- 不要在路由器上做端口转发，不要直接暴露到公网，也不要在公共 Wi-Fi 上使用。
- 防火墙只允许必要的专用网络。结束使用后停止串流。
- 共享电脑画面前关闭不想暴露的窗口；选区可能因窗口移动而显示其他内容。

诊断中不要公开带认证的 WebSocket 链接、配对码、设备序列号、Apple 配对记录、签名证书或描述文件。iOS 中继只报告安全的 HTTP 状态 / 连接错误，不包含认证 URL。USB 长度限制与 v1 校验减少畸形输入风险，不能代替具体发行构建审查。参见 [USB 教程](docs/USB.md)、[协议](docs/PROTOCOL.md)、[验证记录](docs/VALIDATION.md)。

### 输入控制

手机不能自行授权电脑鼠标。必须同时满足 第一人称模式、有效连接、实时姿态和电脑主动授权；授权后五秒内切到游戏，按 **F8** 停止。切换模式、断线、停止主机、电脑切换语言后均需重新授权；姿态超时或前台窗口改变也会解除。手机进入后台 / 切换语言会结束会话，需显式重连。先用桌面或离线应用检查方向、灵敏度与停止键，再进入游戏。游戏可能拒绝系统鼠标输入，VRization 不绕过游戏保护。

Windows 目标为 10 / 11 x64，本地已记录测试来自 Windows 11。华为 Android 硬件证据与 iOS 假 usbmux / 模拟器证据分开记录，不表示真实 iPhone、真实 FPS 游戏或盒子镜片的安全 / 兼容性已经通过。

### 报告问题

普通功能问题请开 Issue。涉及绕过配对、未授权输入、远程代码执行或画面泄漏的问题，请优先使用 GitHub 仓库 **Security → Report a vulnerability**（仓库维护者启用私密报告后可用）。若入口尚未启用，可先开一个仅请求私密联系渠道的 Issue，不公开利用步骤、个人数据或配对码。

该 Alpha 没有正式安全维护 SLA。报告中请包含版本、操作系统、最小复现条件和可能影响，移除真实 IP、配对码和屏幕私密内容。


### 编辑 / 重置与本地偏好边界

编辑拖动不发设置、不写偏好。手机暂停姿态，进入时丢弃应用层待发姿态（已提交传输层字节无法撤回）并用 hello 一次发送仅解除授权的 `editing: true`；视频 / ping 可继续，电脑进入也解除授权。退出 / 保存不重新授权；放弃恢复进入快照。手机已提交本地配置只在合法 hello 后通过普通有界设置消息恢复，排除配对秘密。重置不授予控制或平台信任；电脑保留明确的采集显示器 / 选区与 ADB 路径，避免分享非预期画面或改变工具。手机重置断线、不自动重连，见 [编辑范围](docs/EDITING.md)。

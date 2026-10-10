# 🔌 VRization v0.3.3-alpha — release notes / 发布说明

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

Windows, Android and iOS application labels are **0.3.3** (mobile build **6**). Protocol v1, saved profiles, viewer fitting, all-mode bounds and default-off stabilization remain compatible. **Candidate: final packaged and hardware acceptance is pending.**

### Connection and stopping

- Explicit USB **Connect** on the phone can request PC streaming; PC **Connect / Start streaming** can notify the selected authorized phone. Automatic detection alone never starts capture or mouse input. iOS requires the app in the foreground and existing Apple pairing.
- Control is separate from video: Android control `18764` and video `18765`; iOS foreground control `18767` and video `18766`. The PC video listener still stops when Stop is pressed. These ports are local USB endpoints, not additional public LAN listeners.
- ADB cold startup and recovery receive an eight-second budget, with bounded failure backoff; successful normal queries retain the shorter budget. A failed reverse-map query keeps the instance's ownership claim until cleanup is conclusively known. Foreign mappings are never overwritten or removed.
- Android owns and cancels every actual socket. Connection-attempt and socket generations reject late callbacks, retries and decoded frames; explicit Disconnect clears output and stops pose transmission. USB requests bypass HTTP proxies without changing LAN behavior.
- PC Stop immediately disables sending and input, closes the viewer, and waits for capture/network cleanup. Restart remains unavailable while cleanup is incomplete. Disconnection clears displayed statistics; late events from older sessions cannot restore them.
- A repeated PC Connect must preserve an already connected phone's session and pose center. A queued or failed connection request cannot revive a later explicit stop.

### Masked desktop capture and phone version

Windows already blacks out protected regions in the DXGI surface. The earlier host incorrectly treated its `ProtectedContentMaskedOut` flag as a fatal whole-stream error. The new capture uses exactly that OS-masked surface, leaves protected regions black, and reports masking without switching APIs or reopening protected content. Layout changes, output access loss and actual resource failures still stop the session. Both phone UIs show the installed version/build from package metadata.

### Reuse and AI handoff

The [AI handoff](../AI_HANDOFF.md) explains each module, ownership, entry points, transport flow, commands and a copyable continuation prompt in both languages. The host connection coordinator is separate from capture/video. Android `vr-core` exposes pure connection-attempt, socket-ownership, endpoint and request-policy helpers alongside the existing renderer and pose/fit core. See [architecture](ARCHITECTURE.md) and [protocol](PROTOCOL.md).

### Verified causes and limits

The observed ADB log repeatedly showed startup-handshake failure after approximately three seconds, matching the old command timeout. Reverse-map ownership loss is also a reproducible code path. These explain specific recovery failures; they do not prove a single cause for every historical USB incident.

At the inspected old PC Stop, port 8765 was closed even though old FPS/bitrate text remained. A separate synthetic slow-capture-close test reproduced the old host returning Stopped while its capture worker still existed. Button text, stale statistics and a successful build alone are insufficient acceptance evidence.

Final acceptance results will be recorded here before publication. Physical iPhone USB and real game input are not established by Simulator or synthetic tests. No new end-to-end latency/FPS guarantee follows from these lifecycle changes. See [validation](VALIDATION.md), [compatibility](COMPATIBILITY.md) and [performance](PERFORMANCE.md).

### Updating and publication

Close the earlier host, extract the complete Windows ZIP and use its launcher. Update Android in place with the same public certificate; keep application data. The publication gate uses official `apksigner` and rejects a different/random CI debug signer. Only the public fingerprint is stored in source; private signing keys are never published. Keep verified checksums, historical releases and separately installed USB tools. iOS source requires Xcode/Apple signing; the Mac Simulator archive is not an iPhone installer.

[USB guide](USB.md) · [iOS guide](IOS.md) · [v0.3.2 archived notes](releases/v0.3.2-alpha.md) · [Changelog](../CHANGELOG.md)

---

<!-- vrization:chinese -->
## 简体中文

Windows、Android 与 iOS 应用版本均为 **0.3.3**，手机构建号 **6**。协议 v1、保存的配置、画面编辑、所有模式的显示范围和默认关闭的防抖继续兼容。**当前为候选，最终打包与真机验收待完成。**

### 连接与停止

- 手机主动点击 USB“**连接**”可请求电脑开始串流；电脑“**连接 / 开始串流**”可通知已选中且授权的手机。自动检测本身不会启动采集或鼠标控制。iOS 需要应用在前台并已有 Apple 配对。
- 控制与视频分离：Android 控制 `18764`、视频 `18765`；iOS 前台控制 `18767`、视频 `18766`。电脑 Stop 仍关闭视频监听。这些是本地 USB 端点，不是新增局域网公开监听。
- ADB 冷启动 / 恢复最多等待八秒，失败采用有限退避，正常成功查询保留较短等待。映射查询失败时保留本实例的归属记录，直到确定清理结果；不会覆盖或删除其他程序的映射。
- Android 持有并取消每个真实 socket；连接尝试和 socket 两层代际校验拒绝迟到回调、重试与解码帧。主动断开清空画面并停止姿态发送；仅 USB 请求绕过 HTTP 代理，局域网策略保留。
- 电脑 Stop 即时停止发送 / 输入并关闭观看会话，等待采集与网络清理完成后才能重开。断线清空统计，旧会话迟到事件不能重新填回。
- 重复电脑连接请求应保留手机已连接的会话与姿态中心。排队或失败的旧连接请求不能复活之后的主动停止。

### 系统遮罩画面与手机版本号

Windows 已在 DXGI 画面中把受保护区域遮黑，旧电脑端却把 `ProtectedContentMaskedOut` 标志当成整次串流的致命故障。新版直接使用系统已经遮罩的画面，受保护区域保持黑色，提示遮罩但不换接口或重读受保护内容。显示布局变化、输出访问丢失及真实资源故障仍停止会话；两个手机界面也从安装包信息显示版本 / 构建号。

### 复用与 AI 接手

[AI 接手指南](../AI_HANDOFF.md) 以中英双语解释每个模块、资源归属、入口、连接流程、命令，并提供可复制的继续开发提示词。电脑连接协调器独立于采集 / 视频；Android `vr-core` 除原有渲染、姿态和画面几何外，还提供纯连接尝试、socket 归属、端点与请求策略辅助类。见 [架构](ARCHITECTURE.md) 与 [协议](PROTOCOL.md)。

### 已确认原因与限制

现场 ADB 日志多次在约三秒后出现启动握手失败，与旧命令超时吻合；映射归属丢失也有可复现代码路径。这解释了具体恢复故障，不能断言全部历史 USB 问题都来自同一个原因。

检查旧电脑 Stop 时，8765 已关闭，但旧帧率 / 码率文字仍在。独立的合成慢采集清理测试复现旧版宣布停止时采集线程仍未结束。按钮文字、旧统计和构建通过都不足以证明验收成功。

发布前会在这里补齐最终验收结果。模拟器与合成测试不代表真实 iPhone USB 或实际游戏输入，本次生命周期修复没有新增端到端延迟 / 帧率保证。见 [验证](VALIDATION.md)、[兼容性](COMPATIBILITY.md) 与 [性能](PERFORMANCE.md)。

### 更新与发布

关闭旧电脑端，完整解压 Windows ZIP 后运行启动器。Android 使用相同公开证书覆盖升级，保留应用数据；发布门槛调用官方 `apksigner`，拒绝不同 / 随机 CI 调试签名。仓库仅保存公开指纹，不公开私有签名密钥。保留校验值、历史版与独立 USB 工具。iOS 源码需要 Xcode / Apple 签名，Mac 模拟器包不能作为 iPhone 安装器。

[USB 教程](USB.md) · [iOS 教程](IOS.md) · [v0.3.2 历史说明](releases/v0.3.2-alpha.md) · [版本日志](../CHANGELOG.md)

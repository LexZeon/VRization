# 🔌 VRization v0.3.1-alpha — release notes / 发布说明

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

This is a **Windows USB connection patch**. The Windows host is **0.3.1**; Android and iOS applications remain **0.3.0** and use the unchanged protocol v1. **An existing v0.3.0 phone installation does not need reinstalling or upgrading for this patch.** Visual headset editing, saved profiles, capture defaults and the PC-only FPS authorization boundary are retained. The original [v0.3.0-alpha notes](releases/v0.3.0-alpha.md) preserve that release's completed checks and measurements.

### Changes

- Background ADB commands use an independent null standard input, avoiding reliance on a missing or invalid input handle inherited from the Windows launcher.
- Official ADB discovery includes the already managed SDK installation. An explicitly selected official `adb.exe` remains supported; Platform Tools and USB drivers are not bundled.
- The PC's top connection card offers **USB connection…**, opening the Stream tab at its USB controls. USB status changes also appear in the bottom activity log. The [USB guide](USB.md) shows where to find the automatic-detection checkbox, official ADB selector and readiness status.

### Verification and limits

The Windows candidate passed **157 tests plus 36 subcases**, and its source check matched 15 project modules. A controlled native experiment with an invalid standard-input handle failed with the former ADB launch behavior and detected the authorized USB phone with the new behavior. This is evidence for the robustness fix, **not proof of the precise original GUI failure**. The local machine already had a configured SDK; the additional discovery path is not established as the cause of that failure.

The candidate launched through the ordinary Windows GUI, automatically established the phone's `18765` → host `8765` reverse mapping, and returned USB bootstrap **HTTP 200**. After the user selected **Start streaming** and connected on the Huawei, host health reported **connected=true**. The user confirmed that the phone showed the stream and the experience was good. This establishes the observed connection / visible-image result; **no new quantitative FPS or latency measurement was made for this patch**.

Historical v0.3.0 hardware / Simulator results remain scoped to that release. Physical iPhone USB, headset optics, real FPS game input and end-to-end latency remain unverified. This patch does not claim a complete Windows editor GUI acceptance. See [historical validation](VALIDATION.md), [performance boundaries](PERFORMANCE.md) and [compatibility](COMPATIBILITY.md).

### Assets and update steps

| Asset | Version / update scope |
| --- | --- |
| `VRization-Windows-x64.zip` | Updated Windows host **0.3.1** and documentation. Extract the complete archive and run its `VRization-Host.exe`. |
| `VRization-Android-debug.apk`, `VRization-vr-core-alpha.aar` | The verified **0.3.0** assets are reused byte for byte with the same SHA-256 values. Existing phone installs can stay in place. |
| `VRization-iOS-Simulator.zip` | The verified **0.3.0 / build 4** arm64 Simulator asset is reused unchanged. It is not an iPhone installer. |
| `VRization-iOS-source.zip` | Regenerated source bundle includes the updated desktop / documentation; the iOS application's version remains **0.3.0 / build 4**. Physical installation still needs your Apple signing. |
| `VRization-Licenses.zip`, `SHA256SUMS.txt` | License notices and the manifest for this release's exact assets. Check the manifest when downloading. |

Close the old Windows host before using the new one. Keep the complete extracted folder and the separately installed Microsoft Visual C++ v14 x64 runtime. Leave the existing Android app and its saved profiles installed. Open **USB connection…**, keep automatic USB detection enabled, and check for **Android USB ready: …** before retrying **Detect USB and connect** on the phone. Follow [the USB prerequisites](USB.md) and [download / archive instructions](DOWNLOADS.md); preserve the old verified release archive.

USB connection never authorizes PC mouse input. FPS still requires explicit PC arming, and **F8** stops it. LAN remains optional and uses unencrypted `ws://` on trusted networks.

[v0.3.0-alpha](releases/v0.3.0-alpha.md) · [v0.2.0-alpha](releases/v0.2.0-alpha.md) · [Release history](releases/README.md)

---

<!-- vrization:chinese -->
## 简体中文

本版是 **Windows USB 连接补丁**。电脑端为 **0.3.1**，Android 与 iOS 应用仍为 **0.3.0**，使用不变的协议 v1。**手机已经安装 v0.3.0 时，本补丁无需重装或升级手机软件。** 可视盒子编辑、配置保存、采集默认与电脑主动授权 FPS 的边界继续保留。[v0.3.0-alpha 原说明](releases/v0.3.0-alpha.md) 保留该版已完成的检查和测量。

### 修改内容

- 后台 ADB 命令使用独立的空标准输入，不依赖 Windows 启动环境传入的缺失或无效输入句柄。
- 官方 ADB 发现包含已管理的 SDK 安装位置，仍支持手动选择官方 `adb.exe`；不附带 Platform Tools 或 USB 驱动。
- 电脑顶部连接卡片新增“**USB 连接…**”，直接打开串流设置页的 USB 控件；USB 状态变化也写入底部活动日志。[USB 教程](USB.md) 说明自动检测开关、官方 ADB 选择及就绪状态的位置。

### 检查与限制

Windows 候选通过 **157 项测试及 36 个子项**，源代码核对匹配 15 个自有模块。受控原生无效标准输入句柄实验中，旧 ADB 启动方式失败，新方式能识别已授权 USB 手机。这证明稳健性修复的作用，**不等于证明原电脑界面故障的精确原因**。本机已有配置好的 SDK，不能把新增发现路径认定为当时故障的原因。

候选通过普通 Windows 界面启动后，自动建立手机 `18765` → 电脑 `8765` 反向映射，USB bootstrap 返回 **HTTP 200**。用户点“**开始串流**”并在华为连接后，主机 health 显示 **connected=true**。用户确认手机可以看到串流，且效果不错。这证明本次观察到的连接 / 可见画面结果，**本补丁没有新增定量 FPS 或延迟测量**。

历史 v0.3.0 真机 / 模拟器结果仍只证明对应版本。真实 iPhone USB、盒子镜片、真实 FPS 游戏输入与端到端延迟仍未验证，本补丁不宣称已完整交互验收 Windows 编辑器界面。参见 [历史验证](VALIDATION.md)、[性能边界](PERFORMANCE.md) 与 [兼容性](COMPATIBILITY.md)。

### 产物与更新步骤

| 产物 | 版本 / 更新范围 |
| --- | --- |
| `VRization-Windows-x64.zip` | 更新后的 **0.3.1** 电脑端与文档。完整解压，运行其中的 `VRization-Host.exe`。 |
| `VRization-Android-debug.apk`、`VRization-vr-core-alpha.aar` | 原样复用已验证 **0.3.0** 产物，字节与 SHA-256 不变；已有手机安装可保留。 |
| `VRization-iOS-Simulator.zip` | 原样复用已验证 **0.3.0 / build 4** arm64 模拟器产物，不是 iPhone 安装包。 |
| `VRization-iOS-source.zip` | 重新生成的源码包包含更新后的桌面端 / 文档，iOS 应用仍为 **0.3.0 / build 4**；真机安装仍需自己的 Apple 签名。 |
| `VRization-Licenses.zip`、`SHA256SUMS.txt` | 本次产物的许可通知与校验清单，下载后按清单核对。 |

先关闭旧电脑端，再运行新版；保留完整解压目录与另行安装的 Microsoft Visual C++ v14 x64 运行库。手机保留已有 Android 安装及保存配置。打开“**USB 连接…**”，保持自动检测 USB，确认电脑显示“**安卓 USB 已就绪：…**”，再在手机点“**检测 USB 并连接**”。按 [USB 前提](USB.md) 与 [下载 / 归档说明](DOWNLOADS.md) 使用，并保留旧版已校验归档。

USB 连接不会授权电脑鼠标；FPS 仍须在电脑主动授权，**F8** 停止控制。局域网继续可选，明文 `ws://` 仅用于可信网络。

[v0.3.0-alpha](releases/v0.3.0-alpha.md) · [v0.2.0-alpha](releases/v0.2.0-alpha.md) · [发布历史](releases/README.md)

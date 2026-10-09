# 🎯 VRization v0.3.2-alpha — release notes / 发布说明

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

This version updates the Windows host, Android app / library and iOS app to **0.3.2**, retaining **protocol v1**. It adds adjustable First-person gyro stabilization with **0% as the default**, preserving the previous unfiltered behavior, and improves USB tools setup for an ordinary downloaded Windows application. Windows / Android build and test jobs, clean-environment packaged USB discovery and physical Huawei settings acceptance passed. The iOS test / build job also passed; the version-specific evidence and remaining limits are below.

### First-person stabilization

- PC and phone settings add a 0–100% stabilization slider. Only the Windows host filters phone rotation before mouse output; the phone does not filter twice. Sensitivity remains separate.
- Committed values synchronize through normal settings / acknowledgment / broadcasts and persist locally. Reset returns stabilization to zero. Earlier ten-field profiles migrate by adding zero without discarding other values.
- Settings schema 2 negotiates eleven fields inside protocol v1. New clients omit the new field for older hosts while preserving it locally and explaining that a new PC host is required. Legacy acknowledgments do not erase it.
- An initial USB ten-field hello advertising support is followed by a complete eleven-field snapshot before profile adoption / no-sensor fallback. An omitted initial field is not treated as a remote zero.
- Explicit PC arming, **F8**, focus / disconnect / capture checks and the pose watchdog remain. Filtering creates no timer-driven mouse output. Stronger smoothing can add following lag; see [the tuning guide](STABILIZATION.md).

The original filter acknowledges One Euro Filter by Géry Casiez, Nicolas Roussel and Daniel Vogel, plus the pinned BSD-3-Clause Python reference. No upstream implementation or runtime dependency is bundled. The [unchanged license and provenance](../licenses/references/README.md) are preserved; [third-party notices](../THIRD_PARTY_NOTICES.md) distinguish references from dependencies.

### Display naming and range

The visible FPS mode is renamed **First person / 第一人称**; the stored / wire identifier remains `fps` for compatibility. All phone viewing modes honor the resolved physical per-eye display rectangle, including cinema / distortion; perspective content need not fill the masked rectangle. Existing flat editor, seam contact and saved profiles remain available. A physical-device custom GLES runner passed 288 offscreen mask cases across both eyes; this is shader / pixel evidence, not headset optics or physical display-latency validation.

### USB tools and ordinary Windows launch

The complete Windows ZIP includes **Start-Windows.bat** and runs without Python or a development environment. Official Android Platform Tools and USB drivers remain separately installed. PC USB controls provide Google's download page, manual downloaded-tools ZIP import and an explicit `adb.exe` selector. Import does not accept Google's terms automatically or bundle its SDK in the release.

Tool lookup includes fixed portable locations relative to the application / managed archive, alongside explicit and environment paths. Archive launchers set SDK variables only for the child app when a separate `tools/android-sdk` exists, preserving that installation across archive updates. This avoids depending on an SDK visible only inside a packaged application's virtualized AppData. See [USB setup](USB.md) and [archive layout](DOWNLOADS.md).

Android USB detection uses a bounded attempt of up to 30 seconds, covering bootstrap discovery and the connection handshake. Success, cancellation, disconnect or backgrounding ends it; it is not permanent background reconnection. iOS retains foreground listening and explicit reconnection.

### Verification and limits

- The final packaged Windows EXE was tested with SDK variables cleared and fresh application preferences. It selected the separate portable tools beside the executable, found one authorized physical USB device and completed diagnostics without errors; no developer-SDK fallback was found. Its static audit matched 19 project modules, 47 notice files and 38 recorded native components. The public Windows ZIP also passed CI's run-without-a-developer-SDK check. Official tools remain separately installed.
- On the physical **HUAWEI Pura 70 Ultra**, the phone slider saved **50%** and synchronized to the host. A host update to **65%** persisted on the phone, survived restart and restored to the host. The earlier viewing profile was retained; no OS mouse moves were recorded. The installed APK matched the candidate's SHA-256.
- Phone-first USB retry passed: the phone started first, the test host started **6.08 seconds** later, and connection succeeded at **7.67 seconds** from phone startup (**1.59 seconds** after the host). The profile stayed unchanged and mouse output remained zero. This is one bounded startup result, not a long-duration connection guarantee.
- [Actions 37991498159](https://github.com/LexZeon/VRization/actions/runs/37991498159) passed Windows, Android, iOS and documentation jobs, including **220 Windows tests, 77 Swift core tests and five native iOS Simulator UI cases**. Simulator / unsigned device builds, both-eye LAN / simulated-USB Metal color / row-direction checks and exact seam-boundary checks passed; these are not physical-iPhone USB results. The exact official tools ZIP was imported into a separate test folder with the complete NOTICE retained; actual importer-GUI interaction is not claimed.

An earlier ordinary double-click launch with the previous builds also showed the stream after portable SDK configuration. SDK visibility across packaged-app storage was one verified discovery issue, **not a proven explanation of every historical USB failure**. Shared ADB-session / phone-authorization drops were observed separately; recovery required the user's USB-debugging toggle after one authorized restart. No old-host GUI or port collision was found. A Windows USB interface alone does not establish an online, authorized debugging channel.

Synthetic filter traces test an algorithm, not a real game or end-to-end latency. No new FPS / latency claim follows from the USB lookup fix. Earlier v0.3.0 measurements and v0.3.1 visible connection results remain in [archived notes](releases/README.md). Physical iPhone USB, viewer optics, real first-person input and end-to-end latency remain unverified; no new Windows visual-editor GUI acceptance is claimed. See [validation](VALIDATION.md), [performance](PERFORMANCE.md) and [compatibility](COMPATIBILITY.md).

### Update and assets

1. Preserve the earlier verified archive. Close the old host, extract the complete new Windows ZIP and use its launcher or EXE.
2. Update Android for the new slider. An in-place update requires the same signing certificate; retain saved profiles rather than clearing application data. Use the matching AAR for integration.
3. Use updated iOS source / arm64 Mac Simulator output. A physical iPhone still needs your Apple signing; no signed IPA is supplied.
4. Check this release's `SHA256SUMS.txt`. Application labels are 0.3.2, Android code 5 and iOS build 5. Source / license ZIPs and exact hashes belong to this release.
5. Connect through USB or explicitly selected LAN, then tune stabilization from 0%. Connection, slider changes and profile restoration never authorize PC mouse input.

For an older host, stabilization stays a local preference until a capable host is used. Both current endpoints are recommended. The earlier Windows-only v0.3.1 patch intentionally retained mobile apps 0.3.0; that policy is historical, not this update's scope.

[v0.3.1-alpha](releases/v0.3.1-alpha.md) · [v0.3.0-alpha](releases/v0.3.0-alpha.md) · [v0.2.0-alpha](releases/v0.2.0-alpha.md) · [Release history](releases/README.md)

---

<!-- vrization:chinese -->
## 简体中文

本版将 Windows 电脑端、Android 应用 / 库及 iOS 应用都更新至 **0.3.2**，保留 **协议 v1**。新增可调第一人称陀螺仪防抖，默认 **0%** 保留此前无滤波行为，并改进普通下载 Windows 应用的 USB 工具设置。Windows / Android 构建与测试、独立环境的打包 USB 发现及华为真机设置验收通过，iOS 测试 / 构建任务也通过；下方按版本记录证据与剩余限制。

### 第一人称防抖

- 电脑与手机设置新增 0–100% 滑块，仅 Windows 主机在鼠标输出前滤波，手机不重复处理；灵敏度独立调整。
- 已提交值经普通设置 / 确认 / 广播同步并本地保存，重置归零；旧十字段配置迁移时添加零，不丢其他值。
- 在协议 v1 内协商十一字段的 schema 2。新客户端向旧主机发送时去掉新字段，本地保留并提示需要新版电脑端，旧确认不会清空它。
- USB 初始十字段 hello 若声明支持，先取得完整十一字段快照再接纳配置 / 缺传感器回退，尚未发送的字段不误当成主机设置为零。
- 电脑主动授权、**F8**、焦点 / 断线 / 采集检查和姿态看门狗继续保留，不新增定时鼠标输出；更强平滑可能增加跟随迟滞，见 [调节教程](STABILIZATION.md)。

原创滤波鸣谢 Géry Casiez、Nicolas Roussel、Daniel Vogel 的 One Euro Filter 与固定版本 BSD-3-Clause Python 参考，没有引入上游实现或运行依赖。[完整许可原文与来源](../licenses/references/README.md) 随项目保留，[第三方声明](../THIRD_PARTY_NOTICES.md) 区分参考与依赖。

### 模式名称与显示范围

界面 FPS 模式改称“**First person / 第一人称**”，保存 / 协议标识仍为 `fps`，保持兼容；所有手机观看模式遵守解析后的物理单眼显示矩形，包括大屏幕 / 畸变，透视内容不一定填满遮罩范围。平面编辑、接缝相接及配置保存继续保留。真机自定义 GLES 检查通过双眼共 288 个离屏遮罩用例，这是着色器 / 像素证据，不是盒子镜片或物理屏幕延迟验证。

### USB 工具与普通 Windows 启动

完整 Windows ZIP 包含 **Start-Windows.bat**，运行无需 Python 或开发环境；官方 Android Platform Tools 与 USB 驱动仍需另行安装。电脑 USB 控件提供 Google 下载页、手动导入已下载工具 ZIP 和明确选择 `adb.exe`；导入不替用户自动接受 Google 条款，也不把 SDK 附带在发布包中。

工具查找除明确路径和环境变量外，新增相对应用 / 已管理归档的固定便携位置。归档启动器在独立 `tools/android-sdk` 存在时只为子应用设置 SDK 变量，归档更新保留该安装，避免依赖仅在打包应用虚拟化 AppData 内可见的 SDK。见 [USB 设置](USB.md) 与 [归档结构](DOWNLOADS.md)。

Android USB 检测采用最长 30 秒的有限尝试，覆盖 bootstrap 发现与连接握手；成功、取消、断线或进入后台即结束，不是无限后台重连。iOS 保留前台监听和主动重连。

### 检查与限制

- 最终打包 Windows EXE 在清空 SDK 变量、使用全新应用偏好的条件下，选中程序旁独立便携工具，识别一台已授权真实 USB 设备，诊断完成且无错误，没有找到开发 SDK 回退。静态审计匹配 19 个自有模块、47 份通知与 38 个已记录原生组件。公开 Windows ZIP 也通过 CI 的脱离开发 SDK 运行检查；官方工具仍另行安装。
- **HUAWEI Pura 70 Ultra 真机**滑块保存 **50%** 并同步主机；主机更新 **65%** 后手机保存，重启仍保留并恢复到主机。原观看配置保留，没有操作系统鼠标移动，已安装 APK 的 SHA-256 与候选一致。
- 手机先启动的 USB 重试通过：手机启动后 **6.08 秒**才启动测试主机，手机启动后 **7.67 秒**连接成功，即主机启动后 **1.59 秒**；配置不变、鼠标输出为零。这是一次有限启动检查，不是长期连接保证。
- [Actions 37991498159](https://github.com/LexZeon/VRization/actions/runs/37991498159) 的 Windows、Android、iOS、文档任务全部通过，包含 **220 项 Windows、77 项 Swift 核心和五项原生 iOS 模拟器界面用例**；模拟器 / 未签名真机目标构建、双眼局域网 / 模拟 USB 的 Metal 颜色 / 行方向及准确中缝边界检查通过，不是 iPhone 真机 USB 结果。精确官方工具包实际导入独立测试目录并保留完整 NOTICE，不宣称导入器界面交互已验收。

此前较早构建也在配置便携 SDK 后，由用户普通双击启动并确认可见画面。打包应用存储的 SDK 可见性是一个已核实的发现问题，**不能据此解释全部历史 USB 故障**。另观察到共享 ADB 会话 / 手机授权掉线，经一次授权重启后仍需用户切换 USB 调试才恢复；未发现旧电脑端界面或端口冲突。Windows USB 接口存在本身不代表调试链路在线且已授权。

合成轨迹是算法检查，不是真实游戏或端到端延迟，USB 查找修复不推导新增 FPS / 延迟结论；较早 v0.3.0 测量与 v0.3.1 可见连接保留在 [历史说明](releases/README.md)。真实 iPhone USB、盒子镜片、真实第一人称输入与端到端延迟仍未验证，不宣称新增 Windows 可视编辑器界面验收。见 [验证](VALIDATION.md)、[性能](PERFORMANCE.md)、[兼容性](COMPATIBILITY.md)。

### 更新与产物

1. 保留较早已校验归档，关闭旧电脑端，完整解压新 Windows ZIP，运行其中的启动器或 EXE。
2. 更新 Android 使用新滑块，覆盖升级需要签名一致；保留配置而不清数据，集成开发使用对应 AAR。
3. 使用更新的 iOS 源码 / arm64 Mac 模拟器产物；真实 iPhone 仍需自己的 Apple 签名，不提供签名 IPA。
4. 核对本版 `SHA256SUMS.txt`；应用版本均为 0.3.2、Android code 5、iOS build 5，源码 / 许可 ZIP 与精确哈希属于本次发布。
5. 通过 USB 或主动选择的局域网连接，防抖从零调起；连接、滑块变化和恢复配置均不授权电脑鼠标输入。

面对旧主机，防抖只保存为本地偏好，换用支持的主机后才生效；建议两端均用当前版。此前 Windows 专属 v0.3.1 有意保留 0.3.0 手机应用，该策略属于历史，不是本版更新范围。

[v0.3.1-alpha](releases/v0.3.1-alpha.md) · [v0.3.0-alpha](releases/v0.3.0-alpha.md) · [v0.2.0-alpha](releases/v0.2.0-alpha.md) · [发布历史](releases/README.md)

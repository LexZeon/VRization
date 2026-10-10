# 🌀 VRization v0.4.0 — development notes / 开发说明

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

Windows, Android and iOS applications target **0.4.0**, mobile build **8**. This version is in development; publication and verification are pending. The [published v0.3.4 notes](releases/v0.3.4-alpha.md) and all historical downloads/checksums remain preserved. Protocol v1 and the eleven-field settings schema 2 remain; enhanced-mode support is negotiated separately.

### Fourth mode: Enhanced first person

- Every eye has a fixed **1:1 physical square**. The same 2D desktop texture is resampled into it and given a curved wide-angle appearance by original GPU inverse equidistant sampling on Android GLES and iOS Metal.
- Existing scale, offsets and mirrored eye spacing remain adjustable. Corner resizing preserves the square; **Save/Discard**, local committed preferences and connected PC/phone synchronization retain their existing boundaries.
- The enhanced editor keeps the square and warp visible. Windows uses an approximate mesh over the existing latest frame at up to 10 preview updates/second; phone rendering uses the actual GPU projection. Older Cinema fitting retains its flat preview.
- Existing **FOV 50–110° (default 80°)** changes the warp span. Out-of-source samples are black, producing curved/black corners. No new setting field or OpenCV runtime dependency is added. [Projection details and tutorial](ENHANCED_FIRST_PERSON.md).
- Full screen, Cinema and ordinary First person retain their existing presentations. Enhanced viewing can work without a rotation sensor; that device cannot drive the gyro mouse. Both first-person modes use the same default-enabled Windows policy, sensitivity/stabilization and latched **F8 / PC Resume**. Mode changes, Save and reconnect do not clear a pause latch.

### Mixed-version negotiation

`fps_enhanced` is sent only after enhanced support is negotiated. LAN clients opt in with `enhancedFirstPerson=1`; client hello can send `capabilities:["enhanced-first-person"]`. Host hello advertises support, and hello/every settings snapshot explicitly confirm the negotiated `enhancedFirstPerson` boolean. After a legacy USB hello, the new phone waits for a true full snapshot before restoring an enhanced profile. A new host maps enhanced settings to ordinary `fps` for an old client; a new phone sends `fps` to an old host while retaining its own enhanced profile/rendering. Schema 2 alone does not grant the new mode. See [Protocol](PROTOCOL.md).

### Provenance, validation and future work

The user reference image informed the style only and is not redistributed. The [OpenCV 4.12.0 mathematical reference](../licenses/references/README.md#enhanced-first-person-projection) records authors, exact tag, document/source links and the root Apache/source BSD distinction; no upstream code or binaries are incorporated. VRization's mapping and square-fit implementation are original MIT code.

New-version source/build/package, native rendering and physical-device results are **pending** in [Validation](VALIDATION.md). Earlier test counts and performance results do not establish this mode's GPU output, real-phone frame rate, game feel or latency. iOS source/Simulator outputs are not signed iPhone installers. All existing files and historical releases are retained. A separate SteamVR experimental version is **planned**, not this mode or an implemented SteamVR driver. See [Roadmap](ROADMAP.md).

[Quick start](QUICKSTART.md) · [Editor](EDITING.md) · [AI handoff](../AI_HANDOFF.md) · [Changelog](../CHANGELOG.md)

---

<!-- vrization:chinese -->
## 简体中文

Windows、Android 与 iOS 应用目标版本 **0.4.0**，手机构建号 **8**。本版开发中，发布与验证待完成；[已发布 v0.3.4 说明](releases/v0.3.4-alpha.md) 和全部历史下载／哈希保持保留。协议仍 v1，十一字段配置 schema 仍 2，新模式能力单独协商。

### 第四模式：加强第一人称

- 每眼固定 **1:1 物理正方形**，把同一张二维桌面纹理重采样后呈现弯曲广角效果；Android GLES 与 iOS Metal 通过原创 GPU 逆等距采样实现。
- 仍可调缩放、偏移与镜像眼间距，角点缩放保持正方形；**保存／放弃**、本地已提交偏好和连接时电脑／手机同步沿用原边界。
- 加强模式编辑器保留正方形及变形预览；Windows 在已有最新帧上用网格近似，预览最高每秒十次，手机使用实际 GPU 投影。旧大屏幕适配继续使用平面预览。
- 已有 **视场角 50–110°（默认 80°）**改变变形范围；超出源图的采样为黑色，形成弯曲／黑角。不新增设置字段或 OpenCV 运行依赖，见 [投影与教程](ENHANCED_FIRST_PERSON.md)。
- 全屏、大屏幕、普通第一人称保留原有显示；加强模式在无旋转传感器时仍可观看，但该设备无法进行陀螺仪鼠标控制。两种第一人称共用 Windows 默认启用策略、灵敏度／防抖及锁定的 **F8／电脑恢复**；切模式、保存和重连不能解除暂停锁。

### 混合版本协商

`fps_enhanced` 仅在新模式能力协商完成后发送。局域网客户端以 `enhancedFirstPerson=1` 主动启用，也可在 hello 发送 `capabilities:["enhanced-first-person"]`；主机 hello 声明支持，hello／每条设置快照都以 `enhancedFirstPerson` 布尔值明确确认协商。旧格式 USB hello 后，新手机等待 true 完整快照再恢复加强配置。新版电脑向旧客户端把加强模式映射成普通 `fps`；新版手机对旧电脑发送 `fps`，自身仍保留加强配置／渲染。schema 2 本身不授予新模式，见 [协议](PROTOCOL.md)。

### 来源、验证与后续方向

用户参考图仅用于理解风格，不再发布。[OpenCV 4.12.0 数学参考记录](../licenses/references/README.md#enhanced-first-person-projection) 写明作者、准确标签、文档／源码地址及根 Apache／文件 BSD 区别，没有采用上游代码或二进制；VRization 的映射与正方形适配为 MIT 原创实现。

新版源码／构建／打包、原生渲染与真机结果目前在 [验证](VALIDATION.md) **待完成**；旧测试数量和性能数字不能证明此模式的 GPU 输出、真机帧率、游戏手感或延迟。iOS 源码／模拟器不是签名 iPhone 安装包。全部已有文件和历史发布保留；另行 **计划** SteamVR 实验版本，不是此模式或已实现的 SteamVR 驱动，见 [路线](ROADMAP.md)。

[快速开始](QUICKSTART.md) · [编辑器](EDITING.md) · [AI 接手](../AI_HANDOFF.md) · [版本日志](../CHANGELOG.md)

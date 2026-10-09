# 🤝 Contributing / 参与贡献

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

Contributions to quality, compatibility, controls, tutorials and reusable interfaces are welcome. Read [build](docs/BUILD.md), [architecture](docs/ARCHITECTURE.md), and [protocol](docs/PROTOCOL.md) when changing wire behavior.

### Report a problem

Include the release version, PC OS / GPU, phone and Android / derivative or iOS version, mode, dimensions, transport and reproduction steps. For USB, describe the cable, authorization, official SDK / Apple Devices version and device-count / port-conflict symptoms. Explain performance measurement methods: received FPS and ping RTT are not end-to-end video latency. Separate physical Huawei / other hardware evidence from emulators, simulated usbmux and unsigned device-SDK compilation. Remove private screens, addresses, pairing codes, serials and signing / pairing material from logs or screenshots.

### Submit code

1. Fork and create a focused branch; solve one clear problem per PR.
2. Add meaningful tests for pose, validation or authorization changes. Documentation / appearance changes do not need mechanical tests.
3. Run affected checks and describe untested hardware / platforms.
4. Update documentation and compatibility records; describe trigger, changed behavior and validation.

Retain explicit PC arming and an emergency stop. Remote clients must not unlock input themselves. Add codecs / adapters through interfaces instead of mixing platform implementations into Android `vr-core` or Swift `VRizationCore`. Preserve v1 WebSocket behavior for old Android clients; new codecs / per-eye formats require explicit negotiation. Default USB detection must not steal existing reverse ports, manage wireless ADB, kill the ADB server, create Apple trust records or start OS input automatically. Keep bootstrap local and browser-origin restrictions intact.

Host changes can be checked without a real mouse using `python -m unittest discover -s desktop/tests -v`. Android changes need affected app / core tests; Swift changes need `swift test --package-path ios` on the supported development environment. Run appropriate builds / lint when application code changes. Use fake capture, input sinks, USB mappings and mux services in automation; physical-device tests require separate evidence. The supplied Windows target remains 10 / 11 x64; do not report a Windows 10 or mixed-DPI hardware pass from unit tests alone.

### English first, Chinese below — every public page

All project-owned public documents, README files, tutorials, release notes, issue / PR templates and repository descriptions must provide complete English first and complete Chinese below on the **same page**. Keep both sections accurate when adding or changing content. Use `<!-- vrization:english -->` before `## English` and `<!-- vrization:chinese -->` before `## 简体中文` in repository pages. Run `python scripts/check_docs.py` before submitting. CI checks structure, nonempty sections and relative file links; reviewers must check meaning and completeness. Passing it does not prove translation quality.

Original license / copyright texts remain verbatim; explanatory bilingual text supplements them rather than replacing them. Do not invent a translated license as the controlling text.

English is the default and primary software language. Windows, Android and iOS applications must retain selectable Simplified Chinese and save language choice locally. Phone language / background transitions must not silently reconnect; desktop language changes must revoke input authorization.

### Attribution and licensing

Original contributions are submitted under this repository's MIT license. Before adding third-party code, assets, dependencies **or ideas used to guide an optimization**, inspect the exact upstream material's terms and record URL, author, version / commit or document, referenced idea, purpose, modifications / original rewrite and license in [third-party notices](THIRD_PARTY_NOTICES.md). Keep this credit even when no source was copied. Distinguish bundled runtime components, adapted code and research-only references. Rewriting does not remove applicable license obligations. Preserve required copyrights, NOTICE and full license texts; do not edit original upstream notices to match a project summary.

Prefer compatible commercially usable MIT, BSD or Apache-2.0 dependencies. Free installation is not a source-code commercial-use license. Explain unusual conditions in the PR; never silently copy snippets. Icons and tutorial images also need distributable provenance.

### Compatibility report

```text
VRization version:
Windows / GPU:
Phone / Android, derivative or iOS version:
Rotation sensor available:
VR viewer (optional):
Mode / dimensions / FPS / JPEG quality:
Transport (USB / LAN), SDK or Apple Devices version:
Cable / authorization / number of USB devices, or network details:
Evidence type (physical device / emulator / simulated mux):
Received FPS / ping RTT / end-to-end measurement (distinguish them):
Symptoms, reproduction, measurement method:
```

### Editor / profile invariants

Keep the shared y-up per-eye geometry, linked mirrored horizontal spacing with preserved offsetX, and center-fixed proportional corner contract in [editing](docs/EDITING.md). Compute drags from their gesture-start snapshot and preserve actual mode / optical fields in a flat preview. Drafts must not broadcast settings, persist or send poses; the entry hello editing:true is disarm-only control metadata. Save / Discard have explicit transaction boundaries. Persist committed phone settings only, validate hello before restoration with normal clientSeq synchronization, and never store pairing secrets. Reset retains PC capture selection / ADB path and cannot auto-connect or arm input. Use pure geometry / fake storage / fake transport checks, then record actual UI acceptance separately.

---

<!-- vrization:chinese -->
## 简体中文

欢迎改进画质、兼容性、设置、教程和移植接口。先读 [构建指南](docs/BUILD.md) 与 [架构](docs/ARCHITECTURE.md)；协议变更还需更新 [协议 v1](docs/PROTOCOL.md)。

### 提交问题

请提供发行版本、电脑系统 / GPU、手机及 Android / 衍生系统或 iOS 版本、模式、尺寸、传输与复现步骤。USB 问题说明数据线、授权、官方 SDK / Apple Devices 版本，以及设备数量 / 端口冲突。性能反馈区分接收帧率、ping RTT 与端到端视频延迟。华为 / 其他真机证据应与模拟器、模拟 usbmux、未签名真机 SDK 编译分开。日志 / 截图移除个人画面、地址、配对码、序列号和签名 / 配对材料。

### 提交代码

1. Fork 并创建主题分支，一次 PR 解决一个明确问题。
2. 对姿态、协议校验、输入授权等核心行为补充有意义的测试；纯文档或外观修改无需机械添加测试。
3. 运行受影响模块的检查，记录无法测试的设备与平台。
4. 更新文档与兼容性记录，PR 描述说明触发条件、行为变化和验证方法。

保留“电脑主动授权 + 紧急停止”边界，不让远程客户端自行解锁鼠标。编码器 / 适配器通过接口接入，避免把平台实现混入 Android `vr-core` 或 Swift `VRizationCore`。保留旧 Android 的 v1 WebSocket 行为，新编码 / 左右眼格式需显式协商。默认 USB 检测不得抢占已有 reverse 端口、管理无线 ADB、关闭 ADB server、创建 Apple 信任记录或自动启动系统输入；保留 bootstrap 的本机与浏览器来源限制。

主机改动可用 `python -m unittest discover -s desktop/tests -v` 检查，无需真实鼠标。Android 改动运行受影响 app / core 测试；Swift 改动在支持的开发环境运行 `swift test --package-path ios`；应用代码改动还需适当构建 / lint。自动化使用假采集、输入接收器、USB 映射与 mux 服务，实机测试另记证据。Windows 发行目标仍为 10 / 11 x64，不能仅凭单测报告 Windows 10 或混合 DPI 硬件已通过。

### 所有公共页面：完整英文在上，完整中文在下

所有项目自有公共文档、README、教程、发布说明、Issue / PR 模板与仓库简介都必须在**同一页**先提供完整英文，再提供完整中文。修改内容时同步维护两种语言。仓库页面使用 `<!-- vrization:english -->` + `## English` 和 `<!-- vrization:chinese -->` + `## 简体中文` 分区，提交前运行 `python scripts/check_docs.py`。CI 只检查结构、非空和相对文件链接；含义与完整性必须人工审阅，不能把检查通过当作翻译质量保证。

许可证与版权原文保持完整；双语解释作为补充，不制作替代原文的“译版许可证”。

软件以英文为默认和主语言，Windows、Android、iOS 均保留可选简体中文并在本地保存。手机切语言 / 进入后台不得悄悄重连；电脑切语言必须撤销输入授权。

### 来源与许可

原创贡献按本仓库 MIT 许可提交。引用第三方代码、素材、依赖或**用于指导优化的思路**时，先核对实际上游材料的条款，并在 [第三方声明](THIRD_PARTY_NOTICES.md) 记录原始 URL、作者、版本 / commit 或文档、参考思路、用途、修改 / 原创重写情况和许可文件。即使没有复制源码也保留鸣谢，区分随包运行组件、改编代码与仅研究参考；重写不消除适用许可义务。保留必要的版权、NOTICE 和许可证全文，不为配合项目摘要而修改上游声明原文。

优先采用允许商业使用的 MIT、BSD、Apache-2.0 等兼容依赖。不要把“能免费下载安装”当作代码可商用许可。新增带特殊许可条件的依赖需要在 PR 明确解释，不要悄悄复制代码片段。图标和教程截图也需要有可分发来源。

### 兼容性反馈模板

```text
VRization 版本：
Windows 版本 / GPU：
手机 / Android、衍生系统或 iOS 版本：
旋转传感器是否可用：
VR 盒子型号（可选）：
模式 / 画面尺寸 / FPS / JPEG 质量：
传输（USB / 局域网）、SDK 或 Apple Devices 版本：
线缆 / 授权 / USB 设备数，或网络条件：
证据类型（真机 / 模拟器 / 模拟 mux）：
接收帧率 / ping RTT / 端到端测量（分别填写）：
现象、复现步骤、测量方法：
```


### 编辑器 / 配置不变量

保持 [编辑合同](docs/EDITING.md) 的每眼 y 向上坐标、保留 offsetX 的水平镜像联动间距与中心固定等比角点。从手势起点快照计算拖动，平面预览保留实际模式 / 光学字段。草稿不得广播设置、持久保存或发送姿态；进入时的 hello editing:true 只是解除授权的控制元数据。保存 / 放弃有明确事务边界；只保存手机已提交设置，合法 hello 后才经普通 clientSeq 恢复，不存配对秘密。重置保留电脑采集选择 / ADB 路径，不自动连接或授权。用纯几何 / 假存储 / 假传输检查，再另记真实界面验收。

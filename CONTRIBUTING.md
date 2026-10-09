# 🤝 Contributing / 参与贡献

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

Contributions to quality, compatibility, controls, tutorials and reusable interfaces are welcome. Read [build](docs/BUILD.md), [architecture](docs/ARCHITECTURE.md), and [protocol](docs/PROTOCOL.md) when changing wire behavior.

### Report a problem

Include PC OS / GPU, phone and Android / derivative version, mode, dimensions, network and reproduction steps. Explain performance measurement methods; emulator results do not establish physical-viewer experience. Remove private screens, addresses and pairing codes from logs / screenshots.

### Submit code

1. Fork and create a focused branch; solve one clear problem per PR.
2. Add meaningful tests for pose, validation or authorization changes. Documentation / appearance changes do not need mechanical tests.
3. Run affected checks and describe untested hardware / platforms.
4. Update documentation and compatibility records; describe trigger, changed behavior and validation.

Retain explicit PC arming and an emergency stop. Remote clients must not unlock input themselves. Add codecs / adapters through interfaces instead of mixing platform implementations into `vr-core`.

### English first, Chinese below — every public page

All project-owned public documents, README files, tutorials, release notes, issue / PR templates and repository descriptions must provide complete English first and complete Chinese below on the **same page**. Keep both sections accurate when adding or changing content. Use `<!-- vrization:english -->` before `## English` and `<!-- vrization:chinese -->` before `## 简体中文` in repository pages. Run `python scripts/check_docs.py` before submitting. CI checks structure, nonempty sections and relative file links; reviewers must check meaning and completeness. Passing it does not prove translation quality.

Original license / copyright texts remain verbatim; explanatory bilingual text supplements them rather than replacing them. Do not invent a translated license as the controlling text.

English is the default and primary software language. Both applications must retain selectable Simplified Chinese and save the user's language choice locally.

### Attribution and licensing

Original contributions are submitted under this repository's MIT license. Before adding third-party code, assets or dependencies, inspect the exact upstream version's terms and record URL, author, version / commit, purpose, modifications and license in [third-party notices](THIRD_PARTY_NOTICES.md). Preserve required copyrights, NOTICE and full license texts.

Prefer compatible commercially usable MIT, BSD or Apache-2.0 dependencies. Free installation is not a source-code commercial-use license. Explain unusual conditions in the PR; never silently copy snippets. Icons and tutorial images also need distributable provenance.

### Compatibility report

```text
VRization version:
Windows / GPU:
Phone / Android or derivative version:
Rotation sensor available:
VR viewer (optional):
Mode / dimensions / FPS / JPEG quality:
Network (Ethernet / Wi-Fi band):
Symptoms, reproduction, measurement method:
```

---

<!-- vrization:chinese -->
## 简体中文

欢迎改进画质、兼容性、设置、教程和移植接口。先读 [构建指南](docs/BUILD.md) 与 [架构](docs/ARCHITECTURE.md)；协议变更还需更新 [协议 v1](docs/PROTOCOL.md)。

### 提交问题

请提供电脑系统、手机型号 / 系统版本、是否为兼容 Android 的衍生系统、模式、分辨率、网络条件和复现步骤。性能反馈应说明测量方法；不要用模拟器结果代替手机盒子实机表现。日志和截图先移除个人画面、IP 与配对码。

### 提交代码

1. Fork 并创建主题分支，一次 PR 解决一个明确问题。
2. 对姿态、协议校验、输入授权等核心行为补充有意义的测试；纯文档或外观修改无需机械添加测试。
3. 运行受影响模块的检查，记录无法测试的设备与平台。
4. 更新文档与兼容性记录，PR 描述说明触发条件、行为变化和验证方法。

保留“电脑主动授权 + 紧急停止”的输入边界。不要让远程客户端自行解锁鼠标。新增编码器或插件应通过模块接口接入，避免将平台实现混入 `vr-core`。

### 所有公共页面：完整英文在上，完整中文在下

所有项目自有公共文档、README、教程、发布说明、Issue / PR 模板与仓库简介都必须在**同一页**先提供完整英文，再提供完整中文。修改内容时同步维护两种语言。仓库页面使用 `<!-- vrization:english -->` + `## English` 和 `<!-- vrization:chinese -->` + `## 简体中文` 分区，提交前运行 `python scripts/check_docs.py`。CI 只检查结构、非空和相对文件链接；含义与完整性必须人工审阅，不能把检查通过当作翻译质量保证。

许可证与版权原文保持完整；双语解释作为补充，不制作替代原文的“译版许可证”。

软件以英文为默认和主语言。两端保留可选简体中文，并在本地保存用户的语言选择。

### 来源与许可

原创贡献按本仓库 MIT 许可提交。引用第三方代码、素材或依赖时，先核对精确版本的上游许可，并在 [第三方声明](THIRD_PARTY_NOTICES.md) 记录原始 URL、作者、版本 / commit、用途、修改情况和许可文件。保留必要的版权、NOTICE 和许可证文本。

优先采用允许商业使用的 MIT、BSD、Apache-2.0 等兼容依赖。不要把“能免费下载安装”当作代码可商用许可。新增带特殊许可条件的依赖需要在 PR 明确解释，不要悄悄复制代码片段。图标和教程截图也需要有可分发来源。

### 兼容性反馈模板

```text
VRization 版本：
Windows 版本 / GPU：
手机 / Android 或衍生系统版本：
旋转传感器是否可用：
VR 盒子型号（可选）：
模式 / 画面尺寸 / FPS / JPEG 质量：
网络（有线 / Wi-Fi 频段）：
现象、复现步骤、测量方法：
```

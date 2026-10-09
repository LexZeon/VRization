# VRization project instructions / 项目要求

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

All project-owned public GitHub pages must contain complete English first, followed by complete Chinese on the same page. This applies to README files, guides, architecture / protocol documents, compatibility records, release notes, issue / PR templates and repository descriptions. Update both sections together in future work.

Use the existing `<!-- vrization:english -->` and `<!-- vrization:chinese -->` section markers with `## English` and `## 简体中文`. Run `python scripts/check_docs.py` after documentation changes. Its checks cover structure, nonempty sections and relative file links; human review remains responsible for translation accuracy and completeness.

Credit the source of optimization ideas as well as reused code: record the upstream project, authors, exact version / commit or document, URL, license, what was referenced, and what was changed or rewritten. Rewriting an implementation does not remove its provenance or applicable license obligations. Distinguish bundled dependencies, reused code, and architecture-only references. Maintain these records in both languages.

Preserve original license and copyright texts verbatim. Project-written bilingual explanation must not replace the controlling upstream text. Document concrete tests and limitations accurately; do not claim untested hardware or Android derivatives passed.

English is the default and primary software language. Both desktop and phone applications must offer selectable English and Simplified Chinese. Keep language choice local to each application, and preserve the host's explicit input authorization / emergency stop boundaries.

USB is the default connection preference on the host and both phone platforms. Keep LAN available explicitly. Distinguish a tested USB transport from a simulated bridge or a merely connected charging cable. Keep low-latency defaults adjustable and report measured FPS / round-trip time without calling them end-to-end latency.

When publishing a release in the user's local workspace, preserve verified historical version downloads and refresh a complete extracted latest runnable Windows copy with `scripts/archive_releases.py --destination <local archive folder>`. Keep private local paths out of public documentation. iOS source / Simulator outputs must never be described as signed, directly installable iPhone applications.

Keep [CHANGELOG.md](CHANGELOG.md) updated for every user-visible feature, fix, optimization, compatibility change or default-setting change. Record implemented changes under Unreleased in both language sections during development. Before publishing, move them into the matching version entry with the actual UTC publication date, affected component versions and a release link. Label documentation-only changes and distinguish completed work from plans. Preserve older entries; do not replace published binaries or move an existing tag merely to update the log. The root Markdown changelog is automatically included in future Windows and iOS source packages. Refresh a standalone changelog at the local archive root when saving a new release, without editing verified historical downloads.

---

<!-- vrization:chinese -->
## 简体中文

所有项目自有 GitHub 公共页面必须在同一页先提供完整英文，再提供完整中文。范围包括 README、教程、架构 / 协议、兼容性记录、发布说明、Issue / PR 模板与仓库简介。今后的修改必须同步维护两种语言。

沿用 `<!-- vrization:english -->`、`<!-- vrization:chinese -->` 分区标记及 `## English`、`## 简体中文` 标题。文档修改后运行 `python scripts/check_docs.py`；它只检查结构、内容非空与相对文件链接，翻译含义与完整性仍需人工审阅。

优化思路与复用代码都要记录来源并鸣谢：写明上游项目、作者、准确版本 / commit 或文档、链接、许可、参考内容，以及修改或重写的部分。重写实现不会消除来源记录或适用的许可义务。区分随包依赖、采用的代码和仅参考架构的材料，并同步维护中英文记录。

许可证与版权原文必须保持完整。项目编写的双语解释不能替代上游控制文本。准确记录实际检查与限制，不把未验证硬件或 Android 衍生系统说成已经通过。

软件以英文为默认和主语言。电脑端和手机端都必须支持用户选择 English / 简体中文。两端语言独立保存，并保留电脑主动输入授权与紧急停止边界。

电脑端与两类手机都默认优先 USB 连接，并保留显式局域网选项。区分真实 USB 测试、模拟桥接及仅接入充电线。低延迟默认参数允许调整，记录实际 FPS / 往返时间，不冒充端到端延迟。

在用户本地工作区发布版本时，用 `scripts/archive_releases.py --destination <本地归档目录>` 保留已校验历史版本，并更新完整解压、可直接运行的最新版 Windows 程序。公共文档不要包含用户私有路径。iOS 源码 / 模拟器产物不能描述为已签名、可直接安装的 iPhone 应用。

每次新增用户可见功能、修复、优化、兼容性变化或默认设置变化，都更新 [CHANGELOG.md](CHANGELOG.md)。开发期间将已实现变化同步记在两种语言的“未发布”段；发布前归入对应版本，记录实际 UTC 发布日期、各端版本范围与发布链接。纯文档变化须注明，已完成内容与计划分开。保留旧条目，不为更新日志替换已发布二进制或移动已有标签。根目录 Markdown 日志会自动附带在今后的 Windows 与 iOS 源码包中；保存新发布时同步刷新本地归档根目录的独立日志，不修改已校验历史下载。

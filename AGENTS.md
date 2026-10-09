# VRization project instructions / 项目要求

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

All project-owned public GitHub pages must contain complete English first, followed by complete Chinese on the same page. This applies to README files, guides, architecture / protocol documents, compatibility records, release notes, issue / PR templates and repository descriptions. Update both sections together in future work.

Use the existing `<!-- vrization:english -->` and `<!-- vrization:chinese -->` section markers with `## English` and `## 简体中文`. Run `python scripts/check_docs.py` after documentation changes. Its checks cover structure, nonempty sections and relative file links; human review remains responsible for translation accuracy and completeness.

Preserve original license and copyright texts verbatim. Project-written bilingual explanation must not replace the controlling upstream text. Document concrete tests and limitations accurately; do not claim untested hardware or Android derivatives passed.

English is the default and primary software language. Both desktop and phone applications must offer selectable English and Simplified Chinese. Keep language choice local to each application, and preserve the host's explicit input authorization / emergency stop boundaries.

---

<!-- vrization:chinese -->
## 简体中文

所有项目自有 GitHub 公共页面必须在同一页先提供完整英文，再提供完整中文。范围包括 README、教程、架构 / 协议、兼容性记录、发布说明、Issue / PR 模板与仓库简介。今后的修改必须同步维护两种语言。

沿用 `<!-- vrization:english -->`、`<!-- vrization:chinese -->` 分区标记及 `## English`、`## 简体中文` 标题。文档修改后运行 `python scripts/check_docs.py`；它只检查结构、内容非空与相对文件链接，翻译含义与完整性仍需人工审阅。

许可证与版权原文必须保持完整。项目编写的双语解释不能替代上游控制文本。准确记录实际检查与限制，不把未验证硬件或 Android 衍生系统说成已经通过。

软件以英文为默认和主语言。电脑端和手机端都必须支持用户选择 English / 简体中文。两端语言独立保存，并保留电脑主动输入授权与紧急停止边界。

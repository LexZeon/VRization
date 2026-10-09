# Pull request / 合并请求

<!-- vrization:english -->
## English

### Problem and changed behavior

Describe the concrete trigger, previous behavior and result. Link related issues where useful.

### Validation and limits

List meaningful checks, devices / OS versions tested and anything still unverified. State how performance was measured.

### Documentation and attribution

- [ ] Public documentation contains complete English first and Chinese below on the same page; `python scripts/check_docs.py` passes.
- [ ] User-visible changes are recorded in both Unreleased sections of `CHANGELOG.md`, or this PR has no user-visible change.
- [ ] New dependencies / copied assets have exact upstream provenance, license texts and required notices.
- [ ] Input authorization, F8 stop and disconnect boundaries are retained where affected.

Translation quality requires human review; the automated check verifies structure and file links only. Never include private signing keys, pairing codes or private screen content.

---

<!-- vrization:chinese -->
## 简体中文

### 问题与行为变化

说明具体触发条件、原来的行为与修改结果；需要时链接相关 Issue。

### 验证与限制

列出有意义的检查、实际测试的设备 / 系统，以及仍未验证的部分。性能说明须包含测量方法。

### 文档与来源

- [ ] 公共文档同一页完整英文在上、完整中文在下，`python scripts/check_docs.py` 通过。
- [ ] 用户可见变化已同步记入 `CHANGELOG.md` 的中英“未发布”段，或本次 PR 没有用户可见变化。
- [ ] 新依赖 / 引用素材记录精确上游来源，附带许可与必要声明。
- [ ] 涉及输入时保留主动授权、F8 停止与断线停止边界。

翻译质量须人工审阅，自动检查只判断结构与文件链接。请勿提交私钥、配对码或私密屏幕内容。

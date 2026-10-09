# 安全说明 / Security

v0.1.0-alpha 面向同一可信局域网内的试用。服务器会把电脑选定的显示器 / 区域内容发送给已连接客户端；FPS 功能还可以发送鼠标移动。

## 连接边界

- 当前使用明文 WebSocket (`ws://`)；画面、设置和配对码可能被同网段攻击者读取。
- 六位配对码是基础访问控制，不能替代 TLS、强身份认证或可信网络。
- 不要在路由器上做端口转发，不要直接暴露到公网，也不要在公共 Wi-Fi 上使用。
- 防火墙只允许必要的专用网络。结束使用后停止串流。
- 共享电脑画面前关闭不想暴露的窗口；选区可能因窗口移动而显示其他内容。

## 输入控制

手机不能自行授权电脑鼠标控制。必须同时满足 FPS 模式、有效客户端连接和电脑端主动授权；按 **F8** 可停止鼠标控制。切换模式、断开连接或停止服务后，应重新在电脑上授权。先用桌面和离线应用检查方向、灵敏度和停止键，再进入游戏。

## 报告问题

普通功能问题请开 Issue。涉及绕过配对、未授权输入、远程代码执行或画面泄漏的问题，请优先使用 GitHub 仓库 **Security → Report a vulnerability**（仓库维护者启用私密报告后可用）。若入口尚未启用，可先开一个仅请求私密联系渠道的 Issue，不公开利用步骤、个人数据或配对码。

该 Alpha 没有正式安全维护 SLA。报告中请包含版本、操作系统、最小复现条件和可能影响，移除真实 IP、配对码和屏幕私密内容。

---

The alpha uses unencrypted LAN WebSockets. Do not expose it to the internet or untrusted networks. A short pairing code is not encryption. Mouse input requires an explicit host-side arm, and **F8** stops it. Prefer GitHub private vulnerability reporting when enabled; otherwise request a private contact without publishing exploit details.

# 🥽 VRization v0.1.1-alpha — release notes / 发布说明

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

Windows screen → Android phone VR viewer, with fixed full screen, a head-tracked cinema screen and gyro-to-mouse FPS mode. Phone controls include scale, offsets, separation, field of view, screen distance and distortion. FPS requires explicit PC arming; **F8** stops input.

### Changes since v0.1.0-alpha

- Selectable English / Simplified Chinese on PC and phone, with local persistence. PC language switching keeps streaming but disarms mouse control; phone switching disconnects and requires reconnecting.
- Settings revisions and client acknowledgments prevent delayed responses from rolling newer slider values back. Session-scoped callbacks avoid stale reconnect / background events.
- Every public project document now contains complete English first and Chinese below; CI checks language structure and local file links, with human translation review still required.
- Windows packages include the documentation's offline targets, and the standalone core AAR includes the original MIT license.
- Validation: 20 host tests and 15 Android tests (6 core, 9 app), plus build / lint checks. The final APK passed Google-free Android 6 / API 23 and Android 16 / API 36 emulator upgrade, language persistence, streaming and lifecycle / reconnection checks. API 23 recorded one transient popup `EGL_BAD_SURFACE`, followed by normal rendering; see the validation record. Physical phones, viewers and real FPS games still need hardware validation.
- API 23 also confirmed English default on a Chinese system, no-sensor cinema / FPS fallback to full screen, and stable slider boundary values. See the [compatibility record](https://github.com/LexZeon/VRization/blob/main/docs/COMPATIBILITY.md) and [detailed validation](https://github.com/LexZeon/VRization/blob/main/docs/VALIDATION.md).

### Downloads

- `VRization-Windows-x64.zip`: extract completely, then run `VRization-Host.exe`.
- `VRization-Android-debug.apk`: test-signed Android 6.0+ APK; compatible derivatives depend on device capabilities.
- `VRization-vr-core-alpha.aar`: reusable Android core, with alpha APIs.
- `VRization-Licenses.zip`: license texts and provenance indexes; preserve applicable texts when distributing.
- `SHA256SUMS.txt`: SHA-256 download checksums.

### First connection

Use the same trusted LAN → start PC streaming → enter the PC IP, port and pairing code on the phone → try full screen → fit the image before inserting the phone. See the [illustrated tutorial](https://github.com/LexZeon/VRization/blob/main/docs/QUICKSTART.zh-CN.md).

### Alpha boundaries

CPU JPEG + WebSocket sends the same 2D image to both eyes. It does not create native game stereo, carry audio or promise production VR latency. Physical viewers, Android derivatives and real games still need hardware testing.

`ws://` is unencrypted; use trusted LANs and never forward the port to the internet. Debug signatures can differ between build machines, requiring uninstall / reinstall and clearing settings. The Windows EXE has no commercial code signature.

Windows requires Microsoft Visual C++ v14 x64 runtime; Microsoft runtime DLLs are not bundled. For a missing DLL or error 126, follow [Microsoft's guide](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist/) and use the [current x64 runtime](https://aka.ms/vc14/vc_redist.x64.exe). First local and CI builds use different CPython builds; check the inventory for the actual artifact.

---

<!-- vrization:chinese -->
## 简体中文

### 🥽 VRization Alpha

Windows 电脑画面 → Android 手机 VR 盒子：固定全屏、头部追踪虚拟大屏幕与 FPS 鼠标控制三种模式。手机端提供缩放、偏移、眼间距、视场角、屏幕距离和畸变调节；FPS 需要电脑主动授权，F8 停止。

#### 相对 v0.1.0-alpha 的变化

- 电脑与手机可选英文 / 简体中文，并在本地保留。电脑切换保持串流但解除鼠标授权；手机切换断线，需重连。
- 设置版本与客户端确认防止迟到响应覆盖较新的滑块值；按会话绑定回调，避免重连 / 后台旧事件干扰。
- 所有公共自有文档同页完整英文在上、中文在下，CI 检查语言结构与本地文件链接；翻译质量仍需人工审阅。
- Windows 包补齐文档离线链接目标，独立核心 AAR 内嵌原创 MIT 许可。
- 已有 20 项电脑检查与 15 项 Android 检查（核心 6、应用 9）及构建 / lint；最终 APK 在无 Google 的 Android 6 / API 23 与 Android 16 / API 36 模拟器通过升级、语言保留、串流、生命周期 / 重连检查。API 23 记录过一次临时弹窗 `EGL_BAD_SURFACE`，随后渲染正常，详见验证记录。手机真机、盒子与真实 FPS 仍需硬件验证。
- API 23 还确认系统中文时默认英文、无传感器的大屏幕 / FPS 回退全屏，以及滑块边界值稳定。详见 [兼容性记录](https://github.com/LexZeon/VRization/blob/main/docs/COMPATIBILITY.md) 和 [详细验证](https://github.com/LexZeon/VRization/blob/main/docs/VALIDATION.md)。

#### 下载

- `VRization-Windows-x64.zip`：完整解压后运行 `VRization-Host.exe`。
- `VRization-Android-debug.apk`：Android 6.0+ 测试签名 APK，兼容 Android 的系统可按设备能力尝试。
- `VRization-vr-core-alpha.aar`：供 Android 软件集成的核心库，仍为 Alpha API。
- `VRization-Licenses.zip`：完整许可文本与来源索引；分发时保留相关文本。
- `SHA256SUMS.txt`：下载文件的 SHA-256 校验值。

#### 首次连接

两端连接同一可信局域网 → 电脑开始串流 → 手机填写电脑 IP、端口与配对码 → 先试全屏 → 调整画面后放入盒子。详细图文教程见仓库 `docs/QUICKSTART.zh-CN.md`。

#### Alpha 边界

当前采用 CPU JPEG + WebSocket，左右眼显示相同二维画面，不提供普通游戏自动立体化、音频或生产级低延迟承诺。实际手机盒子、Android 衍生系统和游戏兼容性仍需实机测试。

传输为明文 `ws://`，仅用于可信局域网，不要开放公网端口。APK 使用测试签名；不同机器重新构建后可能需要卸载旧版再安装，保存的设置会被清除。Windows 程序未做商业代码签名。

Windows 端需要 Microsoft Visual C++ v14 x64 运行库，包内不附带微软运行库 DLL。若提示缺少 DLL 或错误 126，可按 [微软官方说明](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist/) 安装 [当前 x64 运行库](https://aka.ms/vc14/vc_redist.x64.exe)。首发本机与 CI 使用不同 CPython 构建，原生组件版本请按具体产物核对。

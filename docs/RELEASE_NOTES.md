## 🥽 VRization Alpha

Windows 电脑画面 → Android 手机 VR 盒子：固定全屏、头部追踪虚拟大屏幕与 FPS 鼠标控制三种模式。手机端提供缩放、偏移、眼间距、视场角、屏幕距离和畸变调节；FPS 需要电脑主动授权，F8 停止。

### 下载

- `VRization-Windows-x64.zip`：完整解压后运行 `VRization-Host.exe`。
- `VRization-Android-debug.apk`：Android 6.0+ 测试签名 APK，兼容 Android 的系统可按设备能力尝试。
- `VRization-vr-core-alpha.aar`：供 Android 软件集成的核心库，仍为 Alpha API。
- `VRization-Licenses.zip`：完整第三方许可与来源；分发时保留相关文本。
- `SHA256SUMS.txt`：下载文件的 SHA-256 校验值。

### 首次连接

两端连接同一可信局域网 → 电脑开始串流 → 手机填写电脑 IP、端口与配对码 → 先试全屏 → 调整画面后放入盒子。详细图文教程见仓库 `docs/QUICKSTART.zh-CN.md`。

### Alpha 边界

当前采用 CPU JPEG + WebSocket，左右眼显示相同二维画面，不提供普通游戏自动立体化、音频或生产级低延迟承诺。实际手机盒子、Android 衍生系统和游戏兼容性仍需实机测试。

传输为明文 `ws://`，仅用于可信局域网，不要开放公网端口。APK 使用测试签名；不同机器重新构建后可能需要卸载旧版再安装，保存的设置会被清除。Windows 程序未做商业代码签名。

Windows 端需要 Microsoft Visual C++ v14 x64 运行库，包内不附带微软运行库 DLL。若提示缺少 DLL 或错误 126，可按 [微软官方说明](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist/) 安装 [当前 x64 运行库](https://aka.ms/vc14/vc_redist.x64.exe)。首发本机与 CI 使用不同 CPython 构建，原生组件版本请按具体产物核对。

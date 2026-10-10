# 🛠️ Development and builds / 开发与构建

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

Commands start at the repository root. The host targets Windows 10 / 11 x64; Android can be built on Windows, Linux or macOS. The iOS app targets iOS / iPadOS 15+ and is built with Xcode on macOS; Windows remains the streaming host.

### Environment

| Component | Configuration |
| --- | --- |
| Python | 3.12+; first local release 3.12.14, Windows CI 3.12.10 |
| Java | JDK 17 |
| Gradle | Wrapper 8.9 |
| Android Gradle Plugin | 8.7.3 |
| Android SDK | Platform 35; minimum runtime API 23 / Android 6.0 |

Install [Python](https://www.python.org/downloads/), [JDK 17](https://adoptium.net/temurin/releases/?version=17) and [Android Studio](https://developer.android.com/studio). Install platform 35 in SDK Manager. Set `ANDROID_HOME`, or put `sdk.dir` in the untracked `android/local.properties`. Google Play services, the NDK and a physical device are not required to build.

CI uses CPython 3.12.10 available on GitHub Actions; the first locally verified release used 3.12.14. `licenses/native/runtime-audit.json` records that first local binary, not every CI build. Recheck the actual native runtime when publishing a rebuild.

### Windows host

In PowerShell at the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r desktop/requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e ./desktop
.\.venv\Scripts\python.exe -m vrization_host
```

Run core checks and build the executable:

```powershell
.\.venv\Scripts\python.exe -m pip install 'pytest==9.1.1' 'pytest-asyncio==1.4.0'
.\.venv\Scripts\python.exe -m pytest desktop/tests
.\scripts\build-windows.ps1 -Python (Resolve-Path .\.venv\Scripts\python.exe).Path
```

The script installs the specified build tools, runs checks and produces `desktop/dist/VRization-Host.exe`. Use an absolute custom Python path because the script changes directories. PyInstaller builds on the target OS. The single-file EXE contains Python and application dependencies; distribute it with `LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES.md` and `licenses/`.

The EXE excludes `VCRUNTIME140*.dll`. Microsoft Visual C++ v14 x64 runtime is installed separately. For missing DLL / error 126, use [Microsoft's guide](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist/) and the [current x64 installer](https://aka.ms/vc14/vc_redist.x64.exe). The runtime must be at least as recent as the build toolchain requires; the first local Python build used MSVC 14.44.

### Android APK

From the repository root on Windows:

```powershell
Set-Location android
.\gradlew.bat :vr-core:testDebugUnitTest :app:testDebugUnitTest :vr-core:assembleDebug :app:assembleDebug :app:lintDebug
```

On Linux / macOS:

```sh
cd android
./gradlew :vr-core:testDebugUnitTest :app:testDebugUnitTest :vr-core:assembleDebug :app:assembleDebug :app:lintDebug
```

Output: `android/app/build/outputs/apk/debug/app-debug.apk`. With USB debugging enabled and while still in `android/`:

```sh
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

This is a test-signed APK. Debug keys differ across build machines, so an update can require uninstalling the previous app and clearing its settings. Store distributors must create and protect their own release key; never commit private signing keys.

### iOS / iPadOS client

Open `ios/VRization.xcodeproj` in a compatible Xcode on a Mac. The local `VRizationCore` Swift package has no external dependencies. Run `swift test --package-path ios` for the pure core. The CI helper `python3 scripts/build_ios.py` builds simulator and device SDKs without signing, runs iPhone UI tests against an original loopback calibration stream, exports screenshots and packages source / Simulator downloads. Install fixture dependencies as shown in the workflow first.

Physical iPhone installation requires choosing your own Apple signing team and running from Xcode. Simulator applications are not iPhone IPA files and do not run on Windows. Full steps and Apple references: [iOS + Windows guide](IOS.md).

### Documentation, CI and releases

Run `python scripts/check_docs.py`. After building both release binaries and `:vr-core:assembleRelease`, run `python scripts/package_release.py` to create `artifacts/release/`; the packager verifies included Markdown file links. CI uses the same packager with a platform selection. Every public project-owned page contains complete English first and complete Chinese below. The check verifies markers, order, nonempty sections and relative file links; it cannot judge translation accuracy. Original third-party license texts remain verbatim.

Actions builds the host on Windows, Android on Linux and iOS on macOS, then retains downloadable artifacts. A `v*` tag waits for all platform checks and triggers alpha publication with SHA-256 checksums. New publication also requires an APK verified by official `apksigner` against the canonical public certificate; a fresh runner's unrelated debug signature is rejected. See the [Android publication gate](../AI_HANDOFF.md#public-android-signing-gate). If that release already exists, CI preserves its binaries and signing identity and leaves new outputs in Actions. Passing CI establishes successful checks and builds, not physical-headset or game compatibility.

Runtime Python packages are pinned in [requirements-lock.txt](../desktop/requirements-lock.txt); direct Android versions and the Gradle wrapper are specified. This is not a promise of byte-identical reproducibility: runner images, JDK patch versions, Python build isolation (`setuptools>=75`) and some build-tool transitive dependencies can change. Record resolved tools and native inventories when publishing.

Update [third-party notices](../THIRD_PARTY_NOTICES.md) and bundled texts after dependency changes. To inspect Android resolution from `android/`:

```sh
./gradlew :app:dependencies --configuration debugRuntimeClasspath
```

For USB prerequisites and default profiles, see [USB setup](USB.md). After publishing, [the local archive guide](DOWNLOADS.md) preserves each release and a fully extracted latest Windows program.

### Physical-device validation

Before a release, check connection, all modes, layout, recentering, default-enabled First-person input, F8 latched pause / PC Resume, all-window control and sensor-gap rebaselining, input stopping on disconnect, and no-sensor fallback. Check optics, heat, delay and sensor directions on an actual phone and viewer. Do not describe emulator screenshots or synthetic frames as hardware validation.

### v0.3 geometry / preference changes

Run the host suite above for `view_edit.py`; it includes pure both-eye geometry and local transaction tests without GUI / capture / input. Android / Swift cores also own the shared geometry, and app tests cover committed profiles, draft / reset behavior and reconnect restoration. Build on the original target platforms and validate application behavior separately; pure math or SDK compilation alone does not establish a completed headset editor UI pass. See [the editor contract](EDITING.md).

---

<!-- vrization:chinese -->
## 简体中文

本文以仓库根目录为起点。电脑端目标是 Windows 10 / 11 x64；Android 构建可在 Windows、Linux 或 macOS 上进行。iOS 手机端目标为 iOS / iPadOS 15+，需在 macOS 用 Xcode 构建；Windows 继续作为串流主机。

### 环境

| 组件 | 本项目配置 |
| --- | --- |
| Python | 3.12+；首发本机构建 3.12.14，Windows CI 3.12.10 |
| Java | JDK 17 |
| Gradle | Wrapper 8.9 |
| Android Gradle Plugin | 8.7.3 |
| Android SDK | Platform 35；最低运行 API 23 / Android 6.0 |

可安装 [Python](https://www.python.org/downloads/)、[JDK 17](https://adoptium.net/temurin/releases/?version=17) 和 [Android Studio](https://developer.android.com/studio)。Android Studio 的 SDK Manager 中安装 Android 35 平台；配置 `ANDROID_HOME`，或在不提交版本库的 `android/local.properties` 中设置 `sdk.dir`。不需要 Google Play 服务、NDK 或真机才能构建 APK。

Windows CI 固定使用 GitHub Actions 可提供的 CPython 3.12.10；首发本机构建使用 3.12.14。它们不能视作同一份原生运行时清单。本仓库 `licenses/native/runtime-audit.json` 描述首发本机构建，重建发布时需重新核对实际原生组件。

### Windows 电脑端

PowerShell，在仓库根目录执行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r desktop/requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e ./desktop
.\.venv\Scripts\python.exe -m vrization_host
```

运行核心检查：

```powershell
.\.venv\Scripts\python.exe -m pip install 'pytest==9.1.1' 'pytest-asyncio==1.4.0'
.\.venv\Scripts\python.exe -m pytest desktop/tests
```

生成 Windows 程序：

```powershell
.\scripts\build-windows.ps1 -Python (Resolve-Path .\.venv\Scripts\python.exe).Path
```

该脚本安装固定版本的构建工具、运行检查并打包，输出为 `desktop/dist/VRization-Host.exe`。如果传入自定义 Python 路径，建议使用绝对路径，因为脚本会切换工作目录。PyInstaller 需要在目标操作系统上构建；当前生成包含 Python 与应用依赖的单文件程序，分发包仍须附上仓库的 `LICENSE`、`NOTICE`、`THIRD_PARTY_NOTICES.md` 和 `licenses/`。

程序不附带 `VCRUNTIME140*.dll`，Microsoft Visual C++ v14 x64 运行库作为系统前提由微软安装器提供。遇到启动缺少 DLL 或错误 126 时，按 [微软说明](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist/) 使用 [当前 x64 安装器](https://aka.ms/vc14/vc_redist.x64.exe)。运行库版本应不早于构建工具所需版本；首发本机 Python 使用 MSVC 14.44。

### Android APK

在仓库根目录执行：

```powershell
Set-Location android
.\gradlew.bat :vr-core:testDebugUnitTest :app:testDebugUnitTest :vr-core:assembleDebug :app:assembleDebug :app:lintDebug
```

Linux / macOS 使用：

```sh
cd android
./gradlew :vr-core:testDebugUnitTest :app:testDebugUnitTest :vr-core:assembleDebug :app:assembleDebug :app:lintDebug
```

输出位于 `android/app/build/outputs/apk/debug/app-debug.apk`。连接开启 USB 调试的手机后，可安装：

```sh
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

这是测试签名 APK。不同构建机器的 debug key 可能不同，覆盖安装可能失败；可先卸载旧版，代价是删除保存的设置。正式商店分发应由发布者创建并安全保存自己的签名密钥，密钥不要提交到 GitHub。

### iOS / iPadOS 客户端

在 Mac 用兼容的 Xcode 打开 `ios/VRization.xcodeproj`。本地 `VRizationCore` Swift 包没有外部依赖，执行 `swift test --package-path ios` 检查纯核心。CI 辅助脚本 `python3 scripts/build_ios.py` 在不签名的情况下构建模拟器和真机 SDK，对原创本机校准卡串流运行 iPhone UI 测试、导出截图，并打包源码 / 模拟器下载。先按工作流安装测试依赖。

真实 iPhone 安装需要选择自己的 Apple 签名团队，并在 Xcode 运行。模拟器应用不是 iPhone IPA，也不能在 Windows 运行。具体步骤和 Apple 官方说明见 [iOS 与 Windows 教程](IOS.md)。

### CI 与发布

GitHub Actions 分别在 Windows 构建电脑端、Linux 构建 APK、macOS 构建 iOS，并保留产物。`v*` 标签等待所有平台检查后触发 Alpha 发布，附带 SHA-256；新发布还必须用官方 `apksigner` 校验 APK 与公开固定证书一致，拒绝新 runner 的无关调试签名，见 [Android 发布签名门槛](../AI_HANDOFF.md#android-公开签名门槛)。如果同标签 Release 已存在，CI 保留已有二进制和签名，只在 Actions 留下新构建产物。CI 的通过只表示自动检查和构建成功，不代表手机盒子实机体验或全部游戏兼容性已经验证。

运行时 Python 包锁定在 [requirements-lock.txt](../desktop/requirements-lock.txt)，Android 直接依赖和 Gradle Wrapper 指定版本；这不承诺字节一致的可重复构建。CI 系统镜像、JDK 补丁版本、Python 隔离构建使用的 `setuptools>=75` 和部分构建工具传递依赖仍可能变化，发布时应记录实际解析工具与原生组件。运行 `python scripts/check_docs.py` 检查公共页面英文在上、中文在下的分区、非空内容和相对文件链接；该检查不能判断翻译质量。升级时同步核查 [第三方声明](../THIRD_PARTY_NOTICES.md) 与随产物分发的许可文本。Android 依赖解析可以执行：

```sh
./gradlew :app:dependencies --configuration debugRuntimeClasspath
```

USB 前提与默认预设见 [USB 教程](USB.md)。发布后可按 [本地归档说明](DOWNLOADS.md) 保留每个版本和完整解压的最新版 Windows 程序。

### 实机验证

构建两端与 `:vr-core:assembleRelease` 后运行 `python scripts/package_release.py`，产物在 `artifacts/release/`；打包器检查附带 Markdown 文件链接，CI 使用相同打包逻辑。

发布前至少检查：两端连接、四种模式（包括加强模式 1:1／广角变形）、缩放偏移、回正、默认启用第一人称、F8 锁定暂停／电脑恢复、所有窗口控制与传感器间断重建基准、断线后停止输入、无传感器设备的全屏回退。还应在实际手机与盒子上检查对齐、发热、延迟和传感器方向。不要把模拟器截图或局域网合成帧测试写成实机验证结果。


### v0.3 几何 / 偏好变化

上述主机测试包含 `view_edit.py` 的纯双眼几何与本地事务，不需要界面 / 采屏 / 输入；Android / Swift 核心也负责共用几何，应用检查覆盖已提交配置、草稿 / 重置和重连恢复。仍在原目标平台构建，另行验证应用行为；纯数学或 SDK 编译不能算作盒子编辑器界面验收。见 [编辑合同](EDITING.md)。

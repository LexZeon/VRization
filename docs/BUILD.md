# 🛠️ 开发与构建

本文以仓库根目录为起点。电脑端目标是 Windows 10 / 11 x64；Android 构建可在 Windows、Linux 或 macOS 上进行。

## 环境

| 组件 | 本项目配置 |
| --- | --- |
| Python | 3.12+；首发本机构建 3.12.14，Windows CI 3.12.10 |
| Java | JDK 17 |
| Gradle | Wrapper 8.9 |
| Android Gradle Plugin | 8.7.3 |
| Android SDK | Platform 35；最低运行 API 23 / Android 6.0 |

可安装 [Python](https://www.python.org/downloads/)、[JDK 17](https://adoptium.net/temurin/releases/?version=17) 和 [Android Studio](https://developer.android.com/studio)。Android Studio 的 SDK Manager 中安装 Android 35 平台；配置 `ANDROID_HOME`，或在不提交版本库的 `android/local.properties` 中设置 `sdk.dir`。不需要 Google Play 服务、NDK 或真机才能构建 APK。

Windows CI 固定使用 GitHub Actions 可提供的 CPython 3.12.10；首发本机构建使用 3.12.14。它们不能视作同一份原生运行时清单。本仓库 `licenses/native/runtime-audit.json` 描述首发本机构建，重建发布时需重新核对实际原生组件。

## Windows 电脑端

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
.\.venv\Scripts\python.exe -m unittest discover -s desktop/tests -v
```

生成 Windows 程序：

```powershell
.\scripts\build-windows.ps1 -Python (Resolve-Path .\.venv\Scripts\python.exe).Path
```

该脚本安装固定版本的构建工具、运行检查并打包，输出为 `desktop/dist/VRization-Host.exe`。如果传入自定义 Python 路径，建议使用绝对路径，因为脚本会切换工作目录。PyInstaller 需要在目标操作系统上构建；当前生成包含 Python 与应用依赖的单文件程序，分发包仍须附上仓库的 `LICENSE`、`NOTICE`、`THIRD_PARTY_NOTICES.md` 和 `licenses/`。

程序不附带 `VCRUNTIME140*.dll`，Microsoft Visual C++ v14 x64 运行库作为系统前提由微软安装器提供。遇到启动缺少 DLL 或错误 126 时，按 [微软说明](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist/) 使用 [当前 x64 安装器](https://aka.ms/vc14/vc_redist.x64.exe)。运行库版本应不早于构建工具所需版本；首发本机 Python 使用 MSVC 14.44。

## Android APK

在仓库根目录执行：

```powershell
Set-Location android
.\gradlew.bat :vr-core:testDebugUnitTest :vr-core:assembleDebug :app:assembleDebug :app:lintDebug
```

Linux / macOS 使用：

```sh
cd android
./gradlew :vr-core:testDebugUnitTest :vr-core:assembleDebug :app:assembleDebug :app:lintDebug
```

输出位于 `android/app/build/outputs/apk/debug/app-debug.apk`。连接开启 USB 调试的手机后，可安装：

```sh
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

这是测试签名 APK。不同构建机器的 debug key 可能不同，覆盖安装可能失败；可先卸载旧版，代价是删除保存的设置。正式商店分发应由发布者创建并安全保存自己的签名密钥，密钥不要提交到 GitHub。

## CI 与发布

GitHub Actions 分别在 Windows 构建电脑端、在 Linux 构建 APK，保留产物供下载。`v*` 标签触发 Alpha 预发布流程，附带 SHA-256 文件；如果同标签的 Release 已存在，CI 保留已有二进制和签名，只在 Actions 留下新构建产物。CI 的通过只表示自动检查和构建成功，不代表手机盒子实机体验或全部游戏兼容性已经验证。

第三方依赖使用固定版本，升级时同步核查 [第三方声明](../THIRD_PARTY_NOTICES.md) 与随产物分发的许可文本。Android 依赖解析可以执行：

```sh
./gradlew :app:dependencies --configuration debugRuntimeClasspath
```

## 实机验证

发布前至少检查：两端连接、三种模式、缩放偏移、回正、FPS 电脑授权与 F8 停止、断线后停止输入、无传感器设备的全屏回退。还应在实际手机与盒子上检查对齐、发热、延迟和传感器方向。不要把模拟器截图或局域网合成帧测试写成实机验证结果。

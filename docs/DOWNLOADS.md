# 📦 Downloads and local version archive / 下载与本地版本归档

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

Download published assets and `SHA256SUMS.txt` from [GitHub Releases](https://github.com/LexZeon/VRization/releases). Use the application versions listed for that release: a host-only patch can intentionally retain older phone assets. Published alpha builds have the limitations recorded in [release notes](RELEASE_NOTES.md) and [compatibility records](COMPATIBILITY.md).

### v0.4.0 development and preserved downloads

Enhanced first person is being prepared as a separate v0.4.0 release. Until published, use the explicitly identified development build rather than assuming older downloads contain it. Its protocol capability is separate from settings schema 2; see [projection and fallback](ENHANCED_FIRST_PERSON.md). Keep all existing files, published assets, signed APK data and historical checksums. A separate SteamVR experimental version is planned, not an existing download.

### v0.3.4-alpha: default-enabled First-person control

Windows, Android and iOS applications are **0.3.4**, mobile build **7**; the reusable Android core AAR is unchanged. Protocol v1/settings schema 2 remain compatible, including phone 0.3.3 messages. Windows saves the default-enabled First-person gyro mouse preference across desktop/application/game windows, with latched F8/editor/failure/Stop and explicit PC Resume. The new mobile notices explain that policy. Use [this release's assets/manifest](https://github.com/LexZeon/VRization/releases/tag/v0.3.4-alpha) and [verification limits](RELEASE_NOTES.md). Preserve matching-signer Android data, the complete Windows ZIP, checksums and independent USB tools. iOS remains source/Mac Simulator output, not a signed iPhone installer. The Windows ZIP includes the bilingual [AI handoff](../AI_HANDOFF.md). Use the archive instructions below to save verified versions locally.

The earlier [v0.3.1-alpha patch](releases/v0.3.1-alpha.md) combined Windows 0.3.1 with unchanged mobile 0.3.0 assets. That historical mixed-version policy does not mean the new phone slider is available without updating.

| Download | What to do with it |
| --- | --- |
| `VRization-Windows-x64.zip` | Extract the **whole ZIP**, then run **Start-Windows.bat** or `VRization-Host.exe` inside it. Keep the documentation and license folders with the app. No Python installation is needed for this packaged host. |
| `VRization-Android-debug.apk` | Install on Android. This is the project's debug-signed alpha APK; normal Android installation approval still applies. A matching signing certificate is required to upgrade an existing installation without uninstalling it. |
| `VRization-vr-core-alpha.aar` | Android library for developers integrating rendering / pose functionality; not a phone installer. |
| `VRization-iOS-source.zip` | Source and Xcode project. Build on a Mac and use your own Apple signing for a physical iPhone / iPad. See [iOS instructions](IOS.md). |
| `VRization-iOS-Simulator.zip` | arm64 application for an Apple Silicon Mac's iOS Simulator. Intel Mac users build the source for their architecture. It cannot be installed on an iPhone or run as a Windows application. |
| `VRization-Licenses.zip` | License texts and provenance indexes; not an application. |

iOS source and Simulator downloads are **not signed, directly installable iPhone packages**. Android USB requires separately installed official Platform Tools; iOS USB requires separately installed Apple Devices / Apple Mobile Device support on Windows. See [the USB guide](USB.md).

### Separate official USB tools

Running the packaged app needs no Python, Java or SDK development environment. Android USB still requires Google's official Platform Tools and the phone's authorization; Windows / OEM drivers and Apple Devices for iOS remain separate prerequisites. Use **USB connection… → Download official Android USB tools…**, accept Google's terms on its site and download the Windows package, then **Import downloaded USB tools ZIP…**. The importer accepts the verified Windows **37.0.1** ZIP, preserves its complete NOTICE and existing installations, and lets you choose the destination. An existing official `adb.exe` can be selected manually instead; other downloaded package versions are not silently imported.

For a standalone extracted Windows folder, the default separate installation is `tools/android-sdk/platform-tools/` beside its EXE. In a managed archive it belongs at the archive root's `tools/android-sdk/`, outside `latest` and version folders, so refreshes keep it. The package / archive launchers set SDK variables only for the launched child when that directory exists; no global environment change or bundled SDK is involved. See [USB prerequisites and troubleshooting](USB.md).

### Create a verified local archive

The repository's [archive script](https://github.com/LexZeon/VRization/blob/main/scripts/archive_releases.py) preserves historical public downloads and prepares a complete extracted Windows copy for everyday use. It is a source-checkout tool, not an action automatically performed when you run the host. Install Python 3.12, download / clone the repository, open PowerShell in its root and run:

```powershell
py -3.12 scripts/archive_releases.py --destination "$env:USERPROFILE\Documents\VRization-Releases"
```

`Documents/VRization-Releases` is an example; choose your own archive folder. Network access to GitHub is needed while downloading. The script fetches up to 100 public releases from GitHub's releases list, skips drafts and downloads recognized assets that each release actually publishes. Older releases can lack assets introduced later. It checks every downloaded application / library / license asset against that release's published SHA-256 manifest before using it. Existing matching downloads are reused; an existing mismatching file stops the operation for inspection rather than being overwritten.

By default the first public release in GitHub's returned list becomes `latest`, including a prerelease if it heads that list. To choose a particular published version, append `--latest-tag <published-tag>`, replacing the placeholder with an existing tag. A checksum match confirms agreement with GitHub's published manifest; it is not a Windows code signature or an independent authentication of the publisher.

The example folder contains:

```text
Documents/VRization-Releases/
  OPEN-ME.html
  tools/android-sdk/         separately installed official tools, when present
  latest/
    Start-Windows.bat
    Start-on-second-monitor.bat
    Windows/                 fully extracted app, docs and licenses
    Android/                 APK, when published
    iOS-source/              source ZIP, when published
    iOS-Simulator/           Simulator ZIP, when published
    downloads/               original assets and SHA256SUMS.txt
  versions/
    <release-tag>/           verified original assets and platform folders
  previous-latest-<date>-<id>/ previous managed latest copy, after an update
```

Open `OPEN-ME.html` for the local bilingual index. Double-click `latest/Start-Windows.bat`, or open `latest/Windows/VRization-Host.exe`. The second-monitor launcher selects display number 2; verify the display name before streaming. These are fully extracted Windows files, so no ZIP extraction is required each time you run them. The script does not launch the app, install an APK, sign iOS code or enable streaming / FPS control.

Updating stages a complete new `latest` copy and preserves the old managed copy as `previous-latest-…`. `versions/` retains the historical downloads. An existing `latest` without the script's ownership metadata is left untouched and causes an error; choose another destination rather than deleting an unrelated folder. Keep the full Windows folder when moving an extracted version. Refresh the archive after a new GitHub release is published to obtain that release; unpublished local builds are not downloaded.

### Preserve historical versions when updating

v0.2.0-alpha preceded the v0.3 editor / reset / profile release; v0.3.1-alpha is the Windows USB patch. Keep each version's verified assets and checksums, even where phone assets are identical. Refresh the archive only after the next version is actually published. [Release history](releases/README.md) preserves old notes. Reset in an application changes local preferences; it does not delete historical releases or replace archive downloads. See [editor reset scope](EDITING.md).

---

<!-- vrization:chinese -->
## 简体中文

从 [GitHub Releases](https://github.com/LexZeon/VRization/releases) 下载已发布产物及 `SHA256SUMS.txt`，使用该次发布明确列出的应用版本；仅修复电脑端的补丁可以有意保留较早手机产物。Alpha 版限制见 [发布说明](RELEASE_NOTES.md) 与 [兼容性记录](COMPATIBILITY.md)。

### v0.4.0 开发与保留下载

加强第一人称准备单独作为 v0.4.0 发布；发布前需使用明确标注的开发构建，不能假定旧下载包含它。模式能力与配置 schema 2 分开，见 [投影与回退](ENHANCED_FIRST_PERSON.md)。保留全部已有文件、发布产物、同签名 APK 数据与历史哈希；另行计划 SteamVR 实验版本，目前没有对应下载。

### v0.3.4-alpha：默认开启第一人称控制

Windows、Android 与 iOS 应用为 **0.3.4**、手机构建号 **7**；可复用 Android 核心 AAR 不变。协议 v1／配置 schema 2 继续兼容，包含手机 0.3.3 消息。电脑保存默认启用第一人称陀螺仪偏好，桌面／应用／游戏均可控制，F8／编辑器／故障／Stop 锁定暂停，须电脑主动恢复；新版手机说明解释该策略。使用 [本版文件／清单](https://github.com/LexZeon/VRization/releases/tag/v0.3.4-alpha) 并查看 [验证范围](RELEASE_NOTES.md)。保留同签名 Android 数据、完整 Windows ZIP、校验值与独立 USB 工具；iOS 仍是源码／Mac 模拟器产物，不是签名 iPhone 安装器。Windows 包含双语 [AI 接手指南](../AI_HANDOFF.md)；按下文方法将已校验版本保存在本地。

此前 [v0.3.1-alpha 补丁](releases/v0.3.1-alpha.md) 用 Windows 0.3.1 搭配未变的 0.3.0 手机产物。该历史混合版本策略不表示不升级手机就能使用新滑块。

| 下载文件 | 用法 |
| --- | --- |
| `VRization-Windows-x64.zip` | **完整解压 ZIP**，运行其中的 **Start-Windows.bat** 或 `VRization-Host.exe`，保留文档和许可证文件夹。此打包电脑端无需另装 Python。 |
| `VRization-Android-debug.apk` | 安装到 Android。它是项目 debug 签名的 alpha APK，仍需正常 Android 安装授权。若要保留数据升级已有安装，签名证书必须一致。 |
| `VRization-vr-core-alpha.aar` | 供开发者集成渲染 / 姿态功能的 Android 库，不是手机安装包。 |
| `VRization-iOS-source.zip` | 源码与 Xcode 工程。在 Mac 构建，使用自己的 Apple 签名安装到真实 iPhone / iPad。见 [iOS 教程](IOS.md)。 |
| `VRization-iOS-Simulator.zip` | Apple Silicon Mac 的 iOS 模拟器 arm64 应用；Intel Mac 需从源码编译对应架构，不能安装到 iPhone，也不是 Windows 程序。 |
| `VRization-Licenses.zip` | 许可证原文与来源索引，不是应用程序。 |

iOS 源码与模拟器产物**不是已签名、可直接安装到 iPhone 的安装包**。Android USB 需要另行安装官方 Platform Tools；iOS USB 需要 Windows 另行安装 Apple Devices / Apple Mobile Device 支持。见 [USB 指南](USB.md)。

### 另行获取官方 USB 工具

运行打包软件无需 Python、Java 或 SDK 开发环境；Android USB 仍需 Google 官方 Platform Tools 和手机授权，Windows / 厂商驱动及 iOS 的 Apple Devices 是独立前提。打开“**USB 连接… → 下载官方安卓 USB 工具…**”，在 Google 网站阅读并接受条款、下载 Windows 包，再“**导入已下载的 USB 工具 ZIP…**”。导入器只接受已校验的 Windows **37.0.1** ZIP，保留完整 NOTICE 和已有安装，可选择目录；也可手动选择已安装官方 `adb.exe`，不会悄悄导入其他版本。

独立解压的 Windows 文件夹默认把另装工具放到 EXE 旁的 `tools/android-sdk/platform-tools/`。已管理归档则放在归档根目录的 `tools/android-sdk/`，位于 `latest` 和版本目录之外，刷新时保留。发布包 / 归档启动器只在该目录存在时为子应用设置 SDK 变量，不改全局环境、不随包附带 SDK。见 [USB 前提与排查](USB.md)。

### 建立已校验的本地归档

仓库中的 [归档脚本](https://github.com/LexZeon/VRization/blob/main/scripts/archive_releases.py) 保留历史公开下载，并准备完整解压、方便日常运行的 Windows 副本。它是源码检出工具，不会在运行电脑端时自动执行。安装 Python 3.12，下载 / 克隆仓库，在仓库根目录打开 PowerShell，运行：

```powershell
py -3.12 scripts/archive_releases.py --destination "$env:USERPROFILE\Documents\VRization-Releases"
```

`Documents/VRization-Releases` 只是示例，可换成自己的归档目录。下载时需能访问 GitHub。脚本读取 GitHub 发布列表中最多 100 个公开版本，跳过草稿，只下载每个版本实际发布的已识别产物；旧版本可能没有后来新增的文件。每个应用 / 库 / 许可下载都会先与该版本公开的 SHA-256 清单核对，再使用。已有文件校验一致时复用；不一致时停止以供检查，不覆盖旧文件。

默认把 GitHub 返回列表中的第一个公开版本设为 `latest`，若列表首项是预发布版也会选中。要指定版本，可追加 `--latest-tag <published-tag>`，将占位符替换为已发布标签。校验一致表示与 GitHub 公布的清单相符，不代表 Windows 代码签名，也不是对发布者的独立身份认证。

示例目录结构：

```text
Documents/VRization-Releases/
  OPEN-ME.html
  tools/android-sdk/         另行安装的官方工具，仅安装后存在
  latest/
    Start-Windows.bat
    Start-on-second-monitor.bat
    Windows/                 完整解压的程序、文档与许可证
    Android/                 APK，仅该版本发布时存在
    iOS-source/              源码 ZIP，仅发布时存在
    iOS-Simulator/           模拟器 ZIP，仅发布时存在
    downloads/               原始产物与 SHA256SUMS.txt
  versions/
    <release-tag>/           已校验原始产物与各平台目录
  previous-latest-<date>-<id>/ 更新前由脚本管理的 latest 副本
```

打开 `OPEN-ME.html` 查看本地双语索引。双击 `latest/Start-Windows.bat`，或打开 `latest/Windows/VRization-Host.exe`。第二显示器启动器选择编号 2 的屏幕，串流前请核对显示器名称。这些 Windows 文件已经完整解压，之后每次运行无需再解压 ZIP。脚本不会自动运行软件、安装 APK、为 iOS 签名或启用串流 / FPS 控制。

更新时先准备完整的新 `latest`，再把旧的已管理副本保留为 `previous-latest-…`；`versions/` 继续保留历史下载。如果已有 `latest` 不含脚本归属元数据，会保持不动并报错；应选择其他目标目录，不要删除无关文件夹。移动已解压版本时保留整个 Windows 文件夹。GitHub 新版本发布后重新运行才能取得该版本，尚未发布的本机构建不会被下载。


### 更新时保留历史版本

v0.2.0-alpha 先于 v0.3 编辑器 / 重置 / 配置发布，v0.3.1-alpha 则是电脑端 USB 补丁。即使手机产物相同，也保留每版已校验产物与校验值，下一版实际发布后再刷新归档。[发布历史](releases/README.md) 保留原说明。应用内重置只改变本地偏好，不删除历史版本或替换归档下载，见 [编辑重置范围](EDITING.md)。

# 📦 Downloads and local version archive / 下载与本地版本归档

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

Download published assets and `SHA256SUMS.txt` from [GitHub Releases](https://github.com/LexZeon/VRization/releases). Use the application versions listed for that release: a host-only patch can intentionally retain older phone assets. Published alpha builds have the limitations recorded in [release notes](RELEASE_NOTES.md) and [compatibility records](COMPATIBILITY.md).

### v0.3.1-alpha: update Windows, keep the phone app

This release combines **Windows host 0.3.1** with the verified **Android APK / AAR and iOS app 0.3.0** over unchanged protocol v1. The Android APK, AAR and arm64 iOS Simulator ZIP are reused unchanged, with the same SHA-256 values as v0.3.0-alpha. **An existing v0.3.0 Android installation does not need reinstalling, upgrading or clearing its saved profiles.** Close the old host, extract the full new Windows ZIP and run the new EXE.

The iOS source ZIP is regenerated to include updated desktop sources / documentation; its iOS application remains **0.3.0 / build 4**, as does the unchanged Simulator app. It still requires your Apple signing for a physical phone. Match each downloaded asset to this release's `SHA256SUMS.txt`, rather than expecting all application version labels or all ZIP hashes to change. The patch's connection checks and inherited limits are in [current notes](RELEASE_NOTES.md); [v0.3.0 notes](releases/v0.3.0-alpha.md) preserve the earlier acceptance.

| Download | What to do with it |
| --- | --- |
| `VRization-Windows-x64.zip` | Extract the **whole ZIP**, then run `VRization-Host.exe` inside it. Keep the documentation and license folders with the app. No Python installation is needed for this packaged host. |
| `VRization-Android-debug.apk` | Install on Android. This is the project's debug-signed alpha APK; normal Android installation approval still applies. A matching signing certificate is required to upgrade an existing installation without uninstalling it. |
| `VRization-vr-core-alpha.aar` | Android library for developers integrating rendering / pose functionality; not a phone installer. |
| `VRization-iOS-source.zip` | Source and Xcode project. Build on a Mac and use your own Apple signing for a physical iPhone / iPad. See [iOS instructions](IOS.md). |
| `VRization-iOS-Simulator.zip` | arm64 application for an Apple Silicon Mac's iOS Simulator. Intel Mac users build the source for their architecture. It cannot be installed on an iPhone or run as a Windows application. |
| `VRization-Licenses.zip` | License texts and provenance indexes; not an application. |

iOS source and Simulator downloads are **not signed, directly installable iPhone packages**. Android USB requires separately installed official Platform Tools; iOS USB requires separately installed Apple Devices / Apple Mobile Device support on Windows. See [the USB guide](USB.md).

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

### v0.3.1-alpha：更新电脑端，保留手机软件

本次发布用 **0.3.1 电脑端**搭配已验证的 **0.3.0 Android APK / AAR 与 iOS 应用**，共用不变的协议 v1。Android APK、AAR 和 arm64 iOS 模拟器 ZIP 原样复用，SHA-256 与 v0.3.0-alpha 相同。**已有 v0.3.0 Android 安装无需重装、升级或清除保存配置。** 关闭旧电脑端，完整解压新的 Windows ZIP，再运行新 EXE。

iOS 源码 ZIP 重新生成，包含更新的桌面源码 / 文档；其中 iOS 应用仍是 **0.3.0 / build 4**，模拟器应用也不变。真实手机仍需自己的 Apple 签名。按本次 `SHA256SUMS.txt` 核对每个产物，不要要求所有应用版本号或全部 ZIP 校验值都变化。补丁连接检查与继承限制见 [当前说明](RELEASE_NOTES.md)，[v0.3.0 原说明](releases/v0.3.0-alpha.md) 保留较早验收。

| 下载文件 | 用法 |
| --- | --- |
| `VRization-Windows-x64.zip` | **完整解压 ZIP**，运行其中的 `VRization-Host.exe`，保留文档和许可证文件夹。此打包电脑端无需另装 Python。 |
| `VRization-Android-debug.apk` | 安装到 Android。它是项目 debug 签名的 alpha APK，仍需正常 Android 安装授权。若要保留数据升级已有安装，签名证书必须一致。 |
| `VRization-vr-core-alpha.aar` | 供开发者集成渲染 / 姿态功能的 Android 库，不是手机安装包。 |
| `VRization-iOS-source.zip` | 源码与 Xcode 工程。在 Mac 构建，使用自己的 Apple 签名安装到真实 iPhone / iPad。见 [iOS 教程](IOS.md)。 |
| `VRization-iOS-Simulator.zip` | Apple Silicon Mac 的 iOS 模拟器 arm64 应用；Intel Mac 需从源码编译对应架构，不能安装到 iPhone，也不是 Windows 程序。 |
| `VRization-Licenses.zip` | 许可证原文与来源索引，不是应用程序。 |

iOS 源码与模拟器产物**不是已签名、可直接安装到 iPhone 的安装包**。Android USB 需要另行安装官方 Platform Tools；iOS USB 需要 Windows 另行安装 Apple Devices / Apple Mobile Device 支持。见 [USB 指南](USB.md)。

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

# 📦 Downloads and local version archive / 下载与本地版本归档

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

Download published assets and `SHA256SUMS.txt` from [GitHub Releases](https://github.com/LexZeon/VRization/releases). Keep release versions together when updating the computer and phone. Published alpha builds have the limitations recorded in [release notes](RELEASE_NOTES.md) and [compatibility records](COMPATIBILITY.md).

| Download | What to do with it |
| --- | --- |
| `VRization-Windows-x64.zip` | Extract the **whole ZIP**, then run `VRization-Host.exe` inside it. Keep the documentation and license folders with the app. No Python installation is needed for this packaged host. |
| `VRization-Android-debug.apk` | Install on Android. This is the project's debug-signed alpha APK; normal Android installation approval still applies. A matching signing certificate is required to upgrade an existing installation without uninstalling it. |
| `VRization-vr-core-alpha.aar` | Android library for developers integrating rendering / pose functionality; not a phone installer. |
| `VRization-iOS-source.zip` | Source and Xcode project. Build on a Mac and use your own Apple signing for a physical iPhone / iPad. See [iOS instructions](IOS.md). |
| `VRization-iOS-Simulator.zip` | Build for the matching Mac Simulator architecture. It cannot be installed on an iPhone or run as a Windows application. |
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

---

<!-- vrization:chinese -->
## 简体中文

从 [GitHub Releases](https://github.com/LexZeon/VRization/releases) 下载已发布产物及 `SHA256SUMS.txt`。更新时尽量让电脑与手机使用同一发布版本。Alpha 版限制见 [发布说明](RELEASE_NOTES.md) 与 [兼容性记录](COMPATIBILITY.md)。

| 下载文件 | 用法 |
| --- | --- |
| `VRization-Windows-x64.zip` | **完整解压 ZIP**，运行其中的 `VRization-Host.exe`，保留文档和许可证文件夹。此打包电脑端无需另装 Python。 |
| `VRization-Android-debug.apk` | 安装到 Android。它是项目 debug 签名的 alpha APK，仍需正常 Android 安装授权。若要保留数据升级已有安装，签名证书必须一致。 |
| `VRization-vr-core-alpha.aar` | 供开发者集成渲染 / 姿态功能的 Android 库，不是手机安装包。 |
| `VRization-iOS-source.zip` | 源码与 Xcode 工程。在 Mac 构建，使用自己的 Apple 签名安装到真实 iPhone / iPad。见 [iOS 教程](IOS.md)。 |
| `VRization-iOS-Simulator.zip` | 用于匹配架构的 Mac 模拟器，不能安装到 iPhone，也不是 Windows 程序。 |
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

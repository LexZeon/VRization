# 🙏 第三方来源与贡献 / Third-party notices

VRization 的原创实现使用 MIT 许可。以下依赖独立维护并保留各自许可；本文件记录版本、用途和来源，不会把依赖重新授权为 MIT。当前没有从其他 VR 应用复制实现源码，也没有引入外部照片、字体包或应用图标素材；界面截图来自本项目运行界面。

所有列出的运行时许可允许在满足其条件时商业使用。分发者仍需随二进制保留相应完整许可证、版权和 NOTICE；完整文本在 [licenses/](licenses/) 中。本文件的简述不能代替上游原文。

## 电脑端直接运行依赖

| 组件 / 版本 | 用途与贡献 | 作者 / 维护方 | 许可与精确来源 |
| --- | --- | --- | --- |
| aiohttp 3.14.4 | HTTP / WebSocket 服务端 | aio-libs contributors；Nikolay Kim、Andrew Svetlov 及贡献者 | Apache-2.0 AND MIT；[版本源码](https://github.com/aio-libs/aiohttp/tree/v3.14.4)、[Apache 文本](https://github.com/aio-libs/aiohttp/blob/v3.14.4/LICENSE.txt)。安装包中的附加 MIT 文本同样保留在 `licenses/python/aiohttp-3.14.4/`。 |
| MSS 10.2.0 | Windows 桌面与区域采集 | Mickaël “Tiger-222” Schoentgen 及贡献者 | MIT；[版本源码](https://github.com/BoboTiG/python-mss/tree/v10.2.0)、[许可](https://github.com/BoboTiG/python-mss/blob/v10.2.0/LICENSE.txt)。 |
| Pillow 12.3.0 | 图像缩放与 JPEG 编码 | Jeffrey “Alex” Clark 及贡献者；PIL 的 Secret Labs AB、Fredrik Lundh 及贡献者 | MIT-CMU；[版本源码](https://github.com/python-pillow/Pillow/tree/12.3.0)、[许可](https://github.com/python-pillow/Pillow/blob/12.3.0/LICENSE)。Pillow 该版本使用 MIT-CMU 名称；不可仅凭旧资料写成通用 MIT。 |

Python 运行环境、标准库与 Tcl/Tk 8.6.12 进入首版 Windows 单文件分发。其完整声明随包保存在 `licenses/python/CPython-LICENSE.txt`、`licenses/python/tcl-tk/` 和 `licenses/native/`，来源为构建时实际 Python 安装与对应上游版本。

原生审计范围是**首发本机 CPython 3.12.14 构建**。Windows CI 使用 CPython 3.12.10，尽管 Python 包固定版本相同，也不能假定 Python 内置 DLL、OpenSSL、Tcl/Tk 等原生版本完全相同。CI 会重新收集安装包许可；发布任何新二进制前仍应核对其实际运行时清单。本机构建清单不冒充所有 CI 产物的 SBOM。

Windows 程序不分发 Microsoft `VCRUNTIME140*.dll`，Visual C++ v14 x64 运行库作为系统前提由用户在需要时通过 [微软官方安装器](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist/) 安装。微软系统 / 运行库的许可由其供应方管理，不归项目 MIT 许可覆盖。

Pillow Windows wheel 还包含原生图像与字体组件，不能仅核对 Python 包名。wheel 的完整 `LICENSE` 与原始 CycloneDX SBOM 保存在 `licenses/python/pillow-12.3.0/`；实际功能探测、运行组件版本与补充上游来源记录在 `licenses/native/runtime-audit.json`、`licenses/native/upstream-sources.json` 及该目录 README 中。附加声明覆盖实际使用的 JPEG / TIFF / FreeType 等组件，以及 dav1d 1.5.3 和 aom 3.14.1 的许可 / 专利文件。可选且探测为不可用的功能不当作已分发运行组件；原始 SBOM 保留供核对。

Independent JPEG Group、FreeType Project 和加州大学伯克利分校的归属说明也保存在 [NOTICE](NOTICE)。这些原生组件的许可保持原样，不由项目 MIT 许可替代。

## 电脑端传递运行依赖

以下版本来自首版固定依赖解析，原始包的完整文本与必要 NOTICE 已保存在 `licenses/python/<名称>-<版本>/`。详细安装元数据与来源 URL 见 [python-components.json](licenses/python-components.json)，固定列表见 [requirements-lock.txt](desktop/requirements-lock.txt)。

| 组件 / 版本 | 上游 | 许可 |
| --- | --- | --- |
| aiohappyeyeballs 2.7.1 | [aio-libs/aiohappyeyeballs](https://github.com/aio-libs/aiohappyeyeballs) | PSF-2.0 |
| aiosignal 1.4.0 | [aio-libs/aiosignal](https://github.com/aio-libs/aiosignal) | Apache-2.0 |
| attrs 26.1.0 | [python-attrs/attrs](https://github.com/python-attrs/attrs) | MIT |
| frozenlist 1.8.0 | [aio-libs/frozenlist](https://github.com/aio-libs/frozenlist) | Apache-2.0 |
| idna 3.20 | [kjd/idna](https://github.com/kjd/idna) | BSD-3-Clause |
| multidict 6.9.1 | [aio-libs/multidict](https://github.com/aio-libs/multidict) | Apache-2.0 |
| propcache 0.5.4 | [aio-libs/propcache](https://github.com/aio-libs/propcache) | Apache-2.0；保留 NOTICE |
| typing_extensions 4.16.0 | [python/typing_extensions](https://github.com/python/typing_extensions) | PSF-2.0 |
| yarl 1.25.1 | [aio-libs/yarl](https://github.com/aio-libs/yarl) | Apache-2.0；保留 NOTICE |

这些组件分别提供连接调度、信号、数据结构、URL / Unicode 处理和类型支持。它们由上述上游项目的版权持有人及贡献者维护；准确版权年份和原始措辞以随包保存的许可文件为准。

## Android 运行依赖

`vr-core` 本身只使用 Android 平台框架；app 使用以下运行依赖。首版 Gradle 实际解析将 OkHttp 请求的较旧 Kotlin 标准库统一为 Okio 所需的 1.9.10。

| 组件 / 版本 | 用途与贡献 | 维护方 | 许可与来源 |
| --- | --- | --- | --- |
| OkHttp 4.12.0 | WebSocket 手机客户端 | Square, Inc. 及贡献者 | Apache-2.0；[版本源码](https://github.com/square/okhttp/tree/parent-4.12.0)、[许可](https://github.com/square/okhttp/blob/parent-4.12.0/LICENSE.txt)。 |
| Okio / okio-jvm 3.6.0 | OkHttp 所需 I/O | Square, Inc. 及贡献者 | Apache-2.0；[版本源码](https://github.com/square/okio/tree/parent-3.6.0)、[许可](https://github.com/square/okio/blob/parent-3.6.0/LICENSE.txt)。 |
| kotlin-stdlib、common、jdk7、jdk8 1.9.10 | OkHttp / Okio 的运行支持 | JetBrains 及 Kotlin 贡献者 | Apache-2.0；[版本源码](https://github.com/JetBrains/kotlin/tree/v1.9.10)、[许可](https://github.com/JetBrains/kotlin/blob/v1.9.10/license/LICENSE.txt)。 |
| JetBrains annotations 13.0 | JVM 注解与元数据 | JetBrains | Apache-2.0；[官方发布元数据](https://repo.maven.apache.org/maven2/org/jetbrains/annotations/13.0/annotations-13.0.pom)、[原始 source artifact](https://repo.maven.apache.org/maven2/org/jetbrains/annotations/13.0/annotations-13.0-sources.jar)。 |

完整 Android 文本与来源索引在 [licenses/android/](licenses/android/README.md)。测试使用的 JUnit 如有解析，仅属于单元测试环境，不打入应用运行时。

## 构建工具与文档服务

| 工具 | 用途 | 来源 / 许可说明 |
| --- | --- | --- |
| CPython 3.12 | 开发与 Windows 运行时 | [Python 许可](https://docs.python.org/3/license.html)；实际分发保留完整安装许可。 |
| PyInstaller 6.22.3 | Windows 程序打包 | [官方许可与例外](https://pyinstaller.org/en/stable/license.html)。工具采用 GPL-2.0 及例外，部分文件 Apache-2.0；例外允许商业程序打包，输出仍需遵守其运行依赖许可。没有修改 PyInstaller 源码。 |
| Gradle Wrapper 8.9 | Android 构建入口 | [Gradle](https://github.com/gradle/gradle/tree/v8.9.0)，Apache-2.0；构建工具，不作为应用运行组件。 |
| Android Gradle Plugin 8.7.3 | Android 构建 | [Android 构建工具](https://developer.android.com/build)，Android 开源工具组件按各自声明，SDK 安装同时受其发布条款约束。 |
| JDK 17 / Android SDK 35 | 编译、检查与模拟器 | 使用各自供应商的开发工具条款；不将 JDK / 完整 SDK 随 APK 分发。 |
| GitHub Actions 官方 actions | 检出、环境与产物 | [actions](https://github.com/actions)，各 action 上游 MIT；工作流按提交 SHA 固定。 |
| Shields.io | README 状态徽章 | [Shields](https://github.com/badges/shields)，在线徽章服务；未复制其服务器源码。 |

开发测试工具仅用于构建 / 检查，不按运行时功能引入。工具许可不意味着其生成产物自动拥有相同许可；实际分发组件仍需单独核查。

## 来源记录规则

新增依赖、代码片段或素材时记录：名称、作者、精确版本 / commit、原始 URL、用途、是否修改、许可路径与分发要求。任何修改过的第三方文件需明确标注修改，不删除原始版权头。依赖升级后重新收集许可证并对照实际安装 / Gradle 解析结果，避免声明和二进制不一致。

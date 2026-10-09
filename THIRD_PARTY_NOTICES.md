# 🙏 Third-party sources and credit / 第三方来源与贡献

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

Original VRization implementation is MIT. Independently maintained dependencies retain their own terms; this index records versions, purposes and sources without relicensing them. No implementation was copied from another VR application. No external photo, font package or app icon asset is included; screenshots show this project running.

The listed runtime terms permit commercial use when their conditions are met. Redistributors must preserve full applicable licenses, copyrights and NOTICE files in [licenses/](licenses/). This summary does not replace upstream texts.

### Direct host runtime dependencies

| Component | Purpose / maintainers | License and exact source |
| --- | --- | --- |
| aiohttp 3.14.4 | HTTP / WebSocket server; aio-libs contributors, Nikolay Kim and Andrew Svetlov | Apache-2.0 AND MIT; [source](https://github.com/aio-libs/aiohttp/tree/v3.14.4), [Apache license](https://github.com/aio-libs/aiohttp/blob/v3.14.4/LICENSE.txt). Additional installed MIT text is preserved in `licenses/python/aiohttp-3.14.4/`. |
| MSS 10.2.0 | Windows desktop / region capture; Mickaël “Tiger-222” Schoentgen and contributors | MIT; [source](https://github.com/BoboTiG/python-mss/tree/v10.2.0), [license](https://github.com/BoboTiG/python-mss/blob/v10.2.0/LICENSE.txt). |
| Pillow 12.3.0 | Scaling and JPEG encoding; Jeffrey “Alex” Clark and contributors, with PIL work by Secret Labs AB / Fredrik Lundh | MIT-CMU; [source](https://github.com/python-pillow/Pillow/tree/12.3.0), [license](https://github.com/python-pillow/Pillow/blob/12.3.0/LICENSE). Use this version's MIT-CMU designation, not generic MIT inferred from older references. |

The first Windows binary includes Python, standard-library components and Tcl/Tk 8.6.12. Full installed / upstream notices are retained in `licenses/python/CPython-LICENSE.txt`, `licenses/python/tcl-tk/` and `licenses/native/`.

The native audit describes **the first locally verified CPython 3.12.14 release build**. Windows CI uses 3.12.10. Matching Python package pins do not establish matching Python DLL, OpenSSL or Tcl/Tk versions. CI recollects installed-package notices; publishing any new binary still requires inspecting that artifact's native inventory. The local record is not an SBOM for every CI output.

Microsoft `VCRUNTIME140*.dll` is excluded. Visual C++ v14 x64 runtime is a system prerequisite installed when necessary through [Microsoft's official guide](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist/). Microsoft system / runtime terms remain its supplier's terms, outside this project's MIT license.

Pillow Windows wheels bundle native image / font components. The full wheel `LICENSE` and unchanged CycloneDX SBOM are retained in `licenses/python/pillow-12.3.0/`. Runtime feature tests, versions and additional sources are recorded in `licenses/native/runtime-audit.json`, `upstream-sources.json` and that directory's README. Supplemental texts cover JPEG / TIFF / FreeType components, dav1d 1.5.3 and aom 3.14.1 licenses / patent notices. Optional features detected as absent are not claimed as shipped; the publisher's SBOM remains intact for comparison.

Independent JPEG Group, FreeType Project and University of California, Berkeley attributions also appear in [NOTICE](NOTICE). The original native terms are never replaced by the project's MIT license.

### Transitive host runtime dependencies

Versions come from the first pinned resolution. Full texts / required NOTICE files are in `licenses/python/<name>-<version>/`. See [installed metadata and source URLs](licenses/python-components.json) and [requirements-lock.txt](desktop/requirements-lock.txt).

| Component | Upstream | License |
| --- | --- | --- |
| aiohappyeyeballs 2.7.1 | [aio-libs/aiohappyeyeballs](https://github.com/aio-libs/aiohappyeyeballs) | PSF-2.0 |
| aiosignal 1.4.0 | [aio-libs/aiosignal](https://github.com/aio-libs/aiosignal) | Apache-2.0 |
| attrs 26.1.0 | [python-attrs/attrs](https://github.com/python-attrs/attrs) | MIT |
| frozenlist 1.8.0 | [aio-libs/frozenlist](https://github.com/aio-libs/frozenlist) | Apache-2.0 |
| idna 3.20 | [kjd/idna](https://github.com/kjd/idna) | BSD-3-Clause |
| multidict 6.9.1 | [aio-libs/multidict](https://github.com/aio-libs/multidict) | Apache-2.0 |
| propcache 0.5.4 | [aio-libs/propcache](https://github.com/aio-libs/propcache) | Apache-2.0; NOTICE retained |
| typing_extensions 4.16.0 | [python/typing_extensions](https://github.com/python/typing_extensions) | PSF-2.0 |
| yarl 1.25.1 | [aio-libs/yarl](https://github.com/aio-libs/yarl) | Apache-2.0; NOTICE retained |

These provide connection scheduling, signals, structures, URL / Unicode handling and typing support. Copyright holders and contributors are the listed upstreams; exact years and wording remain in the bundled original texts.

### Android runtime dependencies

`vr-core` uses Android framework APIs only. The app uses these dependencies. First-release Gradle resolution aligned the older Kotlin requested by OkHttp with Okio's required 1.9.10.

| Component | Purpose / maintainer | License and source |
| --- | --- | --- |
| OkHttp 4.12.0 | Phone WebSocket client; Square, Inc. and contributors | Apache-2.0; [source](https://github.com/square/okhttp/tree/parent-4.12.0), [license](https://github.com/square/okhttp/blob/parent-4.12.0/LICENSE.txt). |
| Okio / okio-jvm 3.6.0 | I/O support; Square, Inc. and contributors | Apache-2.0; [source](https://github.com/square/okio/tree/parent-3.6.0), [license](https://github.com/square/okio/blob/parent-3.6.0/LICENSE.txt). |
| kotlin-stdlib / common / jdk7 / jdk8 1.9.10 | OkHttp / Okio runtime; JetBrains and Kotlin contributors | Apache-2.0; [source](https://github.com/JetBrains/kotlin/tree/v1.9.10), [license](https://github.com/JetBrains/kotlin/blob/v1.9.10/license/LICENSE.txt). |
| JetBrains annotations 13.0 | JVM annotations / metadata; JetBrains | Apache-2.0; [official POM](https://repo.maven.apache.org/maven2/org/jetbrains/annotations/13.0/annotations-13.0.pom), [original source artifact](https://repo.maven.apache.org/maven2/org/jetbrains/annotations/13.0/annotations-13.0-sources.jar). |

Full texts / source index: [licenses/android/](licenses/android/README.md). JUnit belongs to unit testing and is not an application runtime dependency.

The Android frame-handoff / texture-reuse optimization is original MIT implementation. It hands decoded images directly to a session-checked renderer slot, requests rendering from the decoder thread, reuses matching texture storage and caches shader locations. The consulted Google / Android API references are [GLSurfaceView.requestRender](https://developer.android.com/reference/android/opengl/GLSurfaceView#requestRender()) (documented as callable from any thread) and [GLUtils.texSubImage2D](https://developer.android.com/reference/android/opengl/GLUtils) (API 1); consulted 2026-10-09. No Android platform implementation or sample code was copied. These are OS-provided APIs, not new bundled libraries. Google's [documentation policy](https://developer.android.com/license) identifies CC-BY-4.0 documentation and Apache-2.0 code samples unless otherwise noted; this reference credit does not replace platform or sample terms. Phone-local timing ends when the texture-upload call returns, not when the GPU or screen finishes.

### iOS runtime and USB references

The original Swift client uses Apple's system Foundation / URLSession, UIKit, ImageIO, Core Graphics, Metal / MetalKit, Network and Core Motion frameworks. No third-party iOS runtime library or copied VR implementation is included. System frameworks and Apple SDK / signing services retain [Apple's terms](https://developer.apple.com/support/terms/); the original app and Swift core remain MIT. System frameworks are supplied by the operating system, not redistributed as third-party application libraries.

Android USB support invokes a separately installed official Android Debug Bridge; it does not bundle or relicense ADB, the Android SDK or device drivers. Syntax for `devices`, `get-devpath` and `reverse --no-rebind` was checked against Google's [ADB manual](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/user/adb.1.md) (`main` documentation, consulted 2026-10-09). Users obtain [Platform Tools](https://developer.android.com/tools/releases/platform-tools) separately under its applicable terms. The original Windows USB-presence fallback uses system SetupAPI through Python `ctypes`, referencing Microsoft's [SetupDiGetClassDevsW](https://learn.microsoft.com/en-us/windows/win32/api/setupapi/nf-setupapi-setupdigetclassdevsw), [SetupDiGetDeviceInstanceIdW](https://learn.microsoft.com/en-us/windows/win32/api/setupapi/nf-setupapi-setupdigetdeviceinstanceidw) and [SP_DEVINFO_DATA](https://learn.microsoft.com/en-us/windows/win32/api/setupapi/ns-setupapi-sp_devinfo_data) documentation; no driver or sample implementation is incorporated.

The Python Apple-USB adapter and Swift USB framing are original implementations. The following were consulted for usbmux interoperability: plist message framing, device selection, network-order ports and existing pairing-record fields. **These are references, not bundled or linked runtime dependencies:** no application / library implementation code, daemon, `iproxy` executable or binary from these projects is included or modified.

| Reference / contributors | Exact material consulted | Upstream terms |
| --- | --- | --- |
| node-usbmux; Sterling DeMille and contributors | [Protocol documentation](https://github.com/DeMille/node-usbmux/blob/54cafd659947d3c7761e4498392a49ad73c2ad60/README.md#usbmuxd-protocol), commit `54cafd659947d3c7761e4498392a49ad73c2ad60` | [MIT](https://github.com/DeMille/node-usbmux/blob/54cafd659947d3c7761e4498392a49ad73c2ad60/LICENSE). |
| go-ios; Daniel Paulus and contributors | [usbmux API documentation](https://pkg.go.dev/github.com/danielpaulus/go-ios@v0.0.0-20191119131658-c495aaebbeb6/usbmux), including `ReadPair` / `PairRecord`, version `v0.0.0-20191119131658-c495aaebbeb6` | MIT, as recorded by that version's documentation / license tab. This records the version actually consulted, not a current implementation dependency. |
| libusbmuxd; Nikias Bassen, Martin Szulecki, Paul Sladen and contributors | [README](https://github.com/libimobiledevice/libusbmuxd/blob/93eb168bf6b07472d17781328c21df0c60300524/README.md) and [client protocol API](https://github.com/libimobiledevice/libusbmuxd/blob/93eb168bf6b07472d17781328c21df0c60300524/src/libusbmuxd.c), commit `93eb168bf6b07472d17781328c21df0c60300524` | LGPL-2.1-or-later, stated in the source header; [COPYING](https://github.com/libimobiledevice/libusbmuxd/blob/93eb168bf6b07472d17781328c21df0c60300524/COPYING). |
| usbmuxd; initial daemon by Hector Martin, with Nikias Bassen and other contributors | [README](https://github.com/libimobiledevice/usbmuxd/blob/3ded00c9985a5108cfc7591a309f9a23d57a8cba/README.md) and [message fields in client.c](https://github.com/libimobiledevice/usbmuxd/blob/3ded00c9985a5108cfc7591a309f9a23d57a8cba/src/client.c), commit `3ded00c9985a5108cfc7591a309f9a23d57a8cba` | README declares GPL v3; the consulted `client.c` header permits GPL version 2 **or** version 3. This daemon is distinct from the LGPL libusbmuxd library. [GPL v3 text](https://github.com/libimobiledevice/usbmuxd/blob/3ded00c9985a5108cfc7591a309f9a23d57a8cba/COPYING.GPLv3). |

Apple Devices / Apple Mobile Device support must be installed separately under Apple's terms; Apple's [Windows guide](https://support.apple.com/guide/devices-windows/welcome/windows) and [USB / Trust instructions](https://support.apple.com/en-us/108643) inform user setup. Protocol-reference credit does not claim ownership of upstream contributions or relicense upstream materials. VRization's four-byte big-endian JSON / JPEG framing inside the iOS USB tunnel is its own application protocol, separate from usbmux's plist framing. Future incorporation of any reference project's code or binary requires a new license and distribution review.

### Build tools and documentation services

| Tool | Use / terms |
| --- | --- |
| CPython 3.12 | Development and Windows runtime; [Python license](https://docs.python.org/3/license.html), with full installed notices when distributed. |
| PyInstaller 6.22.3 | EXE packaging; [official GPL-2.0 exception](https://pyinstaller.org/en/stable/license.html), some files Apache-2.0. The exception permits packaging commercial applications; runtime dependencies retain their conditions. PyInstaller source was not modified. |
| Gradle Wrapper 8.9 | Build entry; [source](https://github.com/gradle/gradle/tree/v8.9.0), Apache-2.0; not an app runtime. |
| Android Gradle Plugin 8.7.3 | [Android build tools](https://developer.android.com/build); components and SDK installation retain their applicable upstream terms. |
| JDK 17 / Android SDK 35 | Compilation, checks and emulator under vendor tool terms; not bundled wholesale with the APK. |
| Swift / Xcode | Original Swift compilation, Apple SDKs, Simulator and optional local signing. [Swift sources](https://github.com/swiftlang/swift), Apache-2.0 with Runtime Library Exception; Xcode / Apple SDK components retain [Apple's applicable terms](https://developer.apple.com/support/terms/). No compiler / Simulator is bundled in the application. |
| Official GitHub Actions | Checkout, environment and artifacts; [actions](https://github.com/actions), upstream MIT, pinned by commit SHA. |
| Shields.io | README badge service; [Shields](https://github.com/badges/shields); no server source copied. |

Test / build tooling is separate from runtime features. A tool's license does not automatically become the output's license; inspect components actually distributed.

### Provenance rules

Record name, author, exact version / commit or document, original URL, purpose, modifications, license path and distribution conditions for each new dependency, snippet, asset **or optimization idea**. Credit remains required when an implementation is rewritten. Distinguish shipped dependencies, copied / adapted code, and research-only references; rewriting is not a substitute for checking applicable upstream terms. Mark changes to third-party files without removing copyright headers. Recollect licenses after updates and compare actual installed / Gradle-resolved dependencies with the declaration.

---

### Windows GPU capture: original implementation and acknowledged ideas

[windows_gpu.py](https://github.com/LexZeon/VRization/blob/main/desktop/src/vrization_host/windows_gpu.py) is original VRization MIT code: its `ctypes` COM bindings, resource ownership, output checks, shaders and failure handling were written for this project. The optimization moves crop, display rotation and linear downscaling onto D3D11 before reading a small output buffer. Windows supplies DXGI, D3D11 and the shader compiler; no Microsoft system DLL, SDK, sample implementation or third-party capture binary is bundled. GDI pre-scaling and MSS remain compatibility paths. See [architecture](https://github.com/LexZeon/VRization/blob/main/docs/ARCHITECTURE.md) and [performance](https://github.com/LexZeon/VRization/blob/main/docs/PERFORMANCE.md).

The following projects informed capture alternatives, adapter / output selection, rotation, staging readback or future streaming design. **They are research references, not runtime dependencies or incorporated application source.** DXcam and its NumPy / comtypes dependencies were evaluated in an isolated research environment; none is required or bundled by the final original GPU backend. No Sunshine / Moonlight GPL code, library or executable was copied, linked or redistributed.

| Reference / authors | Exact version / source and upstream terms | Referenced idea / VRization result |
| --- | --- | --- |
| DXcam; Rain and contributors | **0.3.0**, commit `de356cb5a39f50645d495c522fabb03e984728e7`; [source](https://github.com/ra1nty/DXcam/tree/de356cb5a39f50645d495c522fabb03e984728e7), [MIT license](https://github.com/ra1nty/DXcam/blob/de356cb5a39f50645d495c522fabb03e984728e7/LICENSE), copyright 2022 Rain. | Desktop Duplication, explicit adapter / output binding, rotation and staging readback research. VRization uses its own COM calls, GPU crop / resize and resource lifecycle; it does not import or vendor DXcam. |
| Win32CaptureSample; Robert Mikhayelyan and contributors | Commit `49fefe79fd9b11025f0b5eb91783a98888516070`; [source](https://github.com/robmikh/Win32CaptureSample/tree/49fefe79fd9b11025f0b5eb91783a98888516070), [MIT license](https://github.com/robmikh/Win32CaptureSample/blob/49fefe79fd9b11025f0b5eb91783a98888516070/LICENSE), copyright 2019 Robert Mikhayelyan. | Windows Graphics Capture / monitor selection informed the comparison of Windows capture approaches. The current backend uses original Desktop Duplication bindings, not this sample's implementation or WGC transport. |
| Windows-classic-samples; Microsoft Corporation and contributors | Commit `434f6002bdf9cf9829406c3ff2b33387982d6168`; [Desktop Duplication sample](https://github.com/microsoft/Windows-classic-samples/tree/434f6002bdf9cf9829406c3ff2b33387982d6168/Samples/DXGIDesktopDuplication), [MIT license](https://github.com/microsoft/Windows-classic-samples/blob/434f6002bdf9cf9829406c3ff2b33387982d6168/LICENSE). The repository also identifies some font material under SIL OFL; no font material is used. | DXGI lifecycle, rotation and D3D texture ownership informed the original system API implementation. No sample code is included. |
| comtypes; Thomas Heller and Comtypes Developers | **1.4.17**, commit `f855872f7da2e3ad561eca9861b488ecb8b6422f`; [source](https://github.com/enthought/comtypes/tree/f855872f7da2e3ad561eca9861b488ecb8b6422f), [MIT license](https://github.com/enthought/comtypes/blob/f855872f7da2e3ad561eca9861b488ecb8b6422f/LICENSE.txt), copyright 2006–2013 Thomas Heller and 2014 Comtypes Developers. | COM support in the isolated DXcam experiment. The final backend has its own standard-library `ctypes` bindings and does not use this package. |
| NumPy; NumPy Developers | **2.5.3**, commit `dd88c0c19b54ad9ed3533224221285bf0873249a`; [source](https://github.com/numpy/numpy/tree/dd88c0c19b54ad9ed3533224221285bf0873249a), [core BSD-3-Clause license](https://github.com/numpy/numpy/blob/dd88c0c19b54ad9ed3533224221285bf0873249a/LICENSE.txt), copyright 2005–2025 NumPy Developers. Binary wheels have additional component terms. | Image arrays in the isolated DXcam experiment. The final backend returns owned bytes and uses no NumPy; its wheels / native libraries are not bundled. |
| Sunshine; LizardByte / Sunshine contributors | **v2026.914.233613**, commit `63d35f702ee9e362e43263742981836ec0710384`; [source](https://github.com/LizardByte/Sunshine/tree/63d35f702ee9e362e43263742981836ec0710384), [GPL-3.0-only declaration](https://github.com/LizardByte/Sunshine/blob/63d35f702ee9e362e43263742981836ec0710384/CMakeLists.txt). | Architecture-only comparison of capture, hardware encoding and transport stages. VRization retains JPEG v1; no Sunshine implementation or binary is included. |
| Moonlight Qt; Moonlight developers and contributors | **v6.2.0**, commit `de2467e433821664cdd2224aad8c89a625be1ad9`; [source](https://github.com/moonlight-stream/moonlight-qt/tree/de2467e433821664cdd2224aad8c89a625be1ad9), [GPL-3.0-or-later project declaration](https://github.com/moonlight-stream/moonlight-qt/blob/de2467e433821664cdd2224aad8c89a625be1ad9/app/deploy/linux/com.moonlight_stream.Moonlight.appdata.xml). Its CC0 metadata label does not license the application. | Architecture-only comparison of hardware decode and presentation stages. No Moonlight source, library or executable is included. |

MIT / BSD references allow commercial reuse subject to their conditions, including applicable notices; NumPy binary distribution requires reviewing all bundled component terms. GPL also permits commercial use, but incorporating GPL code or binaries requires complying with its source / copyleft and distribution conditions. This project does not relicense any reference. Future adoption of code or binaries needs a fresh review of the exact material and combined distribution; an original rewrite does not erase source credit or applicable obligations.

Microsoft's API documentation was consulted on 2026-10-09 for: [Desktop Duplication](https://learn.microsoft.com/en-us/windows/win32/direct3ddxgi/desktop-dup-api), [DuplicateOutput](https://learn.microsoft.com/en-us/windows/win32/api/dxgi1_2/nf-dxgi1_2-idxgioutput1-duplicateoutput), [AcquireNextFrame](https://learn.microsoft.com/en-us/windows/win32/api/dxgi1_2/nf-dxgi1_2-idxgioutputduplication-acquirenextframe), [DXGI_OUTPUT_DESC](https://learn.microsoft.com/en-us/windows/win32/api/dxgi/ns-dxgi-dxgi_output_desc), [D3D11CreateDevice](https://learn.microsoft.com/en-us/windows/win32/api/d3d11/nf-d3d11-d3d11createdevice), [texture descriptions](https://learn.microsoft.com/en-us/windows/win32/api/d3d11/ns-d3d11-d3d11_texture2d_desc), [D3DCompile](https://learn.microsoft.com/en-us/windows/win32/api/d3dcompiler/nf-d3dcompiler-d3dcompile) and [CreateForMonitor](https://learn.microsoft.com/en-us/windows/win32/api/windows.graphics.capture.interop/nf-windows-graphics-capture-interop-igraphicscaptureiteminterop-createformonitor). Windows / SDK terms remain Microsoft's; documentation reference is not a bundled SDK or a transferred license for its DLLs.

### Windows GDI capture API references

The original GDI adapter scales into a smaller top-down bitmap before Python reads pixels. Microsoft references: [StretchBlt](https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-stretchblt), [CreateDIBSection](https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-createdibsection), [GdiFlush](https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-gdiflush), [SetStretchBltMode](https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-setstretchbltmode), [GetDC](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getdc), [ReleaseDC](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-releasedc) and [GetMonitorInfoW](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getmonitorinfow). No Microsoft sample implementation, SDK or system DLL is copied or bundled. Windows supplies these APIs under its own terms; the adapter is original MIT code. MSS remains the compatibility fallback.

---

<!-- vrization:chinese -->
## 简体中文

VRization 的原创实现使用 MIT 许可。以下依赖独立维护并保留各自许可；本文件记录版本、用途和来源，不会把依赖重新授权为 MIT。当前没有从其他 VR 应用复制实现源码，也没有引入外部照片、字体包或应用图标素材；界面截图来自本项目运行界面。

所有列出的运行时许可允许在满足其条件时商业使用。分发者仍需随二进制保留相应完整许可证、版权和 NOTICE；完整文本在 [licenses/](licenses/) 中。本文件的简述不能代替上游原文。

### 电脑端直接运行依赖

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

### 电脑端传递运行依赖

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

### Android 运行依赖

`vr-core` 本身只使用 Android 平台框架；app 使用以下运行依赖。首版 Gradle 实际解析将 OkHttp 请求的较旧 Kotlin 标准库统一为 Okio 所需的 1.9.10。

| 组件 / 版本 | 用途与贡献 | 维护方 | 许可与来源 |
| --- | --- | --- | --- |
| OkHttp 4.12.0 | WebSocket 手机客户端 | Square, Inc. 及贡献者 | Apache-2.0；[版本源码](https://github.com/square/okhttp/tree/parent-4.12.0)、[许可](https://github.com/square/okhttp/blob/parent-4.12.0/LICENSE.txt)。 |
| Okio / okio-jvm 3.6.0 | OkHttp 所需 I/O | Square, Inc. 及贡献者 | Apache-2.0；[版本源码](https://github.com/square/okio/tree/parent-3.6.0)、[许可](https://github.com/square/okio/blob/parent-3.6.0/LICENSE.txt)。 |
| kotlin-stdlib、common、jdk7、jdk8 1.9.10 | OkHttp / Okio 的运行支持 | JetBrains 及 Kotlin 贡献者 | Apache-2.0；[版本源码](https://github.com/JetBrains/kotlin/tree/v1.9.10)、[许可](https://github.com/JetBrains/kotlin/blob/v1.9.10/license/LICENSE.txt)。 |
| JetBrains annotations 13.0 | JVM 注解与元数据 | JetBrains | Apache-2.0；[官方发布元数据](https://repo.maven.apache.org/maven2/org/jetbrains/annotations/13.0/annotations-13.0.pom)、[原始 source artifact](https://repo.maven.apache.org/maven2/org/jetbrains/annotations/13.0/annotations-13.0-sources.jar)。 |

完整 Android 文本与来源索引在 [licenses/android/](licenses/android/README.md)。测试使用的 JUnit 如有解析，仅属于单元测试环境，不打入应用运行时。

Android 帧交接 / 纹理复用优化为原创 MIT 实现：解码图像直接交给检查会话的渲染单槽，在解码线程请求渲染，复用相同尺寸格式的纹理存储并缓存着色器位置。参考 Google / Android 官方 API 文档：[GLSurfaceView.requestRender](https://developer.android.com/reference/android/opengl/GLSurfaceView#requestRender())（明确允许任意线程调用）与 [GLUtils.texSubImage2D](https://developer.android.com/reference/android/opengl/GLUtils)（API 1），查阅于 2026-10-09；没有复制 Android 平台实现或示例代码。这些是操作系统提供的 API，不是新增随包库。Google [文档政策](https://developer.android.com/license) 说明文档默认 CC-BY-4.0、代码示例默认 Apache-2.0，特别说明除外；参考鸣谢不能代替平台或示例条款。手机内部计时止于纹理上传调用返回，不代表 GPU 或屏幕完成。

### iOS 运行时与 USB 参考

原创 Swift 客户端使用 Apple 系统 Foundation / URLSession、UIKit、ImageIO、Core Graphics、Metal / MetalKit、Network 与 Core Motion 框架，没有第三方 iOS 运行库或复制的 VR 实现。系统框架、Apple SDK 和签名服务保留 [Apple 条款](https://developer.apple.com/support/terms/)，原创应用与 Swift 核心仍为 MIT。系统框架由操作系统提供，不作为第三方应用库重新分发。

Android USB 功能调用另行安装的官方 Android Debug Bridge，不打包或重新授权 ADB、Android SDK 或设备驱动。`devices`、`get-devpath` 与 `reverse --no-rebind` 语法参考 Google 的 [ADB 手册](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/user/adb.1.md)（`main` 文档，查阅于 2026-10-09）。用户按相应条款另行获取 [Platform Tools](https://developer.android.com/tools/releases/platform-tools)。原创 Windows USB 存在性回退通过 Python `ctypes` 调用系统 SetupAPI，参考微软的 [SetupDiGetClassDevsW](https://learn.microsoft.com/en-us/windows/win32/api/setupapi/nf-setupapi-setupdigetclassdevsw)、[SetupDiGetDeviceInstanceIdW](https://learn.microsoft.com/en-us/windows/win32/api/setupapi/nf-setupapi-setupdigetdeviceinstanceidw) 与 [SP_DEVINFO_DATA](https://learn.microsoft.com/en-us/windows/win32/api/setupapi/ns-setupapi-sp_devinfo_data) 文档，没有引入驱动或示例实现。

Python Apple USB 适配器和 Swift USB 分帧均为原创实现。以下材料用于 usbmux 互操作参考，涉及 plist 消息分帧、设备选择、网络字节序端口和已有配对记录字段。**它们是参考资料，不是随包或链接的运行依赖：** 没有引入或修改这些项目的应用 / 库实现代码、daemon、`iproxy` 程序或二进制。

| 参考 / 贡献者 | 实际查阅材料 | 上游条款 |
| --- | --- | --- |
| node-usbmux；Sterling DeMille 及贡献者 | [协议文档](https://github.com/DeMille/node-usbmux/blob/54cafd659947d3c7761e4498392a49ad73c2ad60/README.md#usbmuxd-protocol)，commit `54cafd659947d3c7761e4498392a49ad73c2ad60` | [MIT](https://github.com/DeMille/node-usbmux/blob/54cafd659947d3c7761e4498392a49ad73c2ad60/LICENSE)。 |
| go-ios；Daniel Paulus 及贡献者 | [usbmux API 文档](https://pkg.go.dev/github.com/danielpaulus/go-ios@v0.0.0-20191119131658-c495aaebbeb6/usbmux)，包括 `ReadPair` / `PairRecord`，版本 `v0.0.0-20191119131658-c495aaebbeb6` | 该版文档 / license 标签记录为 MIT。记录实际参考版本，不表示依赖当前实现。 |
| libusbmuxd；Nikias Bassen、Martin Szulecki、Paul Sladen 及贡献者 | [README](https://github.com/libimobiledevice/libusbmuxd/blob/93eb168bf6b07472d17781328c21df0c60300524/README.md) 与 [客户端协议 API](https://github.com/libimobiledevice/libusbmuxd/blob/93eb168bf6b07472d17781328c21df0c60300524/src/libusbmuxd.c)，commit `93eb168bf6b07472d17781328c21df0c60300524` | 源码头声明 LGPL-2.1-or-later；[COPYING](https://github.com/libimobiledevice/libusbmuxd/blob/93eb168bf6b07472d17781328c21df0c60300524/COPYING)。 |
| usbmuxd；初始 daemon 作者 Hector Martin，及 Nikias Bassen 等贡献者 | [README](https://github.com/libimobiledevice/usbmuxd/blob/3ded00c9985a5108cfc7591a309f9a23d57a8cba/README.md) 与 [client.c 消息字段](https://github.com/libimobiledevice/usbmuxd/blob/3ded00c9985a5108cfc7591a309f9a23d57a8cba/src/client.c)，commit `3ded00c9985a5108cfc7591a309f9a23d57a8cba` | README 声明 GPL v3；实际参考的 `client.c` 头允许 GPL 第 2 版**或**第 3 版。此 daemon 与 LGPL 的 libusbmuxd 库不同。[GPL v3 原文](https://github.com/libimobiledevice/usbmuxd/blob/3ded00c9985a5108cfc7591a309f9a23d57a8cba/COPYING.GPLv3)。 |

Apple Devices / Apple Mobile Device 支持需按 Apple 条款另行安装；用户设置参考 Apple 的 [Windows 指南](https://support.apple.com/guide/devices-windows/welcome/windows) 与 [USB / 信任说明](https://support.apple.com/en-us/108643)。协议参考致谢不冒称上游贡献归本项目，不重新授权上游材料。iOS USB 隧道内的四字节大端 JSON / JPEG 分帧是 VRization 自有应用协议，与 usbmux 的 plist 分帧不同。以后如引入任一参考项目的代码或二进制，须重新核对许可与分发条件。

### 构建工具与文档服务

| 工具 | 用途 | 来源 / 许可说明 |
| --- | --- | --- |
| CPython 3.12 | 开发与 Windows 运行时 | [Python 许可](https://docs.python.org/3/license.html)；实际分发保留完整安装许可。 |
| PyInstaller 6.22.3 | Windows 程序打包 | [官方许可与例外](https://pyinstaller.org/en/stable/license.html)。工具采用 GPL-2.0 及例外，部分文件 Apache-2.0；例外允许商业程序打包，输出仍需遵守其运行依赖许可。没有修改 PyInstaller 源码。 |
| Gradle Wrapper 8.9 | Android 构建入口 | [Gradle](https://github.com/gradle/gradle/tree/v8.9.0)，Apache-2.0；构建工具，不作为应用运行组件。 |
| Android Gradle Plugin 8.7.3 | Android 构建 | [Android 构建工具](https://developer.android.com/build)，Android 开源工具组件按各自声明，SDK 安装同时受其发布条款约束。 |
| JDK 17 / Android SDK 35 | 编译、检查与模拟器 | 使用各自供应商的开发工具条款；不将 JDK / 完整 SDK 随 APK 分发。 |
| Swift / Xcode | Swift 编译、Apple SDK、模拟器与可选本地签名 | [Swift 源码](https://github.com/swiftlang/swift) 按 Apache-2.0 及 Runtime Library Exception；Xcode / Apple SDK 保留 [Apple 适用条款](https://developer.apple.com/support/terms/)。应用不附带编译器 / 模拟器。 |
| GitHub Actions 官方 actions | 检出、环境与产物 | [actions](https://github.com/actions)，各 action 上游 MIT；工作流按提交 SHA 固定。 |
| Shields.io | README 状态徽章 | [Shields](https://github.com/badges/shields)，在线徽章服务；未复制其服务器源码。 |

开发测试工具仅用于构建 / 检查，不按运行时功能引入。工具许可不意味着其生成产物自动拥有相同许可；实际分发组件仍需单独核查。

### 来源记录规则

新增依赖、代码片段、素材或**优化思路**时记录：名称、作者、精确版本 / commit 或文档、原始 URL、用途、是否修改、许可路径与分发要求。重写实现也要鸣谢，区分随包依赖、复制 / 改编代码与仅研究参考；重写不能替代适用许可核查。任何修改过的第三方文件需明确标注修改，不删除原始版权头。依赖升级后重新收集许可证并对照实际安装 / Gradle 解析结果，避免声明和二进制不一致。

### Windows GPU 采集：原创实现与思路鸣谢

[windows_gpu.py](https://github.com/LexZeon/VRization/blob/main/desktop/src/vrization_host/windows_gpu.py) 是 VRization 原创 MIT 代码：为本项目编写 `ctypes` COM 绑定、资源管理、输出校验、着色器与错误处理。优化把裁切、显示旋转与线性缩小放到 D3D11，仅回读小尺寸缓冲区。DXGI、D3D11 和着色器编译器由 Windows 提供；不打包微软系统 DLL、SDK、示例实现或第三方采集二进制。GDI 预缩放与 MSS 保留作兼容路径，见 [架构](https://github.com/LexZeon/VRization/blob/main/docs/ARCHITECTURE.md) 与 [性能](https://github.com/LexZeon/VRization/blob/main/docs/PERFORMANCE.md)。

以下项目帮助研究采集方案、显卡 / 输出选择、旋转、staging 回读或未来串流设计。**它们是研究参考，不是运行依赖或采用的应用源码。** DXcam 及其 NumPy / comtypes 依赖在独立研究环境评估，最终原创 GPU 后端不需要也不分发这些组件；没有复制、链接或分发 Sunshine / Moonlight 的 GPL 代码、库或可执行文件。

| 参考 / 作者 | 精确版本 / 来源与上游许可 | 参考思路 / 本项目实现 |
| --- | --- | --- |
| DXcam；Rain 及贡献者 | **0.3.0**，commit `de356cb5a39f50645d495c522fabb03e984728e7`；[源码](https://github.com/ra1nty/DXcam/tree/de356cb5a39f50645d495c522fabb03e984728e7)、[MIT 许可](https://github.com/ra1nty/DXcam/blob/de356cb5a39f50645d495c522fabb03e984728e7/LICENSE)，版权 2022 Rain。 | 研究 Desktop Duplication、显式显卡 / 输出绑定、旋转与 staging 回读；本项目自行实现 COM 调用、GPU 裁切 / 缩放和资源生命周期，不导入或复制 DXcam。 |
| Win32CaptureSample；Robert Mikhayelyan 及贡献者 | commit `49fefe79fd9b11025f0b5eb91783a98888516070`；[源码](https://github.com/robmikh/Win32CaptureSample/tree/49fefe79fd9b11025f0b5eb91783a98888516070)、[MIT 许可](https://github.com/robmikh/Win32CaptureSample/blob/49fefe79fd9b11025f0b5eb91783a98888516070/LICENSE)，版权 2019 Robert Mikhayelyan。 | Windows Graphics Capture / 显示器选择用于比较 Windows 采集路线；当前后端为原创 Desktop Duplication 绑定，没有采用该示例实现或 WGC 传输。 |
| Windows-classic-samples；Microsoft Corporation 及贡献者 | commit `434f6002bdf9cf9829406c3ff2b33387982d6168`；[Desktop Duplication 示例](https://github.com/microsoft/Windows-classic-samples/tree/434f6002bdf9cf9829406c3ff2b33387982d6168/Samples/DXGIDesktopDuplication)、[MIT 许可](https://github.com/microsoft/Windows-classic-samples/blob/434f6002bdf9cf9829406c3ff2b33387982d6168/LICENSE)。仓库另声明部分字体材料使用 SIL OFL，本项目没有使用字体材料。 | DXGI 生命周期、旋转与 D3D 纹理所有权帮助设计原创系统 API 实现；不包含示例代码。 |
| comtypes；Thomas Heller 与 Comtypes Developers | **1.4.17**，commit `f855872f7da2e3ad561eca9861b488ecb8b6422f`；[源码](https://github.com/enthought/comtypes/tree/f855872f7da2e3ad561eca9861b488ecb8b6422f)、[MIT 许可](https://github.com/enthought/comtypes/blob/f855872f7da2e3ad561eca9861b488ecb8b6422f/LICENSE.txt)，版权 2006–2013 Thomas Heller、2014 Comtypes Developers。 | 独立 DXcam 实验中的 COM 支持；最终后端自行编写标准库 `ctypes` 绑定，不使用此包。 |
| NumPy；NumPy Developers | **2.5.3**，commit `dd88c0c19b54ad9ed3533224221285bf0873249a`；[源码](https://github.com/numpy/numpy/tree/dd88c0c19b54ad9ed3533224221285bf0873249a)、[核心 BSD-3-Clause 许可](https://github.com/numpy/numpy/blob/dd88c0c19b54ad9ed3533224221285bf0873249a/LICENSE.txt)，版权 2005–2025 NumPy Developers；二进制 wheel 另有组件条款。 | 独立 DXcam 实验中的图像数组；最终后端返回独立字节，不使用 NumPy，不打包其 wheel / 原生库。 |
| Sunshine；LizardByte / Sunshine 贡献者 | **v2026.914.233613**，commit `63d35f702ee9e362e43263742981836ec0710384`；[源码](https://github.com/LizardByte/Sunshine/tree/63d35f702ee9e362e43263742981836ec0710384)、[GPL-3.0-only 声明](https://github.com/LizardByte/Sunshine/blob/63d35f702ee9e362e43263742981836ec0710384/CMakeLists.txt)。 | 仅架构比较：采集、硬件编码与传输各阶段；本项目保留 JPEG v1，不引入 Sunshine 实现或二进制。 |
| Moonlight Qt；Moonlight 开发者及贡献者 | **v6.2.0**，commit `de2467e433821664cdd2224aad8c89a625be1ad9`；[源码](https://github.com/moonlight-stream/moonlight-qt/tree/de2467e433821664cdd2224aad8c89a625be1ad9)、[应用 GPL-3.0-or-later 声明](https://github.com/moonlight-stream/moonlight-qt/blob/de2467e433821664cdd2224aad8c89a625be1ad9/app/deploy/linux/com.moonlight_stream.Moonlight.appdata.xml)。CC0 元数据标签不适用于应用源码。 | 仅架构比较：硬件解码与呈现阶段；不引入 Moonlight 源码、库或可执行文件。 |

MIT / BSD 参考允许满足条件后的商业复用，包括保留适用声明；分发 NumPy 二进制还要核查所有随包组件条款。GPL 也允许商业使用，但采用 GPL 代码或二进制必须遵守源码 / copyleft 与分发条件。本项目不重新授权参考材料；以后引入代码或二进制，要针对实际材料与组合分发重新核查。原创重写不消除来源鸣谢或适用义务。

2026-10-09 查阅的 Microsoft API 文档包括：[Desktop Duplication](https://learn.microsoft.com/en-us/windows/win32/direct3ddxgi/desktop-dup-api)、[DuplicateOutput](https://learn.microsoft.com/en-us/windows/win32/api/dxgi1_2/nf-dxgi1_2-idxgioutput1-duplicateoutput)、[AcquireNextFrame](https://learn.microsoft.com/en-us/windows/win32/api/dxgi1_2/nf-dxgi1_2-idxgioutputduplication-acquirenextframe)、[DXGI_OUTPUT_DESC](https://learn.microsoft.com/en-us/windows/win32/api/dxgi/ns-dxgi-dxgi_output_desc)、[D3D11CreateDevice](https://learn.microsoft.com/en-us/windows/win32/api/d3d11/nf-d3d11-d3d11createdevice)、[纹理描述](https://learn.microsoft.com/en-us/windows/win32/api/d3d11/ns-d3d11-d3d11_texture2d_desc)、[D3DCompile](https://learn.microsoft.com/en-us/windows/win32/api/d3dcompiler/nf-d3dcompiler-d3dcompile) 和 [CreateForMonitor](https://learn.microsoft.com/en-us/windows/win32/api/windows.graphics.capture.interop/nf-windows-graphics-capture-interop-igraphicscaptureiteminterop-createformonitor)。Windows / SDK 保留微软自身条款；参考文档不等于打包 SDK 或取得其 DLL 的重授权。

### Windows GDI 采集 API 参考

原创 GDI 适配器先缩小到顶向下位图，再由 Python 读取像素。Microsoft 参考：[StretchBlt](https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-stretchblt)、[CreateDIBSection](https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-createdibsection)、[GdiFlush](https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-gdiflush)、[SetStretchBltMode](https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-setstretchbltmode)、[GetDC](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getdc)、[ReleaseDC](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-releasedc) 和 [GetMonitorInfoW](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getmonitorinfow)。未复制或随包分发微软示例实现、SDK 或系统 DLL。Windows 按自身条款提供这些 API，适配器为原创 MIT 代码；保留 MSS 兼容回退。

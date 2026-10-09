# Native runtime notices / 原生运行时说明

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

`runtime-audit.json` records the Windows x64 runtime inspected for the first locally verified v0.1.0-alpha release (CPython 3.12.14), not every CI rebuild, including native binary hashes, Pillow feature detection and AVIF codec versions. `upstream-sources.json` records original download URLs and SHA-256 hashes of the additional notices in this directory, together with official prerequisite references. License texts are preserved verbatim.

The complete installed Pillow 12.3.0 wheel license is retained at `../python/pillow-12.3.0/LICENSE`. It contains bundled notices for Brotli 1.2.0, FreeType 2.14.3, HarfBuzz 14.2.1, Little CMS 2.19.1, libavif 1.4.2, libjpeg-turbo 3.1.4.1, libpng 1.6.58, libwebp 1.6.0, OpenJPEG 2.5.4, libtiff 4.7.1, XZ 5.8.3 and zlib-ng 2.3.3. FreeType is used under the FreeType License (FTL). This directory additionally retains the exact libavif codec notices for dav1d 1.5.3 and aom 3.14.1, including aom's patent grant and authors list.

Pillow's publisher SBOM is retained unchanged at `../python/pillow-12.3.0/sboms/pillow-12.3.0.cdx.json`. It describes optional build capabilities as well as installed capabilities. Runtime checks show RAQM/FriBiDi, libimagequant and XCB support unavailable in this Windows wheel; the presence of those optional components in that SBOM does not establish that their binaries are shipped. Pillow's Little CMS API reports 2.19, while its bundled license section identifies the build dependency as 2.19.1.

That first local host build distributes CPython 3.12.14, Tcl/Tk 8.6.12, OpenSSL 3.5.8, libffi ABI 8, Expat 2.8.3, libmpdec 2.5.1 and standard-library compression code. The CPython and installed Tk notices are retained in `../python/`; Tcl's upstream core license is additionally retained here. The bundled libffi DLL does not expose its release version: its ABI and binary hash are recorded instead of inventing a release number. Its permissive MIT license text is retained from upstream v3.4.4. The `_lzma` extension similarly does not expose an XZ release; current 0BSD and historical public-domain notices are retained without asserting an exact release.

This software is based in part on the work of the Independent JPEG Group. Portions of this software are copyright © 1996–2026 The FreeType Project (https://freetype.org). All rights reserved. This software includes code developed by the University of California, Berkeley.

Microsoft's Visual C++ x64 runtime is a separately installed prerequisite. The EXE excludes `vcruntime140*.dll`, `api-ms-win-*.dll` and `ucrtbase.dll`; Windows 10/11 supply the latter system libraries. Microsoft runtime installation terms are referenced through official URLs in the source index; neither Microsoft runtime binaries nor copied Microsoft EULAs are distributed here. Obtain the prerequisite from [Microsoft's official download](https://aka.ms/vc14/vc_redist.x64.exe).

When updating runtime dependencies, rerun the license collector and inspect the new wheel notices, SBOM, runtime features, native codecs and PyInstaller dependency graph before updating this audit.

Windows CI uses CPython 3.12.10 and retains this historical audit for provenance; its native hashes and versions must be checked against the concrete CI output before publishing. The recorded hashes below are not regenerated or relabeled as a CI inventory.

---

<!-- vrization:chinese -->
## 简体中文

`runtime-audit.json` 记录首个本机验证的 v0.1.0-alpha Windows x64 产物（CPython 3.12.14）的原生二进制哈希、Pillow 功能探测与 AVIF 编解码器版本。它不是全部 CI 重建的清单。`upstream-sources.json` 记录补充声明的原始下载 URL、SHA-256 与官方系统前提来源。第三方许可原文保持不变。

Pillow 12.3.0 wheel 的完整许可位于 `../python/pillow-12.3.0/LICENSE`，含 Brotli 1.2.0、FreeType 2.14.3、HarfBuzz 14.2.1、Little CMS 2.19.1、libavif 1.4.2、libjpeg-turbo 3.1.4.1、libpng 1.6.58、libwebp 1.6.0、OpenJPEG 2.5.4、libtiff 4.7.1、XZ 5.8.3 和 zlib-ng 2.3.3。FreeType 使用 FTL；本目录补充 dav1d 1.5.3、aom 3.14.1 的完整许可、aom 专利授权与作者列表。

发布方原始 SBOM 保存在 `../python/pillow-12.3.0/sboms/pillow-12.3.0.cdx.json`，其中同时描述可选能力。该 Windows wheel 的运行探测显示 RAQM/FriBiDi、libimagequant、XCB 不可用，不因 SBOM 提及就声称这些二进制已分发。Little CMS API 报告 2.19，而许可中构建依赖为 2.19.1。

首发本机产物还含 CPython 3.12.14、Tcl/Tk 8.6.12、OpenSSL 3.5.8、libffi ABI 8、Expat 2.8.3、libmpdec 2.5.1 及标准库压缩代码。完整 Python / Tk 声明见 `../python/`，Tcl 上游许可另存于本目录。libffi DLL 不公开发行版本，故记录 ABI 与哈希，保留上游 v3.4.4 MIT 文本；`_lzma` 同样不公开 XZ 版本，保留当前 0BSD 和历史公有领域声明而不杜撰版本。

上方完整英文保留 Independent JPEG Group、FreeType Project、加州大学伯克利分校的所需归属原文。这些归属及许可不由项目 MIT 条款替代。

Microsoft Visual C++ x64 运行库须单独安装。EXE 排除 `vcruntime140*.dll`、`api-ms-win-*.dll` 和 `ucrtbase.dll`，后两者由 Windows 10/11 提供。微软安装条款在来源索引中链接；这里不分发微软运行库 DLL 或复制其 EULA。需要时使用 [微软官方当前安装器](https://aka.ms/vc14/vc_redist.x64.exe)。

Windows CI 使用 CPython 3.12.10，并保留这份历史清单供追溯；发布具体 CI 产物前须另行核对其原生版本与哈希。这里的哈希没有被改写或冒充 CI 清单。依赖升级时重新收集许可，检查 wheel 声明、SBOM、运行特性、编解码器与 PyInstaller 依赖图。

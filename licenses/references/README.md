# 📚 Algorithm reference licenses / 算法参考许可

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

This directory preserves upstream license text and provenance for referenced ideas. It does not indicate that the referenced project's implementation or package is included as a runtime dependency. VRization's original implementation remains covered by the root [MIT license](../../LICENSE).

### One Euro Filter

The original host-side stabilization implementation acknowledges the One Euro Filter algorithm by **Géry Casiez, Nicolas Roussel and Daniel Vogel**, published at CHI 2012, DOI [10.1145/2207676.2208639](https://doi.org/10.1145/2207676.2208639). The [authors' official page](https://gery.casiez.net/1euro/) explains the speed-dependent cutoff and jitter / lag tradeoff.

The implementation reference is **OneEuroFilter Python 0.2.1**, commit `d78925584245597f2aa9c4c01a802eb0f0b77fb9`, credited to Nicolas Roussel / Géry Casiez, with source copyright 2019 Inria. Its [original BSD-3-Clause license](https://github.com/casiez/OneEuroFilter/blob/d78925584245597f2aa9c4c01a802eb0f0b77fb9/python/LICENSE) states copyright 2023 Inria. The unchanged text is saved as [OneEuroFilter-python-BSD-3-Clause.txt](OneEuroFilter-python-BSD-3-Clause.txt); [upstream-sources.json](upstream-sources.json) records the URL and SHA-256.

No upstream implementation source or OneEuroFilter package is bundled. VRization independently implements the speed-adaptive idea for angular input, bounded accumulated lag and explicit session / input resets. Its strength mapping and parameters are VRization choices, not claimed upstream defaults. See the [stabilization guide](https://github.com/LexZeon/VRization/blob/main/docs/STABILIZATION.md) and [third-party notices](../../THIRD_PARTY_NOTICES.md).

### Enhanced first-person projection

Angular-projection background was consulted in the [OpenCV 4.12.0 fisheye documentation](https://docs.opencv.org/4.12.0/db/d58/group__calib3d__fisheye.html), with the exact [4.12.0 source tag](https://github.com/opencv/opencv/tree/4.12.0). Credit: OpenCV contributors; the consulted [`fisheye.cpp` header](https://github.com/opencv/opencv/blob/4.12.0/modules/calib3d/src/fisheye.cpp) credits Intel Corporation (2000–2008), Willow Garage Inc. (2009–2011) and respective third-party copyright holders. The tagged [root LICENSE](https://github.com/opencv/opencv/blob/4.12.0/LICENSE) is Apache-2.0; that historical source file retains its own permissive BSD-style header, which must not be relabeled as Apache-only.

Consulted 2026-10-10. This is a mathematical reference only: no OpenCV code, samples, library or binaries are copied, modified, linked or bundled. VRization independently implements inverse equidistant sampling in Android GLES/iOS Metal and pure reference helpers, with its own square-fit, finite-input and black-border choices. It does not implement OpenCV calibration or its coefficient-fitting routines. Upstream controlling texts stay at the exact links above; the original VRization implementation remains MIT. See [projection behavior](https://github.com/LexZeon/VRization/blob/main/docs/ENHANCED_FIRST_PERSON.md).

### Separately obtained Android USB tools

The source index also pins Google's separately downloaded Windows Platform Tools 37.0.1 ZIP and its hash. It is not inside VRization release assets. The original offline importer preserves the complete package NOTICE and existing installations; users obtain it through Google's own download / terms flow. See [the official tool page](https://developer.android.com/tools/releases/platform-tools) and [the SDK terms](https://developer.android.com/studio/terms).

---

<!-- vrization:chinese -->
## 简体中文

本目录保存参考思路的上游许可原文与来源记录，不表示随运行软件引入了该项目实现或软件包。VRization 原创实现仍采用根目录的 [MIT 许可](../../LICENSE)。

### One Euro Filter

原创主机防抖实现鸣谢 **Géry Casiez、Nicolas Roussel 与 Daniel Vogel** 的 One Euro Filter 算法，发表于 CHI 2012，DOI [10.1145/2207676.2208639](https://doi.org/10.1145/2207676.2208639)。[作者官方网站](https://gery.casiez.net/1euro/) 说明随速度变化的截止频率，以及抖动与跟随迟滞的取舍。

实现参考为 **OneEuroFilter Python 0.2.1**，commit `d78925584245597f2aa9c4c01a802eb0f0b77fb9`，作者 Nicolas Roussel / Géry Casiez，源文件版权为 2019 Inria。[BSD-3-Clause 许可原文](https://github.com/casiez/OneEuroFilter/blob/d78925584245597f2aa9c4c01a802eb0f0b77fb9/python/LICENSE) 标注版权 2023 Inria。完整原文未改动地保存在 [OneEuroFilter-python-BSD-3-Clause.txt](OneEuroFilter-python-BSD-3-Clause.txt)，[upstream-sources.json](upstream-sources.json) 记录下载地址与 SHA-256。

没有引入上游实现源码或 OneEuroFilter 运行包。VRization 独立实现速度自适应思路，用于角度输入、限制累积迟滞并明确重置会话 / 输入状态。强度映射与参数是 VRization 的选择，不冒称上游默认。详见 [防抖教程](https://github.com/LexZeon/VRization/blob/main/docs/STABILIZATION.md) 与 [第三方声明](../../THIRD_PARTY_NOTICES.md)。

### 加强第一人称投影

角度投影数学背景参考 [OpenCV 4.12.0 鱼眼文档](https://docs.opencv.org/4.12.0/db/d58/group__calib3d__fisheye.html) 与准确 [4.12.0 源码标签](https://github.com/opencv/opencv/tree/4.12.0)。鸣谢 OpenCV 贡献者；所查阅的 [`fisheye.cpp` 文件头](https://github.com/opencv/opencv/blob/4.12.0/modules/calib3d/src/fisheye.cpp) 标注 Intel Corporation（2000–2008）、Willow Garage Inc.（2009–2011）及各第三方版权持有人。该标签的 [根 LICENSE](https://github.com/opencv/opencv/blob/4.12.0/LICENSE) 为 Apache-2.0，而这个历史源文件仍保留自身宽松 BSD 风格声明，不能一概重新标为仅 Apache。

查阅日期为 2026-10-10。只参考数学背景，没有复制、修改、链接或附带 OpenCV 源码、示例、库或二进制；VRization 在 Android GLES／iOS Metal 及纯数学参考辅助中独立实现逆等距采样，正方形适配、有限输入校验与黑边规则均为自己的选择，不实现 OpenCV 标定或系数拟合。上游控制文本保留在上述准确链接，VRization 原创实现仍采用 MIT，见 [投影行为](https://github.com/LexZeon/VRization/blob/main/docs/ENHANCED_FIRST_PERSON.md)。

### 另行获取的 Android USB 工具

来源索引同时固定记录 Google 另行下载的 Windows Platform Tools 37.0.1 ZIP 与哈希，不附带在 VRization 发布产物中。原创离线导入器保留完整安装包 NOTICE 和已有安装，由用户按 Google 下载 / 条款流程取得，见 [官方工具页](https://developer.android.com/tools/releases/platform-tools) 与 [SDK 条款](https://developer.android.com/studio/terms)。

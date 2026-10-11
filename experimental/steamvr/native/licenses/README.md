# Native provenance / 原生来源记录

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

Valve Corporation and OpenVR contributors provide the OpenVR SDK. This experiment pins **v2.15.6**, peeled commit **`0924064316de3effbcd1acf1e309182a2deb1c05`**. Its controlling license is **BSD-3-Clause**, preserved verbatim in [OpenVR-LICENSE.txt](OpenVR-LICENSE.txt). It permits commercial use subject to retaining notices and the other original terms. The SDK license does not grant a right to redistribute the separately installed SteamVR runtime or third-party headset drivers. No Valve endorsement is implied.

| Exact reused SDK file | SHA256 |
| --- | --- |
| `headers/openvr.h` | `1e6ed57199896cc1f7c5484e50fa18955e97be15be690beb28d998c877ead7fd` |
| `headers/openvr_driver.h` | `1036efe998d63e82d1d3db2b32a2f58df4a8eeaf5280f50aaf28220ff60a40ab` |
| `lib/win64/openvr_api.lib` | `a0bf57c5920f569e8d21ab3e5bc95bac4b73e2016217f8b5b93495a2a7197bbb` |
| `bin/win64/openvr_api.dll` | `bab8ac6ef64e68a9ca53315b0014d131088584b2efdfa6db511d67ec03cfcb4a` |
| `LICENSE` | `f56ff606104d4ef18e617921a75c73ad73b5a1a1d70c69590c29de16919e04ad` |

All five files are fetched unmodified from the [pinned Valve repository](https://github.com/ValveSoftware/openvr/tree/0924064316de3effbcd1acf1e309182a2deb1c05). Headers and import library are compile dependencies. `openvr_api.dll` and the complete license are bundled with native helpers. The build verifies each hash and the staged DLL/license before producing its report.

Architecture and interface references, at the same pinned commit:

- [Driver API documentation](https://github.com/ValveSoftware/openvr/blob/0924064316de3effbcd1acf1e309182a2deb1c05/docs/Driver_API_Documentation.md): provider lifecycle, properties, display component and pose publication.
- [Tutorial driver manifest](https://github.com/ValveSoftware/openvr/blob/0924064316de3effbcd1acf1e309182a2deb1c05/samples/drivers/drivers/tutorial/sample/driver.vrdrivermanifest): the empty `hmd_presence` list is a legal configuration. VRization references this configuration idea, without copying sample code, because USB VID.PID presence patterns cannot represent an authenticated USB/LAN phone session. Its existing pose-map discovery remains responsible for adding the phone HMD; no always-present wildcard is advertised. This removes the invalid serial-as-USB-pattern entry, not a proof of headless runtime acceptance.
- [Simple HMD sample](https://github.com/ValveSoftware/openvr/blob/0924064316de3effbcd1acf1e309182a2deb1c05/samples/drivers/drivers/simplehmd/src/hmd_device_driver.cpp): ABI/lifecycle and property ideas. VRization wrote its own bounded shared-memory input, late map discovery, invalid/stale handling, fixed 3DOF geometry and identity optics. Sample code is not copied into the implementation.
- [OpenVR API header](https://github.com/ValveSoftware/openvr/blob/0924064316de3effbcd1acf1e309182a2deb1c05/headers/openvr.h): `GetMirrorTextureD3D11` specifies undistorted per-eye textures and `ReleaseMirrorTextureD3D11` ownership. GPU packing, color conversion and small staging readback are original VRization code.
- [Hello World Overlay sample](https://github.com/ValveSoftware/openvr/blob/0924064316de3effbcd1acf1e309182a2deb1c05/samples/helloworldoverlay/openvroverlaycontroller.cpp): overlay creation/texture/lifecycle concepts. VRization implements its own shared BGRA input, selected-adapter D3D11 texture, unique owned overlay, head-relative placement and inactive/stale Stop clearing. Its Qt UI and source are not copied or bundled.
- [Historical virtual-display sample](https://github.com/ValveSoftware/virtual_display/tree/da13899ea6b4c0e4167ed97c77c6d433718489b1c05): architecture-only comparison, separately BSD-3-Clause under that repository's [own license](https://github.com/ValveSoftware/virtual_display/blob/da13899ea6b4c0e4167ed97c77c6d433718489b1c05/LICENSE). It is not a phone HMD driver. Its legacy transport/sample implementation is not copied, compiled or bundled; this experiment uses the official compositor mirror path instead.

The original native IPC, ctypes intrinsic bridge (`VRization-SteamVR-IPC.dll`), driver, D3D11 shaders/packing, overlay, tests and build scripts are written for VRization under the [project MIT license](https://github.com/LexZeon/VRization/blob/main/LICENSE), whose complete text is staged as `VRization-MIT.txt`. The intrinsic bridge has no OpenVR dependency. Contributions: VRization contributors designed session ownership, validated tracking, GPU resize/readback and reproducible fixture/build checks; Valve/OpenVR contributors supplied interfaces, SDK implementation and reference lifecycle concepts. Windows D3D11/DXGI/D3DCompiler and Microsoft's C++ runtime are system/toolchain dependencies under their own terms and are not copied into this native bundle. See [native operation and test scope](../README.md).

Additional Windows frame-pacing references, reviewed **2026-10-11 UTC** (research, not a validated performance result):

- Microsoft Learn, [CreateWaitableTimerExW](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createwaitabletimerexw), page updated 2022-06-16: owned timer handles and the high-resolution flag, available from Windows 10 version 1803.
- Microsoft Learn, [SetWaitableTimer](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-setwaitabletimer), updated 2024-11-18: negative relative due times in 100 ns units, period zero for single-shot waits and `fResume=FALSE` to avoid waking a sleeping system; precision still depends on hardware.
- Microsoft Learn, [WaitForMultipleObjects](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitformultipleobjects), updated 2024-08-22: waiting on the timer together with the already owned Stop event, ordering signaled handles and retaining handles throughout a pending wait.
- Microsoft Learn, [CancelWaitableTimer](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-cancelwaitabletimer), updated 2024-02-22: cancellation makes the timer inactive but does not itself wake a blocked wait, so an independently signaled Stop event is required.

These are **API-contract references only**. No Microsoft example code/document text is copied and no timer library, system DLL or global timer-resolution change is bundled. The implemented scheduler is original VRization work under MIT using installed Windows APIs under their own terms: owned local timer, QPC deadlines and Stop-cancellable waits, with no global timer-resolution change. Implementation is original and complete. The prior `fc607e6` candidate passed MSVC/CTest, including 48 timer cadence checks alongside 365 native fixtures. The newer `ad092b0` Windows CI also passed those 413 fixtures and its extracted ZIP diagnostic gate. Fresh physical performance/lifecycle and final release packaging remain pending; these compiled fixtures do not establish hardware improvement.

---

<!-- vrization:chinese -->
## 简体中文

OpenVR SDK 由 Valve Corporation 和 OpenVR 贡献者提供。本实验版锁定 **v2.15.6**、解析后的 commit **`0924064316de3effbcd1acf1e309182a2deb1c05`**；控制许可证是 **BSD-3-Clause**，原文完整保存在 [OpenVR-LICENSE.txt](OpenVR-LICENSE.txt)。遵守保留声明等原有条件时允许商用。SDK 许可不授予另外安装的 SteamVR 运行环境或第三方头显驱动的再分发权，也不表示 Valve 为本项目背书。

| 原样采用的 SDK 文件 | SHA256 |
| --- | --- |
| `headers/openvr.h` | `1e6ed57199896cc1f7c5484e50fa18955e97be15be690beb28d998c877ead7fd` |
| `headers/openvr_driver.h` | `1036efe998d63e82d1d3db2b32a2f58df4a8eeaf5280f50aaf28220ff60a40ab` |
| `lib/win64/openvr_api.lib` | `a0bf57c5920f569e8d21ab3e5bc95bac4b73e2016217f8b5b93495a2a7197bbb` |
| `bin/win64/openvr_api.dll` | `bab8ac6ef64e68a9ca53315b0014d131088584b2efdfa6db511d67ec03cfcb4a` |
| `LICENSE` | `f56ff606104d4ef18e617921a75c73ad73b5a1a1d70c69590c29de16919e04ad` |

五个文件均从 [Valve 锁定仓库](https://github.com/ValveSoftware/openvr/tree/0924064316de3effbcd1acf1e309182a2deb1c05) 原样下载。头文件和导入库用于编译，`openvr_api.dll` 和完整许可证随原生工具打包；生成报告前，构建检查每个哈希及暂存 DLL／许可证。

同一锁定 commit 的架构与接口参考：

- [驱动 API 文档](https://github.com/ValveSoftware/openvr/blob/0924064316de3effbcd1acf1e309182a2deb1c05/docs/Driver_API_Documentation.md)：提供器生命周期、属性、显示组件及姿态发布。
- [教程驱动 manifest](https://github.com/ValveSoftware/openvr/blob/0924064316de3effbcd1acf1e309182a2deb1c05/samples/drivers/drivers/tutorial/sample/driver.vrdrivermanifest)：空 `hmd_presence` 列表是合法配置。VRization 仅参考该配置思路，没有复制示例代码；USB VID.PID 存在匹配无法代表已认证的 USB／局域网手机会话。仍由原有姿态映射发现机制添加手机头显，不声明永久存在的通配头显。本改动移除把序列号误当 USB 匹配的条目，不代表已证明无实体显示器时运行环境能启动。
- [Simple HMD 示例](https://github.com/ValveSoftware/openvr/blob/0924064316de3effbcd1acf1e309182a2deb1c05/samples/drivers/drivers/simplehmd/src/hmd_device_driver.cpp)：ABI／生命周期与属性思路。VRization 自行实现有边界的共享内存、延迟发现映射、无效／过期处理、固定 3DOF 几何与恒等光学；没有复制示例源码到实现。
- [OpenVR API 头文件](https://github.com/ValveSoftware/openvr/blob/0924064316de3effbcd1acf1e309182a2deb1c05/headers/openvr.h)：`GetMirrorTextureD3D11` 规定分眼未畸变纹理，`ReleaseMirrorTextureD3D11` 规定所有权。GPU 拼接、颜色转换和小分辨率读回是 VRization 原创代码。
- [Hello World Overlay 示例](https://github.com/ValveSoftware/openvr/blob/0924064316de3effbcd1acf1e309182a2deb1c05/samples/helloworldoverlay/openvroverlaycontroller.cpp)：覆盖层创建、纹理与生命周期概念。VRization 自行实现共享 BGRA 输入、指定显卡 D3D11 纹理、独立覆盖层、头部相对定位及停用／过期清空；未复制或打包它的 Qt 界面与源码。
- [历史 virtual-display 示例](https://github.com/ValveSoftware/virtual_display/tree/da13899ea6b4c0e4167ed97c77c6d433718489b1c05)：仅作架构比较，按该仓库[自身许可证](https://github.com/ValveSoftware/virtual_display/blob/da13899ea6b4c0e4167ed97c77c6d433718489b1c05/LICENSE) 为独立 BSD-3-Clause 项目。它不是手机头显驱动；旧传输／示例实现未复制、编译或打包，本实验改用官方合成器镜像通路。

原创原生 IPC、ctypes intrinsic 桥接（`VRization-SteamVR-IPC.dll`）、驱动、D3D11 shader／拼接、覆盖层、测试和构建脚本遵守[项目 MIT 许可证](https://github.com/LexZeon/VRization/blob/main/LICENSE)，完整文本暂存为 `VRization-MIT.txt`；intrinsic 桥接没有 OpenVR 依赖。贡献记录：VRization 贡献者设计会话所有权、追踪校验、GPU 缩小／读回及可复现测试／构建；Valve／OpenVR 贡献者提供接口、SDK 实现与参考生命周期概念。Windows D3D11／DXGI／D3DCompiler 和 Microsoft C++ 运行库属于各自条款下的系统／工具链依赖，不复制进原生包。参见[原生运行与测试范围](../README.md)。

补充 Windows 帧节奏来源，核对时间为 **2026-10-11 UTC**（研究阶段，不是已验证性能结果）：

- Microsoft Learn，[CreateWaitableTimerExW](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createwaitabletimerexw)，页面更新 2022-06-16：自有定时器句柄、高分辨率标志；后者从 Windows 10 1803 起可用。
- Microsoft Learn，[SetWaitableTimer](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-setwaitabletimer)，更新 2024-11-18：以 100 纳秒为单位的负相对到期时间、周期为零的单次等待，以及避免唤醒休眠系统的 `fResume=FALSE`；精度仍依赖硬件。
- Microsoft Learn，[WaitForMultipleObjects](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitformultipleobjects)，更新 2024-08-22：将定时器与已经拥有的 Stop 事件一起等待、多个已触发句柄的优先顺序，以及等待期间保持句柄存活。
- Microsoft Learn，[CancelWaitableTimer](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-cancelwaitabletimer)，更新 2024-02-22：取消只令定时器停用，并不唤醒已阻塞的等待，因此需独立触发 Stop 事件。

这些仅是 **API 契约参考**，不复制 Microsoft 示例源码／文档原文，不打包定时器库、系统 DLL，也不附带全局定时器分辨率变更。已经实现的调度器是 MIT 下的 VRization 原创工作，通过各自条款下的已安装 Windows API 运行：自有本地定时器、QPC 截止时间及可被 Stop 取消的等待，不更改全局定时器分辨率。原创实现已完成；先前 `fc607e6` 候选版已通过 MSVC／CTest，其中有 48 个定时器节奏及 365 个原生夹具检查。更新 `ad092b0` Windows CI 同样通过这 413 个夹具检查及解压 ZIP 诊断门控；新真机性能／生命周期和最终发布打包仍待验收，已编译测试不代表硬件提升通过。

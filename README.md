<div align="center">

# 🥽 VRization

**把电脑画面装进手机 VR 盒子。**

Windows 桌面串流 · Android / 兼容 Android 的系统 · 可复用的核心模块

![Alpha](https://img.shields.io/badge/version-0.1.0--alpha-orange)
![License](https://img.shields.io/badge/license-MIT-green)
![Desktop](https://img.shields.io/badge/desktop-Windows%2010%2F11-blue)
![Android](https://img.shields.io/badge/Android-6.0%2B-3DDC84)
[![Build](https://github.com/LexZeon/VRization/actions/workflows/build.yml/badge.svg)](https://github.com/LexZeon/VRization/actions/workflows/build.yml)

[🚀 上手教程](docs/QUICKSTART.zh-CN.md) · [🛠️ 开发与构建](docs/BUILD.md) · [🧩 集成指南](docs/ARCHITECTURE.md) · [English](README.en.md)

</div>

VRization 是一个开源的电脑 → 手机串流实验项目。电脑端采集显示器或指定矩形区域，手机端将画面显示在 VR 盒子的左右眼区域。你可以让画面固定在眼前，也可以把它当成一个随头部转动观看的虚拟大屏幕，或者用手机的姿态控制电脑游戏视角。

> **当前版本：可运行的 Alpha 基础版。** 使用 CPU 编码 JPEG + WebSocket，优先打通安装、串流、调节与模块复用；尚未达到专用 VR 串流产品的画质、延迟和稳定性。左右眼接收同一张二维桌面图像，**不会把普通游戏自动变成立体 3D**。

## 🎮 三种观看方式

| 模式 | 画面表现 | 手机姿态 | 适合做什么 |
| --- | --- | --- | --- |
| 🖥️ 全屏模式 | 同一画面分别填入左右眼区域 | 不参与画面或鼠标控制 | 稳定观看桌面、视频和普通游戏 |
| 🎬 大屏幕模式 | 电脑或选区画面放在虚拟平面上 | 转头改变观看方向 | 像在眼前放了一块大屏幕 |
| 🎯 FPS 游戏模式 | 左右眼显示游戏画面 | 转头映射成电脑鼠标移动 | 在支持普通鼠标输入的游戏里试验头部瞄准 |

FPS 控制需要在**电脑端主动授权**。手机连接或切换模式不会自动接管鼠标；按电脑键盘 **F8** 可以立即停止控制。不同游戏、独占全屏、原始输入和反作弊机制可能不接受这种输入，建议先用桌面或离线游戏验证。

## ✨ 为不同手机与盒子留出调节空间

- **画面缩放与水平 / 垂直偏移**：大手机也能把有效画面收进镜片可见区域。
- **左右眼间距、视场角、虚拟屏幕距离、畸变调节**：根据盒子镜片与佩戴方式微调。
- **重新居中**：把当前头部方向设为正前方。
- **鼠标灵敏度与 Y 轴反转**：调整 FPS 头部控制手感。
- **显示器 / 矩形选区、输出最长边、帧率和 JPEG 质量**：保持画面比例，同时限制横屏与竖屏的解码负担。
- **纯局域网、无需 Google 服务**：Android 6.0+，可在提供 Android APK 兼容层的系统上尝试安装。兼容性仍取决于设备的图形、网络与传感器实现；全屏模式不要求陀螺仪。

## 📸 看看界面

电脑端负责选画面、开串流和授权 FPS；手机端负责连接、观看和调整镜片中的布局。

| 电脑控制台 | 手机客户端 |
| --- | --- |
| ![VRization 电脑端实际界面](docs/images/desktop.png) | ![VRization Android 客户端实际界面](docs/images/android.png) |

图示来自项目运行界面。手机图来自不含 Google 服务的 Android 6.0 / API 23 模拟器，画面为本项目的 [动态校准卡示例](examples/embedded_host.py)。截图展示连接与显示流程，不代表手机盒子实机测试结果；界面上的接收帧率不是延迟或性能基准。

<details>
<summary>🥽 展开：双眼观看与盒子适配设置</summary>

![隐藏设置后的双眼画面，接收同一张二维校准卡](docs/images/android-vr.png)

隐藏操作区后，将同一张二维画面显示在左右眼区域。长按画面或按返回键可恢复设置。

![手机端画面缩放、位置、双眼间距与镜片畸变调节](docs/images/android-settings.png)

用缩放与偏移让大手机的有效画面收进盒子镜片范围。不同手机与镜片需要分别调整。

</details>

## 🚀 五步把电脑放进盒子

1. 在 [Releases](https://github.com/LexZeon/VRization/releases) 下载 Windows 电脑端压缩包与 Android APK；首次体验建议使用同一个版本。
2. 让电脑与手机连接同一可信局域网。电脑尽量接网线，手机靠近 5 GHz / 6 GHz 路由器。
3. 打开电脑端，选显示器或矩形区域，再开始串流。如果 Windows 弹出防火墙提示，只允许可信的**专用网络**。
4. 在手机端填写电脑端显示的 IP 地址、端口与配对码，连接后先试全屏模式。
5. 调整缩放、偏移和眼间距，确认两眼舒适对齐，再放入 VR 盒子。大屏幕模式先重新居中；FPS 模式还需在电脑端授权鼠标控制。

Windows 端需要 Microsoft Visual C++ v14 x64 运行库。多数电脑已经安装；如果启动提示缺少 `VCRUNTIME140*.dll`、加载 Python DLL 失败或错误 126，再按 [微软官方说明](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist/) 安装 [当前受支持的 x64 运行库](https://aka.ms/vc14/vc_redist.x64.exe)。

详细步骤、截图说明和常见问题见 [上手教程](docs/QUICKSTART.zh-CN.md)。还没有下载产物时，可以按 [构建指南](docs/BUILD.md) 从源码启动。

## 🧩 为移植而拆开的结构

```text
Windows 桌面端                         Android 手机端
采集 → JPEG 编码 → WebSocket ───────→ 解码 → 双眼显示
鼠标输入 ← 姿态增量与本机授权 ←─────── 旋转传感器
                 ↑                      ↑
          Python 主机模块          Android vr-core library
```

`vr-core` 是 Java 编写的 Android library，提供姿态与双眼渲染接口；桌面端把采集、网络和输入分开。集成到其他 Android 软件 / 游戏时，可以复用核心库；跨平台客户端可以按协议替换画面来源、传输或输入适配器。当前提供源码级模块和协议说明，尚无 Unity / Unreal 插件、OpenXR 驱动或公开稳定 SDK。

参见 [架构与移植](docs/ARCHITECTURE.md)、[协议 v1](docs/PROTOCOL.md) 和 [后续路线](docs/ROADMAP.md)。

## 🧪 当前边界

Alpha 版尚未提供音频、硬件视频编码、WebRTC、USB 专用通道、原生立体渲染或 6DoF 位置追踪。没有承诺帧率或端到端延迟数字；实际体验取决于电脑、手机和网络。传感器不足的设备可以使用全屏模式，大屏幕 / FPS 需要兼容的旋转传感器。已完成的检查与尚需实测的项目见 [验证记录](docs/VALIDATION.md)。

串流使用明文 `ws://`，配对码只是基础访问门槛，**不是加密**。只在可信局域网使用，不要把服务端口映射到公网。详见 [安全说明](SECURITY.md)。

## 🤝 开源与致谢

原创代码以 [MIT](LICENSE) 授权，允许商业使用并要求保留相关许可与版权声明。依赖保留各自许可证；来源、用途、作者与分发注意事项记录在 [第三方声明](THIRD_PARTY_NOTICES.md) 和 [NOTICE](NOTICE)。本项目没有复制其他 VR 应用的实现源码。

感谢 aiohttp、MSS、Pillow、OkHttp、Okio、Kotlin 及相关工具的维护者。欢迎提交兼容性记录、问题、翻译与 PR，开始前可看 [贡献指南](CONTRIBUTING.md)。

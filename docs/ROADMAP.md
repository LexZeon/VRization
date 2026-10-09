# 🛤️ Roadmap and scope / 路线与范围

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

This separates existing baseline capabilities from possible future work. Dates are not promised.

### v0.1.0-alpha baseline

- Windows display / rectangular capture and JPEG WebSocket streaming.
- Android APK and reusable Android `vr-core` library.
- Fixed full screen, rotation-tracked cinema and pose-to-mouse FPS modes.
- Phone layout and viewing controls.
- PC input arming, F8 stop, disconnect and mode-change boundaries.
- Tutorials, actual UI screenshots, dependency attribution and automated builds.

### v0.1.1-alpha maintenance

Selectable English / Simplified Chinese, bilingual public pages, regression checks for settings / reconnect behavior, complete offline documentation packaging and the core AAR's original MIT notice.

### Next candidates

1. Physical tests on Android derivatives and phone viewers; improved sensor mapping.
2. Hardware codecs, timestamps and reproducible end-to-end latency measurements.
3. Encryption / stronger authentication, reconnect behavior and clearer discovery.
4. Audio sync, lens presets and configuration import / export.
5. USB / WebRTC transport adapters.
6. Independent math core, Unity / Unreal samples and in-game camera interfaces.
7. Independent per-eye rendering where the engine supports it, rather than presenting 2D duplication as native stereo.

### Outside current scope

This is not an OpenXR runtime or SteamVR driver. It does not provide 6DoF tracking, universal game injection, anti-cheat bypass, or automatic conversion of ordinary games into native VR.

---

<!-- vrization:chinese -->
## 简体中文

此文件区分已经提供的基础功能与后续方向，不承诺日期。

### v0.1.0-alpha 基础

- Windows 桌面 / 矩形选区采集与 JPEG WebSocket 串流。
- Android APK 与可复用 Android `vr-core` library。
- 固定全屏、旋转追踪虚拟大屏幕、姿态到鼠标三种模式。
- 手机端画面布局与观看参数调节。
- 电脑授权鼠标控制、F8 停止、断线和模式切换的输入边界。
- 中文教程、界面截图、依赖来源与许可记录、自动构建配置。

### v0.1.1-alpha 维护改进

可选英文 / 简体中文界面、双语公共页面、设置 / 重连回归检查、完整离线文档打包和核心 AAR 原创 MIT 声明。

### 下一阶段候选

1. 收集 Android 衍生系统与手机盒子的实机兼容性数据，改进传感器坐标映射。
2. 硬件视频编码与解码，时间戳和可复现的端到端延迟测量。
3. 加密 / 更强身份认证、重连策略与更直观的设备发现。
4. 音频同步、镜片参数预设与配置导入导出。
5. USB / WebRTC 等替代传输适配器。
6. 独立数学核心、Unity / Unreal 示例及游戏内部相机输入接口。
7. 在引擎明确支持的场景加入左右眼独立渲染；不会把二维桌面伪装成原生立体画面。

### 暂无的能力

当前不是 OpenXR 运行时或 SteamVR 驱动，没有 6DoF 位置追踪、通用游戏注入、反作弊绕过或一键将普通游戏转换成原生 VR 的功能。

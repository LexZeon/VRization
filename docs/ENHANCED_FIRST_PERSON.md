# 🌀 Enhanced first person / 加强第一人称

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

**Enhanced first person** is the fourth viewing mode, alongside Full screen, Cinema and First person. Each eye uses a fixed **1:1 physical square**, with a curved wide-angle remapping of the same streamed 2D desktop image. Source and GPU-rendering checks for v0.4.0 are recorded in [Validation](VALIDATION.md); earlier releases do not include this mode.

### Choose, fit and save

1. Update both the Windows host and phone to a version supporting the new mode, then select **Enhanced first person** on either endpoint.
2. Open the first settings action, the [visual headset editor](EDITING.md). Corner dragging scales both squares without changing their 1:1 ratio. Horizontal dragging keeps the linked mirror behavior: left-eye left / right-eye right increases spacing; the opposite directions bring the squares together. Vertical dragging moves both normally. The shared offsets and seam limits still apply.
3. **Save** commits the fit and synchronizes with the connected endpoint. **Discard** restores the entry draft. Only committed settings persist locally; editing pauses phone poses and latches PC input paused.
4. Change **Field of view**, 50–110° (default 80°), to change the wide-angle warp. Scale, offsets and eye separation still fit the result to the viewer. The existing lens-distortion control remains an additional optical adjustment; it does not unlock the square ratio.
5. Use the same gyro sensitivity, stabilization and invert-Y controls as First person. Windows defaults gyro mouse control on; **F8** pauses it, and **Resume gyro control** on the PC resumes. Save, mode changes and reconnecting cannot clear an existing pause latch.

The enhanced-mode editor keeps the square and wide-angle warp visible. Android/iOS use their GPU renderer; Windows approximates the mapping with a mesh using the existing latest frame, at up to ten preview updates per second, without a second capture. Corner handles describe the physical square even when image corners are black. The older Cinema editor retains its flat-preview behavior. Rendering can still show the enhanced image without a rotation sensor, but gyro mouse control is unavailable on that device.

### What the projection does

The original Android GLES and iOS Metal fragment shaders map an output square back into the streamed texture. They run on the phone GPU; the host continues sending ordinary JPEG frames. The square resamples a rectangular desktop source to the requested 1:1 presentation, so content proportions change deliberately in this mode. It cannot recover content outside the captured desktop or create separate stereo viewpoints, scene depth or a native VR180 video.

For a centered output point `q = (x,y)` after fit/lens adjustments:

```text
outside the output square (|x| > 1 or |y| > 1) → black
r = length(q)
a = radians(fov) / 2
if r < 0.000001: source = (0, 0)
otherwise: source = q × tan(r × a) / (r × tan(a))
outside the source square → black
```

The accepted FOV range keeps the corner angle below π/2. The center is stable, axial edges sample source edges, and nonaxial edges can become black. These are presentation choices, not a camera calibration or a measured lens profile. Android `EnhancedProjection` and Swift `EnhancedProjection` expose the pure mapping for other projects; match its units and black-border behavior when replacing a renderer. See [Module catalogue](MODULES.md).

### Version negotiation and limits

The wire value is `fps_enhanced`. Protocol stays v1 and settings schema stays 2: no new settings fields are added. Clients opt in with URL `enhancedFirstPerson=1` or hello `capabilities:["enhanced-first-person"]`; host messages confirm the negotiated boolean `enhancedFirstPerson`. A new host gives an older client ordinary `fps` snapshots instead of an unknown mode. A new phone connected to an older host sends ordinary `fps` while retaining its local enhanced rendering/profile. Do not infer support from schema 2 or a capability advertisement alone. See [the exact handshake](PROTOCOL.md).

The user's reference picture informed the requested curved, square, side-by-side style only. It is not copied, redistributed or included as a test asset. Mathematical background is acknowledged in the [OpenCV reference credit](../THIRD_PARTY_NOTICES.md#enhanced-first-person-projection-reference); no OpenCV implementation or runtime dependency is bundled. All diagrams/test cards in this project remain original assets. GPU use does not by itself establish an achieved frame rate, end-to-end latency or physical headset comfort.

A separate **SteamVR experimental version is planned** after preserving existing files. It is not this viewing mode, an implemented SteamVR driver or a current download. Track that work separately in [Roadmap](ROADMAP.md).

---

<!-- vrization:chinese -->
## 简体中文

**加强第一人称**是新增的第四种观看模式，与全屏、大屏幕和第一人称并列。每只眼固定为 **1:1 物理正方形**，把同一张二维桌面串流变形成弯曲广角画面。v0.4.0 源码与 GPU 渲染检查记录在 [验证](VALIDATION.md)；此前发布不包含此模式。

### 选择、适配与保存

1. 将 Windows 和手机都更新至支持新模式的版本，再在任一端选择“**加强第一人称**”。
2. 打开设置第一项的 [可视化盒子编辑器](EDITING.md)。拖角点同时缩放两眼，保持 1:1；水平拖动仍镜像联动：左眼向左／右眼向右增大间距，反向让正方形靠近；竖向正常同时移动，共用偏移与中缝限位仍生效。
3. “**保存**”提交适配，连接时同步至另一端；“**放弃**”恢复进入时的草稿。只有已提交配置保存到本地；编辑期间手机暂停姿态，电脑锁定输入暂停。
4. 用“**视场角**”50–110°（默认 80°）改变广角变形范围；缩放、偏移与眼间距仍用于适配盒子。已有镜片畸变是额外光学调节，不解除正方形比例。
5. 使用与第一人称相同的鼠标灵敏度、防抖及 Y 轴反转；Windows 默认开启陀螺仪鼠标，**F8** 暂停，电脑“**恢复陀螺仪控制**”恢复。保存、切换模式或重连不能解除已有暂停锁。

加强模式编辑器保留正方形及广角变形预览；Android／iOS 用 GPU 渲染器，Windows 以网格近似已有最新帧的映射，预览最高每秒十次，不额外采集。即使内容角点变黑，角点把手仍表示物理正方形范围；旧大屏幕编辑器仍采用平面预览。没有旋转传感器的设备仍可观看加强图像，但无法进行陀螺仪鼠标控制。

### 投影的作用

原创 Android GLES 与 iOS Metal 片元着色器把输出正方形反向映射到串流纹理，由手机 GPU 执行；电脑仍发送普通 JPEG。矩形桌面源按要求重采样至 1:1，因此此模式有意改变内容比例；不能补回采集范围之外的信息，也不能产生独立立体视点、场景深度或原生 VR180 视频。

适配／镜片调节后的输出中心坐标 `q = (x,y)`：

```text
超出输出正方形（|x| > 1 或 |y| > 1）→ 黑色
r = length(q)
a = radians(fov) / 2
若 r < 0.000001：source = (0, 0)
否则：source = q × tan(r × a) / (r × tan(a))
超出源正方形 → 黑色
```

允许的视场角范围让角点角度保持小于 π/2；中心稳定，坐标轴方向边缘采样源边缘，其他边缘可能变黑。这是显示设计，不是相机标定或实测镜片参数。Android 与 Swift 的 `EnhancedProjection` 提供纯数学映射，移植渲染器时保持单位与黑边行为一致，见 [模块目录](MODULES.md)。

### 版本协商与限制

线上值为 `fps_enhanced`，协议仍 v1、配置 schema 仍 2，不增加设置字段。客户端用地址 `enhancedFirstPerson=1` 或 hello `capabilities:["enhanced-first-person"]` 主动启用，电脑消息以 `enhancedFirstPerson` 布尔值确认协商；新版电脑向旧客户端发普通 `fps` 快照，避免陌生模式；新版手机连接旧电脑时发送普通 `fps`，保留本地加强渲染／保存配置，不能只凭 schema 2 或能力声明判断协商完成。准确握手见 [协议](PROTOCOL.md)。

用户参考图只用于理解弯曲、正方形、左右眼并排的显示风格，没有复制、再发布或作为测试素材。数学背景鸣谢 [OpenCV 参考记录](../THIRD_PARTY_NOTICES.md#enhanced-first-person-projection-reference)，不附带 OpenCV 实现或运行依赖；项目图示／测试卡仍为原创。使用 GPU 本身不证明达到的帧率、端到端延迟或真实盒子舒适度。

在保留已有文件之后，计划另做 **SteamVR 实验版本**；它不是此观看模式、已实现的 SteamVR 驱动或当前下载，单独记在 [路线](ROADMAP.md)。

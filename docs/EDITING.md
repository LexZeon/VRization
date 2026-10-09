# 🥽 Headset-fit editor and saved profiles / 盒子适配编辑器与保存配置

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

v0.3.0-alpha places visual headset fitting first in the settings on Windows, Android and iOS. It adjusts the image inside the two eye areas without adding a fourth viewing mode. The editor uses a flat, undistorted preview; your actual full-screen / cinema / FPS mode and other optical settings remain in the draft unchanged.

| Application | Entry and actions |
| --- | --- |
| Windows | First tab **Headset editor**, then **Open visual headset editor**; Save / Discard. |
| Android | **Fit headset visually**; Save / Discard. |
| iOS | **Visual headset fit editor**; Save / Discard. |

### Drag, preview, then choose

1. Open the editor using the entry above. The entry settings are captured as a snapshot. Windows shows an approximate phone-shaped preview with whole-phone aspect choices 20:9 (default), 16:9 and 19.5:9; a phone uses its own screen. The PC reuses the existing latest JPEG at up to 10 preview updates per second; it starts no additional capture and does not change the display / rectangle.
2. Drag inside either image to move both eyes together. **Interior horizontal dragging is reversed on all three applications:** finger / mouse left moves the picture right, and right moves it left. Vertical dragging follows the pointer normally. Drag any corner to resize while keeping the image center fixed; corner motion is direct on all platforms, and the image aspect ratio stays unchanged. Scale is limited to 50–100%, and offsets to −0.3…+0.3.
3. **Save** on a phone commits the complete draft through normal settings synchronization when connected. On Windows it updates only scale / offsetX / offsetY once against the current host snapshot, preserving other settings changed during editing, then saves that complete committed state. **Discard** restores the local entry preview and sends no update. Dragging the preview never writes host settings or saved preferences.

The preview temporarily suppresses motion-driven viewing and outgoing phone poses. A connected phone stops new poses and drops application-pending pose work (already submitted transport bytes cannot be recalled) and sends one normal hello with `editing: true` on entry; the current host disarms input immediately on receipt. Desktop entry also disarms it. Video, ping and normal exit recentering may continue; no draft settings or preferences are written. Older hosts still stop on the pose timeout. Saving or leaving the editor never grants new authorization. Use the normal PC authorization flow again before FPS control.

Phone backgrounding, disconnecting or changing language discards an open draft; iOS also cancels it when the viewport changes during rotation. Saved values remain separate from a temporary drag. The editor is a visual fit aid, not a measurement of physical lens alignment, interpupillary distance or headset comfort. A valid offset / eye separation can place an image partly outside an eye viewport; the viewport clips it.

### Local phone profile and reconnecting

Both phones keep the complete **committed VR settings** locally, including mode, scale, offsets, eye separation, field of view, distance, distortion, sensitivity and invert Y. Changes made offline are retained; drafts are not. A restart restores the saved profile before connecting. An accepted complete settings snapshot from normal connected synchronization updates the committed profile.

After a valid host `hello`, a phone with a saved profile sends that complete profile once as a normal v1 `settings` update with a new `clientSeq`. This is an intentional user preference: it takes precedence over the host's initial settings for that connection. It does not skip session validation or input authorization. A phone without a saved profile starts from the validated host snapshot. Later PC changes and acknowledgments use the existing revision / sequence rules. See [protocol v1](PROTOCOL.md).

When connected, Save from either side propagates through normal validated settings, acknowledgments and broadcasts, and both sides retain the accepted committed state. Offline Save can only change that application's local preferences. **If both sides changed offline, the saved phone profile wins on the next validated connection**; Save again from the PC afterward to apply its chosen fit to both sides. This version does not compare unsynchronized clocks or merge conflicting complete offline profiles.

Pairing codes and Apple pairing records are never part of the saved view profile. USB remains the default, with LAN explicitly selectable. Saving a profile does not connect automatically or start streaming.

### Reset all settings

Reset is explicit and separate from Discard. It removes a pending edit and returns product preferences to their defaults:

| Preference | Default |
| --- | --- |
| Mode / scale / offsets | Full screen / 0.85 / 0, 0 |
| Eye separation / field of view / distance | 0.03 / 80° / 3 |
| Distortion / sensitivity / invert Y | 0 / 1000 / false |
| Language / preferred connection | English / USB |
| Windows capture preset | Low latency: long edge 640, target 60 FPS, JPEG Q45 |
| Phone LAN fields | Empty address, port 8765, empty pairing field |

The PC **preserves the explicitly selected capture display / rectangle and configured ADB executable path**. These identify the intended output and installed tools; resetting viewing preferences must not switch to another screen or remove the user's development environment. USB device choice returns to automatic selection. Reset does not uninstall drivers / SDKs, change platform authorization, start streaming or arm mouse input.

Phone reset clears local view and connection preferences, selects English / USB and ends the current connection; it does not silently reconnect. Any settings update on an already connected host uses the normal validated protocol. A saved reset profile can be restored on the next explicitly established session.

### Reusable geometry contract

The original Python helper is `desktop/src/vrization_host/view_edit.py`; Android `HeadsetGeometry` / `HeadsetEdit` and Swift `HeadsetFit` use the same math in their cores. Swift additionally exposes `PhonePreferencesStore` and `LocalProfileSync` for committed preferences and restoration. No platform UI, networking or storage is required for the geometry itself.

Each eye has normalized coordinates **[−1, 1], y upward**. For image aspect `a` and eye viewport aspect `e`:

```text
fit = (min(1, a/e), min(1, e/a))
center = (offsetX ± eyeSeparation, offsetY)
half-size = fit × scale
pan = clamp(start.offset + total pointer delta, −0.3, +0.3)
resize scale = clamp(start.scale +
    dot((dx × cornerX, dy × cornerY), fit) / dot(fit, fit), 0.5, 1)
```

Use `−` for the left eye and `+` for the right. Corner signs are −1 / +1 for left / right and bottom / top. Pointer deltas are measured from the **gesture-start snapshot**, never accumulated from each event. Screen y increases downward, so convert it with the opposite sign. A corner resize keeps both offsets unchanged. The two eyes share the resulting scale and offsets.

The pure geometry takes logical image-movement deltas. All three UI adapters negate x **only for interior pan** (`dx = −2 × pointerDeltaX / eyeWidth`); y remains `−2 × pointerDeltaY / height`. All corner resizes use direct x (`+2 × pointerDeltaX / eyeWidth`). This editor direction does not change the FPS gyro / mouse mapping, add an invert-X protocol field or reverse corner resizing.

Python exposes `fit_size`, `eye_bounds` (left, bottom, right, top; eye 0 left / 1 right), `dragged` (`pan` / `resize`) and an optional `EditTransaction` with local preview / commit / discard. Callers own rendering, persistence and broadcasts. Automated geometry checks do not establish real headset optics or completed UI / device acceptance; consult [validation](VALIDATION.md).

---

<!-- vrization:chinese -->
## 简体中文

v0.3.0-alpha 将可视盒子适配放在 Windows、Android 与 iOS 设置首位，在两眼区域内直接调整画面，不增加第四种观看模式。编辑器采用平面、无畸变预览；实际全屏 / 大屏幕 / FPS 模式与其他光学设置原样保留在草稿中。

| 应用 | 入口与操作 |
| --- | --- |
| Windows | 第一个标签页**画面编辑**，再点**打开可视画面编辑器**；保存 / 弃用。 |
| Android | **可视化适配 VR 盒子**；保存 / 放弃。 |
| iOS | **可视化盒子画面编辑器**；保存 / 放弃。 |

### 拖动、预览，再决定

1. 按上表打开编辑器，进入时的完整设置会保存为快照。Windows 提供近似手机形状的预览，可选整部手机宽高比 20:9（默认）、16:9 和 19.5:9；手机使用自身屏幕。电脑最多每秒 10 次复用现有最新 JPEG，不新增采集、不改变显示器或选区。
2. 拖画面内部来同步移动两眼。**三端内部横向拖动都反向**：手指 / 鼠标向左，画面向右；向右，画面向左。竖向仍正常跟随；拖任意角点来缩放，三端角点均正常跟随、中心固定、比例保持。缩放范围为 50–100%，偏移限制为 −0.3…+0.3。
3. 手机**保存**提交完整草稿，已连接时通过正常设置同步发送；Windows 保存时只向当前主机快照一次更新 scale / offsetX / offsetY，保留编辑期间其他设置改动，再保存完整已提交状态。**放弃**恢复本地进入预览，不发送更新。预览拖动不会写主机设置或保存偏好。

预览暂时停用姿态控制画面，并暂停手机发送姿态。已连接手机停止新姿态、丢弃应用层待发姿态（已提交传输层字节无法撤回），进入时用普通 hello 一次发送 `editing: true`，当前主机收到后立即解除输入授权；电脑进入也解除授权。视频、ping 和正常退出回正可以继续，但不写草稿设置或偏好。旧主机仍由姿态超时停止输入。保存或退出不会重新授予权限；继续 FPS 控制前，重新走电脑正常授权流程。

手机进入后台、断线或切语言会放弃尚未保存的草稿；iOS 在旋转导致显示区域改变时也取消编辑。已保存值与临时拖动分开。编辑器帮助肉眼适配，不测量实际镜片对齐、瞳距或舒适度。合法偏移 / 眼间距也可能使部分画面越出单眼区域，超出部分会被裁切。

### 手机本地配置与重连

两种手机都在本地保存完整的**已提交 VR 设置**，包括模式、缩放、偏移、眼间距、视场角、距离、畸变、灵敏度与 Y 反转。离线修改也会保留，草稿不保存；重启后先恢复已保存配置。正常连接同步接受的完整设置快照也更新已提交配置。

收到合法主机 `hello` 后，有已保存配置的手机会用新的 `clientSeq`，通过普通 v1 `settings` 一次发送完整配置。这是用户明确选择的偏好，优先于本次连接的主机初始设置，但不跳过会话校验或输入授权。没有已保存配置时先采用合法主机快照。后续电脑更改与确认继续遵循原有 revision / 序号规则，见 [协议 v1](PROTOCOL.md)。

已连接时，任一端保存都经普通合法设置、确认与广播传播，两端保留接受的已提交状态；离线保存只能改本应用的本地偏好。**若两边离线都改过，下次合法连接由已保存手机配置优先**；之后再从电脑保存，就能把电脑选择的适配应用到两端。本版不比较未同步的时钟，也不合并冲突的完整离线配置。

配对码和 Apple 配对记录不属于观看配置，也不会保存进去。仍默认 USB，可显式选择局域网；保存配置不会自动连接或开始串流。

### 重置全部设置

重置需要主动选择，与放弃分开；它清除待保存编辑，把产品偏好恢复默认：

| 偏好 | 默认值 |
| --- | --- |
| 模式 / 缩放 / 偏移 | 全屏 / 0.85 / 0, 0 |
| 眼间距 / 视场角 / 距离 | 0.03 / 80° / 3 |
| 畸变 / 灵敏度 / Y 反转 | 0 / 1000 / false |
| 语言 / 优先连接 | English / USB |
| Windows 采集预设 | 低延迟：最长边 640、目标 60 FPS、JPEG Q45 |
| 手机局域网字段 | 空地址、端口 8765、空配对码 |

电脑**保留明确选择的采集显示器 / 选区及配置的 ADB 程序路径**，因为它们标识用户要分享的画面与已安装工具；重置观看偏好不应偷偷切到其他屏幕或删除开发环境。USB 设备选择恢复自动。重置不会卸载驱动 / SDK、改变平台授权、开始串流或授权鼠标。

手机重置清除本地观看与连接偏好，选择英文 / USB 并结束当前连接，不会悄悄重连。已经连接的主机设置更新仍用正常校验协议。保存后的默认配置可在下次明确建立会话后恢复。

### 可复用的几何合同

原创 Python 工具位于 `desktop/src/vrization_host/view_edit.py`；Android 核心 `HeadsetGeometry` / `HeadsetEdit` 与 Swift 核心 `HeadsetFit` 使用相同数学。Swift 还提供 `PhonePreferencesStore` 与 `LocalProfileSync` 处理已提交偏好及恢复。几何本身不依赖平台界面、网络或存储。

每眼采用**[−1, 1] 归一化坐标，y 向上**。图像宽高比为 `a`、单眼区域宽高比为 `e`：

```text
fit = (min(1, a/e), min(1, e/a))
center = (offsetX ± eyeSeparation, offsetY)
half-size = fit × scale
pan = clamp(start.offset + 从按下位置起的总位移, −0.3, +0.3)
resize scale = clamp(start.scale +
    dot((dx × cornerX, dy × cornerY), fit) / dot(fit, fit), 0.5, 1)
```

左眼取 `−`，右眼取 `+`；角点符号为左 / 右 −1 / +1、下 / 上 −1 / +1。指针位移根据**手势开始快照**计算，不把每个事件重复累加。屏幕 y 向下，转换时取相反符号。角点缩放不改变两个偏移，两眼共用新缩放与偏移。

纯几何接收画面逻辑位移，三端界面适配器**仅对内部平移的 x 取反**（`dx = −2 × 指针水平位移 / 单眼宽度`）；y 仍为 `−2 × 指针竖向位移 / 高度`。三端角点缩放的 x 都正常（`+2 × 指针水平位移 / 单眼宽度`）。编辑方向不改变 FPS 陀螺仪 / 鼠标映射，不新增 invert-X 协议字段，也不反转角点缩放。

Python 提供 `fit_size`、`eye_bounds`（左、下、右、上；eye 0 左 / 1 右）、`dragged`（`pan` / `resize`）及可选 `EditTransaction`，负责本地预览 / 提交 / 放弃。调用方负责渲染、存储与广播。几何自动检查不代表真实盒子镜片或界面 / 设备验收已完成，实测范围见 [验证记录](VALIDATION.md)。

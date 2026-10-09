# 🔌 WebSocket protocol v1 / WebSocket 协议 v1

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

This describes the alpha integration protocol: 2D JPEG frames and JSON control messages, not OpenXR or a stereoscopic video format.

### Connection

```text
ws://<PC LAN IP>:8765/ws?token=<six-digit pairing code>
```

The host listens on `0.0.0.0:8765` and accepts one client at a time. A fresh code is generated when streaming starts; preserve leading zeros. HTTP errors: `401` invalid pairing, `409` another client connected, `429` too many pairing attempts (wait about a minute). Failures are limited per address and globally.

Unauthenticated `GET /health` returns host name, version, protocol and connection status, never desktop frames. Use it only for basic connectivity checks.

`ws://` is unencrypted. The token is in the query string and must not enter public logs. Use trusted LANs only.

### Message directions

| Direction | Type | Content |
| --- | --- | --- |
| Host → phone | Binary | One complete JPEG per message. |
| Host → phone | JSON text | `hello`, `settings`, `pong`, `error`. |
| Phone → host | JSON text | Optional `hello`, `settings`, `pose`, `recenter`, `ping`. |

There is no custom frame header, sequence, timestamp, audio or independent per-eye image. The client draws the same frame in both eyes. Do not concatenate JPEGs into one message. The host keeps the latest frame rather than queueing old ones.

### Version and handshake

Each JSON message requires integer `v: 1` and string `type`. On connection the host sends:

```json
{
  "v": 1,
  "type": "hello",
  "name": "VRization",
  "version": "0.1.1",
  "revision": 0,
  "settings": {
    "mode": "full", "scale": 0.85, "offsetX": 0.0, "offsetY": 0.0,
    "eyeSeparation": 0.03, "fov": 80.0, "distance": 3.0,
    "distortion": 0.0, "sensitivity": 1000.0, "invertY": false
  },
  "stream": {"codec": "jpeg", "fps": 30, "maxWidth": 1280},
  "mouseArmed": false
}
```

Stream numbers are examples. v1 retains `maxWidth` as a width bound; the current host also limits the **longest edge** to this value. A 2160 × 3840 source becomes 720 × 1280 at limit 1280. Render the actual JPEG dimensions rather than inferring aspect ratio from this bound.

Use `hello.settings` for the session instead of overwriting a new host with stale client settings. Optional client handshake: `{"v":1,"type":"hello"}`.

### Settings

Clients can send nonempty partial updates; the host validates and broadcasts complete settings. PC UI changes also broadcast.

Since v0.1.1, `hello` and host `settings` messages include a nonnegative, monotonically increasing server `revision`. Client `settings` may include `clientSeq` (integer 0 through `2^53−1`); the response to that same socket echoes it. Unsolicited PC broadcasts omit `clientSeq`. Read the latest complete snapshot under the host's broadcast lock. Two acknowledgments can share one revision while acknowledging different client sequences; accept the newer acknowledgment without applying older state. Do not send acknowledgments to a replacement socket after reconnecting. Old clients may omit these fields.

```json
{"v":1,"type":"settings","clientSeq":1,"settings":{"mode":"cinema","scale":0.7,"offsetY":0.05}}
```

| Field | Valid values | Initial default | Meaning |
| --- | --- | --- | --- |
| `mode` | `full` / `cinema` / `fps` | `full` | Fixed / virtual screen / gyro mouse. |
| `scale` | 0.5–1.0 | 0.85 | Effective per-eye image scale. |
| `offsetX`, `offsetY` | -0.3–0.3 | 0 | Normalized horizontal / vertical offset. |
| `eyeSeparation` | 0–0.2 | 0.03 | Display spacing; not meters or automatic IPD. |
| `fov` | 50–110 | 80 | Field of view in degrees. |
| `distance` | 1–8 | 3 | Virtual screen distance in scene units. |
| `distortion` | 0–0.5 | 0 | Lens distortion coefficient. |
| `sensitivity` | 100–3000 | 1000 | Mouse displacement per radian. |
| `invertY` | JSON boolean | `false` | Invert vertical mouse direction. |

Numbers must be finite; strings, booleans, NaN and infinity are invalid numeric values. Unknown fields and out-of-range values are rejected rather than clamped.

### Pose and recenter

```json
{"v":1,"type":"pose","seq":42,"yaw":0.12,"pitch":-0.08}
```

Yaw / pitch are landscape-remapped angles in **radians**: positive yaw turns right, positive pitch looks up. Roll affects local cinema rendering and is not sent in the current pose message. `seq` is a strictly increasing nonnegative integer within each session, at most `2^53−1`; reconnecting can restart it at zero. Duplicate / stale sequences cause no movement. Absolute angles are limited to 100 radians; individual jumps over 0.4 radians are dropped. Send continuous, correctly wrapped sensor values.

```json
{"v":1,"type":"recenter"}
```

The phone resets its local camera center and sends this message so the next pose establishes a new host mouse baseline. It never arms input.

FPS needs a valid session, `mode: fps`, recent pose and explicit PC arming. Pose timeout is 0.5 seconds. After arming, select the target window within five seconds; later focus changes disarm. Mouse displacement is also limited. There is no remote `arm` message; preserve this boundary in integrations.

### Heartbeat, errors and close

Application ping / pong messages are `{"v":1,"type":"ping"}` and `{"v":1,"type":"pong"}`. Errors use `{"v":1,"type":"error","message":"..."}`.

Client text messages are limited to 16 KiB. Repeated invalid messages or excessive message rates close with `1008`; client binary messages close with `1003`. Host shutdown or blocked frame sending can close with `1001`. WebSocket ping / pong keeps connections alive but does not replace the FPS pose heartbeat.

### Compatibility

New codecs, native per-eye frames, timestamps or stronger authentication require explicit protocol negotiation / versioning. Do not guess unknown binary formats. `mouseArmed` reports initial state; it does not grant the phone authorization power.

---

<!-- vrization:chinese -->
## 简体中文

该协议描述当前 Alpha 实现，便于其他软件接入。它传输二维 JPEG 帧和 JSON 控制消息，不是 OpenXR 或立体视频协议。

### 连接

```text
ws://<电脑局域网 IP>:8765/ws?token=<六位配对码>
```

主机默认监听 `0.0.0.0:8765`，一次只接受一个客户端。配对码在启动服务时生成，保留开头的零。错误码为 `401`（配对错误）、`409`（已有客户端）和 `429`（配对尝试过多，等待约一分钟）。配对失败有每地址与全局速率限制。

`GET /health` 返回主机名、版本、协议号和连接状态，不需要配对码，也不返回桌面帧。它仅用于基本连通性检查。

`ws://` 没有加密。配对码在 URL 查询参数中传递，不应写入公开日志。服务仅用于可信局域网。

### 消息方向

| 方向 | WebSocket 类型 | 内容 |
| --- | --- | --- |
| 主机 → 手机 | Binary | 一个完整 JPEG 文件；每条消息一帧。 |
| 主机 → 手机 | Text / JSON | `hello`、`settings`、`pong`、`error`。 |
| 手机 → 主机 | Text / JSON | `hello`（可选）、`settings`、`pose`、`recenter`、`ping`。 |

没有自定义二进制头、帧序号、时间戳、音频或左右眼独立图像。客户端自行将同一帧显示到两眼。不要把多个 JPEG 文件拼进一条消息。主机使用最新帧缓冲，避免排队积累旧帧。

### 版本与握手

每条 JSON 消息包含整数 `v: 1` 与字符串 `type`。主机在连接成功后首先发送：

```json
{
  "v": 1,
  "type": "hello",
  "name": "VRization",
  "version": "0.1.1",
  "revision": 0,
  "settings": {
    "mode": "full", "scale": 0.85, "offsetX": 0.0, "offsetY": 0.0,
    "eyeSeparation": 0.03, "fov": 80.0, "distance": 3.0,
    "distortion": 0.0, "sensitivity": 1000.0, "invertY": false
  },
  "stream": {"codec": "jpeg", "fps": 30, "maxWidth": 1280},
  "mouseArmed": false
}
```

`stream` 数值仅为示例，以主机当次配置为准。`maxWidth` 保留 v1 字段名，表示输出宽度上限；当前主机也把该数值作为**最长边**限制，以控制竖屏帧的解码负担。例如 2160 × 3840 的源画面在限值 1280 下输出 720 × 1280。客户端应以实际 JPEG 尺寸渲染，不根据该上限猜测帧的纵横比。

客户端应以 `hello.settings` 为当前会话设置，不用自己的旧设置覆盖新主机。可选客户端握手：

```json
{"v":1,"type":"hello"}
```

### 设置同步

两端使用相同结构；客户端可以发送非空的局部更新，主机校验后广播完整设置。电脑界面修改也会广播。

v0.1.1 起，主机 `hello` 与 `settings` 含非负、单调增加的 `revision`。客户端 `settings` 可附 `clientSeq`（0 到 `2^53−1` 的整数），主机向同一连接回传确认时原样带回；主动的电脑设置广播不带 `clientSeq`。主机在串行广播锁内读取最新完整快照。两个确认可能有相同 revision、不同 clientSeq，客户端应确认较新序号但不回退设置；重连后不能把旧确认发送到新 socket。旧客户端可省略这些兼容字段。

```json
{"v":1,"type":"settings","clientSeq":1,"settings":{"mode":"cinema","scale":0.7,"offsetY":0.05}}
```

| 字段 | 有效值 | 主机初始值 | 含义 |
| --- | --- | --- | --- |
| `mode` | `full` / `cinema` / `fps` | `full` | 全屏 / 虚拟大屏幕 / FPS 鼠标模式。 |
| `scale` | 0.5–1.0 | 0.85 | 每眼有效画面的缩放。 |
| `offsetX` | -0.3–0.3 | 0 | 归一化水平偏移。 |
| `offsetY` | -0.3–0.3 | 0 | 归一化垂直偏移。 |
| `eyeSeparation` | 0–0.2 | 0.03 | 双眼画面的显示间隔参数；不是米或自动测量瞳距。 |
| `fov` | 50–110 | 80 | 视场角，度。 |
| `distance` | 1–8 | 3 | 虚拟屏幕距离，渲染场景单位。 |
| `distortion` | 0–0.5 | 0 | 镜片畸变系数。 |
| `sensitivity` | 100–3000 | 1000 | FPS 鼠标位移 / 弧度比例。 |
| `invertY` | JSON boolean | `false` | 反转纵向鼠标控制。 |

数值必须有限，不能传 `NaN`、无穷、字符串或布尔值冒充数字。主机拒绝未知设置字段和越界值，不会默默截断。

### 姿态与回正

```json
{"v":1,"type":"pose","seq":42,"yaw":0.12,"pitch":-0.08}
```

`yaw` / `pitch` 是横屏坐标映射后的角度，单位为**弧度**；yaw 正值向右，pitch 正值向上。roll 仅用于手机本地大屏幕渲染，当前姿态消息不发送 roll。`seq` 为每会话严格递增的非负整数，最大 `2^53−1`；重连后可以从零开始。重复或旧序号不会产生鼠标移动。主机接受的姿态绝对值上限为 100 弧度，并进一步丢弃超过 0.4 弧度的单次跳变；发送端应使用连续、正确包裹的传感器数据。

```json
{"v":1,"type":"recenter"}
```

手机回正同时重设本地虚拟相机基准，并向主机发送 `recenter`，让下一条姿态建立新鼠标基准。主机收到该消息不会自动授权鼠标。

FPS 控制需要有效会话、`mode: fps`、近期姿态和电脑端主动授权。当前姿态心跳超时为 0.5 秒；授权后需在五秒内切到目标窗口，之后切换焦点会解除授权。输出还限制单次鼠标位移。没有远程 `arm` 消息；集成时应保留此边界。

### 心跳、错误与关闭

```json
{"v":1,"type":"ping"}
```

```json
{"v":1,"type":"pong"}
```

协议错误时主机返回 `{"v":1,"type":"error","message":"..."}`。客户端文本消息最多 16 KiB；持续无效消息或超过消息速率会以 `1008` 关闭。客户端发送二进制消息会以 `1003` 关闭。主机停止或帧发送阻塞时可使用 `1001` 关闭。WebSocket ping / pong 还用于连接保活，不能替代 FPS 姿态心跳。

### 兼容性原则

添加不同编码、原生左右眼帧、时间戳或更强认证时应升级协议并显式协商。v1 客户端不应猜测不认识的二进制内容。`mouseArmed` 是初始状态提示，不是手机的授权能力。

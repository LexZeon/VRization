# 🔌 WebSocket protocol v1 / WebSocket 协议 v1

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

v0.2.0-alpha retains integration **protocol v1**: 2D JPEG frames and JSON control messages. Android and iOS use the same messages over LAN or their USB adapters. This is not OpenXR or a stereoscopic video format. For installation and device authorization, read [USB setup](USB.md).

### LAN WebSocket connection

```text
ws://<PC LAN IP>:8765/ws?token=<six-digit pairing code>
```

The host listens on `0.0.0.0:8765` and accepts one client at a time. A fresh code is generated when streaming starts; preserve leading zeros. HTTP errors: `401` invalid pairing, `409` another client connected, `429` too many pairing attempts (wait about a minute). Failures are limited per address and globally.

Unauthenticated `GET /health` returns host name, version, protocol and connection status, never desktop frames. Use it only for basic connectivity checks.

`ws://` is unencrypted. The token is in the query string and must not enter public logs. Use trusted LANs only. USB is the default phone transport preference; LAN pairing is explicitly selectable.

### Android USB discovery

The Windows GUI's optional `UsbManager` discovers a physical, authorized Android USB device and creates `adb -s <serial> reverse --no-rebind tcp:18765 tcp:<hostport>`. It never replaces an existing reverse mapping. Emulators, IP / port and wireless mDNS transports are excluded; Windows native SetupAPI supplies physical USB evidence when ADB reports an unknown device path. Only one unambiguously selected Android device is mapped automatically. The user still starts streaming on the PC.

The phone requests `GET http://127.0.0.1:18765/usb-bootstrap`:

```json
{"v":1,"name":"VRization","version":"0.2.0","port":8765,"token":"001234"}
```

`port` describes the PC listener; it does **not** change the phone destination. The phone then uses `ws://127.0.0.1:18765/ws?token=001234` with the ordinary v1 WebSocket protocol. The example token is fictitious. Responses use `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`. Access requires a loopback peer, one `Host` header naming `127.0.0.1`, `localhost` or `[::1]` with the PC port or reverse port `18765`, no `Origin` header, and an authorized physical USB mapping owned by this manager. Refusal is `403`; a reachable but stopped host returns `503`, while a stopped listener usually refuses the TCP connection. Ordinary `HostServer` embedding disables bootstrap unless explicitly supplied an authorization callback. No CORS permission is granted.

### iOS USB envelope

The foreground iOS app listens only at phone loopback `127.0.0.1:18766`. Windows enumerates USB devices through Apple's local usbmux service (`127.0.0.1:27015`), requires an existing local pairing record through read-only `ReadPairRecord`, and connects to the selected device's port `18766`. The relay authenticates to the host's local WebSocket using its current token. No six-digit code is entered on the phone. Automatic selection requires a single attached Apple mobile device; VRization sends no Pair / Trust / SavePairRecord request and never logs or persists pairing-record keys.

Inside this tunnel, each VRization frame is:

```text
4-byte unsigned big-endian length | 1-byte kind | payload
```

The length includes the kind and excludes the four-byte prefix; valid length is `1…8 MiB`. Kind `1` carries UTF-8 v1 JSON and kind `2` carries one JPEG. JSON payloads are limited to 16 KiB. Phone → host accepts JSON only. Reject invalid lengths / kinds before allocating a payload; handle partial headers, fragmented payloads and multiple frames in one read. The first host JSON is the normal `hello`; the app requires it before treating the session as connected. Closing either side closes the relay's WebSocket and revokes host input authorization. This envelope is separate from usbmux's own little-endian plist service protocol; it does not change WebSocket v1.

USB starts with one foreground attempt on a fresh phone app launch; after backgrounding, language changes or a disconnect the user connects explicitly. iOS USB evidence currently covers a simulated usbmux service, the production relay and the native Simulator listener, not a physical iPhone / Apple driver test. Huawei Android hardware evidence is recorded separately in [validation](VALIDATION.md).

### Message directions

| Direction | Type | Content |
| --- | --- | --- |
| Host → phone | Binary | One complete JPEG per message. |
| Host → phone | JSON text | `hello`, `settings`, `pong`, `error`. |
| Phone → host | JSON text | Optional `hello`, `settings`, `pose`, `recenter`, `ping`. |

The JPEG WebSocket payload has no custom header, sequence, timestamp, audio or independent per-eye image. The USB envelope above wraps these same payloads for iOS. The client draws the same frame in both eyes. Do not concatenate JPEGs into one message. The host keeps the latest frame rather than queueing old ones.

### Version and handshake

Each JSON message requires integer `v: 1` and string `type`. On connection the host sends:

```json
{
  "v": 1,
  "type": "hello",
  "name": "VRization",
  "version": "0.2.0",
  "revision": 0,
  "settings": {
    "mode": "full", "scale": 0.85, "offsetX": 0.0, "offsetY": 0.0,
    "eyeSeparation": 0.03, "fov": 80.0, "distance": 3.0,
    "distortion": 0.0, "sensitivity": 1000.0, "invertY": false
  },
  "stream": {"codec": "jpeg", "fps": 60, "maxWidth": 640},
  "mouseArmed": false
}
```

Stream numbers are examples. v1 retains `maxWidth` as a width bound; the current host also limits the **longest edge** to this value. A 2160 × 3840 source becomes 360 × 640 at limit 640. Render the actual JPEG dimensions rather than inferring aspect ratio from this bound. GPU crop / rotation / scaling changes the host implementation, not the JPEG payload or protocol version. Static refresh packets can repeat an owned JPEG; v1 has no wire capture timestamp or distinct-frame counter.

Use `hello.settings` for the session instead of overwriting a new host with stale client settings. Optional client handshake: `{"v":1,"type":"hello"}`.

The current iOS client waits for a valid v1 `hello` before marking either LAN or USB connected, with a ten-second host-handshake deadline. A socket opening alone does not establish the session. Invalid / unsupported host messages disconnect; this client-side gate is not a new server protocol version.

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

Clients display received-frame FPS and application-ping round-trip time. Neither measures end-to-end video latency: ping excludes capture, encoding, decoding and presentation. The GUI's new-user low-latency preset is maximum long edge 640, target 60 FPS and JPEG quality 45; stable is 640 / 30 / 50, quality is 960 / 30 / 60. Existing saved capture settings remain effective. These are capture goals, not wire-version changes or measured latency promises. See [performance metrics and queue boundaries](PERFORMANCE.md).

Client text messages are limited to 16 KiB. Repeated invalid messages or excessive message rates close with `1008`; client binary messages close with `1003`. Host shutdown or blocked frame sending can close with `1001`. WebSocket ping / pong keeps connections alive but does not replace the FPS pose heartbeat.

### Compatibility

New codecs, native per-eye frames, timestamps or stronger authentication require explicit protocol negotiation / versioning. Do not guess unknown binary formats. `mouseArmed` reports initial state; it does not grant the phone authorization power.

---

<!-- vrization:chinese -->
## 简体中文

v0.2.0-alpha 保留集成**协议 v1**：传输二维 JPEG 帧和 JSON 控制消息。Android 与 iOS 经局域网或各自 USB 适配器使用相同消息。它不是 OpenXR 或立体视频协议；安装和设备授权见 [USB 教程](USB.md)。

### 局域网 WebSocket 连接

```text
ws://<电脑局域网 IP>:8765/ws?token=<六位配对码>
```

主机默认监听 `0.0.0.0:8765`，一次只接受一个客户端。配对码在启动服务时生成，保留开头的零。错误码为 `401`（配对错误）、`409`（已有客户端）和 `429`（配对尝试过多，等待约一分钟）。配对失败有每地址与全局速率限制。

`GET /health` 返回主机名、版本、协议号和连接状态，不需要配对码，也不返回桌面帧。它仅用于基本连通性检查。

`ws://` 没有加密。配对码在 URL 查询参数中传递，不应写入公开日志。服务仅用于可信局域网。手机默认优先 USB，也可显式选择局域网配对。

### Android USB 发现

Windows 界面可启用 `UsbManager`，检测已授权的真实 Android USB 设备，并建立 `adb -s <serial> reverse --no-rebind tcp:18765 tcp:<hostport>`，不替换已有映射。排除模拟器、IP / 端口和无线 mDNS 连接；ADB 报告未知路径时，Windows 原生 SetupAPI 提供真实 USB 设备证据。只有唯一、明确选中的安卓设备会自动建立映射，电脑仍需用户主动开始串流。

手机请求 `GET http://127.0.0.1:18765/usb-bootstrap`：

```json
{"v":1,"name":"VRization","version":"0.2.0","port":8765,"token":"001234"}
```

`port` 说明电脑监听端口，**不改变**手机目的端口；手机随后以普通 v1 协议连接 `ws://127.0.0.1:18765/ws?token=001234`。示例 token 为虚构。响应含 `Cache-Control: no-store`、`X-Content-Type-Options: nosniff`。请求必须来自回环地址，仅含一个 `Host`，主机为 `127.0.0.1`、`localhost` 或 `[::1]`，端口为电脑端口或反向端口 `18765`，不能含 `Origin`，并且 manager 必须拥有已授权的真实 USB 映射。拒绝返回 `403`；服务可达但已停止返回 `503`，监听停止时通常直接拒绝 TCP 连接。普通 `HostServer` 嵌入默认关闭 bootstrap，须显式提供授权回调；接口不授予 CORS 访问。

### iOS USB 分帧

iOS 应用仅在前台监听手机回环 `127.0.0.1:18766`。Windows 经 Apple 本地 usbmux 服务（`127.0.0.1:27015`）枚举 USB 设备，通过只读 `ReadPairRecord` 要求已有本地配对记录，再连接所选设备的 `18766`。中继使用当次 token 连接主机本地 WebSocket，手机不填写六位码。自动选择要求只接一台 Apple 移动设备；VRization 不发送 Pair / Trust / SavePairRecord，也不输出或保存配对记录密钥。

隧道内每个 VRization 帧为：

```text
4 字节无符号大端长度 | 1 字节类型 | 内容
```

长度包含类型字节、不包含四字节头，有效范围 `1…8 MiB`。类型 `1` 为 UTF-8 v1 JSON，类型 `2` 为一个 JPEG；JSON 内容最多 16 KiB，手机向主机只发 JSON。分配内容前先拒绝非法长度 / 类型；支持分段头、分段内容及一次读取多个帧。首条主机 JSON 为普通 `hello`，应用收到合法握手才认为连接成功。任意一侧关闭会关闭中继 WebSocket，并撤销主机输入授权。此分帧独立于 usbmux 自身的小端 plist 服务协议，不改变 WebSocket v1。

手机软件新启动时只在前台自动尝试一次 USB；进入后台、切换语言或断线后需主动连接。目前 iOS USB 证据包含模拟 usbmux 服务、生产中继与原生模拟器监听，不代表真实 iPhone / Apple 驱动已经通过；华为 Android 实机证据在 [验证记录](VALIDATION.md) 单独列出。

### 消息方向

| 方向 | WebSocket 类型 | 内容 |
| --- | --- | --- |
| 主机 → 手机 | Binary | 一个完整 JPEG 文件；每条消息一帧。 |
| 主机 → 手机 | Text / JSON | `hello`、`settings`、`pong`、`error`。 |
| 手机 → 主机 | Text / JSON | `hello`（可选）、`settings`、`pose`、`recenter`、`ping`。 |

WebSocket 的 JPEG 内容没有自定义二进制头、帧序号、时间戳、音频或左右眼独立图像；iOS USB 以上述分帧包装相同内容。客户端自行将同一帧显示到两眼。不要把多个 JPEG 文件拼进一条消息。主机使用最新帧缓冲，避免排队积累旧帧。

### 版本与握手

每条 JSON 消息包含整数 `v: 1` 与字符串 `type`。主机在连接成功后首先发送：

```json
{
  "v": 1,
  "type": "hello",
  "name": "VRization",
  "version": "0.2.0",
  "revision": 0,
  "settings": {
    "mode": "full", "scale": 0.85, "offsetX": 0.0, "offsetY": 0.0,
    "eyeSeparation": 0.03, "fov": 80.0, "distance": 3.0,
    "distortion": 0.0, "sensitivity": 1000.0, "invertY": false
  },
  "stream": {"codec": "jpeg", "fps": 60, "maxWidth": 640},
  "mouseArmed": false
}
```

`stream` 数值仅为示例，以主机当次配置为准。`maxWidth` 保留 v1 字段名，表示输出宽度上限；当前主机也把该数值作为**最长边**限制，以控制竖屏帧的解码负担。例如 2160 × 3840 的源画面在限值 640 下输出 360 × 640。客户端应以实际 JPEG 尺寸渲染，不根据该上限猜测帧的纵横比。GPU 裁切 / 旋转 / 缩放改变主机实现，不改变 JPEG 内容或协议版本；静态刷新包可能重复自有 JPEG，v1 没有传输采集时间戳或不同帧计数。

客户端应以 `hello.settings` 为当前会话设置，不用自己的旧设置覆盖新主机。可选客户端握手：

当前 iOS 客户端在 LAN / USB 都等待合法 v1 `hello` 才显示已连接，主机握手期限为十秒。仅 socket 打开不代表会话已建立；非法 / 不支持的主机消息会断开。此客户端门控不是新的服务端协议版本。

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

手机显示接收帧率和应用 ping 往返时间，两者都不测量端到端视频延迟：ping 不包括采集、编码、解码与呈现。电脑界面新用户低延迟预设为最长边 640、目标 60 FPS、JPEG 质量 45；稳定为 640 / 30 / 50，画质为 960 / 30 / 60；已有保存配置继续生效。预设是捕获目标，不改变协议版本，也不承诺测得的延迟。详见 [性能指标与队列边界](PERFORMANCE.md)。

协议错误时主机返回 `{"v":1,"type":"error","message":"..."}`。客户端文本消息最多 16 KiB；持续无效消息或超过消息速率会以 `1008` 关闭。客户端发送二进制消息会以 `1003` 关闭。主机停止或帧发送阻塞时可使用 `1001` 关闭。WebSocket ping / pong 还用于连接保活，不能替代 FPS 姿态心跳。

### 兼容性原则

添加不同编码、原生左右眼帧、时间戳或更强认证时应升级协议并显式协商。v1 客户端不应猜测不认识的二进制内容。`mouseArmed` 是初始状态提示，不是手机的授权能力。

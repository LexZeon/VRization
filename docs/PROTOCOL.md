# 🔌 WebSocket protocol v1 / WebSocket 协议 v1

[English](#english) · [简体中文](#简体中文)

<!-- vrization:english -->
## English

The v0.3.3 candidate retains integration **protocol v1**: 2D JPEG frames and JSON control messages. Android and iOS use the same messages over LAN or their USB adapters. This is not OpenXR or a stereoscopic video format. For installation and device authorization, read [USB setup](USB.md).

### LAN WebSocket connection

```text
ws://<PC LAN IP>:8765/ws?token=<six-digit pairing code>&settingsSchema=2
```

The host listens on `0.0.0.0:8765` and accepts one client at a time. A fresh code is generated when streaming starts; preserve leading zeros. HTTP errors: `401` invalid pairing, `409` another client connected, `429` too many pairing attempts (wait about a minute). Failures are limited per address and globally.

Unauthenticated `GET /health` returns host name, version, protocol and connection status, never desktop frames. Use it only for basic connectivity checks.

`ws://` is unencrypted. The token is in the query string and must not enter public logs. Use trusted LANs only. USB is the default phone transport preference; LAN pairing is explicitly selectable.

### Android USB discovery

The Windows GUI's optional `UsbManager` discovers a physical, authorized Android USB device and creates `adb -s <serial> reverse --no-rebind tcp:18765 tcp:<hostport>`. It never replaces an existing reverse mapping. Emulators, IP / port and wireless mDNS transports are excluded; Windows native SetupAPI supplies physical USB evidence when ADB reports an unknown device path. Only one unambiguously selected Android device is mapped automatically. Automatic phone startup can wait for an existing stream; explicit phone / PC Connect can request startup through the separate control path.

The phone requests `GET http://127.0.0.1:18765/usb-bootstrap`:

```json
{"v":1,"name":"VRization","version":"0.3.2","port":8765,"token":"001234"}
```

`port` describes the PC listener; it does **not** change the phone destination. The phone then uses `ws://127.0.0.1:18765/ws?token=001234&settingsSchema=2` with the ordinary v1 WebSocket protocol. The example token is fictitious. Responses use `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`. Access requires a loopback peer, one `Host` header naming `127.0.0.1`, `localhost` or `[::1]` with the PC port or reverse port `18765`, no `Origin` header, and an authorized physical USB mapping owned by this manager. Refusal is `403`; a reachable but stopped host returns `503`, while a stopped listener usually refuses the TCP connection. Ordinary `HostServer` embedding disables bootstrap unless explicitly supplied an authorization callback. No CORS permission is granted.

### Explicit Android USB control (v0.3.3 candidate)

`ConnectionCoordinator` owns request identities independently of capture. The PC binds `UsbConnectService` only to `127.0.0.1:18764`; an owned non-rebinding reverse mapping connects phone `18764` to it. Explicit phone Connect makes one empty-body `POST http://127.0.0.1:18764/connect`, then uses ordinary video bootstrap at `18765`. Automatic waiting, bootstrap polling and socket retries do not repeat this request. The route requires a loopback peer, one literal loopback Host with the control port, no Origin and independently authorized physical USB control mapping. No token or target is supplied. On 200 the response is `{"v":1,"name":"VRization","ready":true}`; refusal is 403, unavailable / eight-second failed startup is 503. GUI acceptance rejects stopped / expired identities. Video bootstrap remains independently authorized.

PC Connect starts the host under the same coordinator and makes one explicit selected-device Activity request (`vrization_connect_usb`). Extras are consumed once; repeated requests preserve an active session. Detection never launches or wakes the phone periodically. Stop invalidates queued requests and video/socket identities; old retries and restored intents cannot revive a stopped session.

### iOS USB envelope

The foreground iOS app keeps control at phone loopback `127.0.0.1:18767`; explicit Connect opens video at `127.0.0.1:18766`. Windows enumerates USB devices through local usbmux (`127.0.0.1:27015`) and requires a read-only existing `ReadPairRecord` before either connection. PC Connect sends exactly one framed kind-1 `{"v":1,"type":"connect"}` to `18767`. Control accepts only these two fields, integer v1 and type connect or stop; it cannot authorize input or choose a capture target. Active sessions ignore repeated control. The control listener persists during video Disconnect and stops in background / destruction. Windows cannot launch a background viewer.

PC Stop first gates pending relay startup and closes its existing video. It sends one paired control `{"v":1,"type":"stop"}`. The native main queue closes video/socket, invalidates decoder state and clears the renderer before replying `{"v":1,"type":"stopped"}`; foreground control remains available. `request_ios_stop` requires that bounded acknowledgment within two seconds. Only acknowledgment or an independently paired explicit video-port refusal can clear the stop gate; a trust/service failure cannot prove listener absence. Old notifications / absence results are checked against the stop epoch. Notification is bounded and a new explicit PC Connect can replace the stopped request; detection does not unlock it after a timeout. This also closes an explicitly opened video listener that had never accepted a peer.

The unique accepted video peer sends the same readiness frame before receiving host hello. `IosRelay` requires it within two seconds, consumes it even for running hosts and never forwards it as a host message. Only valid readiness can request a stopped host through the injected coordinator; the relay waits up to eight seconds for the same request identity and startup. Cancellation / timeout fails pending identities and closes the paired peer; a later different action cannot satisfy an old request. An occupied old listener rejects the new peer without readiness, so TCP acceptance alone never starts capture. This candidate pre-handshake requires the matching native viewer; legacy iOS USB viewers without readiness are not compatible with the new relay. LAN v1 message compatibility is unaffected.

The relay then authenticates to the local host WebSocket with its current token and bridges ordinary messages. No code is entered on iOS; automatic selection requires one attached Apple device. VRization sends no Pair / Trust / SavePairRecord and never logs or saves record keys.

Inside this tunnel, each VRization frame is:

```text
4-byte unsigned big-endian length | 1-byte kind | payload
```

The length includes the kind and excludes the four-byte prefix; valid length is `1…8 MiB`. Kind `1` carries UTF-8 v1 JSON and kind `2` carries one JPEG. JSON payloads are limited to 16 KiB. Phone → host accepts JSON only. Reject invalid lengths / kinds before allocating a payload; handle partial headers, fragmented payloads and multiple frames in one read. The first host JSON is the normal `hello`; the app requires it before treating the session as connected. Closing either side closes the relay's WebSocket and revokes host input authorization. This envelope is separate from usbmux's own little-endian plist service protocol; it does not change WebSocket v1.

Fresh Android startup can wait for an existing stream; fresh iOS startup opens only foreground control. An explicit Connect on either supported device can establish USB. Backgrounding, language changes and Disconnect invalidate video and require another explicit action. New candidate native checks are pending. Historical iOS evidence covers simulated usbmux and the native Simulator, not a physical iPhone / Apple driver. See version-scoped [validation](VALIDATION.md).

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
  "version": "0.3.2",
  "revision": 0,
  "capabilities": ["stabilization"],
  "settings": {
    "mode": "full", "scale": 0.85, "offsetX": 0.0, "offsetY": 0.0,
    "eyeSeparation": 0.03, "fov": 80.0, "distance": 3.0,
    "distortion": 0.0, "sensitivity": 1000.0, "stabilization": 0.0, "invertY": false
  },
  "stream": {"codec": "jpeg", "fps": 60, "maxWidth": 640},
  "mouseArmed": false
}
```

Stream numbers are examples. v1 retains `maxWidth` as a width bound; the current host also limits the **longest edge** to this value. A 2160 × 3840 source becomes 360 × 640 at limit 640. Render the actual JPEG dimensions rather than inferring aspect ratio from this bound. GPU crop / rotation / scaling changes the host implementation, not the JPEG payload or protocol version. Static refresh packets can repeat an owned JPEG; v1 has no wire capture timestamp or distinct-frame counter.

Validate `hello` before establishing the session. Since v0.3, a phone with a saved committed VR profile then sends that complete profile once using a new `clientSeq`; the user's local preference intentionally replaces the initial host settings. Without a saved profile, use the validated initial settings snapshot; a capable legacy USB hello first needs the schema-2 snapshot described below. Later acknowledgments / PC broadcasts follow the revision rules below. Current client metadata: `{"v":1,"type":"hello","settingsSchema":2}`. Legacy token-only URLs / hello remain accepted.

Both current phone clients wait for a valid v1 `hello` before marking either LAN or USB connected, with a ten-second host-handshake deadline. A socket opening alone does not establish the session. Invalid / unsupported host messages disconnect; this client-side gate is not a new server protocol version.

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
| `eyeSeparation` | −1–0.2 | 0.03 | Signed display spacing; dynamic flat-fit contact limits apply. Not meters or automatic IPD. |
| `fov` | 50–110 | 80 | Field of view in degrees. |
| `distance` | 1–8 | 3 | Virtual screen distance in scene units. |
| `distortion` | 0–0.5 | 0 | Lens distortion coefficient. |
| `sensitivity` | 100–3000 | 1000 | Mouse displacement per radian. |
| `stabilization` | 0–1 | 0 | Host-only first-person smoothing; 0 is exact bypass. Schema 2 only. |
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

First-person mode needs a valid session, `mode: fps`, recent pose and explicit PC arming. Pose timeout is 0.5 seconds. After arming, select the target window within five seconds; later focus changes disarm. Mouse displacement is also limited. There is no remote `arm` message; preserve this boundary in integrations.

### Heartbeat, errors and close

Application ping / pong messages are `{"v":1,"type":"ping"}` and `{"v":1,"type":"pong"}`. Errors use `{"v":1,"type":"error","message":"..."}`.

Clients display received-frame FPS and application-ping round-trip time. Neither measures end-to-end video latency: ping excludes capture, encoding, decoding and presentation. The GUI's new-user low-latency preset is maximum long edge 640, target 60 FPS and JPEG quality 45; stable is 640 / 30 / 50, quality is 960 / 30 / 60. Existing saved capture settings remain effective. These are capture goals, not wire-version changes or measured latency promises. See [performance metrics and queue boundaries](PERFORMANCE.md).

Client text messages are limited to 16 KiB. Repeated invalid messages or excessive message rates close with `1008`; client binary messages close with `1003`. Host shutdown or blocked frame sending can close with `1001`. WebSocket ping / pong keeps connections alive but does not replace the first-person pose heartbeat.

### Compatibility

New codecs, native per-eye frames, timestamps or stronger authentication require explicit protocol negotiation / versioning. Do not guess unknown binary formats. `mouseArmed` reports initial state; it does not grant the phone authorization power.

### Editor drafts and saved local profiles (v0.3)

These are client / GUI policies, not new wire types. Preview pan / resize is local: no `settings`, `pose` or preference writes occur while editing. A flat / undistorted preview retains the saved mode and other optical values. Phone Save commits the complete draft and sends one normal settings update when connected. PC Save patches only scale / offsetX / offsetY / eyeSeparation against the latest host state, preserving concurrent changes to other fields. Discard restores the local entry preview and sends none. Editor exit never arms input. Phone backgrounding / disconnecting discards an open draft.

Phones persist all committed VR fields, including offline changes; pairing secrets are not stored. After each validated host hello, a saved profile is restored once via normal complete settings with a fresh clientSeq. Do not replay old socket work, bypass validation or reset revisions to accommodate it. Accepted subsequent complete snapshots update the local profile normally. This explicit user-requested persistence replaces the earlier host-initial-settings preference for v0.3 clients; old v1 clients retain their behavior.

Connected Save from the PC or phone uses settings / acknowledgments / broadcasts and retains the accepted state on both sides. Offline changes stay local. If both sides have conflicting offline changes, the saved phone profile takes precedence on reconnect; the PC can Save again afterward. No timestamp / clock comparison, automatic merge or new conflict wire type is introduced. Editor horizontal dragging updates the existing eyeSeparation field with selected-eye sign (left −1, right +1), mirrored around shared X while the remaining gap permits it; vertical motion updates shared offsetY. Left-eye left / right-eye right widens, the opposite directions narrow. Flat-fit resolution uses h=fit.x×scale, separation=clamp(raw,h−1,.2), gap=max(0,1+separation−h), X=clamp(rawX,±min(.3,gap)). Contact recenters X and enlargement may adjust spacing outward; normal corner motion and first-person mapping stay unchanged. These pure render constraints do not rewrite raw saved settings. Both endpoints must be v0.3 for negative values; v0.2 accepted only 0…0.2. Existing nonnegative profiles remain valid. Only undistorted flat preview / full / first-person guarantees this seam geometry, not cinema or distorted views.

Reset restores standard Settings defaults, English and USB; phone reset clears connection preferences and disconnects without immediate auto-reconnect. A fresh Android launch can wait for an existing stream; iOS opens foreground control only; a valid hello restores the committed defaults. Host reset also restores capture 640 / 60 / Q45 but preserves explicit monitor / region and ADB tool path. Connected updates use ordinary settings validation. No remote reset / arm message is introduced. See [editor geometry and reset scope](EDITING.md).

### Disarm-only editor metadata (v0.3)

```json
{"v":1,"type":"hello","editing":true}
```

On editor entry, the phone stops new poses and drops application-pending pose work (already submitted transport bytes cannot be recalled) and sends this once on an already validated connection. Optional `editing` must be a JSON boolean; true disarms the current host immediately on receipt. False or omission never arms input. It is metadata on the existing v1 hello, not a draft settings update or a fourth mode. Older hosts can ignore the field; withholding poses still triggers their watchdog. Video / ping can continue during editing, and normal exit recentering remains allowed. Save or Discard never sends an arm request; the user must authorize again on the PC.

### Compatible settings negotiation (v0.3.2)

The transport stays `v:1`; settings schema 2 adds stabilization as an eleventh field. Current LAN / Android USB URLs opt in with `settingsSchema=2`. The iOS relay initially authenticates using the legacy URL; the client sends `{"v":1,"type":"hello","settingsSchema":2}`. The current host returns a complete eleven-field **settings** message, current revision and no clientSeq. It is not another host hello and does not increment revision.

A valid host hello can declare `capabilities:["stabilization"]`, or contain the new field in its validated settings. Support is known before saved-profile transmission and reset every connection generation. An initial ten-field hello plus capability is valid, but current clients obtain the full eleven-field snapshot before adopting initial values / sending no-sensor fallback. iOS bounds this supplemental wait to ten seconds. Partial updates or acknowledgments cannot replace this first full snapshot.

Without either support signal, clients strip stabilization only from outbound network settings and preserve the full local profile. Legacy full / partial replies merge into the local base without zeroing an omitted stabilization value. Legacy clients get ten fields unless opting in. Complete persisted / handshake profiles accept exactly legacy ten or new eleven fields; legacy migration adds zero. Partial settings stay nonempty, known-key and range validated. See [stabilization](STABILIZATION.md).

Positive smoothing runs only in the host's first-person pose-to-mouse path. Phones keep the same pose format without duplicate filtering. The host measures its own high-resolution elapsed time; no timestamp is added to v1. Zero bypass, raw-jump rejection, stale-pose stop, editor disarm, F8 and explicit authorization remain. Settings messages cannot arm input.

---

<!-- vrization:chinese -->
## 简体中文

v0.3.3 候选保留集成**协议 v1**：传输二维 JPEG 帧和 JSON 控制消息。Android 与 iOS 经局域网或各自 USB 适配器使用相同消息。它不是 OpenXR 或立体视频协议；安装和设备授权见 [USB 教程](USB.md)。

### 局域网 WebSocket 连接

```text
ws://<电脑局域网 IP>:8765/ws?token=<六位配对码>&settingsSchema=2
```

主机默认监听 `0.0.0.0:8765`，一次只接受一个客户端。配对码在启动服务时生成，保留开头的零。错误码为 `401`（配对错误）、`409`（已有客户端）和 `429`（配对尝试过多，等待约一分钟）。配对失败有每地址与全局速率限制。

`GET /health` 返回主机名、版本、协议号和连接状态，不需要配对码，也不返回桌面帧。它仅用于基本连通性检查。

`ws://` 没有加密。配对码在 URL 查询参数中传递，不应写入公开日志。服务仅用于可信局域网。手机默认优先 USB，也可显式选择局域网配对。

### Android USB 发现

Windows 界面可启用 `UsbManager`，检测已授权的真实 Android USB 设备，并建立 `adb -s <serial> reverse --no-rebind tcp:18765 tcp:<hostport>`，不替换已有映射。排除模拟器、IP / 端口和无线 mDNS 连接；ADB 报告未知路径时，Windows 原生 SetupAPI 提供真实 USB 设备证据。只有唯一、明确选中的安卓设备会自动建立映射，手机自动启动可等待已有串流；手机／电脑主动连接可经独立控制路径请求启动。

手机请求 `GET http://127.0.0.1:18765/usb-bootstrap`：

```json
{"v":1,"name":"VRization","version":"0.3.2","port":8765,"token":"001234"}
```

`port` 说明电脑监听端口，**不改变**手机目的端口；手机随后以普通 v1 协议连接 `ws://127.0.0.1:18765/ws?token=001234&settingsSchema=2`。示例 token 为虚构。响应含 `Cache-Control: no-store`、`X-Content-Type-Options: nosniff`。请求必须来自回环地址，仅含一个 `Host`，主机为 `127.0.0.1`、`localhost` 或 `[::1]`，端口为电脑端口或反向端口 `18765`，不能含 `Origin`，并且 manager 必须拥有已授权的真实 USB 映射。拒绝返回 `403`；服务可达但已停止返回 `503`，监听停止时通常直接拒绝 TCP 连接。普通 `HostServer` 嵌入默认关闭 bootstrap，须显式提供授权回调；接口不授予 CORS 访问。

### Android 主动 USB 控制（v0.3.3 候选）

`ConnectionCoordinator` 独立于采集管理请求身份。电脑仅在 `127.0.0.1:18764` 监听 `UsbConnectService`，自有不重新绑定的 reverse 将手机 `18764` 映射到它。手机主动连接发送一次空 body `POST http://127.0.0.1:18764/connect`，再走普通 `18765` 视频 bootstrap；自动等待、bootstrap 轮询、socket 重试不重复请求。路由要求回环 peer、仅一个带控制端口的字面回环 Host、无 Origin 和独立验证的真实 USB 控制映射；不传 token 或目标。200 返回 `{"v":1,"name":"VRization","ready":true}`，拒绝 403，不可用／八秒启动失败 503；GUI 拒绝已停止或过期身份，视频 bootstrap 独立鉴权。

电脑主动连接经同一协调器启动主机，对选中设备发送一次 Activity 请求（`vrization_connect_usb`）；intent extra 只消费一次，重复请求保留活动会话。定时检测不启动或唤醒手机。停止使排队请求、视频／socket 身份失效，旧重试或 intent 不能恢复已停止会话。

### iOS USB 分帧

iOS 前台在手机回环 `127.0.0.1:18767` 保留控制，主动连接才开放视频 `127.0.0.1:18766`。Windows 经本地 usbmux（`127.0.0.1:27015`）枚举设备，任一路连接前均要求只读已有 `ReadPairRecord`。电脑连接动作对 `18767` 发送一次 framed 类型 1 `{"v":1,"type":"connect"}`；控制仅接受这两个字段、整数 v1 和 connect 或 stop 类型，不授予输入或允许选择采集目标。活动会话忽略重复控制；视频断开后保留控制，后台／销毁停止。Windows 不能启动后台观看端。

电脑停止先限制待处理中继启动、关闭已有视频，并发送一次已配对控制 `{"v":1,"type":"stop"}`。原生主队列关闭视频／socket，使解码状态失效并清渲染器，再回复 `{"v":1,"type":"stopped"}`；前台控制仍保留。`request_ios_stop` 要求两秒内收到有限长确认。只有确认或独立已配对的视频端口明确拒绝可解除停止门控；信任／服务错误不能证明监听消失。旧通知／端口结果核对停止代际。通知有限等待，新电脑主动连接可替代停止请求，检测不因超时自行解除；这也能关闭已开放但从未接受 peer 的视频监听。

视频接受唯一 peer 后，手机在收到 host hello 前发送同样就绪帧。`IosRelay` 两秒内要求就绪，主机已运行也消费它，不将其转成 host 消息；合法就绪才可经注入协调器请求已停止主机，最多八秒等待同一请求身份和启动。取消／超时使待处理身份失败、关闭已配对 peer，后续其他动作不能满足旧请求。旧监听已占用时拒第二 peer、没有就绪，仅 TCP 接受不能开始采集。候选预握手需要匹配原生观看端，无就绪的旧 iOS USB 端不兼容新中继；LAN v1 消息兼容不变。

随后中继使用当前 token 鉴权主机本机 WebSocket、桥接普通消息。iOS 不输入码，自动选择只接一台 Apple 设备。VRization 不发 Pair／Trust／SavePairRecord，不记录／保存其中密钥。

隧道内每个 VRization 帧为：

```text
4 字节无符号大端长度 | 1 字节类型 | 内容
```

长度包含类型字节、不包含四字节头，有效范围 `1…8 MiB`。类型 `1` 为 UTF-8 v1 JSON，类型 `2` 为一个 JPEG；JSON 内容最多 16 KiB，手机向主机只发 JSON。分配内容前先拒绝非法长度 / 类型；支持分段头、分段内容及一次读取多个帧。首条主机 JSON 为普通 `hello`，应用收到合法握手才认为连接成功。任意一侧关闭会关闭中继 WebSocket，并撤销主机输入授权。此分帧独立于 usbmux 自身的小端 plist 服务协议，不改变 WebSocket v1。

全新 Android 启动可等待已有串流，全新 iOS 仅开放前台控制；受支持任一端主动连接可建立 USB，后台、切换语言和断线使视频失效，需再次主动连接。新增候选原生检查待完成，历史 iOS 证据只包含模拟 usbmux 和原生模拟器，不代表真实 iPhone／Apple 驱动。见按版本记录的[验证](VALIDATION.md)。

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
  "version": "0.3.2",
  "revision": 0,
  "capabilities": ["stabilization"],
  "settings": {
    "mode": "full", "scale": 0.85, "offsetX": 0.0, "offsetY": 0.0,
    "eyeSeparation": 0.03, "fov": 80.0, "distance": 3.0,
    "distortion": 0.0, "sensitivity": 1000.0, "stabilization": 0.0, "invertY": false
  },
  "stream": {"codec": "jpeg", "fps": 60, "maxWidth": 640},
  "mouseArmed": false
}
```

`stream` 数值仅为示例，以主机当次配置为准。`maxWidth` 保留 v1 字段名，表示输出宽度上限；当前主机也把该数值作为**最长边**限制，以控制竖屏帧的解码负担。例如 2160 × 3840 的源画面在限值 640 下输出 360 × 640。客户端应以实际 JPEG 尺寸渲染，不根据该上限猜测帧的纵横比。GPU 裁切 / 旋转 / 缩放改变主机实现，不改变 JPEG 内容或协议版本；静态刷新包可能重复自有 JPEG，v1 没有传输采集时间戳或不同帧计数。

先校验 `hello` 再建立会话。v0.3 手机若有保存的已提交 VR 配置，再用新的 `clientSeq` 一次发送完整配置，用户本地偏好明确替代主机初始值；没有保存配置时采用合法初始配置快照；支持防抖的旧格式 USB hello 需先取得下方说明的 schema-2 快照。后续确认 / 电脑广播按下面的 revision 规则处理。可选客户端握手：

两种当前手机客户端在 LAN / USB 都等待合法 v1 `hello` 才显示已连接，主机握手期限为十秒。仅 socket 打开不代表会话已建立；非法 / 不支持的主机消息会断开。此客户端门控不是新的服务端协议版本。

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
| `mode` | `full` / `cinema` / `fps` | `full` | 全屏 / 虚拟大屏幕 / 第一人称鼠标模式。 |
| `scale` | 0.5–1.0 | 0.85 | 每眼有效画面的缩放。 |
| `offsetX` | -0.3–0.3 | 0 | 归一化水平偏移。 |
| `offsetY` | -0.3–0.3 | 0 | 归一化垂直偏移。 |
| `eyeSeparation` | −1–0.2 | 0.03 | 有符号显示间距，平面适配受动态接触边界限制；不是米或自动测量瞳距。 |
| `fov` | 50–110 | 80 | 视场角，度。 |
| `distance` | 1–8 | 3 | 虚拟屏幕距离，渲染场景单位。 |
| `distortion` | 0–0.5 | 0 | 镜片畸变系数。 |
| `sensitivity` | 100–3000 | 1000 | 第一人称鼠标位移 / 弧度比例。 |
| `stabilization` | 0–1 | 0 | 主机第一人称防抖，0 精确绕过；仅 schema 2。 |
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

第一人称控制需要有效会话、`mode: fps`、近期姿态和电脑端主动授权。当前姿态心跳超时为 0.5 秒；授权后需在五秒内切到目标窗口，之后切换焦点会解除授权。输出还限制单次鼠标位移。没有远程 `arm` 消息；集成时应保留此边界。

### 心跳、错误与关闭

```json
{"v":1,"type":"ping"}
```

```json
{"v":1,"type":"pong"}
```

手机显示接收帧率和应用 ping 往返时间，两者都不测量端到端视频延迟：ping 不包括采集、编码、解码与呈现。电脑界面新用户低延迟预设为最长边 640、目标 60 FPS、JPEG 质量 45；稳定为 640 / 30 / 50，画质为 960 / 30 / 60；已有保存配置继续生效。预设是捕获目标，不改变协议版本，也不承诺测得的延迟。详见 [性能指标与队列边界](PERFORMANCE.md)。

协议错误时主机返回 `{"v":1,"type":"error","message":"..."}`。客户端文本消息最多 16 KiB；持续无效消息或超过消息速率会以 `1008` 关闭。客户端发送二进制消息会以 `1003` 关闭。主机停止或帧发送阻塞时可使用 `1001` 关闭。WebSocket ping / pong 还用于连接保活，不能替代 第一人称姿态心跳。

### 兼容性原则

添加不同编码、原生左右眼帧、时间戳或更强认证时应升级协议并显式协商。v1 客户端不应猜测不认识的二进制内容。`mouseArmed` 是初始状态提示，不是手机的授权能力。


### 编辑草稿与本地保存配置（v0.3）

这是客户端 / 界面策略，不新增协议类型。预览平移 / 缩放只在本地，编辑期间不发 `settings`、`pose`，不写偏好；无畸变平面预览保留原模式与其他光学值。手机保存提交完整草稿，已连接时发送一次普通设置更新；电脑只对最新主机状态更新 scale / offsetX / offsetY / eyeSeparation，保留其他字段并发变化。放弃恢复本地进入预览，不发送。退出编辑不授权鼠标，手机后台 / 断线会放弃草稿。

手机保存全部已提交 VR 字段，包括离线更改，不保存配对秘密。每次合法主机 hello 后，通过带新 clientSeq 的普通完整 settings 一次恢复本地配置；不得重放旧 socket 任务、跳过校验或为此重置 revision。后续接受的完整快照正常更新本地配置。此用户明确要求的持久化策略，在 v0.3 客户端替代先前优先主机初始设置的策略；旧 v1 客户端保持原行为。

电脑或手机已连接的保存经设置 / 确认 / 广播传播，两端保留接受状态；离线变化只在本地。若两边离线冲突，重连时已保存手机配置优先，电脑可随后再保存；不比较时间戳 / 时钟、不自动合并、不新增冲突协议类型。编辑器横向拖动根据选中眼符号（左 −1、右 +1）更新已有 eyeSeparation，在剩余间隙允许时围绕共用 X 镜像联动；竖向更新共用 offsetY。左眼向左 / 右眼向右拉开，反向收拢；平面解析采用 h=fit.x×scale、间距=clamp(raw,h−1,.2)、gap=max(0,1+间距−h)、X=clamp(rawX,±min(.3,gap))；接触时 X 居中，放大时可能向外调整间距，普通角点方向与 第一人称映射不变。纯渲染约束不改写原始已存设置。负值需两端均为 v0.3，v0.2 只接受 0…0.2；已有非负配置仍有效。接缝几何只保证无畸变平面预览 / 全屏 / 第一人称，不含大屏幕或畸变视图。

重置恢复标准 Settings 默认、英文与 USB；手机清除连接偏好并断线，当前界面不自动重连；全新 Android 可等待已有串流，iOS 仅开放前台控制，合法 hello 后恢复已提交默认值。主机还恢复采集 640 / 60 / Q45，但保留明确显示器 / 选区和 ADB 工具路径；已连接更新仍经过普通设置校验，不新增远程 reset / arm 消息。见 [几何与重置范围](EDITING.md)。


### 只解除授权的编辑元数据（v0.3）

```json
{"v":1,"type":"hello","editing":true}
```

手机进入编辑器时停止新姿态、丢弃应用层待发姿态（已提交传输层字节无法撤回），在已校验连接上一次发送。可选 `editing` 必须为 JSON 布尔值，true 让当前主机收到后立即解除授权；false 或省略均不授权。这是已有 v1 hello 的元数据，不是草稿设置更新或第四模式；旧主机可忽略，暂停姿态仍触发其看门狗。编辑期间可继续视频 / ping，正常退出仍可回正；保存或放弃不发送授权请求，用户须重新在电脑主动授权。

### 兼容配置协商（v0.3.2）

传输仍为 `v:1`，配置 schema 2 将防抖加为第十一个字段。当前局域网 / Android USB 地址用 `settingsSchema=2` 主动选择；iOS 中继初始认证用旧地址，手机发 `{"v":1,"type":"hello","settingsSchema":2}`。当前主机返回完整十一字段 **settings**，带当前 revision、不带 clientSeq；不是第二次主机 hello，也不增加 revision。

合法主机 hello 可声明 `capabilities:["stabilization"]`，或校验后的配置含新字段。支持能力在恢复手机配置前确定，每次连接代次重置。初始十字段 hello 加能力合法，但当前客户端先取得完整十一字段快照，再接纳值 / 发送缺传感器回退；iOS 额外等待最长十秒，部分更新或确认不能替代首个完整快照。

都没有支持信号时，客户端只从出站网络设置去掉防抖，本地完整值保留；旧完整 / 部分回复基于当前本地值合并，不因缺字段而清零。旧客户端未主动选择时收到十字段。完整保存 / 握手只接受恰好十字段旧格式或十一字段新格式，旧迁移防抖添加零；部分设置仍须非空、字段已知并校验范围。见 [防抖](STABILIZATION.md)。

正防抖只在主机第一人称姿态转鼠标路径执行，手机不改姿态格式、不重复滤波；主机计自身高精度间隔，v1 不加时间戳。零绕过、原始跳变拒绝、姿态超时、编辑解除、F8、主动授权保留，设置消息不能授权输入。

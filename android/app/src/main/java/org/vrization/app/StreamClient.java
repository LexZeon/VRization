package org.vrization.app;

import android.graphics.Bitmap;
import android.content.Context;
import android.graphics.BitmapFactory;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import java.io.IOException;
import java.io.InputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.net.Proxy;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import okhttp3.HttpUrl;
import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;
import okio.ByteString;
import org.json.JSONException;
import org.json.JSONObject;
import org.vrization.core.VrSettings;
import org.vrization.core.SocketAttempt;
import org.vrization.core.UsbConnectionAttempt;
import org.vrization.core.TransportEndpoints;

/** Latest-only JPEG transport. At most one compressed frame waits behind the active decode. */
final class StreamClient {
    interface Listener {
        void onSessionStarted();
        void onSessionStopped();
        void onStatus(String text, boolean connected);
        void onSettings(JSONObject json, Long revision, Long clientSeq);
        void onRoundTrip(long milliseconds);
        /** Decoder-thread handoff only: ownership transfers; do not manipulate UI here. */
        void onFrame(Bitmap bitmap, long session, long receivedAtNanos);
        void onDecodedStats(int width, int height, double fps);
        void onProcessingStats(double milliseconds);
    }
    private final Listener listener;
    private final Context context;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final SessionDispatcher sessions = new SessionDispatcher(action -> main.post(action));
    private final OkHttpClient http = new OkHttpClient.Builder()
        .connectTimeout(8, TimeUnit.SECONDS).readTimeout(0, TimeUnit.SECONDS)
        .pingInterval(10, TimeUnit.SECONDS).build();
    // The cable endpoint is phone loopback, independent of the LAN/system HTTP proxy.
    private final OkHttpClient usbHttp = http.newBuilder().proxy(Proxy.NO_PROXY)
        .connectTimeout(2, TimeUnit.SECONDS).followRedirects(false).followSslRedirects(false)
        .retryOnConnectionFailure(false).build();
    private final OkHttpClient discoveryHttp = usbHttp.newBuilder().connectTimeout(2, TimeUnit.SECONDS)
        .readTimeout(2, TimeUnit.SECONDS).callTimeout(3, TimeUnit.SECONDS)
        .followRedirects(false).followSslRedirects(false).retryOnConnectionFailure(false).build();
    private final ExecutorService decoder = Executors.newSingleThreadExecutor();
    private final Object decodeLock = new Object();
    private final AtomicLong poseSequence = new AtomicLong();
    private final AtomicLong deliveredFrames = new AtomicLong();
    private volatile WebSocket socket;
    private volatile boolean connected;
    private volatile boolean connecting;
    private volatile boolean stabilizationSupported;
    private Call discovery;
    private Runnable helloDeadline;
    private Runnable usbRetry, usbDeadline;
    private String usbFailureStatus;
    private final UsbConnectionAttempt usbAttempt = new UsbConnectionAttempt();
    private final SocketAttempt socketAttempt = new SocketAttempt();
    private final PingTracker ping = new PingTracker();
    private final PhoneFrameStats frameStats = new PhoneFrameStats();
    private final PoseSendGate poseGate = new PoseSendGate();
    private final Runnable pingTick = new Runnable() {
        @Override public void run() {
            if (!connected || sessions.isClosed()) return;
            long now = SystemClock.elapsedRealtime();
            if (ping.shouldSend(now) && send(message("ping"))) ping.sent(now);
            main.postDelayed(this, 2000);
        }
    };
    private byte[] pendingJpeg;
    private long pendingEpoch, pendingSocketEpoch;
    private long pendingReceivedAt;
    private boolean decoding;

    StreamClient(Context context, Listener listener) { this.context = context; this.listener = listener; }
    boolean isConnected() { return connected; }
    boolean isConnecting() { return connecting; }
    boolean isActive() { return connected || connecting; }
    boolean isAutomaticUsbAttempt() { return usbAttempt.isAutomatic(); }
    boolean supportsStabilization() { return stabilizationSupported; }
    /** Phone-local diagnostic: counts real decoded frames handed to the view during this instance. */
    long deliveredFrameCount() { return deliveredFrames.get(); }

    void connect(String host, int port, String code) {
        disconnect(false);
        if (sessions.isClosed()) return;
        final long connectionEpoch = sessions.invalidate();
        connecting = true;
        openSocket(host, port, code, connectionEpoch, false);
    }

    void connectUsb() { connectUsb(UsbConnectionAttempt.Source.AUTOMATIC); }
    void connectUsb(UsbConnectionAttempt.Source source) {
        disconnect(false);
        if (sessions.isClosed()) return;
        final long connectionEpoch = sessions.invalidate();
        connecting = true;
        usbAttempt.start(connectionEpoch, SystemClock.elapsedRealtime(), source);
        usbFailureStatus = context.getString(R.string.usb_not_detected);
        usbDeadline = () -> expireUsbAttempt(connectionEpoch);
        main.postDelayed(usbDeadline, UsbConnectionAttempt.WINDOW_MILLIS);
        listener.onStatus(context.getString(R.string.usb_detecting), false);
        if (usbAttempt.takeHostWake(connectionEpoch, SystemClock.elapsedRealtime())) wakeUsbHost(connectionEpoch);
        else discoverUsb(connectionEpoch);
    }

    private void wakeUsbHost(long connectionEpoch) {
        discovery = discoveryHttp.newCall(new Request.Builder().url(TransportEndpoints.USB_CONNECT)
            .post(RequestBody.create(new byte[0], null)).build());
        discovery.enqueue(new Callback() {
            @Override public void onFailure(Call call, IOException failure) { continueUsbDiscovery(connectionEpoch); }
            @Override public void onResponse(Call call, Response response) {
                // No token or destination is accepted here; normal bootstrap validates the video host.
                response.close(); continueUsbDiscovery(connectionEpoch);
            }
        });
    }
    private void continueUsbDiscovery(long connectionEpoch) {
        sessions.dispatch(connectionEpoch, () -> {
            discovery = null;
            if (usbAttempt.remaining(connectionEpoch, SystemClock.elapsedRealtime()) == 0) expireUsbAttempt(connectionEpoch);
            else discoverUsb(connectionEpoch);
        });
    }

    private void discoverUsb(long connectionEpoch) {
        if (!sessions.isCurrent(connectionEpoch)
            || !usbAttempt.beginDiscovery(connectionEpoch, SystemClock.elapsedRealtime())) return;
        discovery = discoveryHttp.newCall(new Request.Builder().url(UsbBootstrap.ENDPOINT).get().build());
        discovery.enqueue(new Callback() {
            @Override public void onFailure(Call call, IOException failure) {
                retryUsb(connectionEpoch, context.getString(R.string.usb_not_detected));
            }
            @Override public void onResponse(Call call, Response response) {
                try (Response result = response) {
                    if (!result.isSuccessful()) {
                        retryUsb(connectionEpoch, context.getString(result.code() == 403 ? R.string.usb_not_authorized
                            : result.code() == 503 ? R.string.usb_host_stopped : R.string.usb_not_detected));
                        return;
                    }
                    if (result.body() == null) throw new IllegalArgumentException("Empty discovery response");
                    String text;
                    try (InputStream input = result.body().byteStream(); ByteArrayOutputStream output = new ByteArrayOutputStream()) {
                        byte[] buffer = new byte[1024]; int size;
                        while ((size = input.read(buffer)) != -1) {
                            if (output.size() + size > 4096) throw new IllegalArgumentException("Oversized discovery response");
                            output.write(buffer, 0, size);
                        }
                        text = new String(output.toByteArray(), StandardCharsets.UTF_8);
                    }
                    JSONObject json = new JSONObject(text);
                    Map<String, Object> fields = new HashMap<>();
                    Iterator<String> keys = json.keys();
                    while (keys.hasNext()) { String key = keys.next(); fields.put(key, json.get(key)); }
                    UsbBootstrap bootstrap = UsbBootstrap.parse(fields);
                    sessions.dispatch(connectionEpoch, () -> {
                        discovery = null;
                        if (!usbAttempt.beginSocket(connectionEpoch, SystemClock.elapsedRealtime())) {
                            if (usbAttempt.isActive(connectionEpoch) && usbAttempt.remaining(connectionEpoch, SystemClock.elapsedRealtime()) == 0)
                                expireUsbAttempt(connectionEpoch);
                            return;
                        }
                        if (usbRetry != null) main.removeCallbacks(usbRetry); usbRetry = null;
                        usbFailureStatus = context.getString(R.string.connection_failed, context.getString(R.string.check_usb_connection));
                        // Never save pairing material and never trust a remote host/port from discovery.
                        openSocket(UsbBootstrap.HOST, UsbBootstrap.FORWARDED_PORT, bootstrap.token, connectionEpoch, true);
                    });
                } catch (IOException ignored) {
                    retryUsb(connectionEpoch, context.getString(R.string.usb_not_detected));
                } catch (JSONException | IllegalArgumentException ignored) {
                    ended(connectionEpoch, context.getString(R.string.usb_invalid_response));
                }
            }
        });
    }

    private void retryUsb(long connectionEpoch, String failureStatus) {
        sessions.dispatch(connectionEpoch, () -> {
            discovery = null;
            long now = SystemClock.elapsedRealtime();
            long delay = usbAttempt.discoveryFailed(connectionEpoch, now);
            if (delay < 0) {
                if (usbAttempt.isActive(connectionEpoch) && usbAttempt.remaining(connectionEpoch, now) == 0)
                    expireUsbAttempt(connectionEpoch);
                return;
            }
            scheduleUsbRetry(connectionEpoch, delay, failureStatus);
        });
    }
    private void scheduleUsbRetry(long connectionEpoch, long delay, String failureStatus) {
        usbFailureStatus = failureStatus;
        listener.onStatus(context.getString(R.string.usb_waiting), false);
        if (usbRetry != null) main.removeCallbacks(usbRetry);
        usbRetry = () -> {
            usbRetry = null;
            if (!sessions.isCurrent(connectionEpoch)) return;
            if (usbAttempt.remaining(connectionEpoch, SystemClock.elapsedRealtime()) == 0) expireUsbAttempt(connectionEpoch);
            else discoverUsb(connectionEpoch);
        };
        main.postDelayed(usbRetry, delay);
    }
    private void expireUsbAttempt(long connectionEpoch) {
        if (!sessions.isCurrent(connectionEpoch) || !usbAttempt.isActive(connectionEpoch)) return;
        String status = usbFailureStatus;
        disconnect(false);
        listener.onStatus(status, false);
    }
    private void stopUsbAttempt() {
        usbAttempt.cancel();
        if (usbRetry != null) main.removeCallbacks(usbRetry); usbRetry = null;
        if (usbDeadline != null) main.removeCallbacks(usbDeadline); usbDeadline = null;
    }

    private void openSocket(String host, int port, String code, long connectionEpoch, boolean usb) {
        HttpUrl url = new HttpUrl.Builder().scheme("http").host(host).port(port)
            .addPathSegment("ws").addQueryParameter("token", code).addQueryParameter("settingsSchema", "2").build();
        listener.onStatus(context.getString(R.string.connecting), false);
        final HostSessionGate handshake = new HostSessionGate();
        final long socketEpoch = socketAttempt.start();
        socket = (usb ? usbHttp : http).newWebSocket(new Request.Builder().url(url).build(), new WebSocketListener() {
            @Override public void onOpen(WebSocket webSocket, Response response) {
                dispatchSocket(connectionEpoch, socketEpoch, () -> {
                    helloDeadline = () -> {
                        if (!connected) socketEnded(connectionEpoch, socketEpoch,
                            context.getString(R.string.invalid_host_protocol), usb);
                    };
                    main.postDelayed(helloDeadline, 10000);
                    try {
                        JSONObject hello = message("hello").put("client", "android").put("device", Build.MODEL)
                            .put("settingsSchema", 2);
                        webSocket.send(hello.toString());
                    } catch (JSONException ignored) { }
                });
            }
            @Override public void onMessage(WebSocket webSocket, String text) {
                if (!sessions.isCurrent(connectionEpoch) || !socketAttempt.isCurrent(socketEpoch)) return;
                try {
                    if (text.length() > 65536) throw new IllegalArgumentException("Oversized host message");
                    JSONObject json = new JSONObject(text);
                    boolean established = handshake.receive(SettingsJson.fields(json));
                    final boolean supportsStabilization = handshake.supportsStabilization();
                    String type = json.optString("type");
                    if (established) {
                        dispatchSocket(connectionEpoch, socketEpoch, () -> {
                            if (usbAttempt.isActive(connectionEpoch)
                                && !usbAttempt.established(connectionEpoch, SystemClock.elapsedRealtime())) {
                                expireUsbAttempt(connectionEpoch); return;
                            }
                            stopUsbAttempt();
                            if (helloDeadline != null) main.removeCallbacks(helloDeadline);
                            helloDeadline = null; connected = true; connecting = false;
                            // Establish capability before the saved profile is sent by this callback.
                            stabilizationSupported = supportsStabilization;
                            frameStats.newSession(connectionEpoch);
                            ping.reset(); main.removeCallbacks(pingTick); main.post(pingTick);
                            listener.onSessionStarted();
                            listener.onSettings(json.optJSONObject("settings"), optionalSequence(json, "revision"), null);
                            listener.onStatus(context.getString(R.string.connected), true);
                        });
                    } else if ("settings".equals(type)) {
                        JSONObject incoming = json.getJSONObject("settings");
                        dispatchSocket(connectionEpoch, socketEpoch, () -> {
                            stabilizationSupported |= supportsStabilization;
                            listener.onSettings(incoming, optionalSequence(json, "revision"), optionalSequence(json, "clientSeq"));
                        });
                    } else if ("error".equals(type)) {
                        dispatchSocket(connectionEpoch, socketEpoch, () -> listener.onStatus(context.getString(
                            R.string.host_error, json.optString("message", context.getString(R.string.connection_error))), connected));
                    } else if ("pong".equals(type)) {
                        dispatchSocket(connectionEpoch, socketEpoch, () -> {
                            Long milliseconds = ping.pong(SystemClock.elapsedRealtime());
                            if (milliseconds != null) listener.onRoundTrip(milliseconds);
                        });
                    }
                } catch (JSONException | IllegalArgumentException ignored) {
                    handshake.fail();
                    socketEnded(connectionEpoch, socketEpoch, context.getString(R.string.invalid_host_protocol), false);
                }
            }
            @Override public void onMessage(WebSocket webSocket, ByteString bytes) {
                if (!sessions.isCurrent(connectionEpoch) || !socketAttempt.isCurrent(socketEpoch)) return;
                try { handshake.receiveJpeg(bytes.size()); }
                catch (IllegalArgumentException ignored) {
                    socketEnded(connectionEpoch, socketEpoch, context.getString(R.string.invalid_host_protocol), false); return;
                }
                long receivedAt = SystemClock.elapsedRealtimeNanos();
                queueJpeg(bytes.toByteArray(), connectionEpoch, socketEpoch, receivedAt);
            }
            @Override public void onClosed(WebSocket webSocket, int code, String reason) {
                socketEnded(connectionEpoch, socketEpoch, context.getString(R.string.connection_ended, code),
                    usb && code != 1008);
            }
            @Override public void onClosing(WebSocket webSocket, int code, String reason) { webSocket.close(code, reason); }
            @Override public void onFailure(WebSocket webSocket, Throwable failure, Response response) {
                String detail = context.getString(usb ? R.string.check_usb_connection : R.string.check_connection);
                boolean retry = usb && (response == null || response.code() == 401 || response.code() == 403
                    || response.code() == 409 || response.code() >= 500);
                if (response != null) {
                    if (response.code() == 401 || response.code() == 403) detail = context.getString(R.string.bad_pairing);
                    else if (response.code() == 409) detail = context.getString(R.string.headset_busy);
                    else if (response.code() == 429) detail = context.getString(R.string.rate_limited);
                }
                socketEnded(connectionEpoch, socketEpoch, context.getString(R.string.connection_failed, detail), retry);
            }
        });
        socketAttempt.attach(socketEpoch, socket::cancel);
    }

    private void dispatchSocket(long connectionEpoch, long socketEpoch, Runnable action) {
        sessions.dispatch(connectionEpoch, () -> socketAttempt.deliverCurrent(socketEpoch, action));
    }

    private void socketEnded(long connectionEpoch, long socketEpoch, String status, boolean retry) {
        dispatchSocket(connectionEpoch, socketEpoch, () -> {
            if (retry && !connected && usbAttempt.isActive(connectionEpoch)) {
                long delay = usbAttempt.socketFailed(connectionEpoch, SystemClock.elapsedRealtime());
                closeSocket();
                if (delay >= 0) { scheduleUsbRetry(connectionEpoch, delay, status); return; }
            }
            disconnect(false);
            listener.onStatus(status, false);
        });
    }

    private void closeSocket() {
        if (helloDeadline != null) main.removeCallbacks(helloDeadline); helloDeadline = null;
        socketAttempt.cancel();
        socket = null;
    }

    private void ended(long connectionEpoch, String status) {
        sessions.dispatch(connectionEpoch, () -> {
            disconnect(false);
            listener.onStatus(status, false);
        });
    }

    private static Long optionalSequence(JSONObject json, String key) {
        Object value = json.opt(key);
        if (!(value instanceof Number)) return null;
        double number = ((Number) value).doubleValue();
        return !Double.isNaN(number) && !Double.isInfinite(number) && number >= 0
            && number <= 9007199254740991d && number == Math.floor(number) ? (long) number : null;
    }

    private void queueJpeg(byte[] jpeg, long connectionEpoch, long socketEpoch, long receivedAt) {
        synchronized (decodeLock) {
            if (!sessions.isCurrent(connectionEpoch) || !socketAttempt.isCurrent(socketEpoch)) return;
            pendingJpeg = jpeg; pendingEpoch = connectionEpoch; pendingSocketEpoch = socketEpoch; pendingReceivedAt = receivedAt;
            if (decoding) return;
            decoding = true;
            try { decoder.execute(this::decodeLatest); }
            catch (RejectedExecutionException ignored) { decoding = false; pendingJpeg = null; }
        }
    }

    private void decodeLatest() {
        while (true) {
            byte[] jpeg;
            long frameEpoch, frameSocketEpoch, receivedAt;
            synchronized (decodeLock) {
                jpeg = pendingJpeg; frameEpoch = pendingEpoch; frameSocketEpoch = pendingSocketEpoch;
                receivedAt = pendingReceivedAt; pendingJpeg = null;
                if (jpeg == null || sessions.isClosed()) { decoding = false; return; }
            }
            if (!sessions.isCurrent(frameEpoch) || !socketAttempt.isCurrent(frameSocketEpoch) || !connected) continue;
            BitmapFactory.Options options = new BitmapFactory.Options();
            options.inJustDecodeBounds = true;
            BitmapFactory.decodeByteArray(jpeg, 0, jpeg.length, options);
            if (options.outWidth <= 0 || options.outHeight <= 0) continue;
            options.inJustDecodeBounds = false; options.inSampleSize = 1;
            // A malicious or accidental giant JPEG must not exhaust a phone's memory.
            while (options.outWidth / options.inSampleSize > 4096 || options.outHeight / options.inSampleSize > 4096
                || (long)(options.outWidth / options.inSampleSize) * (options.outHeight / options.inSampleSize) > 8_000_000L) {
                options.inSampleSize *= 2;
            }
            options.inPreferredConfig = Bitmap.Config.RGB_565;
            Bitmap bitmap;
            try { bitmap = BitmapFactory.decodeByteArray(jpeg, 0, jpeg.length, options); }
            catch (OutOfMemoryError ignored) { continue; }
            if (bitmap != null) {
                publishBitmap(bitmap, frameEpoch, frameSocketEpoch, receivedAt);
            }
        }
    }

    private void publishBitmap(Bitmap bitmap, long frameEpoch, long frameSocketEpoch, long receivedAt) {
        // The renderer has its own one-slot handoff. Avoid waiting behind UI work,
        // while serializing this short transfer with disconnect/session invalidation.
        boolean delivered = sessions.deliverCurrent(frameEpoch, () -> {
            boolean currentSocket = socketAttempt.deliverCurrent(frameSocketEpoch, () -> {
                if (!connected) { bitmap.recycle(); return; }
                int width = bitmap.getWidth(), height = bitmap.getHeight();
                listener.onFrame(bitmap, frameEpoch, receivedAt);
                deliveredFrames.incrementAndGet();
                Double fps = frameStats.decoded(frameEpoch, SystemClock.elapsedRealtimeNanos());
                if (fps != null) dispatchSocket(frameEpoch, frameSocketEpoch, () -> listener.onDecodedStats(width, height, fps));
            });
            if (!currentSocket) bitmap.recycle();
        });
        if (!delivered) bitmap.recycle();
    }
    void recordTextureSubmission(long frameEpoch, long receivedAt, long submittedAt) {
        sessions.deliverCurrent(frameEpoch, () -> {
            Double milliseconds = frameStats.uploaded(frameEpoch, receivedAt, submittedAt);
            if (milliseconds != null) sessions.dispatch(frameEpoch, () -> listener.onProcessingStats(milliseconds));
        });
    }
    private void clearPending() {
        synchronized (decodeLock) {
            pendingJpeg = null;
        }
        frameStats.clear();
    }
    boolean sendSettings(VrSettings settings, long sequence) {
        try { return send(message("settings").put("settings", SettingsJson.encodeForHost(settings, stabilizationSupported))
            .put("clientSeq", sequence)); }
        catch (JSONException ignored) { return false; }
    }
    void sendPose(float yaw, float pitch) {
        WebSocket current = socket;
        if (current == null || !poseGate.maySend(connected, current.queueSize())) return;
        if (Float.isNaN(yaw) || Float.isInfinite(yaw) || Float.isNaN(pitch) || Float.isInfinite(pitch)) return;
        try { send(message("pose").put("seq", poseSequence.incrementAndGet()).put("yaw", yaw).put("pitch", pitch)); }
        catch (JSONException ignored) { }
    }
    void setPoseEnabled(boolean enabled) { poseGate.setEnabled(enabled); }
    boolean pauseForEditor() {
        poseGate.setEnabled(false);
        if (!connected) return true;
        try {
            if (send(message("hello").put("editing", true))) return true;
        } catch (JSONException ignored) { }
        // If the disarm-only signal cannot be queued, disconnect instead of
        // retaining control authorization across a stalled editor transition.
        disconnect(true); return false;
    }
    void recenter() { send(message("recenter")); }
    private static JSONObject message(String type) {
        JSONObject json = new JSONObject();
        try { json.put("v", 1).put("type", type); } catch (JSONException ignored) { }
        return json;
    }
    private boolean send(JSONObject json) {
        WebSocket current = socket;
        // Drop control messages if a stalled connection already queued >64 KiB.
        return connected && current != null && current.queueSize() < 65536 && current.send(json.toString());
    }
    void disconnect(boolean report) {
        sessions.invalidate(); connected = false; connecting = false;
        stabilizationSupported = false;
        stopUsbAttempt();
        main.removeCallbacks(pingTick); ping.reset();
        Call request = discovery; discovery = null;
        if (request != null) request.cancel();
        WebSocket current = socket;
        if (current != null) current.close(1000, "Client disconnect");
        closeSocket();
        clearPending();
        listener.onSessionStopped();
        if (report && !sessions.isClosed()) listener.onStatus(context.getString(R.string.disconnected), false);
    }
    void shutdown() {
        sessions.close(); disconnect(false); decoder.shutdownNow();
        http.dispatcher().executorService().shutdown(); http.connectionPool().evictAll();
        try { if (http.cache() != null) http.cache().close(); } catch (IOException ignored) { }
    }
}

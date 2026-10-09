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
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;
import okio.ByteString;
import org.json.JSONException;
import org.json.JSONObject;
import org.vrization.core.VrSettings;

/** Latest-only JPEG transport. At most one compressed frame waits behind the active decode. */
final class StreamClient {
    interface Listener {
        void onSessionStarted();
        void onStatus(String text, boolean connected);
        void onSettings(JSONObject json, Long revision, Long clientSeq);
        void onRoundTrip(long milliseconds);
        /** Decoder-thread handoff only: ownership transfers; do not manipulate UI here. */
        void onFrame(Bitmap bitmap, long session, long receivedAtNanos);
        void onDecodedStats(int width, int height, double fps);
        void onProcessingStats(double milliseconds);
    }
    private static final int MAX_FRAME_BYTES = 8 * 1024 * 1024;
    private final Listener listener;
    private final Context context;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final SessionDispatcher sessions = new SessionDispatcher(action -> main.post(action));
    private final OkHttpClient http = new OkHttpClient.Builder()
        .connectTimeout(8, TimeUnit.SECONDS).readTimeout(0, TimeUnit.SECONDS)
        .pingInterval(10, TimeUnit.SECONDS).build();
    private final OkHttpClient discoveryHttp = http.newBuilder().connectTimeout(2, TimeUnit.SECONDS)
        .readTimeout(2, TimeUnit.SECONDS).callTimeout(3, TimeUnit.SECONDS)
        .followRedirects(false).followSslRedirects(false).retryOnConnectionFailure(false).build();
    private final ExecutorService decoder = Executors.newSingleThreadExecutor();
    private final Object decodeLock = new Object();
    private final AtomicLong poseSequence = new AtomicLong();
    private volatile WebSocket socket;
    private volatile boolean connected;
    private volatile boolean connecting;
    private Call discovery;
    private final PingTracker ping = new PingTracker();
    private final PhoneFrameStats frameStats = new PhoneFrameStats();
    private final Runnable pingTick = new Runnable() {
        @Override public void run() {
            if (!connected || sessions.isClosed()) return;
            long now = SystemClock.elapsedRealtime();
            if (ping.shouldSend(now) && send(message("ping"))) ping.sent(now);
            main.postDelayed(this, 2000);
        }
    };
    private byte[] pendingJpeg;
    private long pendingEpoch;
    private long pendingReceivedAt;
    private boolean decoding;

    StreamClient(Context context, Listener listener) { this.context = context; this.listener = listener; }
    boolean isConnected() { return connected; }
    boolean isConnecting() { return connecting; }
    boolean isActive() { return connected || connecting; }

    void connect(String host, int port, String code) {
        disconnect(false);
        if (sessions.isClosed()) return;
        final long connectionEpoch = sessions.invalidate();
        connecting = true;
        openSocket(host, port, code, connectionEpoch, false);
    }

    void connectUsb() {
        disconnect(false);
        if (sessions.isClosed()) return;
        final long connectionEpoch = sessions.invalidate();
        connecting = true;
        listener.onStatus(context.getString(R.string.usb_detecting), false);
        discovery = discoveryHttp.newCall(new Request.Builder().url(UsbBootstrap.ENDPOINT).get().build());
        discovery.enqueue(new Callback() {
            @Override public void onFailure(Call call, IOException failure) {
                ended(connectionEpoch, context.getString(R.string.usb_not_detected));
            }
            @Override public void onResponse(Call call, Response response) {
                try (Response result = response) {
                    if (!result.isSuccessful()) {
                        ended(connectionEpoch, context.getString(result.code() == 403 ? R.string.usb_not_authorized
                            : result.code() == 503 ? R.string.usb_host_stopped : R.string.usb_not_detected));
                        return;
                    }
                    if (result.body() == null) throw new IOException("Empty discovery response");
                    String text;
                    try (InputStream input = result.body().byteStream(); ByteArrayOutputStream output = new ByteArrayOutputStream()) {
                        byte[] buffer = new byte[1024]; int size;
                        while ((size = input.read(buffer)) != -1) {
                            if (output.size() + size > 4096) throw new IOException("Oversized discovery response");
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
                        // Never save pairing material and never trust a remote host/port from discovery.
                        openSocket(UsbBootstrap.HOST, UsbBootstrap.FORWARDED_PORT, bootstrap.token, connectionEpoch, true);
                    });
                } catch (IOException | JSONException | IllegalArgumentException ignored) {
                    ended(connectionEpoch, context.getString(R.string.usb_invalid_response));
                }
            }
        });
    }

    private void openSocket(String host, int port, String code, long connectionEpoch, boolean usb) {
        HttpUrl url = new HttpUrl.Builder().scheme("http").host(host).port(port)
            .addPathSegment("ws").addQueryParameter("token", code).build();
        listener.onStatus(context.getString(R.string.connecting), false);
        socket = http.newWebSocket(new Request.Builder().url(url).build(), new WebSocketListener() {
            @Override public void onOpen(WebSocket webSocket, Response response) {
                sessions.dispatch(connectionEpoch, () -> {
                    connected = true; connecting = false;
                    frameStats.newSession(connectionEpoch);
                    ping.reset(); main.removeCallbacks(pingTick); main.post(pingTick);
                    listener.onSessionStarted();
                    try {
                        JSONObject hello = message("hello").put("client", "android").put("device", Build.MODEL);
                        webSocket.send(hello.toString());
                    } catch (JSONException ignored) { }
                    listener.onStatus(context.getString(R.string.connected), true);
                });
            }
            @Override public void onMessage(WebSocket webSocket, String text) {
                if (!sessions.isCurrent(connectionEpoch) || text.length() > 65536) return;
                try {
                    JSONObject json = new JSONObject(text);
                    String type = json.optString("type");
                    if (json.optInt("v", 1) != 1) return;
                    if (("hello".equals(type) || "settings".equals(type)) && json.optJSONObject("settings") != null) {
                        JSONObject incoming = json.getJSONObject("settings");
                        sessions.dispatch(connectionEpoch, () -> listener.onSettings(incoming,
                            optionalSequence(json, "revision"), optionalSequence(json, "clientSeq")));
                    } else if ("error".equals(type)) {
                        sessions.dispatch(connectionEpoch, () -> listener.onStatus(context.getString(
                            R.string.host_error, json.optString("message", context.getString(R.string.connection_error))), connected));
                    } else if ("pong".equals(type)) {
                        sessions.dispatch(connectionEpoch, () -> {
                            Long milliseconds = ping.pong(SystemClock.elapsedRealtime());
                            if (milliseconds != null) listener.onRoundTrip(milliseconds);
                        });
                    }
                } catch (JSONException ignored) { }
            }
            @Override public void onMessage(WebSocket webSocket, ByteString bytes) {
                if (!sessions.isCurrent(connectionEpoch) || bytes.size() > MAX_FRAME_BYTES || bytes.size() < 4) return;
                long receivedAt = SystemClock.elapsedRealtimeNanos();
                queueJpeg(bytes.toByteArray(), connectionEpoch, receivedAt);
            }
            @Override public void onClosed(WebSocket webSocket, int code, String reason) {
                ended(connectionEpoch, context.getString(R.string.connection_ended, code));
            }
            @Override public void onClosing(WebSocket webSocket, int code, String reason) { webSocket.close(code, reason); }
            @Override public void onFailure(WebSocket webSocket, Throwable failure, Response response) {
                String detail = context.getString(usb ? R.string.check_usb_connection : R.string.check_connection);
                if (response != null) {
                    if (response.code() == 401 || response.code() == 403) detail = context.getString(R.string.bad_pairing);
                    else if (response.code() == 409) detail = context.getString(R.string.headset_busy);
                    else if (response.code() == 429) detail = context.getString(R.string.rate_limited);
                }
                ended(connectionEpoch, context.getString(R.string.connection_failed, detail));
            }
        });
    }

    private void ended(long connectionEpoch, String status) {
        sessions.dispatch(connectionEpoch, () -> {
            sessions.invalidate(); connected = false; connecting = false;
            discovery = null; socket = null;
            main.removeCallbacks(pingTick); ping.reset();
            clearPending();
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

    private void queueJpeg(byte[] jpeg, long connectionEpoch, long receivedAt) {
        synchronized (decodeLock) {
            if (!sessions.isCurrent(connectionEpoch)) return;
            pendingJpeg = jpeg; pendingEpoch = connectionEpoch; pendingReceivedAt = receivedAt;
            if (decoding) return;
            decoding = true;
            try { decoder.execute(this::decodeLatest); }
            catch (RejectedExecutionException ignored) { decoding = false; pendingJpeg = null; }
        }
    }

    private void decodeLatest() {
        while (true) {
            byte[] jpeg;
            long frameEpoch, receivedAt;
            synchronized (decodeLock) {
                jpeg = pendingJpeg; frameEpoch = pendingEpoch; receivedAt = pendingReceivedAt; pendingJpeg = null;
                if (jpeg == null || sessions.isClosed()) { decoding = false; return; }
            }
            if (!sessions.isCurrent(frameEpoch) || !connected) continue;
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
                publishBitmap(bitmap, frameEpoch, receivedAt);
            }
        }
    }

    private void publishBitmap(Bitmap bitmap, long frameEpoch, long receivedAt) {
        // The renderer has its own one-slot handoff. Avoid waiting behind UI work,
        // while serializing this short transfer with disconnect/session invalidation.
        boolean delivered = sessions.deliverCurrent(frameEpoch, () -> {
            if (!connected) { bitmap.recycle(); return; }
            int width = bitmap.getWidth(), height = bitmap.getHeight();
            listener.onFrame(bitmap, frameEpoch, receivedAt);
            Double fps = frameStats.decoded(frameEpoch, SystemClock.elapsedRealtimeNanos());
            if (fps != null) sessions.dispatch(frameEpoch, () -> listener.onDecodedStats(width, height, fps));
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
        try { return send(message("settings").put("settings", SettingsJson.encode(settings)).put("clientSeq", sequence)); }
        catch (JSONException ignored) { return false; }
    }
    void sendPose(float yaw, float pitch) {
        if (Float.isNaN(yaw) || Float.isInfinite(yaw) || Float.isNaN(pitch) || Float.isInfinite(pitch)) return;
        try { send(message("pose").put("seq", poseSequence.incrementAndGet()).put("yaw", yaw).put("pitch", pitch)); }
        catch (JSONException ignored) { }
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
        main.removeCallbacks(pingTick); ping.reset();
        Call request = discovery; discovery = null;
        if (request != null) request.cancel();
        WebSocket current = socket; socket = null;
        if (current != null) { current.close(1000, "Client disconnect"); current.cancel(); }
        clearPending();
        if (report && !sessions.isClosed()) listener.onStatus(context.getString(R.string.disconnected), false);
    }
    void shutdown() {
        sessions.close(); disconnect(false); decoder.shutdownNow();
        http.dispatcher().executorService().shutdown(); http.connectionPool().evictAll();
        try { if (http.cache() != null) http.cache().close(); } catch (IOException ignored) { }
    }
}

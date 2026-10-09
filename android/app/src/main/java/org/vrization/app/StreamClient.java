package org.vrization.app;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.os.Build;
import java.io.IOException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import okhttp3.HttpUrl;
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
        void onStatus(String text, boolean connected);
        void onSettings(JSONObject json);
        /** Ownership of bitmap transfers to the listener. */
        void onFrame(Bitmap bitmap);
    }
    private static final int MAX_FRAME_BYTES = 8 * 1024 * 1024;
    private final Listener listener;
    private final OkHttpClient http = new OkHttpClient.Builder()
        .connectTimeout(8, TimeUnit.SECONDS).readTimeout(0, TimeUnit.SECONDS)
        .pingInterval(10, TimeUnit.SECONDS).build();
    private final ExecutorService decoder = Executors.newSingleThreadExecutor();
    private final Object decodeLock = new Object();
    private final AtomicLong epoch = new AtomicLong();
    private final AtomicLong poseSequence = new AtomicLong();
    private volatile WebSocket socket;
    private volatile boolean connected;
    private volatile boolean closed;
    private byte[] pendingJpeg;
    private long pendingEpoch;
    private boolean decoding;

    StreamClient(Listener listener) { this.listener = listener; }
    boolean isConnected() { return connected; }

    void connect(String host, int port, String code) {
        disconnect(false);
        if (closed) return;
        final long connectionEpoch = epoch.incrementAndGet();
        HttpUrl url = new HttpUrl.Builder().scheme("http").host(host).port(port)
            .addPathSegment("ws").addQueryParameter("token", code).build();
        listener.onStatus("正在连接电脑…", false);
        socket = http.newWebSocket(new Request.Builder().url(url).build(), new WebSocketListener() {
            @Override public void onOpen(WebSocket webSocket, Response response) {
                if (epoch.get() != connectionEpoch || closed) { webSocket.cancel(); return; }
                connected = true;
                try {
                    JSONObject hello = message("hello").put("client", "android").put("device", Build.MODEL);
                    webSocket.send(hello.toString());
                } catch (JSONException ignored) { }
                listener.onStatus("已连接。将手机放入 VR 盒子；触摸“隐藏设置”开始观看。", true);
            }
            @Override public void onMessage(WebSocket webSocket, String text) {
                if (epoch.get() != connectionEpoch || closed || text.length() > 65536) return;
                try {
                    JSONObject json = new JSONObject(text);
                    String type = json.optString("type");
                    if (json.optInt("v", 1) != 1) return;
                    if (("hello".equals(type) || "settings".equals(type)) && json.optJSONObject("settings") != null) {
                        listener.onSettings(json.getJSONObject("settings"));
                    } else if ("error".equals(type)) {
                        listener.onStatus("电脑提示：" + json.optString("message", "连接异常"), connected);
                    }
                } catch (JSONException ignored) { }
            }
            @Override public void onMessage(WebSocket webSocket, ByteString bytes) {
                if (epoch.get() != connectionEpoch || closed || bytes.size() > MAX_FRAME_BYTES || bytes.size() < 4) return;
                queueJpeg(bytes.toByteArray(), connectionEpoch);
            }
            @Override public void onClosed(WebSocket webSocket, int code, String reason) {
                ended(connectionEpoch, "连接已结束（" + code + "）。点击“连接电脑”重新连接。");
            }
            @Override public void onClosing(WebSocket webSocket, int code, String reason) { webSocket.close(code, reason); }
            @Override public void onFailure(WebSocket webSocket, Throwable failure, Response response) {
                String detail = "请检查 Wi-Fi、电脑 IP、配对码及防火墙";
                if (response != null) {
                    if (response.code() == 401 || response.code() == 403) detail = "配对码不正确或已更新";
                    else if (response.code() == 409) detail = "电脑已连接另一台手机；请先断开原手机";
                    else if (response.code() == 429) detail = "尝试次数过多；请稍等片刻再重试";
                }
                ended(connectionEpoch, "连接失败：" + detail + "。点击“连接电脑”重试。");
            }
        });
    }

    private void ended(long connectionEpoch, String status) {
        if (epoch.get() != connectionEpoch || closed) return;
        connected = false;
        synchronized (decodeLock) { pendingJpeg = null; }
        listener.onStatus(status, false);
    }

    private void queueJpeg(byte[] jpeg, long connectionEpoch) {
        synchronized (decodeLock) {
            if (closed || epoch.get() != connectionEpoch) return;
            pendingJpeg = jpeg; pendingEpoch = connectionEpoch;
            if (decoding) return;
            decoding = true;
            try { decoder.execute(this::decodeLatest); }
            catch (RejectedExecutionException ignored) { decoding = false; pendingJpeg = null; }
        }
    }

    private void decodeLatest() {
        while (true) {
            byte[] jpeg;
            long frameEpoch;
            synchronized (decodeLock) {
                jpeg = pendingJpeg; frameEpoch = pendingEpoch; pendingJpeg = null;
                if (jpeg == null || closed) { decoding = false; return; }
            }
            if (epoch.get() != frameEpoch || !connected) continue;
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
                if (closed || epoch.get() != frameEpoch || !connected) bitmap.recycle();
                else listener.onFrame(bitmap);
            }
        }
    }

    void sendSettings(VrSettings settings) {
        try { send(message("settings").put("settings", SettingsJson.encode(settings))); }
        catch (JSONException ignored) { }
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
    private void send(JSONObject json) {
        WebSocket current = socket;
        // Drop control messages if a stalled connection already queued >64 KiB.
        if (connected && current != null && current.queueSize() < 65536) current.send(json.toString());
    }
    void disconnect(boolean report) {
        epoch.incrementAndGet(); connected = false;
        WebSocket current = socket; socket = null;
        if (current != null) { current.close(1000, "Client disconnect"); current.cancel(); }
        synchronized (decodeLock) { pendingJpeg = null; }
        if (report && !closed) listener.onStatus("已断开连接。", false);
    }
    void shutdown() {
        closed = true; disconnect(false); decoder.shutdownNow();
        http.dispatcher().executorService().shutdown(); http.connectionPool().evictAll();
        try { if (http.cache() != null) http.cache().close(); } catch (IOException ignored) { }
    }
}

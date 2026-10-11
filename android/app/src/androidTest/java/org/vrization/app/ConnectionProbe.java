package org.vrization.app;

import android.app.Instrumentation;
import android.content.Intent;
import android.content.SharedPreferences;
import android.opengl.GLES20;
import android.opengl.GLSurfaceView;
import android.os.Bundle;
import android.os.SystemClock;
import android.widget.Button;
import android.widget.Spinner;
import android.widget.TextView;
import java.lang.reflect.Field;
import java.nio.ByteBuffer;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import org.vrization.core.VrRenderer;
import org.vrization.core.VrSettings;

/** Real Activity/socket/frame probe. Preference writes are discarded for the whole Activity lifetime. */
final class ConnectionProbe {
    private interface Check { boolean ready(); }

    /** Called by the runner immediately after synchronous onCreate, before onResume or queued UI callbacks.
     * Production onCreate only reads this file; keep this guard installed through onDestroy so late
     * settings callbacks cannot regain a real preference editor during cleanup.
     */
    static void protectActivity(Instrumentation test, MainActivity activity) {
        SharedPreferences original = test.getTargetContext().getSharedPreferences(ClientVariant.PREFERENCES, 0);
        setField(activity, "preferences", new ReadOnlyPreferences(original));
        ((StreamClient) field(activity, "client")).setPoseEnabled(false);
    }

    static Bundle run(Instrumentation test, boolean pcStopProbe, int performanceSeconds, boolean refreshProbe) {
        SharedPreferences original = test.getTargetContext().getSharedPreferences(ClientVariant.PREFERENCES, 0);
        Map<String, ?> before = new HashMap<>(original.getAll());
        MainActivity activity = null;
        StreamClient client = null;
        try {
            progress(test, "launching real phone Activity; no mouse output");
            Intent launch = new Intent(test.getTargetContext(), MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK).putExtra("suppress_usb_auto", true);
            activity = (MainActivity) test.startActivitySync(launch);
            final MainActivity phone = activity;
            require(field(phone, "preferences") instanceof ReadOnlyPreferences,
                "Runner did not protect preferences before Activity resume");
            require(before.equals(original.getAll()), "User preferences changed during Activity startup");
            test.runOnMainSync(() -> {
                ((Spinner) field(phone, "transportInput")).setSelection(0);
            });
            test.waitForIdleSync();
            client = (StreamClient) field(phone, "client");
            final StreamClient stream = client;
            require(!stream.isActive(), "Fresh probe did not start idle");
            Button button = (Button) field(phone, "connectButton");
            Bundle result = new Bundle();
            for (int cycle = 1; cycle <= 2; cycle++) {
                final int currentCycle = cycle;
                long first = stream.deliveredFrameCount();
                progress(test, "cycle " + cycle + ": explicit phone Connect");
                test.runOnMainSync(() -> require(button.performClick(), "Connect button was not clickable"));
                await(() -> stream.isConnected() && stream.deliveredFrameCount() - first >= 5,
                    35_000, "Cycle " + cycle + " did not receive hello and five real decoded frames");
                result.putLong("connectedFrames" + cycle, stream.deliveredFrameCount() - first);
                if (cycle == 1 && refreshProbe) {
                    assertRefresh(test, phone, stream, result);
                }
                if (cycle == 1 && performanceSeconds > 0) {
                    samplePerformance(test, phone, stream, result, performanceSeconds);
                }
                if (pcStopProbe && cycle == 1) {
                    progress(test, "WAITING_FOR_PC_STOP: click Stop on the PC within 45 seconds");
                    await(() -> !stream.isActive(), 45_000, "PC Stop did not disconnect the real phone session");
                    long stoppedByPc = stream.deliveredFrameCount();
                    SystemClock.sleep(1000);
                    require(stream.deliveredFrameCount() == stoppedByPc, "Live frames continued after PC Stop");
                    assertBlank(phone);
                    result.putBoolean("pcStopDisconnected", true);
                    progress(test, "PC Stop passed; explicit phone Connect must start the PC again");
                    test.runOnMainSync(() -> require(button.performClick(), "Connect after PC Stop was not clickable"));
                    await(() -> stream.isConnected() && stream.deliveredFrameCount() - stoppedByPc >= 5,
                        35_000, "Phone Connect after PC Stop did not receive five real frames");
                    result.putLong("framesAfterPcStopReconnect", stream.deliveredFrameCount() - stoppedByPc);
                }
                progress(test, "cycle " + cycle + ": real Disconnect; checking frame cancellation and blank renderer");
                test.runOnMainSync(() -> require(button.performClick(), "Disconnect button was not clickable"));
                require(!stream.isActive(), "Disconnect left the phone connected or waiting");
                long stoppedAt = stream.deliveredFrameCount();
                SystemClock.sleep(1000);
                require(stream.deliveredFrameCount() == stoppedAt,
                    "Cycle " + currentCycle + " still delivered live frames after Disconnect");
                assertBlank(phone);
                result.putLong("disconnectedFrames" + cycle, stream.deliveredFrameCount() - stoppedAt);
                result.putBoolean("rendererBlank" + cycle, true);
            }
            require(before.equals(original.getAll()), "User preferences changed during the probe");
            result.putBoolean("preferencesUnchanged", true);
            result.putInt("connectionCycles", 2);
            result.putString("stream", "\nOK (2 real USB Connect / Disconnect cycles; >=5 frames each; "
                + "zero frames for 1 second after each Disconnect; renderer blank; preferences unchanged)\n");
            return result;
        } finally {
            final MainActivity phone = activity; final StreamClient stream = client;
            if (phone != null) test.runOnMainSync(() -> {
                if (stream != null) stream.disconnect(false);
                phone.finish();
            });
            test.waitForIdleSync();
            require(before.equals(original.getAll()), "User preferences changed during cleanup");
        }
    }

    /** Negotiated live reset retains HMD epoch; fallback rebuilds it. Neither may Resume input. */
    private static void assertRefresh(Instrumentation test, MainActivity phone, StreamClient stream, Bundle result) {
        AtomicReference<Map<String, Object>> fitted = new AtomicReference<>();
        AtomicReference<StreamSession> previous = new AtomicReference<>();
        boolean[] live = {false}; long[] frames = {0}, poseSequence = {0};
        test.runOnMainSync(() -> {
            fitted.set(SettingsValues.encode(((VrSettings) field(phone, "settings")).copy()));
            previous.set(stream.streamSession());
            live[0] = stream.supportsLiveVideoRefresh();
            poseSequence[0] = ((java.util.concurrent.atomic.AtomicLong) field(stream, "poseSequence")).get();
        });
        progress(test, live[0] ? "live-video Refresh: same HMD epoch/socket/pose gate; wait for ACK and fresh native frames"
            : "fallback Refresh: old session/layout invalidated; wait for new hello; no Resume");
        test.runOnMainSync(() -> {
            require(((Button) field(phone, "refreshButton")).performClick(), "Refresh button was not clickable");
            if (live[0]) {
                require(stream.isConnected() && stream.isVideoRefreshPending(), "Live reset disconnected or did not await ACK");
                require(stream.streamSession().epoch == previous.get().epoch && stream.streamSession().accepted,
                    "Live reset changed the accepted HMD session");
            } else {
                require(!stream.isConnected(), "Fallback retained its already connected state");
                require(!stream.streamSession().hmd && !stream.streamSession().stereo,
                    "Fallback retained the previous session layout before its new handshake");
            }
            frames[0] = stream.deliveredFrameCount();
        });
        await(() -> stream.isConnected() && !stream.isVideoRefreshPending() && stream.deliveredFrameCount() - frames[0] >= 5,
            35_000, "Refresh did not finish and receive five new decoded frames");
        test.runOnMainSync(() -> {
            require(field(phone, "client") == stream, "Refresh replaced the protected client");
            require(fitted.get().equals(SettingsValues.encode((VrSettings) field(phone, "settings"))),
                "Refresh changed headset fit or viewing settings");
            require(!((PoseSendGate) field(stream, "poseGate")).maySend(true, 0),
                "Refresh changed the probe's disabled pose gate");
            if (previous.get().hmd) {
                require(stream.streamSession().hmd, "Refresh lost the virtual-HMD route");
                require(live[0] == (stream.streamSession().epoch == previous.get().epoch),
                    "Refresh used the wrong live/fallback session lifecycle");
            }
            if (live[0]) require(poseSequence[0] == ((java.util.concurrent.atomic.AtomicLong) field(stream, "poseSequence")).get(),
                "Live reset emitted an invalid-tracking or recenter/pose message through the protected gate");
        });
        result.putBoolean("refreshConnected", true); result.putBoolean("refreshFitUnchanged", true);
        result.putBoolean("refreshPoseGateUnchanged", true);
        result.putBoolean("liveVideoRefresh", live[0]);
        result.putBoolean("refreshHmdEpochRetained", stream.streamSession().epoch == previous.get().epoch);
        result.putLong("refreshDeliveredFrames", stream.deliveredFrameCount() - frames[0]);
    }

    /** Passive sampling of decoded frames delivered to the view; never a motion-to-photon measure. */
    private static void samplePerformance(Instrumentation test, MainActivity phone, StreamClient stream,
                                         Bundle result, int seconds) {
        test.waitForIdleSync();
        progress(test, "passive decoded-frame sample for " + seconds + " seconds; no settings gestures or mouse output");
        long started = SystemClock.elapsedRealtime(), first = stream.deliveredFrameCount();
        long duration = seconds * 1000L;
        while (SystemClock.elapsedRealtime() - started < duration) {
            require(stream.isConnected(), "Connection ended during passive performance sample");
            SystemClock.sleep(20);
        }
        long elapsed = SystemClock.elapsedRealtime() - started;
        long frames = stream.deliveredFrameCount() - first;
        require(stream.isConnected() && elapsed > 0 && frames >= 0, "Invalid passive performance sample");
        result.putLong("performanceSampleMillis", elapsed);
        result.putLong("decodedDeliveredFrames", frames);
        result.putDouble("decodedDeliveredFPS", frames * 1000d / elapsed);
        result.putString("performanceScope", "Decoded frames delivered to the view; not displayed FPS or end-to-end latency");
        result.putString("rttScope", "Existing app ping round-trip display; not motion-to-photon latency");
        test.runOnMainSync(() -> {
            result.putString("frameStatus", ((TextView) field(phone, "frameStatus")).getText().toString());
            result.putString("linkStatus", ((TextView) field(phone, "linkStatus")).getText().toString());
            result.putString("processingStatus", ((TextView) field(phone, "processingStatus")).getText().toString());
        });
        progress(test, "sample complete: " + result.getDouble("decodedDeliveredFPS")
            + " decoded-delivered FPS; " + result.getString("linkStatus"));
    }

    private static void assertBlank(MainActivity phone) {
        GLSurfaceView surface = (GLSurfaceView) field(phone, "surface");
        VrRenderer renderer = (VrRenderer) field(phone, "renderer");
        CountDownLatch drawn = new CountDownLatch(1);
        AtomicReference<Throwable> failure = new AtomicReference<>();
        surface.queueEvent(() -> {
            try {
                renderer.onDrawFrame(null);
                require(Boolean.FALSE.equals(field(renderer, "hasTexture")), "Disconnected renderer retained a displayed frame");
                int width = surface.getWidth(), height = surface.getHeight();
                require(width >= 2 && height > 0, "Renderer surface has no size");
                ByteBuffer pixel = ByteBuffer.allocateDirect(4);
                for (int x : new int[]{width / 4, width * 3 / 4}) {
                    pixel.clear(); GLES20.glReadPixels(x, height / 2, 1, 1, GLES20.GL_RGBA, GLES20.GL_UNSIGNED_BYTE, pixel);
                    require(GLES20.glGetError() == GLES20.GL_NO_ERROR, "GLES readback failed");
                    require((pixel.get(0) & 255) <= 3 && (pixel.get(1) & 255) <= 3 && (pixel.get(2) & 255) <= 3,
                        "Disconnected video surface was not black");
                }
            } catch (Throwable error) { failure.set(error); }
            finally { drawn.countDown(); }
        });
        try { require(drawn.await(5, TimeUnit.SECONDS), "GL thread did not process Disconnect"); }
        catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); throw new AssertionError(interrupted); }
        if (failure.get() != null) throw new AssertionError("Blank renderer check failed", failure.get());
    }

    private static void await(Check check, long timeout, String failure) {
        long deadline = SystemClock.elapsedRealtime() + timeout;
        while (!check.ready() && SystemClock.elapsedRealtime() < deadline) SystemClock.sleep(20);
        require(check.ready(), failure);
    }
    private static void progress(Instrumentation test, String text) {
        Bundle status = new Bundle(); status.putString("stream", "\nCONNECTION_PROBE: " + text + "\n"); test.sendStatus(0, status);
    }
    private static Object field(Object owner, String name) {
        try { Field field = owner.getClass().getDeclaredField(name); field.setAccessible(true); return field.get(owner); }
        catch (ReflectiveOperationException error) { throw new AssertionError("Probe cannot read " + name, error); }
    }
    private static void setField(Object owner, String name, Object value) {
        try { Field field = owner.getClass().getDeclaredField(name); field.setAccessible(true); field.set(owner, value); }
        catch (ReflectiveOperationException error) { throw new AssertionError("Probe cannot set " + name, error); }
    }
    private static void require(boolean condition, String message) { if (!condition) throw new AssertionError(message); }

    private static final class ReadOnlyPreferences implements SharedPreferences {
        private final SharedPreferences delegate;
        ReadOnlyPreferences(SharedPreferences delegate) { this.delegate = delegate; }
        @Override public Map<String, ?> getAll() { return delegate.getAll(); }
        @Override public String getString(String key, String fallback) { return delegate.getString(key, fallback); }
        @Override public Set<String> getStringSet(String key, Set<String> fallback) { return delegate.getStringSet(key, fallback); }
        @Override public int getInt(String key, int fallback) { return delegate.getInt(key, fallback); }
        @Override public long getLong(String key, long fallback) { return delegate.getLong(key, fallback); }
        @Override public float getFloat(String key, float fallback) { return delegate.getFloat(key, fallback); }
        @Override public boolean getBoolean(String key, boolean fallback) { return delegate.getBoolean(key, fallback); }
        @Override public boolean contains(String key) { return delegate.contains(key); }
        @Override public void registerOnSharedPreferenceChangeListener(OnSharedPreferenceChangeListener listener) { }
        @Override public void unregisterOnSharedPreferenceChangeListener(OnSharedPreferenceChangeListener listener) { }
        @Override public Editor edit() { return new Editor() {
            @Override public Editor putString(String key, String value) { return this; }
            @Override public Editor putStringSet(String key, Set<String> value) { return this; }
            @Override public Editor putInt(String key, int value) { return this; }
            @Override public Editor putLong(String key, long value) { return this; }
            @Override public Editor putFloat(String key, float value) { return this; }
            @Override public Editor putBoolean(String key, boolean value) { return this; }
            @Override public Editor remove(String key) { return this; }
            @Override public Editor clear() { return this; }
            @Override public boolean commit() { return true; }
            @Override public void apply() { }
        }; }
    }
}

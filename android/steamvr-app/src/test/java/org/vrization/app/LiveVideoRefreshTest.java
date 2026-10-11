package org.vrization.app;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import org.junit.Test;
import static org.junit.Assert.*;

public final class LiveVideoRefreshTest {
    private static Map<String, Object> ack(long epoch, long request, boolean paused) {
        Map<String, Object> value = new HashMap<>(); value.put("v", 1); value.put("type", "videoRefresh");
        value.put("epoch", epoch); value.put("requestId", request); value.put("paused", paused); return value;
    }
    private static VideoRefreshValues.Ack ack(VideoRefreshGate.Request request, boolean paused) {
        return VideoRefreshValues.acknowledgement(ack(request.epoch, request.requestId, paused));
    }
    private static HostSessionGate host(boolean accepted, boolean capability) {
        HostSessionGate gate = new HostSessionGate(); Map<String, Object> hello = SteamFixtures.hello(accepted);
        ArrayList<String> caps = new ArrayList<>(SteamFixtures.CAPS);
        if (capability) caps.add(VideoRefreshValues.CAPABILITY); hello.put("capabilities", caps);
        gate.receive(hello); return gate;
    }
    @Test public void refreshRequiresNegotiatedCapabilityAndAcceptedHmd() {
        HostSessionGate pending = host(false, true); assertFalse(pending.supportsVideoRefresh());
        pending.receive(SteamFixtures.settings(true)); assertTrue(pending.supportsVideoRefresh());
        HostSessionGate legacy = host(true, false); assertFalse(legacy.supportsVideoRefresh());
        assertThrows(IllegalArgumentException.class, () -> legacy.receive(ack(19, 1, false)));
    }
    @Test public void monoOrLegacyRouteCannotAuthorizeLiveHmdRefresh() {
        for (boolean explicit : new boolean[]{true, false}) {
            Map<String, Object> hello = SteamFixtures.hello(true);
            hello.put("capabilities", java.util.Arrays.asList("video-refresh"));
            if (explicit) hello.put("streamSession", SteamFixtures.descriptor(19, true, false));
            else hello.remove("streamSession");
            HostSessionGate gate = new HostSessionGate(); gate.receive(hello); assertFalse(gate.supportsVideoRefresh());
        }
    }
    @Test public void safeIntegerRequestAndExactBooleanAcknowledgementDoNotCoerce() {
        assertEquals(VideoRefreshValues.MAX_SAFE,
            VideoRefreshValues.acknowledgement(ack(VideoRefreshValues.MAX_SAFE, VideoRefreshValues.MAX_SAFE, true)).requestId);
        for (String key : new String[]{"v", "epoch", "requestId"})
            for (Object invalid : new Object[]{true, "1", 1.0, null, 0, -1, VideoRefreshValues.MAX_SAFE + 1}) {
                Map<String, Object> value = ack(19, 1, false); value.put(key, invalid);
                assertThrows(IllegalArgumentException.class, () -> VideoRefreshValues.acknowledgement(value));
            }
        for (Object invalid : new Object[]{"false", 0, 1, null}) {
            Map<String, Object> value = ack(19, 1, false); value.put("paused", invalid);
            assertThrows(IllegalArgumentException.class, () -> VideoRefreshValues.acknowledgement(value));
        }
        assertThrows(IllegalArgumentException.class, () -> VideoRefreshValues.request(19, 0));
        Map<String, Object> request = VideoRefreshValues.request(19, 1);
        assertEquals("refreshVideo", request.get("type")); assertEquals(19L, request.get("epoch"));
    }
    @Test public void malformedAckPoisonsProtocolWithoutReleasingVideo() {
        HostSessionGate host = host(true, true); VideoRefreshGate video = new VideoRefreshGate(); video.begin(19, 100);
        Map<String, Object> malformed = ack(19, 1, false); malformed.put("paused", "false");
        assertThrows(IllegalArgumentException.class, () -> host.receive(malformed));
        assertFalse(host.isEstablished()); assertEquals(-1, video.captureGeneration());
    }
    @Test public void exhaustedSafeRequestCounterCannotWrapOrInventAnIdentity() throws Exception {
        VideoRefreshGate video = new VideoRefreshGate();
        java.lang.reflect.Field counter = VideoRefreshGate.class.getDeclaredField("requestId"); counter.setAccessible(true);
        counter.setLong(video, VideoRefreshValues.MAX_SAFE - 1);
        VideoRefreshGate.Request last = video.begin(19, 100); assertEquals(VideoRefreshValues.MAX_SAFE, last.requestId);
        assertThrows(IllegalArgumentException.class, () -> video.begin(20, 200));
        assertTrue(video.acknowledge(ack(last, false), 200, () -> {}));
        assertNull(video.begin(19, 300)); assertFalse(video.isPending()); assertTrue(video.captureGeneration() >= 0);
    }
    @Test public void wrongRequestWrongEpochAndDuplicatesNeverReleaseVideo() {
        VideoRefreshGate gate = new VideoRefreshGate(); VideoRefreshGate.Request request = gate.begin(19, 100);
        for (VideoRefreshValues.Ack bad : new VideoRefreshValues.Ack[]{
            VideoRefreshValues.acknowledgement(ack(20, request.requestId, false)),
            VideoRefreshValues.acknowledgement(ack(19, request.requestId + 1, false))})
            assertFalse(gate.acknowledge(bad, 200, () -> fail("Wrong ACK resumed video")));
        assertEquals(-1, gate.captureGeneration());
        assertTrue(gate.acknowledge(ack(request, false), 200, () -> {}));
        assertFalse(gate.acknowledge(ack(request, false), 201, () -> fail("Duplicate ACK resumed video")));
    }
    @Test public void inFlightDecodeCannotReappearAfterMatchingAck() {
        SessionDispatcher connection = new SessionDispatcher(Runnable::run); long epoch = connection.invalidate();
        VideoRefreshGate gate = new VideoRefreshGate(); long old = gate.captureGeneration(); int[] pictures = {0};
        VideoRefreshGate.Request request = gate.begin(19, 100);
        assertFalse(gate.deliverCurrent(old, () -> pictures[0]++));
        assertFalse(gate.deliverCurrent(request.generation, () -> pictures[0]++));
        assertTrue(gate.acknowledge(ack(request, false), 200, () -> {
            assertFalse(gate.deliverCurrent(request.generation, () -> fail("Binary arrived before renderer ready")));
        }));
        assertFalse(gate.deliverCurrent(old, () -> pictures[0]++));
        assertTrue(gate.deliverCurrent(request.generation, () -> pictures[0]++));
        assertEquals(1, pictures[0]); assertTrue(connection.isCurrent(epoch));
    }
    @Test public void acknowledgementPauseStateNeverChangesTheInputGate() {
        for (boolean paused : new boolean[]{true, false}) for (boolean enabled : new boolean[]{true, false}) {
            VideoRefreshGate video = new VideoRefreshGate(); PoseSendGate input = new PoseSendGate(); input.setEnabled(enabled);
            VideoRefreshGate.Request request = video.begin(19, 100);
            assertTrue(video.acknowledge(ack(request, paused), 200, () -> {}));
            assertEquals(enabled, input.maySend(true, 0));
        }
    }
    @Test public void repeatedTapCannotExtendEightSecondDeadlineOrCreateConcurrentReset() {
        VideoRefreshGate gate = new VideoRefreshGate(); VideoRefreshGate.Request first = gate.begin(19, 100);
        assertSame(first, gate.begin(19, 7999)); assertEquals(8100, first.deadline);
        assertFalse(gate.expire(first, 8099)); assertTrue(gate.expire(first, 8100));
        assertFalse(gate.expire(first, 8101)); assertEquals(-1, gate.captureGeneration());
        assertFalse(gate.acknowledge(ack(first, false), 8101, () -> fail("Late ACK released video")));
    }
    @Test public void ackAtDeadlineCannotBeatDelayedTimeoutRunnable() {
        VideoRefreshGate gate = new VideoRefreshGate(); VideoRefreshGate.Request request = gate.begin(19, 100);
        assertFalse(gate.acknowledge(ack(request, false), request.deadline, () -> fail("Expired ACK released video")));
        assertTrue(gate.expire(request, request.deadline));
    }
    @Test public void backgroundAbortDropsAckAndKeepsVideoBlockedUntilExplicitAction() {
        VideoRefreshGate gate = new VideoRefreshGate(); VideoRefreshGate.Request old = gate.begin(19, 100);
        gate.abort(); assertFalse(gate.isPending()); assertEquals(-1, gate.captureGeneration());
        assertFalse(gate.acknowledge(ack(old, false), 200, () -> fail("Background ACK resumed video")));
        VideoRefreshGate.Request current = gate.begin(19, 300); assertTrue(current.requestId > old.requestId);
        assertFalse(gate.expire(old, 10000)); assertTrue(gate.acknowledge(ack(current, true), 400, () -> {}));
    }
    @Test public void disconnectOrStopAllowsFreshSessionButNeverOldDecodeOrAck() {
        VideoRefreshGate gate = new VideoRefreshGate(); long oldDecode = gate.captureGeneration();
        VideoRefreshGate.Request old = gate.begin(19, 100); gate.newConnection();
        assertFalse(gate.isPending()); assertTrue(gate.captureGeneration() >= 0);
        assertFalse(gate.deliverCurrent(oldDecode, () -> fail("Stopped decode delivered")));
        assertFalse(gate.acknowledge(ack(old, false), 200, () -> fail("Stopped ACK delivered")));
        VideoRefreshGate.Request current = gate.begin(20, 300);
        assertFalse(gate.acknowledge(ack(old, false), 400, () -> fail("Previous epoch resumed new video")));
        assertTrue(gate.acknowledge(ack(current, true), 400, () -> {}));
    }
    @Test public void impossibleClockCannotWrapRefreshDeadline() {
        VideoRefreshGate gate = new VideoRefreshGate();
        for (long now : new long[]{-1, Long.MAX_VALUE, Long.MAX_VALUE - 7999})
            assertThrows(IllegalArgumentException.class, () -> gate.begin(19, now));
    }
    @Test public void refreshBarrierWaitsForAlreadyStartedShortRendererTransfer() throws Exception {
        VideoRefreshGate gate = new VideoRefreshGate(); long old = gate.captureGeneration();
        CountDownLatch transferring = new CountDownLatch(1), release = new CountDownLatch(1);
        CountDownLatch refreshing = new CountDownLatch(1), refreshed = new CountDownLatch(1);
        ExecutorService threads = Executors.newFixedThreadPool(2);
        try {
            Future<Boolean> frame = threads.submit(() -> gate.deliverCurrent(old, () -> {
                transferring.countDown();
                try { assertTrue(release.await(2, TimeUnit.SECONDS)); }
                catch (InterruptedException failure) { throw new AssertionError(failure); }
            }));
            assertTrue(transferring.await(2, TimeUnit.SECONDS));
            Future<VideoRefreshGate.Request> request = threads.submit(() -> {
                refreshing.countDown(); VideoRefreshGate.Request value = gate.begin(19, 100); refreshed.countDown(); return value;
            });
            assertTrue(refreshing.await(2, TimeUnit.SECONDS)); assertFalse(refreshed.await(40, TimeUnit.MILLISECONDS));
            release.countDown(); assertTrue(frame.get(2, TimeUnit.SECONDS));
            VideoRefreshGate.Request value = request.get(2, TimeUnit.SECONDS);
            assertFalse(gate.deliverCurrent(old, () -> fail("Old decode passed the barrier")));
            assertTrue(gate.acknowledge(ack(value, false), 200, () -> {}));
        } finally { release.countDown(); threads.shutdownNow(); }
    }
}

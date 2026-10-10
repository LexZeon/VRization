package org.vrization.core;

import org.junit.Test;
import static org.junit.Assert.*;

public final class UsbConnectRequestTest {
    @Test public void anExplicitRequestIsConsumedExactlyOnceOnForegroundEntry() {
        UsbConnectRequest request = new UsbConnectRequest(); request.request();
        assertTrue(request.isPending()); assertTrue(request.consume(false));
        assertFalse(request.isPending()); assertFalse(request.consume(false));
    }

    @Test public void anAlreadyActiveConnectionIsNotRestartedByARepeatedPcRequest() {
        UsbConnectRequest request = new UsbConnectRequest(); request.request();
        assertFalse(request.consume(true));
        assertFalse(request.consume(false));
        request.request(); assertTrue(request.consume(false));
    }

    @Test public void aNewExplicitRequestCanConnectAfterPreviousCancellationOrTimeout() {
        UsbConnectRequest request = new UsbConnectRequest(); request.request(); request.cancel();
        assertFalse(request.consume(false));
        request.request(); assertTrue(request.consume(false));
        request.request(); assertTrue(request.consume(false));
    }

    @Test public void restoringAnUnconsumedRequestDoesNotReplayAnAlreadyConsumedIntent() {
        UsbConnectRequest beforePause = new UsbConnectRequest(); beforePause.request();
        UsbConnectRequest restored = new UsbConnectRequest();
        if (beforePause.isPending()) restored.request();
        assertTrue(restored.consume(false));
        UsbConnectRequest recreated = new UsbConnectRequest();
        if (restored.isPending()) recreated.request();
        assertFalse(recreated.consume(false));
    }
    @Test public void aPcActionCanReplaceAnAlmostExpiredAutomaticAttemptWithoutWakingTheHostAgain() {
        UsbConnectionAttempt attempt = new UsbConnectionAttempt(); attempt.start(1, 0);
        assertEquals(100, attempt.remaining(1, 29_900)); assertTrue(attempt.isAutomatic());
        UsbConnectRequest request = new UsbConnectRequest(); request.request();
        assertTrue(request.consume(!attempt.isAutomatic()));
        attempt.start(2, 29_900, UsbConnectionAttempt.Source.COMPUTER_ACTION);
        assertEquals(30_000, attempt.remaining(2, 29_900));
        assertFalse(attempt.takeHostWake(2, 29_900)); assertTrue(attempt.beginDiscovery(2, 29_900));
        request.request(); assertFalse(request.consume(!attempt.isAutomatic()));
    }
    @Test public void aRepeatedConnectedPcRequestRetainsThePoseOriginAndAFreshSessionRecentersIt() {
        PoseMath.RotationCenter center = new PoseMath.RotationCenter();
        center.sample(new float[]{1,0,0, 0,1,0, 0,0,1});
        float yaw = .45f, cosine = (float) Math.cos(yaw), sine = (float) Math.sin(yaw);
        float[] turned = {cosine,0,-sine, 0,1,0, sine,0,cosine};
        assertEquals(yaw, center.sample(turned)[0], .0001f);
        UsbConnectRequest request = new UsbConnectRequest(); request.request();
        assertFalse(request.consume(true));
        assertEquals(yaw, center.sample(turned)[0], .0001f);
        request.request(); assertTrue(request.consume(false)); center.recenter();
        assertArrayEquals(new float[]{0,0,0}, center.sample(turned), .0001f);
    }
}

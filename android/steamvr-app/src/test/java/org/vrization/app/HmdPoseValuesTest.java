package org.vrization.app;
import java.util.Arrays;
import java.util.Map;
import org.junit.Test;
import static org.junit.Assert.*;

public final class HmdPoseValuesTest {
    @Test public void negotiatedPacketHasFullQuaternionAndNoEulerMouseFields() {
        Map<String,Object> packet = HmdPoseValues.encode(SteamFixtures.session(19,true,true),42,7000000,new float[]{0,0,0,1},true);
        assertEquals("hmdPose",packet.get("type")); assertEquals(19L,packet.get("epoch")); assertEquals(42L,packet.get("seq"));
        assertEquals(7000000L,packet.get("timeUs")); assertEquals(Arrays.asList(0f,0f,0f,1f),packet.get("q"));
        assertFalse(packet.containsKey("yaw")); assertFalse(packet.containsKey("pitch"));
    }
    @Test public void unavailablePausedOrDisconnectedTrackingNeverHasAFabricatedQuaternion() {
        Map<String,Object> packet = HmdPoseValues.encode(SteamFixtures.session(19,true,true),43,7000010,null,false);
        assertEquals(false,packet.get("trackingValid")); assertFalse(packet.containsKey("q"));
    }
    @Test public void legacyMonoAndPendingRoutesCannotSendHmdTracking() {
        for (StreamSession session : new StreamSession[]{StreamSession.legacy(),SteamFixtures.session(19,true,false),SteamFixtures.session(19,false,true)})
            assertThrows(IllegalArgumentException.class, () -> HmdPoseValues.encode(session,1,0,new float[]{0,0,0,1},true));
    }
    @Test public void invalidNumbersOrNonunitQuaternionNeverReachTheDriver() {
        StreamSession session = SteamFixtures.session(19,true,true);
        for (float[] bad : new float[][]{null,{0,0,0},{0,0,0,0},{1,1,0,0},{Float.NaN,0,0,1},{0,Float.POSITIVE_INFINITY,0,1}})
            assertThrows(IllegalArgumentException.class, () -> HmdPoseValues.encode(session,1,0,bad,true));
        assertThrows(IllegalArgumentException.class, () -> HmdPoseValues.encode(session,0,0,null,false));
        assertThrows(IllegalArgumentException.class, () -> HmdPoseValues.encode(session,1,-1,null,false));
        assertThrows(IllegalArgumentException.class, () -> HmdPoseValues.encode(session,1,9007199254740992L,null,false));
    }
    @Test public void recenterKeepsPacketSequenceContinuousAndCopiesQuaternion() {
        float[] q = {0,0,0,1}; StreamSession session = SteamFixtures.session(19,true,true);
        Map<String,Object> first = HmdPoseValues.encode(session,44,0,q,true); q[0] = 1;
        Map<String,Object> second = HmdPoseValues.encode(session,45,1,new float[]{0,0,0,1},true);
        assertEquals(Arrays.asList(0f,0f,0f,1f),first.get("q")); assertEquals(45L,second.get("seq"));
    }
}

package org.vrization.app;

import java.util.Arrays;
import java.util.Collections;
import java.util.Map;
import org.junit.Test;
import static org.junit.Assert.*;

public final class StreamSessionTest {
    @Test public void pendingStereoNeedsTheCompleteIntersectionAndAcceptedSnapshot() {
        HostSessionGate gate = new HostSessionGate(); assertTrue(gate.receive(SteamFixtures.hello(false)));
        assertFalse(gate.streamSession().accepted); assertTrue(gate.streamSession().stereo);
        gate.receive(SteamFixtures.settings(false)); // Intermediate schema/enhanced echo is harmless.
        assertFalse(gate.streamSession().accepted);
        gate.receive(SteamFixtures.settings(true)); assertTrue(gate.streamSession().accepted);
        gate.receiveJpeg(100); assertTrue(gate.isEstablished());
    }
    @Test public void binaryBeforeNegotiationFailsUntilReconnect() {
        HostSessionGate gate = new HostSessionGate(); gate.receive(SteamFixtures.hello(false));
        assertThrows(IllegalArgumentException.class, () -> gate.receiveJpeg(100));
        assertThrows(IllegalArgumentException.class, () -> gate.receive(SteamFixtures.settings(true)));
        assertFalse(gate.isEstablished());
    }
    @Test public void eitherMissingCapabilityFailsClosed() {
        for (String cap : new String[]{"stereo-sbs","hmd-orientation"}) {
            Map<String,Object> hello = SteamFixtures.hello(false); hello.put("capabilities",Arrays.asList(cap));
            HostSessionGate gate = new HostSessionGate();
            assertThrows(IllegalArgumentException.class, () -> gate.receive(hello)); assertFalse(gate.isEstablished());
        }
    }
    @Test public void legacyPeerKeepsTheOrdinaryMonoMousePath() {
        Map<String,Object> hello = SteamFixtures.hello(true); hello.remove("streamSession"); hello.remove("capabilities");
        hello.remove("enhancedFirstPerson"); HostSessionGate gate = new HostSessionGate(); gate.receive(hello);
        assertTrue(gate.streamSession().accepted); assertFalse(gate.streamSession().explicit);
        assertFalse(gate.streamSession().stereo); assertFalse(gate.streamSession().hmd); gate.receiveJpeg(100);
        Map<String,Object> update = SteamFixtures.settings(true); update.remove("streamSession"); gate.receive(update);
    }
    @Test public void explicitMonoWorksWithoutStereoCapabilities() {
        StreamSession mono = StreamSession.parse(SteamFixtures.descriptor(8,true,false),Collections.emptyList());
        assertTrue(mono.accepted); assertFalse(mono.stereo); assertFalse(mono.hmd);
    }
    @Test public void layoutAndEpochChangesRequireAReconnect() {
        StreamSession first = SteamFixtures.session(19,true,true);
        assertThrows(IllegalArgumentException.class, () -> first.update(SteamFixtures.session(19,true,false)));
        assertThrows(IllegalArgumentException.class, () -> first.update(SteamFixtures.session(20,true,true)));
        assertThrows(IllegalArgumentException.class, () -> first.update(StreamSession.legacy()));
    }
    @Test public void acceptedSessionCannotBeDowngradedByAnOldFalseEcho() {
        HostSessionGate gate = new HostSessionGate(); gate.receive(SteamFixtures.hello(false));
        gate.receive(SteamFixtures.settings(true));
        assertThrows(IllegalArgumentException.class, () -> gate.receive(SteamFixtures.settings(false)));
        assertFalse(gate.isEstablished());
    }
    @Test public void everyNewSettingsMessageMustRetainItsDescriptor() {
        HostSessionGate gate = new HostSessionGate(); gate.receive(SteamFixtures.hello(true));
        Map<String,Object> update = SteamFixtures.settings(true); update.remove("streamSession");
        assertThrows(IllegalArgumentException.class, () -> gate.receive(update));
    }
    @Test public void missingWrongAndExtraDescriptorFieldsFail() {
        for (String key : SteamFixtures.descriptor(1,true,true).keySet()) {
            Map<String,Object> descriptor = SteamFixtures.descriptor(1,true,true); descriptor.remove(key);
            assertThrows(IllegalArgumentException.class, () -> StreamSession.parse(descriptor,SteamFixtures.CAPS));
        }
        Map<String,Object> extra = SteamFixtures.descriptor(1,true,true); extra.put("future",1);
        assertThrows(IllegalArgumentException.class, () -> StreamSession.parse(extra,SteamFixtures.CAPS));
    }
    @Test public void invalidTypesAndRangesCannotMasqueradeAsEpochsOrAcceptance() {
        for (Object bad : new Object[]{0L,-1L,1.0,true,"1",9007199254740992L}) {
            Map<String,Object> descriptor = SteamFixtures.descriptor(1,true,true); descriptor.put("epoch",bad);
            assertThrows(IllegalArgumentException.class, () -> StreamSession.parse(descriptor,SteamFixtures.CAPS));
        }
        Map<String,Object> descriptor = SteamFixtures.descriptor(1,true,true); descriptor.put("accepted",1);
        assertThrows(IllegalArgumentException.class, () -> StreamSession.parse(descriptor,SteamFixtures.CAPS));
    }
    @Test public void mixedInputAndVideoOrExplicitNullDoNotFallbackToLegacy() {
        Map<String,Object> descriptor = SteamFixtures.descriptor(1,true,true); descriptor.put("inputTarget","mouse");
        assertThrows(IllegalArgumentException.class, () -> StreamSession.parse(descriptor,SteamFixtures.CAPS));
        Map<String,Object> hello = SteamFixtures.hello(true); hello.put("streamSession",null);
        assertThrows(IllegalArgumentException.class, () -> new HostSessionGate().receive(hello));
    }
    @Test public void duplicateHelloAndOversizedCapabilitiesFailClosed() {
        HostSessionGate gate = new HostSessionGate(); gate.receive(SteamFixtures.hello(true));
        assertThrows(IllegalArgumentException.class, () -> gate.receive(SteamFixtures.hello(true)));
        Map<String,Object> hello = SteamFixtures.hello(true); hello.put("capabilities",Collections.nCopies(33,"stereo-sbs"));
        assertThrows(IllegalArgumentException.class, () -> new HostSessionGate().receive(hello));
    }
}

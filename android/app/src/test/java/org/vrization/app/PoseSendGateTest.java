package org.vrization.app;

import org.junit.Test;
import static org.junit.Assert.*;

public final class PoseSendGateTest {
    @Test public void editingDropsPoseSamplesEvenWhenTheTransportIsReady() {
        PoseSendGate gate = new PoseSendGate(); assertTrue(gate.maySend(true, 0));
        gate.setEnabled(false); assertFalse(gate.maySend(true, 0)); assertFalse(gate.maySend(true, 100));
        gate.setEnabled(true); assertTrue(gate.maySend(true, 0));
    }
    @Test public void pendingControlMessagesPreventAccumulatingOldPoseSamples() {
        PoseSendGate gate = new PoseSendGate(); assertFalse(gate.maySend(false, 0));
        assertFalse(gate.maySend(true, 1)); assertFalse(gate.maySend(true, 65536));
        assertTrue(gate.maySend(true, 0));
    }
}

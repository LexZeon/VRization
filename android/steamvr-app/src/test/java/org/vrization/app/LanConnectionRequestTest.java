package org.vrization.app;

import org.junit.Test;
import static org.junit.Assert.*;

public final class LanConnectionRequestTest {
    @Test public void manualRefreshUsesTrimmedAddressAndLeadingZeroCode() {
        LanConnectionRequest request = LanConnectionRequest.parse(" 192.168.1.5 ", " 8766 ", " 001234 ");
        assertEquals("192.168.1.5", request.host); assertEquals(8766, request.port);
        assertEquals("001234", request.code);
    }
    @Test public void hostnameIpv6AndBothPortLimitsRemainAvailable() {
        assertEquals("computer.local", LanConnectionRequest.parse("computer.local", "1", "123456").host);
        assertEquals(65535, LanConnectionRequest.parse("::1", "65535", "123456").port);
    }
    @Test public void missingOrMalformedCodeCannotBecomeAutomaticUsbOrInventedCredentials() {
        for (String code : new String[]{null, "", "12345", "1234567", "１２３４５６", "123&45"})
            assertEquals(LanConnectionRequest.Reason.CODE,
                assertThrows(LanConnectionRequest.Invalid.class,
                    () -> LanConnectionRequest.parse("computer", "8766", code)).reason);
    }
    @Test public void malformedPortsAreReportedBeforeConnecting() {
        for (String port : new String[]{null, "", "12.5", "garbage", "999999999999999999999999"})
            assertEquals(LanConnectionRequest.Reason.PORT,
                assertThrows(LanConnectionRequest.Invalid.class,
                    () -> LanConnectionRequest.parse("computer", port, "123456")).reason);
    }
    @Test public void addressAndPortRangeDoNotPermitUrlOrPathDestinations() {
        for (String host : new String[]{null, "", " ", "http://computer", "ws://computer", "computer/path"})
            assertEquals(LanConnectionRequest.Reason.ADDRESS,
                assertThrows(LanConnectionRequest.Invalid.class,
                    () -> LanConnectionRequest.parse(host, "8766", "123456")).reason);
        for (String port : new String[]{"0", "-1", "65536"})
            assertEquals(LanConnectionRequest.Reason.ADDRESS,
                assertThrows(LanConnectionRequest.Invalid.class,
                    () -> LanConnectionRequest.parse("computer", port, "123456")).reason);
    }
}

package org.vrization.app;
import org.junit.Test;
import static org.junit.Assert.*;

public final class SteamVariantTest {
    @Test public void experimentalIdentityPortsAndStorageAreIsolated() {
        assertTrue(ClientVariant.EXPERIMENTAL); assertEquals("org.vrization.steamvr",BuildConfig.APPLICATION_ID);
        assertEquals("0.5.0-steamvr-preview",BuildConfig.VERSION_NAME); assertEquals(1,BuildConfig.VERSION_CODE);
        assertEquals("vrization_steamvr",ClientVariant.PREFERENCES); assertEquals("8766",ClientVariant.DEFAULT_PORT);
        assertEquals(18774,ClientVariant.CONTROL_PORT); assertEquals(18775,ClientVariant.VIDEO_PORT);
    }
    @Test public void usbBootstrapUsesItsOwnPortButKeepsStrictHostIdentity() {
        assertEquals("http://127.0.0.1:18775/usb-bootstrap",UsbBootstrap.ENDPOINT);
        assertEquals("http://127.0.0.1:18774/connect",ClientVariant.USB_CONNECT);
    }
}

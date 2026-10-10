package org.vrization.app;
/** Compile-time distribution policy. Stable defaults never change. */
final class ClientVariant {
    static final boolean EXPERIMENTAL = BuildConfig.STEAMVR_EXPERIMENT;
    static final int CONTROL_PORT = EXPERIMENTAL ? 18774 : 18764, VIDEO_PORT = EXPERIMENTAL ? 18775 : 18765;
    static final String PREFERENCES = EXPERIMENTAL ? "vrization_steamvr" : "vrization";
    static final String DEFAULT_PORT = EXPERIMENTAL ? "8766" : "8765";
    static final String USB_CONNECT = "http://127.0.0.1:" + CONTROL_PORT + "/connect";
    static final String USB_BOOTSTRAP = "http://127.0.0.1:" + VIDEO_PORT + "/usb-bootstrap";
    private ClientVariant() { }
}

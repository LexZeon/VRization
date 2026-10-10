package org.vrization.core;

/** Phone-side loopback endpoints of the Android USB control and video tunnels. */
public final class TransportEndpoints {
    private TransportEndpoints() { }
    public static final String USB_HOST = "127.0.0.1";
    public static final int USB_CONTROL_PORT = 18764, USB_VIDEO_PORT = 18765;
    public static final String USB_CONNECT = "http://" + USB_HOST + ":" + USB_CONTROL_PORT + "/connect";
    public static final String USB_BOOTSTRAP = "http://" + USB_HOST + ":" + USB_VIDEO_PORT + "/usb-bootstrap";
}

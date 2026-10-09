package org.vrization.app;

/** Local transport preference. Upgrades without a transport preference use USB. */
enum ConnectionMode {
    USB("usb"), LAN("lan");
    final String preferenceValue;
    ConnectionMode(String value) { preferenceValue = value; }
    static ConnectionMode fromPreference(String value) { return "lan".equals(value) ? LAN : USB; }
}

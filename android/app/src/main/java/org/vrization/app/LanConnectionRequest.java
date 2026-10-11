package org.vrization.app;

/** Transient manual LAN material; neither refresh nor connection may invent a pairing code. */
final class LanConnectionRequest {
    enum Reason { PORT, ADDRESS, CODE }
    static final class Invalid extends IllegalArgumentException {
        final Reason reason;
        Invalid(Reason reason) { super(reason.name()); this.reason = reason; }
    }
    final String host, code;
    final int port;
    private LanConnectionRequest(String host, int port, String code) {
        this.host = host; this.port = port; this.code = code;
    }
    static LanConnectionRequest parse(String hostText, String portText, String codeText) {
        String host = hostText == null ? "" : hostText.trim();
        String code = codeText == null ? "" : codeText.trim();
        final int port;
        try { port = Integer.parseInt(portText == null ? "" : portText.trim()); }
        catch (NumberFormatException invalid) { throw new Invalid(Reason.PORT); }
        if (host.isEmpty() || host.contains("://") || host.contains("/") || port < 1 || port > 65535)
            throw new Invalid(Reason.ADDRESS);
        if (!code.matches("[0-9]{6}")) throw new Invalid(Reason.CODE);
        return new LanConnectionRequest(host, port, code);
    }
}

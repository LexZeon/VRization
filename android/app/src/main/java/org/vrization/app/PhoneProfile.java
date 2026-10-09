package org.vrization.app;

import java.util.Map;
import org.vrization.core.VrSettings;

/** Complete committed phone settings; editor drafts never enter this profile. */
final class PhoneProfile {
    static final String DEFAULT_LANGUAGE = "en", DEFAULT_TRANSPORT = "usb", DEFAULT_HOST = "", DEFAULT_PORT = "8765";
    private VrSettings settings;
    private boolean saved;
    PhoneProfile(Map<String, Object> restored) {
        settings = restored == null ? new VrSettings() : SettingsValues.decode(restored, new VrSettings(), true);
        saved = restored != null;
    }
    VrSettings snapshot() { return settings.copy(); }
    boolean hasSavedProfile() { return saved; }
    void commit(VrSettings value) {
        settings = SettingsValues.decode(SettingsValues.encode(value), new VrSettings(), true); saved = true;
    }
    VrSettings reset() { commit(new VrSettings()); return snapshot(); }
}

package org.vrization.core;

/** Local draft transaction: only save() returns changed committed values. No transport or storage. */
public final class HeadsetEdit {
    private final VrSettings entry;
    private final boolean nativeStereo;
    private VrSettings draft;
    private boolean active = true;
    public HeadsetEdit(VrSettings settings) { this(settings,false); }
    public HeadsetEdit(VrSettings settings, boolean nativeStereo) { entry = settings.copy(); draft = entry.copy(); this.nativeStereo=nativeStereo; }
    private void requireActive() { if (!active) throw new IllegalStateException("Editor already closed"); }
    public VrSettings draft() { requireActive(); return draft.copy(); }
    public VrSettings preview() {
        VrSettings value = draft();
        if (nativeStereo) return StereoProjection.viewingSettings(value);
        if (!VrSettings.ENHANCED_FIRST_PERSON.equals(value.mode)) { value.mode = "full"; value.distortion = 0; }
        return value;
    }
    public void update(VrSettings geometry) {
        requireActive(); draft.scale = geometry.scale; draft.offsetX = geometry.offsetX; draft.offsetY = geometry.offsetY;
        draft.eyeSeparation = geometry.eyeSeparation;
        draft.normalize();
    }
    public VrSettings save() { requireActive(); active = false; return draft.copy(); }
    public VrSettings discard() { requireActive(); active = false; return entry.copy(); }
}

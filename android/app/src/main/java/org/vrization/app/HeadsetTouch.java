package org.vrization.app;

import org.vrization.core.HeadsetGeometry;
import org.vrization.core.VrSettings;

/** Phone gesture policy, separate from the reusable mathematical geometry. */
final class HeadsetTouch {
    private HeadsetTouch() { }
    static VrSettings pan(VrSettings entry, float fingerDeltaX, float fingerDeltaY) {
        return HeadsetGeometry.pan(entry, -fingerDeltaX, fingerDeltaY);
    }
    static VrSettings resize(VrSettings entry, float imageAspect, float eyeAspect,
                             int signX, int signY, float fingerDeltaX, float fingerDeltaY) {
        return HeadsetGeometry.resize(entry, imageAspect, eyeAspect, signX, signY, fingerDeltaX, fingerDeltaY);
    }
}

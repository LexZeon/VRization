package org.vrization.core;

/** Tracks successfully allocated texture storage; reset when the GLES context changes. */
final class TextureStorage {
    private int width, height;
    private Object format;
    private boolean allocated;
    boolean needsAllocation(int width, int height, Object format) {
        return !allocated || this.width != width || this.height != height || this.format != format;
    }
    void allocated(int width, int height, Object format) {
        this.width = width; this.height = height; this.format = format; allocated = true;
    }
    void reset() { allocated = false; format = null; }
}

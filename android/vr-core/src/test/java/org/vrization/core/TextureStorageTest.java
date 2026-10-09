package org.vrization.core;

import org.junit.Test;
import static org.junit.Assert.*;

public final class TextureStorageTest {
    @Test public void sameStorageCanBeUpdatedButResizeAndFormatNeedAllocation() {
        TextureStorage storage = new TextureStorage(); Object rgb565 = new Object(), rgba = new Object();
        assertTrue(storage.needsAllocation(360, 640, rgb565));
        storage.allocated(360, 640, rgb565);
        assertFalse(storage.needsAllocation(360, 640, rgb565));
        assertTrue(storage.needsAllocation(640, 360, rgb565));
        assertTrue(storage.needsAllocation(360, 640, rgba));
        storage.allocated(640, 360, rgba);
        assertFalse(storage.needsAllocation(640, 360, rgba));
    }
    @Test public void contextRecreationRequiresAllocationBeforeAnySubimageUpdate() {
        TextureStorage storage = new TextureStorage(); Object format = new Object();
        storage.allocated(640, 360, format); storage.reset();
        assertTrue(storage.needsAllocation(640, 360, format));
        storage.allocated(640, 360, format);
        assertFalse(storage.needsAllocation(640, 360, format));
    }
}

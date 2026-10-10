package org.vrization.app;

import org.junit.Test;
import org.vrization.core.HeadsetEdit;
import org.vrization.core.HeadsetGeometry;
import org.vrization.core.StereoProjection;
import org.vrization.core.VrSettings;
import static org.junit.Assert.*;

public final class StereoProjectionTest {
    @Test public void perEyeAspectUsesHalfThePackedWidth() {
        assertEquals(1,StereoProjection.eyeAspect(2048,1024),0);
        assertEquals(16f/9,StereoProjection.eyeAspect(1920,540),0.000001);
    }
    @Test public void mismatchedOrOversizedEyesAreRejectedInsteadOfCpuResamplingTheSeam() {
        for(int[] size:new int[][]{{1,1},{1919,540},{2049,1080},{2048,2049},{0,0},{-2,100}})
            assertFalse(StereoProjection.validDimensions(size[0],size[1],2048));
        assertTrue(StereoProjection.validDimensions(2048,1024,2048));
        assertThrows(IllegalArgumentException.class,()->StereoProjection.eyeAspect(1919,540));
    }
    @Test public void eachEyeCenterSamplesOnlyItsOwnImage() {
        assertEquals(.25,StereoProjection.sourceU(0,0,2048),0); assertEquals(.75,StereoProjection.sourceU(0,1,2048),0);
    }
    @Test public void bothEdgesClampToPixelCentersInsideEachHalf() {
        for(int width:new int[]{2,64,1024,2048}) {
            float halfTexel=.5f/width;
            assertEquals(.5f-halfTexel,StereoProjection.sourceU(1,0,width),0);
            assertEquals(.5f+halfTexel,StereoProjection.sourceU(-1,1,width),0);
            assertEquals(halfTexel,StereoProjection.sourceU(-1,0,width),0);
            assertEquals(1-halfTexel,StereoProjection.sourceU(1,1,width),0);
            for(float x:new float[]{-1,-.99f,-.2f,0,.8f,.99f,1}) {
                assertTrue(StereoProjection.sourceU(x,0,width)<.5); assertTrue(StereoProjection.sourceU(x,1,width)>.5);
            }
        }
    }
    @Test public void malformedSamplesCannotReadTheOppositeEye() {
        for(float x:new float[]{-2,2,Float.NaN,Float.POSITIVE_INFINITY})
            assertThrows(IllegalArgumentException.class,()->StereoProjection.sourceU(x,0,64));
        assertThrows(IllegalArgumentException.class,()->StereoProjection.sourceU(0,2,64));
        assertThrows(IllegalArgumentException.class,()->StereoProjection.sourceU(0,0,63));
    }
    @Test public void nativeCompositorBypassesBothSceneProjectionsButKeepsOneLensCorrection() {
        for(String mode:new String[]{"cinema",VrSettings.ENHANCED_FIRST_PERSON,"fps","full"}) {
            VrSettings saved=new VrSettings(); saved.mode=mode; saved.distortion=.23f;
            VrSettings viewing=StereoProjection.viewingSettings(saved);
            assertEquals("full",viewing.mode); assertEquals(.23f,viewing.distortion,0); assertEquals(mode,saved.mode);
            assertEquals(16f/9,viewing.contentAspect(16f/9),0); // Enhanced does not force native SBS square.
        }
    }
    @Test public void nativeEditorBoundsMatchViewerAndSavingKeepsThePersistentMode() {
        VrSettings saved=new VrSettings(); saved.mode=VrSettings.ENHANCED_FIRST_PERSON; saved.distortion=.2f;
        HeadsetEdit editor=new HeadsetEdit(saved,true); VrSettings draft=editor.draft(); draft.scale=.6f; draft.offsetX=.15f;
        editor.update(draft); VrSettings preview=editor.preview();
        assertEquals(.2f,preview.distortion,0);
        assertArrayEquals(HeadsetGeometry.bounds(StereoProjection.viewingSettings(draft),16f/9,1,1),
            HeadsetGeometry.bounds(preview,16f/9,1,1),0);
        VrSettings result=editor.save(); assertEquals(VrSettings.ENHANCED_FIRST_PERSON,result.mode); assertEquals(.6f,result.scale,0);
        assertEquals(VrSettings.ENHANCED_FIRST_PERSON,saved.mode); assertEquals(.85f,saved.scale,0);
    }
    @Test public void discardRestoresAllFitSettingsAndTheOriginalMode() {
        VrSettings saved=new VrSettings(); saved.mode="cinema"; saved.eyeSeparation=-.4f;
        HeadsetEdit editor=new HeadsetEdit(saved,true); VrSettings draft=editor.draft(); draft.scale=.5f; draft.eyeSeparation=0;
        editor.update(draft); VrSettings restored=editor.discard();
        assertEquals("cinema",restored.mode); assertEquals(saved.scale,restored.scale,0); assertEquals(-.4f,restored.eyeSeparation,0);
    }
}

package org.vrization.app;

import android.app.Activity;
import android.app.Instrumentation;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.opengl.EGL14;
import android.opengl.EGLConfig;
import android.opengl.EGLContext;
import android.opengl.EGLDisplay;
import android.opengl.EGLSurface;
import android.opengl.GLES20;
import android.os.Bundle;
import android.util.Log;
import java.nio.ByteBuffer;
import org.vrization.core.HeadsetGeometry;
import org.vrization.core.VrRenderer;
import org.vrization.core.VrSettings;
import org.vrization.core.EnhancedProjection;
import org.vrization.core.StereoProjection;

/** Default: offscreen GLES2 probe with synthetic pixels and no Activity/network/device input.
 * Optional -e connectionProbe true exercises real USB buttons and streaming, without mouse output.
 * Run the separately built test APK through platform Instrumentation. A compilation
 * pass alone does not establish a real-driver rendering pass.
 */
public final class RenderMaskProbe extends Instrumentation {
    private static final int WIDTH = 257, HEIGHT = 128; // Different per-eye widths.
    private Bundle arguments;

    @Override public void onCreate(Bundle arguments) {
        super.onCreate(arguments); this.arguments = arguments == null ? new Bundle() : new Bundle(arguments); start();
    }

    @Override public void onStart() {
        Bundle result = new Bundle();
        try {
            if ("true".equals(String.valueOf(arguments.get("connectionProbe")))) {
                result = ConnectionProbe.run(this, "true".equals(String.valueOf(arguments.get("pcStopProbe"))));
                finish(Activity.RESULT_OK, result); return;
            }
            int[] cases = renderCases();
            result.putInt("renderCases", cases[0]); result.putInt("enhancedProjectionSamples", cases[1]);
            result.putInt("nativeStereoColorSamples", cases[2]); result.putInt("nativeStereoLifecycleCases", cases[3]);
            result.putInt("orientationRemapGoldens", cases[4]);
            result.putString("stream", "\nOK (" + cases[0] + " offscreen GLES mask cases, both eyes; "
                + cases[1] + " enhanced projection color samples; " + cases[2] + " native stereo color samples; "
                + cases[3] + " native stereo lifecycle cases; " + cases[4] + " Android orientation remap goldens)\n");
            finish(Activity.RESULT_OK, result);
        } catch (Throwable error) {
            result.putString("stream", "\nFAIL: " + Log.getStackTraceString(error));
            finish(Activity.RESULT_CANCELED, result);
        }
    }

    private static int[] renderCases() {
        EGLDisplay display = EGL14.eglGetDisplay(EGL14.EGL_DEFAULT_DISPLAY);
        EGLContext context = EGL14.EGL_NO_CONTEXT;
        EGLSurface surface = EGL14.EGL_NO_SURFACE;
        boolean initialized = false;
        VrRenderer renderer = new VrRenderer();
        try {
            require(display != EGL14.EGL_NO_DISPLAY, "No EGL display");
            int[] versions = new int[2];
            require(EGL14.eglInitialize(display, versions, 0, versions, 1), "EGL initialize");
            initialized = true;
            int[] attributes = {EGL14.EGL_SURFACE_TYPE, EGL14.EGL_PBUFFER_BIT,
                EGL14.EGL_RENDERABLE_TYPE, EGL14.EGL_OPENGL_ES2_BIT,
                EGL14.EGL_RED_SIZE, 8, EGL14.EGL_GREEN_SIZE, 8, EGL14.EGL_BLUE_SIZE, 8,
                EGL14.EGL_ALPHA_SIZE, 8, EGL14.EGL_NONE};
            EGLConfig[] configs = new EGLConfig[1]; int[] count = new int[1];
            require(EGL14.eglChooseConfig(display, attributes, 0, configs, 0, 1, count, 0)
                && count[0] > 0, "No EGL2 pbuffer config");
            context = EGL14.eglCreateContext(display, configs[0], EGL14.EGL_NO_CONTEXT,
                new int[]{EGL14.EGL_CONTEXT_CLIENT_VERSION, 2, EGL14.EGL_NONE}, 0);
            require(context != EGL14.EGL_NO_CONTEXT, "EGL context");
            surface = EGL14.eglCreatePbufferSurface(display, configs[0],
                new int[]{EGL14.EGL_WIDTH, WIDTH, EGL14.EGL_HEIGHT, HEIGHT, EGL14.EGL_NONE}, 0);
            require(surface != EGL14.EGL_NO_SURFACE, "EGL pbuffer");
            require(EGL14.eglMakeCurrent(display, surface, surface, context), "EGL make current");
            renderer.onSurfaceCreated(null, null);
            renderer.onSurfaceChanged(null, WIDTH, HEIGHT);
            ByteBuffer pixels = ByteBuffer.allocateDirect(WIDTH * HEIGHT * 4);
            int cases = 0;
            for (float imageAspect : new float[]{1f, .5f, 16f / 9}) {
                Bitmap image = Bitmap.createBitmap(imageAspect > 1 ? 32 : 16,
                    imageAspect > 1 ? 18 : imageAspect == 1f ? 16 : 32, Bitmap.Config.ARGB_8888);
                image.eraseColor(Color.WHITE);
                renderer.submitFrame(image);
                for (String mode : new String[]{"full", "cinema", "fps", VrSettings.ENHANCED_FIRST_PERSON})
                    for (float scale : new float[]{.5f, .85f})
                        for (float offset : new float[]{0f, .1f})
                            for (float distortion : new float[]{0f, .3f})
                                for (float spacing : new float[]{.03f, -1f})
                                    for (float yaw : new float[]{-.8f, 0f, .8f}) {
                                        VrSettings settings = new VrSettings();
                                        settings.mode = mode; settings.scale = scale;
                                        settings.offsetX = offset; settings.offsetY = offset;
                                        settings.distortion = distortion; settings.eyeSeparation = spacing;
                                        renderer.setSettings(settings); renderer.setPose(yaw, .2f, 0f);
                                        renderer.onDrawFrame(null);
                                        pixels.clear();
                                        GLES20.glReadPixels(0, 0, WIDTH, HEIGHT, GLES20.GL_RGBA,
                                            GLES20.GL_UNSIGNED_BYTE, pixels);
                                        require(GLES20.glGetError() == GLES20.GL_NO_ERROR, "GLES error");
                                        String label = mode + " aspect=" + imageAspect + " scale=" + scale
                                            + " offset=" + offset + " distortion=" + distortion
                                            + " spacing=" + spacing + " yaw=" + yaw;
                                        assertMask(pixels, settings, imageAspect, label);
                                        cases++;
                                    }
                require(image.isRecycled(), "Renderer did not release transferred Bitmap");
            }
            int enhancedSamples = assertEnhancedProjection(renderer, pixels);
            int stereoSamples = ClientVariant.EXPERIMENTAL ? assertNativeStereo(renderer, pixels) : 0;
            int stereoLifecycle = ClientVariant.EXPERIMENTAL ? assertStereoLifecycle(renderer, pixels) : 0;
            int orientationGoldens = ClientVariant.EXPERIMENTAL ? OrientationProbe.run() : 0;
            return new int[]{cases, enhancedSamples, stereoSamples, stereoLifecycle, orientationGoldens};
        } finally {
            renderer.pauseFrames();
            if (initialized) {
                EGL14.eglMakeCurrent(display, EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_CONTEXT);
                if (surface != EGL14.EGL_NO_SURFACE) EGL14.eglDestroySurface(display, surface);
                if (context != EGL14.EGL_NO_CONTEXT) EGL14.eglDestroyContext(display, context);
                EGL14.eglTerminate(display);
            }
            EGL14.eglReleaseThread();
        }
    }

    /** Compare real shader pixels with normalized source coordinates, without CPU frame warping. */
    private static int assertEnhancedProjection(VrRenderer renderer, ByteBuffer pixels) {
        Bitmap image = Bitmap.createBitmap(320, 180, Bitmap.Config.ARGB_8888);
        for (int y = 0; y < image.getHeight(); y++) for (int x = 0; x < image.getWidth(); x++)
            image.setPixel(x, y, Color.rgb(Math.round(255f * x / (image.getWidth() - 1)),
                Math.round(255f * y / (image.getHeight() - 1)), 180));
        renderer.submitFrame(image);
        float[][] locations = {{0,0}, {.5f,0}, {-.5f,0}, {0,.5f}, {.25f,.5f}, {.8f,.8f},
            {-.8f,-.8f}, {.99f,.99f}, {-.99f,.99f}};
        int samples = 0;
        for (float fov : new float[]{50, 80, 110}) for (float scale : new float[]{.5f, .85f}) {
            VrSettings settings = new VrSettings(); settings.mode = VrSettings.ENHANCED_FIRST_PERSON;
            settings.fov = fov; settings.scale = scale;
            if (scale == .5f) { settings.offsetX = .1f; settings.offsetY = -.12f; settings.eyeSeparation = -.4f; }
            renderer.setSettings(settings); renderer.onDrawFrame(null);
            pixels.clear(); GLES20.glReadPixels(0, 0, WIDTH, HEIGHT, GLES20.GL_RGBA, GLES20.GL_UNSIGNED_BYTE, pixels);
            require(GLES20.glGetError() == GLES20.GL_NO_ERROR, "Enhanced GLES error");
            for (int eye = 0; eye < 2; eye++) {
                int eyeWidth = eye == 0 ? WIDTH / 2 : WIDTH - WIDTH / 2;
                int origin = eye == 0 ? 0 : WIDTH / 2;
                float[] b = HeadsetGeometry.bounds(settings, 16f / 9, eyeWidth / (float)HEIGHT, eye == 0 ? -1 : 1);
                for (float[] location : locations) {
                    int x = Math.round(eyeWidth * (1 + b[0] + location[0] * b[2]) / 2 - .5f);
                    int y = Math.round(HEIGHT * (1 + b[1] + location[1] * b[3]) / 2 - .5f);
                    require(x >= 0 && x < eyeWidth && y >= 0 && y < HEIGHT, "Bad projection probe position");
                    float qx = (2f * (x + .5f) / eyeWidth - 1 - b[0]) / b[2];
                    float qy = (2f * (y + .5f) / HEIGHT - 1 - b[1]) / b[3];
                    float[] source = EnhancedProjection.source(qx, qy, fov);
                    int at = (y * WIDTH + origin + x) * 4;
                    int r = pixels.get(at) & 255, g = pixels.get(at + 1) & 255, blue = pixels.get(at + 2) & 255;
                    String label = "Enhanced fov=" + fov + " scale=" + scale + " eye=" + eye + " q=" + qx + "," + qy;
                    if (source == null) require(r <= 3 && g <= 3 && blue <= 3, label + " corner must be black");
                    else {
                        int expectedR = Math.round(255 * (.5f + source[0] * .5f));
                        int expectedG = Math.round(255 * (.5f - source[1] * .5f));
                        require(Math.abs(r - expectedR) <= 4 && Math.abs(g - expectedG) <= 4 && Math.abs(blue - 180) <= 4,
                            label + " source orientation/warp mismatch: " + r + "," + g + "," + blue);
                    }
                    samples++;
                }
            }
        }
        require(image.isRecycled(), "Enhanced texture ownership was not released");
        return samples;
    }

    private static void assertMask(ByteBuffer pixels, VrSettings settings, float aspect, String label) {
        int leftWidth = WIDTH / 2;
        for (int eye = 0; eye < 2; eye++) {
            int width = eye == 0 ? leftWidth : WIDTH - leftWidth;
            int origin = eye == 0 ? 0 : leftWidth;
            float[] bounds = HeadsetGeometry.bounds(settings, aspect, (float) width / HEIGHT, eye == 0 ? -1 : 1);
            int outside = 0, whiteInside = 0;
            for (int y = 0; y < HEIGHT; y++) for (int x = 0; x < width; x++) {
                float px = 2f * (x + .5f) / width - 1f;
                float py = 2f * (y + .5f) / HEIGHT - 1f;
                float dx = Math.abs(px - bounds[0]), dy = Math.abs(py - bounds[1]);
                int at = (y * WIDTH + origin + x) * 4;
                int r = pixels.get(at) & 255, g = pixels.get(at + 1) & 255, b = pixels.get(at + 2) & 255;
                if (dx > bounds[2] + .02f || dy > bounds[3] + .02f) {
                    if (r > 3 || g > 3 || b > 3)
                        throw new AssertionError(label + " eye=" + eye + " outside pixel " + x + "," + y);
                    outside++;
                } else if (dx <= bounds[2] && dy <= bounds[3] && r >= 250 && g >= 250 && b >= 250) {
                    whiteInside++;
                }
            }
            require(outside > 20, label + " did not sample outside the saved viewport");
            require(whiteInside > 8, label + " eye=" + eye + " has no genuine white video pixels inside");
        }
    }

    /** Distinct eye gradients reveal swapped halves, seam bleed, aspect errors and double projection. */
    private static int assertNativeStereo(VrRenderer renderer, ByteBuffer pixels) {
        renderer.setStreamLayout(true, true);
        float[][] probes = {{0,0},{-.8f,0},{.8f,0},{0,.8f},{0,-.8f},{.8f,.8f},{-.99f,0},{.99f,0}};
        int samples = 0;
        for (int imageHeight : new int[]{32,64}) {
            Bitmap image = Bitmap.createBitmap(128,imageHeight,Bitmap.Config.ARGB_8888);
            for(int y=0;y<imageHeight;y++)for(int x=0;x<128;x++) {
                int ramp=Math.round(40+180f*(x%64)/63), green=Math.round(30+180f*y/(imageHeight-1));
                image.setPixel(x,y,x<64?Color.rgb(ramp,green,10):Color.rgb(10,green,ramp));
            }
            renderer.submitFrame(image);
            for(String mode:new String[]{"full","fps","cinema",VrSettings.ENHANCED_FIRST_PERSON})
                for(float scale:new float[]{.5f,.85f})for(float distortion:new float[]{0,.15f}) {
                    VrSettings saved=new VrSettings(); saved.mode=mode; saved.scale=scale; saved.distortion=distortion;
                    if(scale==.5f) { saved.offsetX=.08f; saved.offsetY=-.08f; saved.eyeSeparation=-.4f; }
                    renderer.setSettings(saved); renderer.setPose(.8f,.9f,.4f); renderer.onDrawFrame(null);
                    readPixels(pixels); VrSettings nativeSettings=StereoProjection.viewingSettings(saved);
                    for(int eye=0;eye<2;eye++) {
                        int eyeWidth=eye==0?WIDTH/2:WIDTH-WIDTH/2, origin=eye==0?0:WIDTH/2;
                        float aspect=StereoProjection.eyeAspect(128,imageHeight), eyeAspect=eyeWidth/(float)HEIGHT;
                        float[] b=HeadsetGeometry.bounds(nativeSettings,aspect,eyeAspect,eye==0?-1:1);
                        float fitX=Math.min(1,aspect/eyeAspect),fitY=Math.min(1,eyeAspect/aspect);
                        for(float[] probe:probes) {
                            int x=Math.round(eyeWidth*(1+b[0]+probe[0]*b[2])/2-.5f);
                            int y=Math.round(HEIGHT*(1+b[1]+probe[1]*b[3])/2-.5f);
                            require(x>=0&&x<eyeWidth&&y>=0&&y<HEIGHT,"Invalid stereo probe position");
                            float px=2f*(x+.5f)/eyeWidth-1,py=2f*(y+.5f)/HEIGHT-1;
                            float d=1+distortion*(px*px+py*py);
                            float qx=(px*d-b[0])/saved.scale/fitX,qy=(py*d-b[1])/saved.scale/fitY;
                            int at=(y*WIDTH+origin+x)*4,r=pixels.get(at)&255,g=pixels.get(at+1)&255,blue=pixels.get(at+2)&255;
                            String label="Native stereo "+mode+" scale="+scale+" distortion="+distortion+" eye="+eye+" q="+qx+","+qy;
                            if(Math.abs(qx)>1||Math.abs(qy)>1||Math.abs(px-b[0])>b[2]||Math.abs(py-b[1])>b[3])
                                require(r<=3&&g<=3&&blue<=3,label+" must be black");
                            else {
                                float u=StereoProjection.sourceU(qx,eye,128),localU=(u-eye*.5f)*2;
                                float sx=Math.max(0,Math.min(1,(localU*64-.5f)/63));
                                float sy=Math.max(0,Math.min(1,((.5f-qy*.5f)*imageHeight-.5f)/(imageHeight-1)));
                                int ramp=Math.round(40+180*sx),green=Math.round(30+180*sy);
                                int expectedR=eye==0?ramp:10,expectedB=eye==0?10:ramp;
                                require(Math.abs(r-expectedR)<=4&&Math.abs(g-green)<=4&&Math.abs(blue-expectedB)<=4,
                                    label+" swapped/warped/seam pixel "+r+","+g+","+blue);
                            }
                            samples++;
                        }
                    }
                }
            require(image.isRecycled(),"Native stereo bitmap ownership leak");
        }
        return samples;
    }

    private static int assertStereoLifecycle(VrRenderer renderer, ByteBuffer pixels) {
        renderer.clearFrames(); renderer.resumeFrames(); renderer.setStreamLayout(true,false);
        Bitmap pending=Bitmap.createBitmap(64,32,Bitmap.Config.ARGB_8888); pending.eraseColor(Color.WHITE);
        renderer.submitFrame(pending); require(pending.isRecycled(),"Unnegotiated frame must be dropped");
        renderer.onDrawFrame(null); readPixels(pixels); requireBlack(pixels,"Unaccepted SBS displayed");
        renderer.setStreamLayout(true,true); renderer.onDrawFrame(null); readPixels(pixels);
        requireBlack(pixels,"Pre-acceptance frame survived negotiation");
        Bitmap odd=Bitmap.createBitmap(63,32,Bitmap.Config.ARGB_8888); odd.eraseColor(Color.WHITE);
        renderer.submitFrame(odd); renderer.onDrawFrame(null); readPixels(pixels);
        require(odd.isRecycled(),"Odd SBS ownership leak"); requireBlack(pixels,"Odd SBS displayed");
        Bitmap old=Bitmap.createBitmap(64,32,Bitmap.Config.ARGB_8888); old.eraseColor(Color.WHITE);
        renderer.submitFrame(old); renderer.setStreamLayout(false,true);
        require(old.isRecycled(),"Route change retained a queued old-layout frame");
        renderer.onDrawFrame(null); readPixels(pixels); requireBlack(pixels,"Old SBS survived mono route change");
        renderer.clearFrames(); Bitmap late=Bitmap.createBitmap(64,32,Bitmap.Config.ARGB_8888);
        renderer.submitFrame(late); require(late.isRecycled(),"Late disconnect frame was accepted");
        renderer.onDrawFrame(null); readPixels(pixels); requireBlack(pixels,"Disconnect retained video");
        return 5;
    }
    private static void readPixels(ByteBuffer pixels) {
        pixels.clear(); GLES20.glReadPixels(0,0,WIDTH,HEIGHT,GLES20.GL_RGBA,GLES20.GL_UNSIGNED_BYTE,pixels);
        require(GLES20.glGetError()==GLES20.GL_NO_ERROR,"Stereo GLES error");
    }
    private static void requireBlack(ByteBuffer pixels,String label) {
        for(int at=0;at<WIDTH*HEIGHT*4;at+=4)
            require((pixels.get(at)&255)<=3&&(pixels.get(at+1)&255)<=3&&(pixels.get(at+2)&255)<=3,label);
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}

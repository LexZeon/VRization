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
            int cases = renderCases();
            result.putInt("renderCases", cases);
            result.putString("stream", "\nOK (" + cases + " offscreen GLES mask cases, both eyes)\n");
            finish(Activity.RESULT_OK, result);
        } catch (Throwable error) {
            result.putString("stream", "\nFAIL: " + Log.getStackTraceString(error));
            finish(Activity.RESULT_CANCELED, result);
        }
    }

    private static int renderCases() {
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
            for (float imageAspect : new float[]{1f, .5f}) {
                Bitmap image = Bitmap.createBitmap(16, imageAspect == 1f ? 16 : 32, Bitmap.Config.ARGB_8888);
                image.eraseColor(Color.WHITE);
                renderer.submitFrame(image);
                for (String mode : new String[]{"full", "cinema", "fps"})
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
            return cases;
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

    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}

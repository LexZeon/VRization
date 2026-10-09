package org.vrization.core;

import android.graphics.Bitmap;
import android.opengl.GLES20;
import android.opengl.GLSurfaceView;
import android.opengl.GLUtils;
import android.os.SystemClock;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.FloatBuffer;
import java.util.HashMap;
import java.util.Map;
import javax.microedition.khronos.egl.EGLConfig;
import javax.microedition.khronos.opengles.GL10;

/** Reusable GLES2 stereo video surface, independent of transport and application UI. */
public final class VrRenderer implements GLSurfaceView.Renderer {
    /** Called on the GL thread after the texture upload call, before physical presentation. */
    public interface TextureSubmissionListener {
        void onSubmitted(long session, long receivedAtNanos, long submittedAtNanos);
    }
    private static final String[] UNIFORMS = {"uTexture", "uAspect", "uImageAspect", "uScale", "uOffsetX",
        "uOffsetY", "uEyeShift", "uEyeSign", "uDistortion", "uFov", "uDistance", "uYaw", "uPitch", "uRoll", "uCinema"};
    private static final String VERTEX =
        "attribute vec2 aPosition; varying vec2 vUv; void main(){vUv=(aPosition+1.0)*0.5; gl_Position=vec4(aPosition,0.0,1.0);}";
    private static final String FRAGMENT =
        "precision mediump float; varying vec2 vUv; uniform sampler2D uTexture;" +
        "uniform float uAspect,uImageAspect,uScale,uOffsetX,uOffsetY,uEyeShift,uEyeSign,uDistortion,uFov,uDistance,uYaw,uPitch,uRoll,uCinema;" +
        "void main(){" +
        "vec2 p=(vUv-0.5)*2.0; p*=1.0+uDistortion*dot(p,p);" +
        "p=(p-vec2(uOffsetX+uEyeShift,uOffsetY))/uScale; vec2 q;" +
        "if(uCinema>0.5){" +
        "float f=tan(radians(uFov)*0.5); vec3 r=normalize(vec3(p.x*uAspect*f,p.y*f,-1.0));" +
        "float cr=cos(uRoll),sr=sin(uRoll); r=vec3(cr*r.x+sr*r.y,-sr*r.x+cr*r.y,r.z);" +
        "float cp=cos(uPitch),sp=sin(uPitch); r=vec3(r.x,cp*r.y-sp*r.z,sp*r.y+cp*r.z);" +
        "float cy=cos(uYaw),sy=sin(uYaw); r=vec3(cy*r.x-sy*r.z,r.y,sy*r.x+cy*r.z);" +
        "if(r.z>=-0.001){gl_FragColor=vec4(0.0,0.0,0.0,1.0);return;}" +
        "vec2 hit=r.xy*(-uDistance/r.z)+vec2(uEyeSign*0.032,0.0); q=hit/vec2(2.0,2.0/uImageAspect);" +
        "}else{vec2 fit=vec2(min(1.0,uImageAspect/uAspect),min(1.0,uAspect/uImageAspect));q=p/fit;}" +
        "if(abs(q.x)>1.0||abs(q.y)>1.0){gl_FragColor=vec4(0.0,0.0,0.0,1.0);return;}" +
        "gl_FragColor=texture2D(uTexture,vec2(q.x*0.5+0.5,0.5-q.y*0.5));}";
    private final FloatBuffer vertices = ByteBuffer.allocateDirect(8 * 4).order(ByteOrder.nativeOrder()).asFloatBuffer();
    private final Object frameLock = new Object();
    private Bitmap pending;
    private long pendingSession, pendingReceivedAt = -1;
    private final TextureStorage storage = new TextureStorage();
    private final Map<String, Integer> uniforms = new HashMap<>();
    private volatile TextureSubmissionListener submissionListener;
    private boolean acceptingFrames = true;
    private volatile VrSettings settings = new VrSettings();
    private volatile float yaw, pitch, roll;
    private int program, texture, positionLocation, width, height, imageWidth = 16, imageHeight = 9, maxTextureSize = 2048;
    private boolean hasTexture;

    public VrRenderer() { vertices.put(new float[]{-1,-1, 1,-1, -1,1, 1,1}).position(0); }
    public void setSettings(VrSettings value) { VrSettings copy = value.copy(); copy.normalize(); settings = copy; }
    public void setPose(float yaw, float pitch) { this.yaw = yaw; this.pitch = pitch; }
    public void setPose(float yaw, float pitch, float roll) { this.yaw = yaw; this.pitch = pitch; this.roll = roll; }
    /** Transfers ownership. Every submitted Bitmap is recycled by this renderer. */
    public void submitFrame(Bitmap bitmap) { submitFrame(bitmap, 0, -1); }
    /** Optional phone-local timing metadata, using SystemClock.elapsedRealtimeNanos(). */
    public void submitFrame(Bitmap bitmap, long session, long receivedAtNanos) {
        if (bitmap == null) return;
        synchronized (frameLock) {
            if (!acceptingFrames) { bitmap.recycle(); return; }
            if (pending != null) pending.recycle();
            pending = bitmap; pendingSession = session; pendingReceivedAt = receivedAtNanos;
        }
    }
    public void setTextureSubmissionListener(TextureSubmissionListener listener) { submissionListener = listener; }
    /** Drop queued frames when Activity stops. A resumed renderer accepts frames again. */
    public void pauseFrames() {
        synchronized (frameLock) {
            acceptingFrames = false;
            if (pending != null) { pending.recycle(); pending = null; }
        }
    }
    public void resumeFrames() { synchronized (frameLock) { acceptingFrames = true; } }

    @Override public void onSurfaceCreated(GL10 unused, EGLConfig config) {
        program = GLES20.glCreateProgram();
        GLES20.glAttachShader(program, compile(GLES20.GL_VERTEX_SHADER, VERTEX));
        GLES20.glAttachShader(program, compile(GLES20.GL_FRAGMENT_SHADER, FRAGMENT));
        GLES20.glLinkProgram(program);
        int[] linked = new int[1]; GLES20.glGetProgramiv(program, GLES20.GL_LINK_STATUS, linked, 0);
        if (linked[0] == 0) throw new IllegalStateException("GLES link: " + GLES20.glGetProgramInfoLog(program));
        uniforms.clear();
        for (String name : UNIFORMS) uniforms.put(name, GLES20.glGetUniformLocation(program, name));
        positionLocation = GLES20.glGetAttribLocation(program, "aPosition");
        int[] textures = new int[1]; GLES20.glGenTextures(1, textures, 0); texture = textures[0];
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, texture);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_MIN_FILTER, GLES20.GL_LINEAR);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_MAG_FILTER, GLES20.GL_LINEAR);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_WRAP_S, GLES20.GL_CLAMP_TO_EDGE);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_WRAP_T, GLES20.GL_CLAMP_TO_EDGE);
        hasTexture = false; storage.reset();
        GLES20.glClearColor(0, 0, 0, 1);
        int[] maximum = new int[1]; GLES20.glGetIntegerv(GLES20.GL_MAX_TEXTURE_SIZE, maximum, 0);
        if (maximum[0] > 0) maxTextureSize = maximum[0];
    }
    @Override public void onSurfaceChanged(GL10 unused, int width, int height) { this.width = width; this.height = height; }
    @Override public void onDrawFrame(GL10 unused) {
        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT);
        Bitmap latest;
        long session, receivedAt;
        synchronized (frameLock) {
            latest = pending; session = pendingSession; receivedAt = pendingReceivedAt; pending = null;
        }
        if (latest != null) {
            if (latest.getWidth() > maxTextureSize || latest.getHeight() > maxTextureSize) {
                float factor = (float) maxTextureSize / Math.max(latest.getWidth(), latest.getHeight());
                Bitmap scaled = Bitmap.createScaledBitmap(latest, Math.max(1, Math.round(latest.getWidth() * factor)),
                    Math.max(1, Math.round(latest.getHeight() * factor)), true);
                latest.recycle(); latest = scaled;
            }
            GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, texture);
            imageWidth = latest.getWidth(); imageHeight = latest.getHeight();
            Bitmap.Config format = latest.getConfig();
            if (storage.needsAllocation(imageWidth, imageHeight, format)) {
                GLUtils.texImage2D(GLES20.GL_TEXTURE_2D, 0, latest, 0);
                storage.allocated(imageWidth, imageHeight, format);
            } else {
                GLUtils.texSubImage2D(GLES20.GL_TEXTURE_2D, 0, 0, 0, latest);
            }
            latest.recycle(); hasTexture = true;
            TextureSubmissionListener callback = submissionListener;
            if (callback != null && receivedAt >= 0) callback.onSubmitted(session, receivedAt, SystemClock.elapsedRealtimeNanos());
        }
        if (!hasTexture || width < 2 || height < 1) return;
        VrSettings current = settings;
        GLES20.glUseProgram(program);
        GLES20.glActiveTexture(GLES20.GL_TEXTURE0); GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, texture);
        GLES20.glUniform1i(uniforms.get("uTexture"), 0);
        int position = positionLocation;
        vertices.position(0); GLES20.glEnableVertexAttribArray(position);
        GLES20.glVertexAttribPointer(position, 2, GLES20.GL_FLOAT, false, 0, vertices);
        uniform("uImageAspect", (float) imageWidth / imageHeight); uniform("uScale", current.scale);
        uniform("uOffsetX", current.offsetX); uniform("uOffsetY", current.offsetY);
        uniform("uDistortion", current.distortion); uniform("uFov", current.fov); uniform("uDistance", current.distance);
        uniform("uYaw", yaw); uniform("uPitch", pitch); uniform("uRoll", roll);
        uniform("uCinema", "cinema".equals(current.mode) ? 1 : 0);
        int leftWidth = width / 2;
        for (int eye = 0; eye < 2; eye++) {
            int eyeWidth = eye == 0 ? leftWidth : width - leftWidth;
            GLES20.glViewport(eye == 0 ? 0 : leftWidth, 0, eyeWidth, height);
            uniform("uAspect", (float) eyeWidth / height);
            uniform("uEyeSign", eye == 0 ? -1 : 1);
            uniform("uEyeShift", current.eyeSeparation * (eye == 0 ? -1 : 1));
            GLES20.glDrawArrays(GLES20.GL_TRIANGLE_STRIP, 0, 4);
        }
        GLES20.glDisableVertexAttribArray(position);
    }
    private void uniform(String name, float value) { GLES20.glUniform1f(uniforms.get(name), value); }
    private static int compile(int type, String source) {
        int shader = GLES20.glCreateShader(type); GLES20.glShaderSource(shader, source); GLES20.glCompileShader(shader);
        int[] status = new int[1]; GLES20.glGetShaderiv(shader, GLES20.GL_COMPILE_STATUS, status, 0);
        if (status[0] == 0) throw new IllegalStateException("GLES shader: " + GLES20.glGetShaderInfoLog(shader));
        return shader;
    }
}

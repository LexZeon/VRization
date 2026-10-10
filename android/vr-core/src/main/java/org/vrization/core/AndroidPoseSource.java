package org.vrization.core;

import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.view.Display;
import android.view.Surface;

/** Android framework tracking; works without Google Play services. */
public final class AndroidPoseSource implements PoseSource, SensorEventListener {
    private final SensorManager manager;
    private final Sensor sensor;
    private final Display display;
    private final float[] rotation = new float[9];
    private final float[] screenRotation = new float[9];
    private Listener listener;
    public interface OrientationListener { void onOrientation(float[] xyzw, long timestampNanos); }
    private OrientationListener orientationListener;
    private final OrientationMath.Center orientationCenter = new OrientationMath.Center();
    private final PoseMath.RotationCenter center = new PoseMath.RotationCenter();
    private long lastEmit;

    public AndroidPoseSource(Context context, Display display) {
        this.display = display;
        manager = (SensorManager) context.getSystemService(Context.SENSOR_SERVICE);
        Sensor preferred = manager.getDefaultSensor(Sensor.TYPE_GAME_ROTATION_VECTOR);
        sensor = preferred != null ? preferred : manager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR);
    }

    @Override public boolean isAvailable() { return sensor != null; }
    @Override public void start(Listener listener) {
        stop(); this.listener = listener;
        if (sensor != null) manager.registerListener(this, sensor, SensorManager.SENSOR_DELAY_GAME);
    }
    public void startOrientation(OrientationListener listener) {
        stop(); orientationListener=listener; if(sensor!=null)manager.registerListener(this,sensor,SensorManager.SENSOR_DELAY_GAME);
    }
    @Override public void stop() { manager.unregisterListener(this); listener = null; orientationListener=null; }
    @Override public void recenter() { center.recenter(); orientationCenter.recenter(); lastEmit = 0; }

    @Override public void onSensorChanged(SensorEvent event) {
        SensorManager.getRotationMatrixFromVector(rotation, event.values);
        int x = SensorManager.AXIS_X, y = SensorManager.AXIS_Y;
        switch (display.getRotation()) {
            case Surface.ROTATION_90: x = SensorManager.AXIS_Y; y = SensorManager.AXIS_MINUS_X; break;
            case Surface.ROTATION_180: x = SensorManager.AXIS_MINUS_X; y = SensorManager.AXIS_MINUS_Y; break;
            case Surface.ROTATION_270: x = SensorManager.AXIS_MINUS_Y; y = SensorManager.AXIS_X; break;
            default: break;
        }
        if (!SensorManager.remapCoordinateSystem(rotation, x, y, screenRotation)) return;
        for (float value : screenRotation) if (Float.isNaN(value) || Float.isInfinite(value)) return;
        if (event.timestamp - lastEmit < 16_666_667L) return;
        lastEmit = event.timestamp;
        if (orientationListener != null) {
            try { orientationListener.onOrientation(orientationCenter.sample(screenRotation), event.timestamp); }
            catch (IllegalArgumentException invalidSample) { /* Invalid fusion output is never tracking. */ }
            return;
        }
        float[] relative = center.sample(screenRotation);
        if (listener != null) listener.onPose(relative[0], relative[1], relative[2], event.timestamp);
    }
    @Override public void onAccuracyChanged(Sensor sensor, int accuracy) { }
}

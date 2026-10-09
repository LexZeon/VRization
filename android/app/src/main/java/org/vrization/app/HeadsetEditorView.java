package org.vrization.app;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.view.MotionEvent;
import android.view.View;
import org.vrization.core.HeadsetEdit;
import org.vrization.core.HeadsetGeometry;
import org.vrization.core.VrSettings;

/** Transparent touch overlay above the live stereo surface; no network or preferences. */
final class HeadsetEditorView extends View {
    interface AspectSource { float get(); }
    private static final int[] SIGN_X = {-1, 1, -1, 1}, SIGN_Y = {1, 1, -1, -1};
    private final HeadsetEdit edit;
    private final AspectSource imageAspect;
    private final Runnable changed;
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final float radius, hitRadius;
    private VrSettings gestureStart;
    private int eye, corner = -1, pointer = -1;
    private float downX, downY, topReserved, gestureImageAspect, gestureEyeAspect;

    HeadsetEditorView(Context context, HeadsetEdit edit, AspectSource imageAspect, Runnable changed) {
        super(context); this.edit = edit; this.imageAspect = imageAspect; this.changed = changed;
        float density = getResources().getDisplayMetrics().density;
        radius = 12 * density; hitRadius = 28 * density;
        setContentDescription(context.getString(R.string.editor_gestures)); setFocusable(true);
    }
    void reserveTop(float pixels) { topReserved = pixels; invalidate(); }
    private int eyeWidth(int index) { return index == 0 ? getWidth() / 2 : getWidth() - getWidth() / 2; }
    private int eyeLeft(int index) { return index == 0 ? 0 : getWidth() / 2; }
    private RectF rectangle(int index) {
        float width = eyeWidth(index);
        float[] b = HeadsetGeometry.bounds(edit.draft(), imageAspect.get(), width / getHeight(), index == 0 ? -1 : 1);
        float centerX = eyeLeft(index) + width * (1 + b[0]) / 2;
        float centerY = getHeight() * (1 - b[1]) / 2;
        return new RectF(centerX - width * b[2] / 2, centerY - getHeight() * b[3] / 2,
            centerX + width * b[2] / 2, centerY + getHeight() * b[3] / 2);
    }
    private float handleX(RectF rect, int index, int handle) {
        return Math.max(eyeLeft(index) + radius, Math.min(eyeLeft(index) + eyeWidth(index) - radius,
            SIGN_X[handle] < 0 ? rect.left : rect.right));
    }
    private float handleY(RectF rect, int handle) {
        return Math.max(Math.min(getHeight() - radius, topReserved + radius),
            Math.min(getHeight() - radius, SIGN_Y[handle] > 0 ? rect.top : rect.bottom));
    }
    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        if (getHeight() == 0 || getWidth() < 2) return;
        paint.setStrokeWidth(2 * getResources().getDisplayMetrics().density);
        paint.setColor(Color.argb(200, 70, 212, 185)); paint.setStyle(Paint.Style.STROKE);
        canvas.drawLine(getWidth() / 2f, topReserved, getWidth() / 2f, getHeight(), paint);
        for (int index = 0; index < 2; index++) {
            canvas.save(); canvas.clipRect(eyeLeft(index), 0, eyeLeft(index) + eyeWidth(index), getHeight());
            RectF rect = rectangle(index);
            paint.setStyle(Paint.Style.FILL); paint.setColor(Color.argb(25, 70, 212, 185)); canvas.drawRect(rect, paint);
            paint.setStyle(Paint.Style.STROKE); paint.setColor(Color.rgb(70, 212, 185)); canvas.drawRect(rect, paint);
            paint.setStyle(Paint.Style.FILL);
            for (int handle = 0; handle < 4; handle++) canvas.drawCircle(handleX(rect, index, handle), handleY(rect, handle), radius, paint);
            canvas.restore();
        }
    }
    @Override public boolean onTouchEvent(MotionEvent event) {
        if (getHeight() == 0 || getWidth() < 2) return false;
        if (event.getActionMasked() == MotionEvent.ACTION_DOWN) {
            eye = event.getX() < getWidth() / 2 ? 0 : 1;
            RectF rect = rectangle(eye); corner = -1;
            for (int handle = 0; handle < 4; handle++) {
                double dx = event.getX() - handleX(rect, eye, handle), dy = event.getY() - handleY(rect, handle);
                if (dx * dx + dy * dy <= hitRadius * hitRadius) { corner = handle; break; }
            }
            if (corner < 0 && !rect.contains(event.getX(), event.getY())) return false;
            gestureStart = edit.draft(); downX = event.getX(); downY = event.getY(); pointer = event.getPointerId(0);
            gestureImageAspect = imageAspect.get(); gestureEyeAspect = (float) eyeWidth(eye) / getHeight();
            return true;
        }
        if (gestureStart == null) return false;
        if (event.getActionMasked() == MotionEvent.ACTION_MOVE) {
            int position = event.findPointerIndex(pointer);
            if (position < 0) { gestureStart = null; return true; }
            float dx = 2 * (event.getX(position) - downX) / eyeWidth(eye);
            float dy = -2 * (event.getY(position) - downY) / getHeight();
            VrSettings draft = corner < 0 ? HeadsetTouch.pan(gestureStart, eye == 0 ? -1 : 1, dx, dy)
                : HeadsetTouch.resize(gestureStart, gestureImageAspect, gestureEyeAspect,
                    SIGN_X[corner], SIGN_Y[corner], dx, dy);
            edit.update(draft); changed.run(); invalidate();
        } else if (event.getActionMasked() == MotionEvent.ACTION_UP || event.getActionMasked() == MotionEvent.ACTION_CANCEL
            || (event.getActionMasked() == MotionEvent.ACTION_POINTER_UP && event.getPointerId(event.getActionIndex()) == pointer)) {
            gestureStart = null; pointer = -1; performClick();
        }
        return true;
    }
    @Override public boolean performClick() { super.performClick(); return true; }
    @Override protected void onSizeChanged(int width, int height, int oldWidth, int oldHeight) { gestureStart = null; }
}

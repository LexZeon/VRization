package org.vrization.app;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.content.res.Configuration;
import android.graphics.Color;
import android.graphics.Typeface;
import android.opengl.GLSurfaceView;
import android.os.Build;
import android.os.Bundle;
import android.text.InputType;
import android.view.GestureDetector;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.SeekBar;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import org.json.JSONException;
import org.json.JSONObject;
import org.vrization.core.AndroidPoseSource;
import org.vrization.core.VrRenderer;
import org.vrization.core.VrSettings;

/** Native Android viewer. No Google services, account, camera or storage permission required. */
public final class MainActivity extends Activity {
    private static final int INK = Color.rgb(229, 239, 246);
    private static final int MUTED = Color.rgb(165, 182, 199);
    private static final int ACCENT = Color.rgb(70, 212, 185);
    private SharedPreferences preferences;
    private VrSettings settings = new VrSettings();
    private VrRenderer renderer;
    private AndroidPoseSource pose;
    private StreamClient client;
    private GLSurfaceView surface;
    private ScrollView panel;
    private LinearLayout overlay;
    private Button panelButton, connectButton;
    private TextView status, frameStatus;
    private EditText hostInput, portInput, codeInput;
    private Spinner modeInput;
    private CheckBox invertInput;
    private final List<Slider> sliders = new ArrayList<>();
    private boolean refreshing;
    private boolean resumed;
    private boolean trackingActive;
    private boolean destroyed;
    private boolean panelVisible = true;
    private long lastUiFrame;
    private int receivedFrames;
    private long lastSettingsSent;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        if (Build.VERSION.SDK_INT >= 28) {
            WindowManager.LayoutParams attributes = getWindow().getAttributes();
            attributes.layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
            getWindow().setAttributes(attributes);
        }
        preferences = getSharedPreferences("vrization", MODE_PRIVATE);
        try { settings = SettingsJson.decode(new JSONObject(preferences.getString("settings", "{}")), settings); }
        catch (JSONException ignored) { }
        renderer = new VrRenderer();
        pose = new AndroidPoseSource(this, getWindowManager().getDefaultDisplay());
        if (!pose.isAvailable()) settings.mode = "full";
        renderer.setSettings(settings);
        client = new StreamClient(new StreamClient.Listener() {
            @Override public void onStatus(String text, boolean connected) {
                runOnUiThread(() -> {
                    if (destroyed) return;
                    status.setText(text); connectButton.setText(connected ? "断开连接" : "连接电脑");
                });
            }
            @Override public void onSettings(JSONObject json) {
                runOnUiThread(() -> {
                    if (destroyed) return;
                    String oldMode = settings.mode;
                    settings = SettingsJson.decode(json, settings);
                    boolean unavailable = !pose.isAvailable() && !"full".equals(settings.mode);
                    if (unavailable) settings.mode = "full";
                    renderer.setSettings(settings); saveSettings(); refreshControls();
                    if (!oldMode.equals(settings.mode)) { recenter(); updateTracking(); }
                    if (unavailable) {
                        client.sendSettings(settings);
                        status.setText("此手机缺少旋转传感器，已切换为全屏模式。");
                    }
                });
            }
            @Override public void onFrame(android.graphics.Bitmap bitmap) {
                int frameWidth = bitmap.getWidth(), frameHeight = bitmap.getHeight();
                renderer.submitFrame(bitmap);
                long now = android.os.SystemClock.elapsedRealtime();
                if (lastUiFrame == 0) lastUiFrame = now;
                receivedFrames++;
                if (now - lastUiFrame > 1000) {
                    float fps = receivedFrames * 1000f / (now - lastUiFrame);
                    lastUiFrame = now;
                    receivedFrames = 0;
                    runOnUiThread(() -> {
                        if (!destroyed) frameStatus.setText(String.format(Locale.CHINA,
                            "%d × %d · 接收 %.1f 帧/秒 · 双击回正，长按或返回键打开设置", frameWidth, frameHeight, fps));
                    });
                }
            }
        });
        createUi();
        immersive();
    }

    private void createUi() {
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.BLACK);
        surface = new GLSurfaceView(this) {
            @Override public boolean performClick() { super.performClick(); return true; }
        };
        surface.setContentDescription("VR 双眼观看画面。双击回正，长按打开设置。");
        surface.setEGLContextClientVersion(2);
        surface.setRenderer(renderer);
        surface.setPreserveEGLContextOnPause(false);
        GestureDetector gestures = new GestureDetector(this, new GestureDetector.SimpleOnGestureListener() {
            @Override public boolean onDown(MotionEvent event) { return true; }
            @Override public boolean onSingleTapConfirmed(MotionEvent event) { surface.performClick(); return true; }
            @Override public boolean onDoubleTap(MotionEvent event) { recenter(); return true; }
            @Override public void onLongPress(MotionEvent event) { setPanelVisible(true); }
        });
        surface.setOnTouchListener((view, event) -> gestures.onTouchEvent(event));
        root.addView(surface, new FrameLayout.LayoutParams(-1, -1));

        overlay = new LinearLayout(this);
        overlay.setOrientation(LinearLayout.VERTICAL);
        overlay.setPadding(dp(12), dp(6), dp(12), dp(6));
        FrameLayout.LayoutParams overlayParams = new FrameLayout.LayoutParams(panelWidth(), -1, Gravity.TOP | Gravity.START);
        root.addView(overlay, overlayParams);
        // Keep touch controls clear of OEM navigation bars and landscape display cutouts.
        overlay.setOnApplyWindowInsetsListener((view, insets) -> {
            int left = insets.getSystemWindowInsetLeft(), top = insets.getSystemWindowInsetTop();
            int right = insets.getSystemWindowInsetRight(), bottom = insets.getSystemWindowInsetBottom();
            if (Build.VERSION.SDK_INT >= 28 && insets.getDisplayCutout() != null) {
                left = Math.max(left, insets.getDisplayCutout().getSafeInsetLeft());
                top = Math.max(top, insets.getDisplayCutout().getSafeInsetTop());
                right = Math.max(right, insets.getDisplayCutout().getSafeInsetRight());
                bottom = Math.max(bottom, insets.getDisplayCutout().getSafeInsetBottom());
            }
            view.setPadding(dp(12) + left, dp(6) + top, dp(12) + right, dp(6) + bottom);
            return insets;
        });
        LinearLayout toolbar = row();
        panelButton = button("隐藏设置", () -> setPanelVisible(!panelVisible));
        toolbar.addView(panelButton, new LinearLayout.LayoutParams(dp(120), dp(44)));
        Button recenterButton = button("视角回正", this::recenter);
        toolbar.addView(recenterButton, new LinearLayout.LayoutParams(dp(120), dp(44)));
        overlay.addView(toolbar);
        panel = new ScrollView(this);
        panel.setFillViewport(false);
        panel.setBackgroundColor(Color.argb(242, 16, 26, 41));
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL); content.setPadding(dp(16), dp(8), dp(16), dp(16));
        panel.addView(content);
        overlay.addView(panel, new LinearLayout.LayoutParams(-1, 0, 1));
        content.addView(text("VRization", 25, ACCENT, true));
        content.addView(text("电脑画面 → 手机 VR 盒子", 14, MUTED, false));
        status = text("将手机与电脑接入同一可信 Wi-Fi，填入电脑端显示的 IP 和六位配对码。", 14, INK, false);
        content.addView(status);
        frameStatus = text("等待电脑画面", 12, MUTED, false); content.addView(frameStatus);
        hostInput = input("电脑 IP，例如 192.168.1.10", preferences.getString("host", ""), InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        portInput = input("端口", preferences.getString("port", "8765"), InputType.TYPE_CLASS_NUMBER);
        codeInput = input("六位配对码", "", InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_VARIATION_PASSWORD);
        LinearLayout address = row();
        address.addView(hostInput, new LinearLayout.LayoutParams(0, dp(52), 3));
        address.addView(portInput, new LinearLayout.LayoutParams(0, dp(52), 1));
        content.addView(address); content.addView(codeInput, new LinearLayout.LayoutParams(-1, dp(52)));
        connectButton = button("连接电脑", this::connectOrDisconnect);
        content.addView(connectButton, new LinearLayout.LayoutParams(-1, dp(48)));
        content.addView(text("局域网画面与控制未加密，请只在可信网络使用。电脑端默认关闭鼠标控制，FPS 模式需在电脑上开启。", 12, MUTED, false));
        if (!pose.isAvailable()) content.addView(text("未检测到旋转传感器：全屏模式仍可使用；大屏幕及 FPS 模式已禁用。", 14, ACCENT, false));
        content.addView(text("观看模式", 16, INK, true));
        modeInput = new Spinner(this);
        String[] modes = {"全屏模式 · 固定双眼画面", "大屏幕模式 · 转头观看虚拟屏幕", "FPS 游戏模式 · 转头控制电脑视角"};
        ArrayAdapter<String> modeAdapter = new ArrayAdapter<String>(this, android.R.layout.simple_spinner_item, modes) {
            @Override public boolean isEnabled(int position) { return position == 0 || pose.isAvailable(); }
            @Override public View getDropDownView(int position, View convertView, ViewGroup parent) {
                TextView view = (TextView) super.getDropDownView(position, convertView, parent);
                view.setTextColor(isEnabled(position) ? INK : MUTED); return view;
            }
        };
        modeAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        modeInput.setAdapter(modeAdapter);
        content.addView(modeInput, new LinearLayout.LayoutParams(-1, dp(48)));
        modeInput.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                if (refreshing) return;
                if (position > 0 && !pose.isAvailable()) { modeInput.setSelection(0); return; }
                String selected = new String[]{"full", "cinema", "fps"}[position];
                if (!selected.equals(settings.mode)) { settings.mode = selected; recenter(); updateTracking(); settingsChanged(true); }
            }
            @Override public void onNothingSelected(AdapterView<?> parent) { }
        });
        content.addView(text("盒子适配", 16, INK, true));
        addSlider(content, "画面缩放", .5f, 1f, 100, () -> settings.scale, value -> settings.scale = value, "%.0f%%", 100f);
        addSlider(content, "水平位置", -.3f, .3f, 120, () -> settings.offsetX, value -> settings.offsetX = value, "%.2f", 1f);
        addSlider(content, "垂直位置", -.3f, .3f, 120, () -> settings.offsetY, value -> settings.offsetY = value, "%.2f", 1f);
        addSlider(content, "双眼间距", 0f, .2f, 100, () -> settings.eyeSeparation, value -> settings.eyeSeparation = value, "%.2f", 1f);
        addSlider(content, "镜头畸变校正", 0f, .5f, 100, () -> settings.distortion, value -> settings.distortion = value, "%.2f", 1f);
        content.addView(text("大屏幕与游戏", 16, INK, true));
        addSlider(content, "视野角度（大屏幕）", 50f, 110f, 60, () -> settings.fov, value -> settings.fov = value, "%.0f°", 1f);
        addSlider(content, "屏幕距离（大屏幕）", 1f, 8f, 140, () -> settings.distance, value -> settings.distance = value, "%.1f", 1f);
        addSlider(content, "鼠标灵敏度（FPS）", 100f, 3000f, 290, () -> settings.sensitivity, value -> settings.sensitivity = value, "%.0f 像素/弧度", 1f);
        invertInput = new CheckBox(this); invertInput.setText("FPS 垂直方向反转"); invertInput.setTextColor(INK);
        invertInput.setOnCheckedChangeListener((button, checked) -> {
            if (!refreshing) { settings.invertY = checked; settingsChanged(true); }
        });
        content.addView(invertInput);
        content.addView(button("恢复显示设置", () -> {
            String currentMode = settings.mode; settings = new VrSettings(); settings.mode = currentMode;
            refreshControls(); settingsChanged(true); recenter();
        }));
        content.addView(button("关于与开源许可", this::showLicenses));
        content.addView(text("全屏和 FPS 使用固定双眼画面；大屏幕把二维桌面放在虚拟空间。画面本身并非游戏原生双眼立体。耳机声音请暂用电脑输出。\n应用进入后台时自动断开串流并停止控制；回到前台后点击连接。", 12, MUTED, false));
        refreshControls();
        setContentView(root);
    }

    private void connectOrDisconnect() {
        if (client.isConnected()) { client.disconnect(true); return; }
        String host = hostInput.getText().toString().trim();
        String code = codeInput.getText().toString().trim();
        int port;
        try { port = Integer.parseInt(portInput.getText().toString().trim()); }
        catch (NumberFormatException ignored) { status.setText("端口应为 1 到 65535 的整数。"); return; }
        if (host.isEmpty() || host.contains("://") || host.contains("/") || port < 1 || port > 65535) {
            status.setText("请输入电脑 IP 或主机名，以及正确端口；不需要 http:// 前缀。"); return;
        }
        if (!code.matches("[0-9]{6}")) { status.setText("请输入电脑端显示的六位数字配对码。"); return; }
        preferences.edit().putString("host", host).putString("port", Integer.toString(port)).apply();
        recenter();
        try { client.connect(host, port, code); }
        catch (IllegalArgumentException ignored) { status.setText("电脑 IP 或主机名格式无效。"); }
    }

    private void settingsChanged(boolean sendNow) {
        settings.normalize(); renderer.setSettings(settings); saveSettings();
        long now = android.os.SystemClock.elapsedRealtime();
        if (sendNow || now - lastSettingsSent >= 80) { lastSettingsSent = now; client.sendSettings(settings); }
    }
    private void saveSettings() { preferences.edit().putString("settings", SettingsJson.encode(settings).toString()).apply(); }
    private void refreshControls() {
        refreshing = true;
        modeInput.setSelection("cinema".equals(settings.mode) ? 1 : "fps".equals(settings.mode) ? 2 : 0);
        for (Slider slider : sliders) slider.refresh();
        invertInput.setChecked(settings.invertY);
        refreshing = false;
    }
    private void recenter() {
        pose.recenter(); renderer.setPose(0, 0, 0); client.recenter();
    }
    private void setPanelVisible(boolean visible) {
        panelVisible = visible; overlay.setVisibility(visible ? View.VISIBLE : View.GONE);
        panelButton.setText(visible ? "隐藏设置" : "显示设置");
        if (!visible) Toast.makeText(this, "长按画面或按返回键显示设置；双击画面回正", Toast.LENGTH_SHORT).show();
        immersive();
    }
    private int panelWidth() { return Math.min(dp(510), getResources().getDisplayMetrics().widthPixels); }
    @Override public void onConfigurationChanged(Configuration configuration) {
        super.onConfigurationChanged(configuration);
        ViewGroup.LayoutParams params = overlay.getLayoutParams(); params.width = panelWidth(); overlay.setLayoutParams(params);
        pose.recenter(); renderer.setPose(0, 0, 0); client.recenter();
    }
    private void showLicenses() {
        List<String> files = new ArrayList<>();
        files.add("VRization-LICENSE.txt");
        try {
            String[] androidLicenses = getAssets().list("android");
            if (androidLicenses != null) for (String name : androidLicenses) files.add("android/" + name);
        } catch (java.io.IOException ignored) { }
        new AlertDialog.Builder(this).setTitle("开源许可 · VRization 原创代码 MIT")
            .setItems(files.toArray(new String[0]), (dialog, which) -> showLicenseFile(files.get(which)))
            .setPositiveButton("关闭", null).show();
    }
    private void showLicenseFile(String name) {
        String content;
        try (InputStream input = getAssets().open(name); ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[4096]; int size;
            while ((size = input.read(buffer)) >= 0) output.write(buffer, 0, size);
            content = new String(output.toByteArray(), StandardCharsets.UTF_8);
        } catch (java.io.IOException ignored) { content = "无法读取许可证；项目仓库的 licenses 目录包含完整许可。"; }
        ScrollView scroll = new ScrollView(this);
        TextView body = text(content, 12, INK, false); body.setTextIsSelectable(true); body.setPadding(dp(16), dp(8), dp(16), dp(8)); scroll.addView(body);
        new AlertDialog.Builder(this).setTitle(name).setView(scroll).setPositiveButton("关闭", null).show();
    }
    private void immersive() {
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_FULLSCREEN
            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_LAYOUT_STABLE);
    }
    @Override public void onWindowFocusChanged(boolean focused) { super.onWindowFocusChanged(focused); if (focused) immersive(); }
    @Override protected void onResume() {
        super.onResume(); resumed = true; renderer.resumeFrames(); surface.onResume(); pose.recenter();
        updateTracking();
    }
    private void updateTracking() {
        boolean needed = resumed && !"full".equals(settings.mode) && pose.isAvailable();
        if (!needed) { if (trackingActive) pose.stop(); trackingActive = false; return; }
        if (trackingActive) return;
        trackingActive = true;
        pose.start((yaw, pitch, roll, timestamp) -> {
            if (!resumed) return;
            if ("cinema".equals(settings.mode)) renderer.setPose(yaw, pitch, roll);
            else if ("fps".equals(settings.mode)) client.sendPose(yaw, pitch);
        });
    }
    @Override protected void onPause() {
        resumed = false; trackingActive = false; pose.stop(); client.disconnect(false); renderer.pauseFrames(); surface.onPause();
        status.setText("应用进入后台，已断开连接并停止控制。点击“连接电脑”恢复。");
        connectButton.setText("连接电脑");
        super.onPause();
    }
    @Override protected void onDestroy() {
        destroyed = true; pose.stop(); client.shutdown(); renderer.pauseFrames(); super.onDestroy();
    }
    @Override public void onBackPressed() {
        if (!panelVisible) setPanelVisible(true);
        else { client.disconnect(false); super.onBackPressed(); }
    }
    private LinearLayout row() { LinearLayout view = new LinearLayout(this); view.setOrientation(LinearLayout.HORIZONTAL); return view; }
    private int dp(float value) { return Math.round(value * getResources().getDisplayMetrics().density); }
    private TextView text(String value, int size, int color, boolean bold) {
        TextView view = new TextView(this); view.setText(value); view.setTextSize(size); view.setTextColor(color);
        view.setPadding(0, dp(5), 0, dp(5)); if (bold) view.setTypeface(Typeface.DEFAULT, Typeface.BOLD); return view;
    }
    private Button button(String label, Runnable action) {
        Button view = new Button(this); view.setText(label); view.setTextColor(INK); view.setAllCaps(false);
        view.setOnClickListener(ignored -> action.run()); return view;
    }
    private EditText input(String hint, String value, int type) {
        EditText view = new EditText(this); view.setHint(hint); view.setText(value); view.setSingleLine(true);
        view.setTextColor(INK); view.setHintTextColor(MUTED); view.setTextSize(14); view.setInputType(type); return view;
    }
    private interface Getter { float get(); }
    private interface Setter { void set(float value); }
    private void addSlider(LinearLayout parent, String name, float min, float max, int steps, Getter getter, Setter setter, String format, float factor) {
        Slider slider = new Slider(name, min, max, steps, getter, setter, format, factor);
        sliders.add(slider); parent.addView(slider.label); parent.addView(slider.bar);
    }
    private final class Slider {
        final TextView label;
        final SeekBar bar;
        final String name, format;
        final float min, max, factor;
        final int steps;
        final Getter getter;
        Slider(String name, float min, float max, int steps, Getter getter, Setter setter, String format, float factor) {
            this.name = name; this.min = min; this.max = max; this.steps = steps; this.getter = getter; this.format = format; this.factor = factor;
            label = text("", 13, INK, false); bar = new SeekBar(MainActivity.this); bar.setMax(steps);
            bar.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
                @Override public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser) {
                    if (!fromUser || refreshing) return;
                    setter.set(min + (max - min) * progress / steps); updateLabel(); settingsChanged(false);
                }
                @Override public void onStartTrackingTouch(SeekBar seekBar) { }
                @Override public void onStopTrackingTouch(SeekBar seekBar) { settingsChanged(true); }
            });
        }
        void updateLabel() { label.setText(name + "  " + String.format(Locale.CHINA, format, getter.get() * factor)); }
        void refresh() { bar.setProgress(Math.round((getter.get() - min) / (max - min) * steps)); updateLabel(); }
    }
}

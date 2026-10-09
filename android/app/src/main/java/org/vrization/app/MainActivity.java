package org.vrization.app;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.content.Context;
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
    private final SettingsSync settingsSync = new SettingsSync();

    @Override protected void attachBaseContext(Context base) {
        String language = base.getSharedPreferences("vrization", MODE_PRIVATE).getString("language", "en");
        Locale locale = new Locale("zh".equals(language) ? "zh" : "en");
        Configuration configuration = new Configuration(base.getResources().getConfiguration());
        configuration.setLocale(locale);
        super.attachBaseContext(base.createConfigurationContext(configuration));
    }

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
        client = new StreamClient(this, new StreamClient.Listener() {
            @Override public void onSessionStarted() { settingsSync.newSession(); }
            @Override public void onStatus(String text, boolean connected) {
                runOnUiThread(() -> {
                    if (destroyed) return;
                    status.setText(text); connectButton.setText(connected ? R.string.disconnect : R.string.connect);
                });
            }
            @Override public void onSettings(JSONObject json, Long revision, Long clientSeq) {
                runOnUiThread(() -> {
                    if (destroyed) return;
                    String oldMode = settings.mode;
                    VrSettings incoming = SettingsJson.decode(json, settings);
                    if (!settingsSync.accept(incoming, revision, clientSeq)) return;
                    settings = incoming;
                    boolean unavailable = !pose.isAvailable() && !"full".equals(settings.mode);
                    if (unavailable) settings.mode = "full";
                    renderer.setSettings(settings); saveSettings(); refreshControls();
                    if (!oldMode.equals(settings.mode)) { recenter(); updateTracking(); }
                    if (unavailable) {
                        settingsChanged(true);
                        status.setText(R.string.sensor_fallback);
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
                        if (!destroyed) frameStatus.setText(getString(R.string.frame_stats, frameWidth, frameHeight, fps));
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
        surface.setContentDescription(getString(R.string.surface_description));
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
        panelButton = button(getString(R.string.hide_settings), () -> setPanelVisible(!panelVisible));
        toolbar.addView(panelButton, new LinearLayout.LayoutParams(dp(120), dp(44)));
        Button recenterButton = button(getString(R.string.recenter), this::recenter);
        toolbar.addView(recenterButton, new LinearLayout.LayoutParams(dp(120), dp(44)));
        overlay.addView(toolbar);
        panel = new ScrollView(this);
        panel.setFillViewport(false);
        panel.setBackgroundColor(Color.argb(242, 16, 26, 41));
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL); content.setPadding(dp(16), dp(8), dp(16), dp(16));
        panel.addView(content);
        overlay.addView(panel, new LinearLayout.LayoutParams(-1, 0, 1));
        content.addView(text(getString(R.string.app_name), 25, ACCENT, true));
        content.addView(text(getString(R.string.language), 14, MUTED, false));
        Spinner languageInput = new Spinner(this);
        ArrayAdapter<String> languages = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item,
            getResources().getStringArray(R.array.languages));
        languages.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        languageInput.setAdapter(languages);
        languageInput.setSelection("zh".equals(preferences.getString("language", "en")) ? 1 : 0);
        languageInput.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                String selected = position == 1 ? "zh" : "en";
                if (!selected.equals(preferences.getString("language", "en"))) {
                    preferences.edit().putString("language", selected).apply();
                    client.disconnect(false); recreate();
                }
            }
            @Override public void onNothingSelected(AdapterView<?> parent) { }
        });
        content.addView(languageInput, new LinearLayout.LayoutParams(-1, dp(44)));
        content.addView(text(getString(R.string.tagline), 14, MUTED, false));
        status = text(getString(R.string.connection_help), 14, INK, false);
        content.addView(status);
        frameStatus = text(getString(R.string.waiting_frame), 12, MUTED, false); content.addView(frameStatus);
        hostInput = input(getString(R.string.host_hint), preferences.getString("host", ""), InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        portInput = input(getString(R.string.port_hint), preferences.getString("port", "8765"), InputType.TYPE_CLASS_NUMBER);
        codeInput = input(getString(R.string.code_hint), "", InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_VARIATION_PASSWORD);
        LinearLayout address = row();
        address.addView(hostInput, new LinearLayout.LayoutParams(0, dp(52), 3));
        address.addView(portInput, new LinearLayout.LayoutParams(0, dp(52), 1));
        content.addView(address); content.addView(codeInput, new LinearLayout.LayoutParams(-1, dp(52)));
        connectButton = button(getString(R.string.connect), this::connectOrDisconnect);
        content.addView(connectButton, new LinearLayout.LayoutParams(-1, dp(48)));
        content.addView(text(getString(R.string.network_notice), 12, MUTED, false));
        if (!pose.isAvailable()) content.addView(text(getString(R.string.sensor_unavailable), 14, ACCENT, false));
        content.addView(text(getString(R.string.watch_mode), 16, INK, true));
        modeInput = new Spinner(this);
        String[] modes = getResources().getStringArray(R.array.watch_modes);
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
        content.addView(text(getString(R.string.headset_fit), 16, INK, true));
        addSlider(content, getString(R.string.scale), .5f, 1f, 100, () -> settings.scale, value -> settings.scale = value, "%.0f%%", 100f);
        addSlider(content, getString(R.string.offset_x), -.3f, .3f, 120, () -> settings.offsetX, value -> settings.offsetX = value, "%.2f", 1f);
        addSlider(content, getString(R.string.offset_y), -.3f, .3f, 120, () -> settings.offsetY, value -> settings.offsetY = value, "%.2f", 1f);
        addSlider(content, getString(R.string.eye_separation), 0f, .2f, 100, () -> settings.eyeSeparation, value -> settings.eyeSeparation = value, "%.2f", 1f);
        addSlider(content, getString(R.string.distortion), 0f, .5f, 100, () -> settings.distortion, value -> settings.distortion = value, "%.2f", 1f);
        content.addView(text(getString(R.string.cinema_game), 16, INK, true));
        addSlider(content, getString(R.string.fov), 50f, 110f, 60, () -> settings.fov, value -> settings.fov = value, "%.0f°", 1f);
        addSlider(content, getString(R.string.distance), 1f, 8f, 140, () -> settings.distance, value -> settings.distance = value, "%.1f", 1f);
        addSlider(content, getString(R.string.sensitivity), 100f, 3000f, 290, () -> settings.sensitivity, value -> settings.sensitivity = value, getString(R.string.format_pixels), 1f);
        invertInput = new CheckBox(this); invertInput.setText(getString(R.string.invert_y)); invertInput.setTextColor(INK);
        invertInput.setOnCheckedChangeListener((button, checked) -> {
            if (!refreshing) { settings.invertY = checked; settingsChanged(true); }
        });
        content.addView(invertInput);
        content.addView(button(getString(R.string.reset_view), () -> {
            String currentMode = settings.mode; settings = new VrSettings(); settings.mode = currentMode;
            refreshControls(); settingsChanged(true); recenter();
        }));
        content.addView(button(getString(R.string.licenses), this::showLicenses));
        content.addView(text(getString(R.string.mode_help), 12, MUTED, false));
        refreshControls();
        setContentView(root);
    }

    private void connectOrDisconnect() {
        if (client.isConnected()) { client.disconnect(true); return; }
        String host = hostInput.getText().toString().trim();
        String code = codeInput.getText().toString().trim();
        int port;
        try { port = Integer.parseInt(portInput.getText().toString().trim()); }
        catch (NumberFormatException ignored) { status.setText(getString(R.string.invalid_port)); return; }
        if (host.isEmpty() || host.contains("://") || host.contains("/") || port < 1 || port > 65535) {
            status.setText(getString(R.string.invalid_address)); return;
        }
        if (!code.matches("[0-9]{6}")) { status.setText(getString(R.string.invalid_code)); return; }
        preferences.edit().putString("host", host).putString("port", Integer.toString(port)).apply();
        recenter();
        try { client.connect(host, port, code); }
        catch (IllegalArgumentException ignored) { status.setText(getString(R.string.invalid_host)); }
    }

    private void settingsChanged(boolean sendNow) {
        settingsSync.edited();
        settings.normalize(); renderer.setSettings(settings); saveSettings();
        long now = android.os.SystemClock.elapsedRealtime();
        if (sendNow || now - lastSettingsSent >= 80) {
            lastSettingsSent = now;
            long sequence = settingsSync.nextSequence();
            if (client.sendSettings(settings, sequence)) settingsSync.sent(sequence, settings);
        }
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
        panelButton.setText(visible ? getString(R.string.hide_settings) : getString(R.string.show_settings));
        if (!visible) Toast.makeText(this, getString(R.string.viewer_gestures), Toast.LENGTH_SHORT).show();
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
        new AlertDialog.Builder(this).setTitle(getString(R.string.license_title))
            .setItems(files.toArray(new String[0]), (dialog, which) -> showLicenseFile(files.get(which)))
            .setPositiveButton(getString(R.string.close), null).show();
    }
    private void showLicenseFile(String name) {
        String content;
        try (InputStream input = getAssets().open(name); ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[4096]; int size;
            while ((size = input.read(buffer)) >= 0) output.write(buffer, 0, size);
            content = new String(output.toByteArray(), StandardCharsets.UTF_8);
        } catch (java.io.IOException ignored) { content = getString(R.string.license_error); }
        ScrollView scroll = new ScrollView(this);
        TextView body = text(content, 12, INK, false); body.setTextIsSelectable(true); body.setPadding(dp(16), dp(8), dp(16), dp(8)); scroll.addView(body);
        new AlertDialog.Builder(this).setTitle(name).setView(scroll).setPositiveButton(getString(R.string.close), null).show();
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
        status.setText(getString(R.string.paused));
        connectButton.setText(getString(R.string.connect));
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
                @Override public void onStartTrackingTouch(SeekBar seekBar) { settingsSync.beginGesture(); }
                @Override public void onStopTrackingTouch(SeekBar seekBar) { settingsSync.endGesture(); settingsChanged(true); }
            });
        }
        void updateLabel() { label.setText(getString(R.string.slider_value, name,
            String.format(getResources().getConfiguration().locale, format, getter.get() * factor))); }
        void refresh() { bar.setProgress(Math.round((getter.get() - min) / (max - min) * steps)); updateLabel(); }
    }
}

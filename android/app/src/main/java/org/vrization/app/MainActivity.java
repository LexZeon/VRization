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
import android.view.Display;
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
import org.vrization.core.HeadsetEdit;

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
    private TextView transportHelp, linkStatus, processingStatus, connectionNotice, stabilizationHelp;
    private LinearLayout lanInputs;
    private EditText hostInput, portInput, codeInput;
    private Spinner modeInput;
    private CheckBox invertInput;
    private final List<Slider> sliders = new ArrayList<>();
    private boolean refreshing;
    private boolean resumed;
    private boolean trackingActive;
    private boolean destroyed;
    private boolean panelVisible = true;
    private long lastSettingsSent;
    private final SettingsSync settingsSync = new SettingsSync();
    private ConnectionMode connectionMode = ConnectionMode.USB;
    private InitialUsbDetection initialUsb;
    private PhoneProfile profile;
    private FrameLayout screenRoot;
    private HeadsetEdit headsetEdit;
    private HeadsetEditorView editorView;
    private LinearLayout editorControls;
    private TextView editorValues;
    private volatile float imageAspect = 16f / 9f;

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
        connectionMode = ConnectionMode.fromPreference(preferences.getString("transport", "usb"));
        initialUsb = new InitialUsbDetection(state == null && !getIntent().getBooleanExtra("suppress_usb_auto", false));
        requestFastDisplay();
        try {
            profile = new PhoneProfile(preferences.contains("settings")
                ? SettingsJson.fields(new JSONObject(preferences.getString("settings", "{}"))) : null);
        } catch (JSONException | IllegalArgumentException ignored) { profile = new PhoneProfile(null); }
        settings = profile.snapshot();
        renderer = new VrRenderer();
        pose = new AndroidPoseSource(this, getWindowManager().getDefaultDisplay());
        if (!pose.isAvailable()) settings.mode = "full";
        renderer.setSettings(settings);
        client = new StreamClient(this, new StreamClient.Listener() {
            @Override public void onSessionStarted() {
                finishHeadsetEdit(false, false);
                settingsSync.newSession();
                if (profile.hasSavedProfile()) settingsChanged(true);
                frameStatus.setText(R.string.waiting_frame); linkStatus.setText(R.string.waiting_ping);
                processingStatus.setText(R.string.waiting_processing);
            }
            @Override public void onStatus(String text, boolean connected) {
                runOnUiThread(() -> {
                    if (destroyed) return;
                    if (!connected && !client.isActive() && headsetEdit != null) finishHeadsetEdit(false, false);
                    status.setText(text); updateConnectButton(); updateStabilizationHelp();
                });
            }
            @Override public void onSettings(JSONObject json, Long revision, Long clientSeq) {
                runOnUiThread(() -> {
                    if (destroyed) return;
                    String oldMode = settings.mode;
                    updateStabilizationHelp();
                    if (profile.waitForExtendedSnapshot(client.supportsStabilization(), json.has("stabilization"))) return;
                    VrSettings incoming = SettingsJson.decode(json, settings);
                    if (!settingsSync.accept(incoming, revision, clientSeq)) return;
                    settings = incoming;
                    boolean unavailable = !pose.isAvailable() && !"full".equals(settings.mode);
                    if (unavailable) settings.mode = "full";
                    renderer.setSettings(settings); surface.requestRender(); saveSettings(); refreshControls();
                    if (!oldMode.equals(settings.mode)) { recenter(); updateTracking(); }
                    if (unavailable) {
                        settingsChanged(true);
                        status.setText(R.string.sensor_fallback);
                    }
                });
            }
            @Override public void onFrame(android.graphics.Bitmap bitmap, long session, long receivedAtNanos) {
                imageAspect = (float) bitmap.getWidth() / bitmap.getHeight();
                renderer.submitFrame(bitmap, session, receivedAtNanos);
                surface.requestRender();
            }
            @Override public void onDecodedStats(int width, int height, double fps) {
                if (!destroyed) frameStatus.setText(getString(R.string.frame_stats, width, height, fps));
            }
            @Override public void onProcessingStats(double milliseconds) {
                if (!destroyed) processingStatus.setText(getString(R.string.processing_stats, milliseconds));
            }
            @Override public void onRoundTrip(long milliseconds) {
                if (!destroyed) linkStatus.setText(getString(R.string.ping_stats, milliseconds));
            }
        });
        renderer.setTextureSubmissionListener(client::recordTextureSubmission);
        createUi();
        immersive();
    }

    private void createUi() {
        FrameLayout root = new FrameLayout(this); screenRoot = root;
        root.setBackgroundColor(Color.BLACK);
        surface = new GLSurfaceView(this) {
            @Override public boolean performClick() { super.performClick(); return true; }
        };
        surface.setContentDescription(getString(R.string.surface_description));
        surface.setEGLContextClientVersion(2);
        surface.setRenderer(renderer);
        surface.setRenderMode(GLSurfaceView.RENDERMODE_WHEN_DIRTY);
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
        Button editHeadset = button(getString(R.string.edit_headset), this::startHeadsetEdit);
        editHeadset.setTextColor(ACCENT); editHeadset.setTypeface(null, Typeface.BOLD);
        content.addView(editHeadset, new LinearLayout.LayoutParams(-1, dp(52)));
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
                    initialUsb.stop(); getIntent().putExtra("suppress_usb_auto", true);
                    client.disconnect(false); recreate();
                }
            }
            @Override public void onNothingSelected(AdapterView<?> parent) { }
        });
        content.addView(languageInput, new LinearLayout.LayoutParams(-1, dp(44)));
        content.addView(text(getString(R.string.tagline), 14, MUTED, false));
        content.addView(text(getString(R.string.connection_method), 14, MUTED, false));
        Spinner transportInput = new Spinner(this);
        ArrayAdapter<String> transports = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item,
            getResources().getStringArray(R.array.connection_methods));
        transports.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        transportInput.setAdapter(transports); transportInput.setSelection(connectionMode == ConnectionMode.LAN ? 1 : 0);
        transportInput.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                ConnectionMode selected = position == 1 ? ConnectionMode.LAN : ConnectionMode.USB;
                if (selected != connectionMode) {
                    initialUsb.stop(); client.disconnect(false); connectionMode = selected;
                    preferences.edit().putString("transport", selected.preferenceValue).apply();
                    status.setText(selected == ConnectionMode.USB ? R.string.usb_ready : R.string.connection_help);
                    frameStatus.setText(R.string.waiting_frame); linkStatus.setText(R.string.waiting_ping);
                    processingStatus.setText(R.string.waiting_processing);
                    updateTransportUi();
                }
            }
            @Override public void onNothingSelected(AdapterView<?> parent) { }
        });
        content.addView(transportInput, new LinearLayout.LayoutParams(-1, dp(44)));
        transportHelp = text("", 13, MUTED, false); content.addView(transportHelp);
        status = text(getString(connectionMode == ConnectionMode.USB ? R.string.usb_ready : R.string.connection_help), 14, INK, false);
        content.addView(status);
        frameStatus = text(getString(R.string.waiting_frame), 12, MUTED, false); content.addView(frameStatus);
        linkStatus = text(getString(R.string.waiting_ping), 12, MUTED, false); content.addView(linkStatus);
        processingStatus = text(getString(R.string.waiting_processing), 12, MUTED, false); content.addView(processingStatus);
        hostInput = input(getString(R.string.host_hint), preferences.getString("host", ""), InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        portInput = input(getString(R.string.port_hint), preferences.getString("port", "8765"), InputType.TYPE_CLASS_NUMBER);
        codeInput = input(getString(R.string.code_hint), "", InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_VARIATION_PASSWORD);
        LinearLayout address = row();
        address.addView(hostInput, new LinearLayout.LayoutParams(0, dp(52), 3));
        address.addView(portInput, new LinearLayout.LayoutParams(0, dp(52), 1));
        lanInputs = new LinearLayout(this); lanInputs.setOrientation(LinearLayout.VERTICAL);
        lanInputs.addView(address); lanInputs.addView(codeInput, new LinearLayout.LayoutParams(-1, dp(52)));
        content.addView(lanInputs);
        connectButton = button(getString(R.string.connect), this::connectOrDisconnect);
        content.addView(connectButton, new LinearLayout.LayoutParams(-1, dp(48)));
        connectionNotice = text("", 12, MUTED, false); content.addView(connectionNotice);
        updateTransportUi();
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
        addSlider(content, getString(R.string.eye_separation), -1f, .2f, 240, () -> settings.eyeSeparation, value -> settings.eyeSeparation = value, "%.2f", 1f);
        addSlider(content, getString(R.string.distortion), 0f, .5f, 100, () -> settings.distortion, value -> settings.distortion = value, "%.2f", 1f);
        content.addView(text(getString(R.string.cinema_game), 16, INK, true));
        addSlider(content, getString(R.string.fov), 50f, 110f, 60, () -> settings.fov, value -> settings.fov = value, "%.0f°", 1f);
        addSlider(content, getString(R.string.distance), 1f, 8f, 140, () -> settings.distance, value -> settings.distance = value, "%.1f", 1f);
        addSlider(content, getString(R.string.sensitivity), 100f, 3000f, 290, () -> settings.sensitivity, value -> settings.sensitivity = value, getString(R.string.format_pixels), 1f);
        addSlider(content, getString(R.string.stabilization), 0f, 1f, 100, () -> settings.stabilization,
            value -> settings.stabilization = value, "%.0f%%", 100f);
        stabilizationHelp = text(getString(R.string.stabilization_help), 12, MUTED, false);
        content.addView(stabilizationHelp);
        invertInput = new CheckBox(this); invertInput.setText(getString(R.string.invert_y)); invertInput.setTextColor(INK);
        invertInput.setOnCheckedChangeListener((button, checked) -> {
            if (!refreshing) { settings.invertY = checked; settingsChanged(true); }
        });
        content.addView(invertInput);
        content.addView(button(getString(R.string.reset_all), this::resetAllPreferences));
        content.addView(button(getString(R.string.licenses), this::showLicenses));
        content.addView(text(getString(R.string.mode_help), 12, MUTED, false));
        refreshControls();
        setContentView(root);
    }

    private void connectOrDisconnect() {
        initialUsb.stop();
        if (client.isActive()) { client.disconnect(true); return; }
        if (connectionMode == ConnectionMode.USB) { recenter(); client.connectUsb(); return; }
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
        catch (IllegalArgumentException ignored) { client.disconnect(false); updateConnectButton(); status.setText(getString(R.string.invalid_host)); }
    }

    private void updateTransportUi() {
        boolean usb = connectionMode == ConnectionMode.USB;
        lanInputs.setVisibility(usb ? View.GONE : View.VISIBLE);
        transportHelp.setText(usb ? R.string.usb_help : R.string.connection_help);
        connectionNotice.setText(usb ? R.string.usb_notice : R.string.network_notice);
        updateConnectButton();
        updateStabilizationHelp();
    }
    private void updateConnectButton() {
        connectButton.setText(client.isConnected() ? R.string.disconnect : client.isConnecting() ? R.string.cancel_connect
            : connectionMode == ConnectionMode.USB ? R.string.connect_usb : R.string.connect);
    }
    private void updateStabilizationHelp() {
        if (stabilizationHelp != null) stabilizationHelp.setText(client.isConnected() && !client.supportsStabilization()
            ? R.string.stabilization_legacy : R.string.stabilization_help);
    }
    private void requestFastDisplay() {
        Display display = getWindowManager().getDefaultDisplay();
        Display.Mode current = display.getMode(), best = current;
        for (Display.Mode mode : display.getSupportedModes()) {
            if (mode.getPhysicalWidth() == current.getPhysicalWidth() && mode.getPhysicalHeight() == current.getPhysicalHeight()
                && mode.getRefreshRate() > best.getRefreshRate()) best = mode;
        }
        WindowManager.LayoutParams attributes = getWindow().getAttributes();
        attributes.preferredDisplayModeId = best.getModeId();
        attributes.preferredRefreshRate = best.getRefreshRate();
        getWindow().setAttributes(attributes);
    }

    private void settingsChanged(boolean sendNow) {
        settingsSync.edited();
        settings.normalize(); renderer.setSettings(settings); surface.requestRender(); saveSettings();
        long now = android.os.SystemClock.elapsedRealtime();
        if (sendNow || now - lastSettingsSent >= 80) {
            lastSettingsSent = now;
            long sequence = settingsSync.nextSequence();
            if (client.sendSettings(settings, sequence)) settingsSync.sent(sequence, settings);
        }
    }
    private void saveSettings() {
        profile.commit(settings);
        preferences.edit().putString("settings", SettingsJson.encode(profile.snapshot()).toString()).apply();
    }
    private void startHeadsetEdit() {
        if (headsetEdit != null) return;
        if (!client.pauseForEditor()) { client.setPoseEnabled(true); return; }
        headsetEdit = new HeadsetEdit(settings); settingsSync.beginGesture(); updateTracking();
        overlay.setVisibility(View.GONE);
        editorView = new HeadsetEditorView(this, headsetEdit, () -> imageAspect, this::previewHeadsetEdit);
        screenRoot.addView(editorView, new FrameLayout.LayoutParams(-1, -1));
        editorControls = new LinearLayout(this); editorControls.setOrientation(LinearLayout.VERTICAL);
        editorControls.setBackgroundColor(Color.argb(238, 16, 26, 41)); editorControls.setPadding(dp(12), dp(4), dp(12), dp(4));
        editorControls.addView(text(getString(R.string.editor_gestures), 12, INK, false));
        editorValues = text("", 12, ACCENT, false); editorControls.addView(editorValues);
        LinearLayout actions = row();
        actions.addView(button(getString(R.string.editor_save), () -> finishHeadsetEdit(true, true)), new LinearLayout.LayoutParams(0, dp(44), 1));
        actions.addView(button(getString(R.string.editor_discard), () -> finishHeadsetEdit(false, true)), new LinearLayout.LayoutParams(0, dp(44), 1));
        editorControls.addView(actions);
        screenRoot.addView(editorControls, new FrameLayout.LayoutParams(Math.min(dp(650), screenRoot.getWidth()), -2, Gravity.TOP | Gravity.CENTER_HORIZONTAL));
        editorControls.addOnLayoutChangeListener((view, left, top, right, bottom, oldLeft, oldTop, oldRight, oldBottom) -> {
            if (editorView != null) editorView.reserveTop(view.getHeight() + dp(4));
        });
        previewHeadsetEdit();
    }
    private void previewHeadsetEdit() {
        if (headsetEdit == null) return;
        VrSettings draft = headsetEdit.draft(); renderer.setSettings(headsetEdit.preview()); surface.requestRender();
        editorValues.setText(getString(R.string.editor_values, draft.scale * 100, draft.eyeSeparation, draft.offsetX, draft.offsetY));
    }
    private void finishHeadsetEdit(boolean save, boolean recenterTracking) {
        if (headsetEdit == null) return;
        settings = save ? headsetEdit.save() : headsetEdit.discard(); headsetEdit = null;
        settingsSync.endGesture();
        screenRoot.removeView(editorView); screenRoot.removeView(editorControls);
        editorView = null; editorControls = null; editorValues = null;
        overlay.setVisibility(panelVisible ? View.VISIBLE : View.GONE);
        renderer.setSettings(settings); surface.requestRender(); refreshControls();
        if (save) settingsChanged(true);
        pose.recenter(); renderer.setPose(0, 0, 0);
        if (recenterTracking) client.recenter();
        client.setPoseEnabled(true);
        updateTracking();
    }
    private void resetAllPreferences() {
        finishHeadsetEdit(false, false); initialUsb.stop(); client.disconnect(false);
        settings = profile.reset();
        preferences.edit().clear().putString("settings", SettingsJson.encode(settings).toString())
            .putString("language", PhoneProfile.DEFAULT_LANGUAGE).putString("transport", PhoneProfile.DEFAULT_TRANSPORT)
            .putString("host", PhoneProfile.DEFAULT_HOST).putString("port", PhoneProfile.DEFAULT_PORT).apply();
        codeInput.setText(""); getIntent().putExtra("suppress_usb_auto", true);
        Toast.makeText(this, getString(R.string.reset_all_done), Toast.LENGTH_LONG).show(); recreate();
    }
    private void refreshControls() {
        refreshing = true;
        modeInput.setSelection("cinema".equals(settings.mode) ? 1 : "fps".equals(settings.mode) ? 2 : 0);
        for (Slider slider : sliders) slider.refresh();
        invertInput.setChecked(settings.invertY);
        refreshing = false;
    }
    private void recenter() {
        pose.recenter(); renderer.setPose(0, 0, 0); if (headsetEdit == null) client.recenter();
        if (surface != null) surface.requestRender();
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
        pose.recenter(); renderer.setPose(0, 0, 0); if (headsetEdit == null) client.recenter();
        surface.requestRender();
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
        if (initialUsb.onForeground(connectionMode) && !client.isActive()) client.connectUsb();
    }
    private void updateTracking() {
        boolean needed = resumed && headsetEdit == null && !"full".equals(settings.mode) && pose.isAvailable();
        if (!needed) { if (trackingActive) pose.stop(); trackingActive = false; return; }
        if (trackingActive) return;
        trackingActive = true;
        pose.start((yaw, pitch, roll, timestamp) -> {
            if (!resumed || headsetEdit != null) return;
            if ("cinema".equals(settings.mode)) { renderer.setPose(yaw, pitch, roll); surface.requestRender(); }
            else if ("fps".equals(settings.mode)) client.sendPose(yaw, pitch);
        });
    }
    @Override protected void onPause() {
        resumed = false; finishHeadsetEdit(false, false); initialUsb.stop(); trackingActive = false; pose.stop(); client.disconnect(false); renderer.pauseFrames(); surface.onPause();
        status.setText(getString(R.string.paused));
        updateConnectButton();
        updateStabilizationHelp();
        super.onPause();
    }
    @Override protected void onDestroy() {
        destroyed = true; pose.stop(); client.shutdown(); renderer.pauseFrames(); super.onDestroy();
    }
    @Override public void onBackPressed() {
        if (headsetEdit != null) finishHeadsetEdit(false, true);
        else if (!panelVisible) setPanelVisible(true);
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

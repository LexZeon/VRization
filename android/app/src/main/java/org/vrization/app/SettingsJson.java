package org.vrization.app;

import org.json.JSONException;
import org.json.JSONObject;
import org.vrization.core.VrSettings;

final class SettingsJson {
    private SettingsJson() { }
    static JSONObject encode(VrSettings value) {
        JSONObject result = new JSONObject();
        try {
            // Widening .3f straight to double produces .30000001192092896, outside
            // the host's strict .3 bound. Use the float's canonical decimal first.
            result.put("mode", value.mode).put("scale", wireNumber(value.scale)).put("offsetX", wireNumber(value.offsetX))
                .put("offsetY", wireNumber(value.offsetY)).put("eyeSeparation", wireNumber(value.eyeSeparation))
                .put("fov", wireNumber(value.fov)).put("distance", wireNumber(value.distance)).put("distortion", wireNumber(value.distortion))
                .put("sensitivity", wireNumber(value.sensitivity)).put("invertY", value.invertY);
        } catch (JSONException ignored) { /* all values are normalized finite numbers */ }
        return result;
    }
    private static double wireNumber(float value) { return Double.parseDouble(Float.toString(value)); }
    static VrSettings decode(JSONObject json, VrSettings base) {
        VrSettings result = base.copy();
        result.mode = json.optString("mode", result.mode);
        result.scale = (float) json.optDouble("scale", result.scale);
        result.offsetX = (float) json.optDouble("offsetX", result.offsetX);
        result.offsetY = (float) json.optDouble("offsetY", result.offsetY);
        result.eyeSeparation = (float) json.optDouble("eyeSeparation", result.eyeSeparation);
        result.fov = (float) json.optDouble("fov", result.fov);
        result.distance = (float) json.optDouble("distance", result.distance);
        result.distortion = (float) json.optDouble("distortion", result.distortion);
        result.sensitivity = (float) json.optDouble("sensitivity", result.sensitivity);
        result.invertY = json.optBoolean("invertY", result.invertY);
        result.normalize();
        return result;
    }
}

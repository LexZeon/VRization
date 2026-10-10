package org.vrization.app;

import org.json.JSONObject;
import org.json.JSONArray;
import org.vrization.core.VrSettings;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Iterator;
import java.util.ArrayList;
import java.util.List;

final class SettingsJson {
    private SettingsJson() { }
    static JSONObject encode(VrSettings value) {
        return new JSONObject(SettingsValues.encode(value));
    }
    static JSONObject encodeForHost(VrSettings value, boolean supportsStabilization) {
        return new JSONObject(SettingsValues.encodeForHost(value, supportsStabilization));
    }
    static JSONObject encodeForHost(VrSettings value, boolean supportsStabilization, boolean supportsEnhanced) {
        return new JSONObject(SettingsValues.encodeForHost(value, supportsStabilization, supportsEnhanced));
    }
    static VrSettings decodeFromHost(JSONObject json, VrSettings base, boolean supportsEnhanced) {
        return SettingsValues.decodeFromHost(fields(json), base, supportsEnhanced);
    }
    static VrSettings decode(JSONObject json, VrSettings base) {
        return SettingsValues.decode(fields(json), base, false);
    }
    static Map<String, Object> fields(JSONObject json) {
        Map<String, Object> values = new LinkedHashMap<>();
        Iterator<String> keys = json.keys();
        while (keys.hasNext()) {
            String key = keys.next(); Object value = json.opt(key);
            values.put(key, field(value));
        }
        return values;
    }
    private static Object field(Object value) {
        if (value instanceof JSONObject) return fields((JSONObject) value);
        if (value instanceof JSONArray) {
            JSONArray array = (JSONArray) value;
            List<Object> result = new ArrayList<>();
            for (int i = 0; i < array.length(); i++) result.add(field(array.opt(i)));
            return result;
        }
        return value;
    }
}

package org.vrization.app;

import org.json.JSONObject;
import org.vrization.core.VrSettings;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Iterator;

final class SettingsJson {
    private SettingsJson() { }
    static JSONObject encode(VrSettings value) {
        return new JSONObject(SettingsValues.encode(value));
    }
    static VrSettings decode(JSONObject json, VrSettings base) {
        return SettingsValues.decode(fields(json), base, false);
    }
    static Map<String, Object> fields(JSONObject json) {
        Map<String, Object> values = new LinkedHashMap<>();
        Iterator<String> keys = json.keys();
        while (keys.hasNext()) {
            String key = keys.next(); Object value = json.opt(key);
            values.put(key, value instanceof JSONObject ? fields((JSONObject) value) : value);
        }
        return values;
    }
}

package org.vrization.app;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.LinkedHashSet;
import java.util.Set;
import org.vrization.core.VrSettings;

/** Strict Java value codec shared by host messages and committed preference snapshots. */
final class SettingsValues {
    private static final Set<String> LEGACY_KEYS = new LinkedHashSet<>(java.util.Arrays.asList(
        "mode", "scale", "offsetX", "offsetY", "eyeSeparation", "fov", "distance", "distortion", "sensitivity", "invertY"));
    private static final Set<String> CURRENT_KEYS = new LinkedHashSet<>(LEGACY_KEYS);
    static { CURRENT_KEYS.add("stabilization"); }
    private SettingsValues() { }
    static Map<String, Object> encode(VrSettings value) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("mode", value.mode); result.put("scale", wire(value.scale));
        result.put("offsetX", wire(value.offsetX)); result.put("offsetY", wire(value.offsetY));
        result.put("eyeSeparation", wire(value.eyeSeparation)); result.put("fov", wire(value.fov));
        result.put("distance", wire(value.distance)); result.put("distortion", wire(value.distortion));
        result.put("sensitivity", wire(value.sensitivity)); result.put("invertY", value.invertY);
        result.put("stabilization", wire(value.stabilization));
        return result;
    }
    /** Transport compatibility must never discard a locally saved preference. */
    static Map<String, Object> encodeForHost(VrSettings value, boolean supportsStabilization) {
        Map<String, Object> result = encode(value);
        if (!supportsStabilization) result.remove("stabilization");
        return result;
    }
    private static double wire(float value) { return Double.parseDouble(Float.toString(value)); }
    static VrSettings decode(Map<String, Object> values, VrSettings base, boolean complete) {
        if (values == null || values.isEmpty() || (complete
            && !values.keySet().equals(LEGACY_KEYS) && !values.keySet().equals(CURRENT_KEYS)))
            throw new IllegalArgumentException("Invalid settings object");
        VrSettings result = base.copy();
        // A complete pre-extension profile migrates to the original, unfiltered behavior.
        // Partial legacy acknowledgements preserve the current local preference instead.
        if (complete && !values.containsKey("stabilization")) result.stabilization = 0;
        for (Map.Entry<String, Object> field : values.entrySet()) {
            String name = field.getKey(); Object value = field.getValue();
            switch (name) {
                case "mode":
                    if (!(value instanceof String) || (!"full".equals(value) && !"cinema".equals(value) && !"fps".equals(value)))
                        throw new IllegalArgumentException("Invalid mode");
                    result.mode = (String) value; break;
                case "invertY":
                    if (!(value instanceof Boolean)) throw new IllegalArgumentException("Invalid invertY");
                    result.invertY = (Boolean) value; break;
                case "scale": result.scale = number(value, .5, 1); break;
                case "offsetX": result.offsetX = number(value, -.3, .3); break;
                case "offsetY": result.offsetY = number(value, -.3, .3); break;
                case "eyeSeparation": result.eyeSeparation = number(value, -1, .2); break;
                case "fov": result.fov = number(value, 50, 110); break;
                case "distance": result.distance = number(value, 1, 8); break;
                case "distortion": result.distortion = number(value, 0, .5); break;
                case "sensitivity": result.sensitivity = number(value, 100, 3000); break;
                case "stabilization": result.stabilization = number(value, 0, 1); break;
                default: throw new IllegalArgumentException("Unknown setting");
            }
        }
        return result;
    }
    private static float number(Object value, double min, double max) {
        if (!(value instanceof Number)) throw new IllegalArgumentException("Invalid setting type");
        double number = ((Number) value).doubleValue();
        if (Double.isNaN(number) || Double.isInfinite(number) || number < min || number > max)
            throw new IllegalArgumentException("Setting outside bounds");
        return (float) number;
    }
}

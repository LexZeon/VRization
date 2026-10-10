package org.vrization.app;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.vrization.core.VrSettings;

final class SteamFixtures {
    static final List<String> CAPS = Arrays.asList("enhanced-first-person", "stereo-sbs", "hmd-orientation");
    static Map<String,Object> descriptor(long epoch, boolean accepted, boolean stereo) {
        Map<String,Object> value = new LinkedHashMap<>();
        value.put("v",1); value.put("epoch",epoch); value.put("accepted",accepted);
        value.put("streamLayout",stereo ? "sbs" : "mono"); value.put("inputTarget",stereo ? "virtual-hmd" : "mouse");
        return value;
    }
    static StreamSession session(long epoch, boolean accepted, boolean stereo) {
        return StreamSession.parse(descriptor(epoch,accepted,stereo),CAPS);
    }
    static Map<String,Object> message(String type) {
        Map<String,Object> value = new LinkedHashMap<>(); value.put("v",1); value.put("type",type); return value;
    }
    static Map<String,Object> hello(boolean accepted) {
        Map<String,Object> value = message("hello"), stream = new LinkedHashMap<>();
        value.put("name","VRization"); value.put("version","0.5.0-steamvr-preview");
        value.put("settings",SettingsValues.encode(new VrSettings())); value.put("mouseArmed",false);
        stream.put("codec","jpeg"); stream.put("fps",60); stream.put("maxWidth",2048); value.put("stream",stream);
        value.put("capabilities",CAPS); value.put("enhancedFirstPerson",true);
        value.put("streamSession",descriptor(19,accepted,true)); return value;
    }
    static Map<String,Object> settings(boolean accepted) {
        Map<String,Object> value = message("settings"); value.put("settings",SettingsValues.encode(new VrSettings()));
        value.put("streamSession",descriptor(19,accepted,true)); return value;
    }
}

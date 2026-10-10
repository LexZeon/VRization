// Original VRization client lifecycle, MIT. Calls pinned BSD-3-Clause OpenVR SDK.
#pragma once
#include "ipc.hpp"
#include "stop.hpp"
#include <openvr.h>
#include <chrono>
#include <iostream>
#include <stdexcept>

namespace vrization {
struct Arguments {
    std::wstring map,stopEvent; UINT width=640,fps=60; bool allowNative=false;
    static Arguments parse(int argc,wchar_t** argv,bool mirror) {
        Arguments result;
        for(int i=1;i<argc;++i) {
            const std::wstring arg=argv[i];
            if(arg==L"--frame-map" && i+1<argc) result.map=argv[++i];
            else if(arg==L"--stop-event" && i+1<argc) result.stopEvent=argv[++i];
            else if(mirror && (arg==L"--width" || arg==L"--fps") && i+1<argc) {
                const std::wstring value=argv[++i]; std::size_t end=0; const auto number=std::stoul(value,&end);
                if(end!=value.size() || number>1920) throw std::runtime_error("Invalid numeric argument");
                if(arg==L"--width") result.width=static_cast<UINT>(number); else result.fps=static_cast<UINT>(number);
            } else if(mirror && arg==L"--allow-native-headset") result.allowNative=true;
            else throw std::runtime_error("Unknown/missing argument");
        }
        if(!local_map_name(result.map) || result.map==kPoseMapName || result.width<2 || result.width>1920 || result.fps<1 || result.fps>120)
            throw std::runtime_error("Use --frame-map Local\\<unique-name>; width 2..1920; fps 1..120");
        if(!result.stopEvent.empty() && (!local_map_name(result.stopEvent) || result.stopEvent==result.map || result.stopEvent==kPoseMapName))
            throw std::runtime_error("Invalid unique stop event name");
        return result;
    }
};
inline std::string hmd_serial(vr::IVRSystem* system) {
    if(!system || !system->IsTrackedDeviceConnected(vr::k_unTrackedDeviceIndex_Hmd) ||
        system->GetTrackedDeviceClass(vr::k_unTrackedDeviceIndex_Hmd)!=vr::TrackedDeviceClass_HMD) return {};
    char buffer[256]{}; vr::ETrackedPropertyError error=vr::TrackedProp_Success;
    const auto size=system->GetStringTrackedDeviceProperty(vr::k_unTrackedDeviceIndex_Hmd,vr::Prop_SerialNumber_String,buffer,sizeof(buffer),&error);
    if(error!=vr::TrackedProp_Success || size<2 || size>sizeof(buffer)) return {};
    return buffer;
}
class Runtime {
    bool initialized_=false;
public:
    vr::IVRSystem* system=nullptr;
    ~Runtime() { if(initialized_) vr::VR_Shutdown(); }
    bool try_init(vr::EVRApplicationType type) {
        if(initialized_) return true;
        vr::EVRInitError error=vr::VRInitError_None; system=vr::VR_Init(&error,type);
        initialized_=error==vr::VRInitError_None && system;
        return initialized_;
    }
    bool quitting() {
        vr::VREvent_t event{};
        while(system && system->PollNextEvent(&event,sizeof(event))) if(event.eventType==vr::VREvent_Quit) stopping=true;
        return should_stop();
    }
};
inline void overlay_checked(vr::EVROverlayError error,const char* operation) {
    if(error!=vr::VROverlayError_None) throw std::runtime_error(std::string(operation)+" OpenVR error "+std::to_string(error));
}
} // namespace vrization

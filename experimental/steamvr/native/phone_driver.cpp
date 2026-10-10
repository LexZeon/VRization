// Original VRization implementation, MIT. OpenVR ABI and sample lifecycle ideas:
// ValveSoftware/openvr 0924064316de3effbcd1acf1e309182a2deb1c05 (BSD-3-Clause).
#include "pose.hpp"
#include <mutex>
#include <cstring>

namespace {
class PhoneHmd final:public vr::ITrackedDeviceServerDriver,public vr::IVRDisplayComponent {
    vr::TrackedDeviceIndex_t index_=vr::k_unTrackedDeviceIndexInvalid;
    std::mutex mutex_; vrization::PoseHeader latest_{};
public:
    void update(const vrization::PoseHeader& input) {
        { std::lock_guard<std::mutex> guard(mutex_); latest_=input; }
        if(index_!=vr::k_unTrackedDeviceIndexInvalid) {
            const auto pose=GetPose(); vr::VRServerDriverHost()->TrackedDevicePoseUpdated(index_,pose,sizeof(pose));
        }
    }
    vr::EVRInitError Activate(std::uint32_t index) override {
        index_=index; auto properties=vr::VRProperties();
        const auto container=properties->TrackedDeviceToPropertyContainer(index);
        properties->SetStringProperty(container,vr::Prop_TrackingSystemName_String,"vrization_phone");
        properties->SetStringProperty(container,vr::Prop_ModelNumber_String,"VRization Phone 3DOF (experimental)");
        properties->SetStringProperty(container,vr::Prop_SerialNumber_String,"VRizationPhone");
        properties->SetInt32Property(container,vr::Prop_DeviceClass_Int32,vr::TrackedDeviceClass_HMD);
        properties->SetFloatProperty(container,vr::Prop_UserIpdMeters_Float,.064f);
        properties->SetFloatProperty(container,vr::Prop_DisplayFrequency_Float,90.f);
        properties->SetFloatProperty(container,vr::Prop_SecondsFromVsyncToPhotons_Float,0.f);
        properties->SetUint64Property(container,vr::Prop_CurrentUniverseId_Uint64,904040);
        properties->SetBoolProperty(container,vr::Prop_IsOnDesktop_Bool,false);
        properties->SetBoolProperty(container,vr::Prop_DisplayDebugMode_Bool,true);
        properties->SetBoolProperty(container,vr::Prop_HasDriverDirectModeComponent_Bool,false);
        return vr::VRInitError_None;
    }
    void Deactivate() override { index_=vr::k_unTrackedDeviceIndexInvalid; }
    void EnterStandby() override {}
    void* GetComponent(const char* version) override {
        return version && std::strcmp(version,vr::IVRDisplayComponent_Version)==0?
            static_cast<vr::IVRDisplayComponent*>(this):nullptr;
    }
    void DebugRequest(const char*,char* response,std::uint32_t size) override { if(response && size) response[0]='\0'; }
    vr::DriverPose_t GetPose() override {
        std::lock_guard<std::mutex> guard(mutex_); return vrization::driver_pose(latest_,GetTickCount64());
    }
    void GetWindowBounds(std::int32_t* x,std::int32_t* y,std::uint32_t* w,std::uint32_t* h) override { *x=*y=0;*w=2048;*h=1024; }
    bool IsDisplayOnDesktop() override { return true; }
    bool IsDisplayRealDisplay() override { return false; }
    void GetRecommendedRenderTargetSize(std::uint32_t* w,std::uint32_t* h) override { *w=*h=1024; }
    void GetEyeOutputViewport(vr::EVREye eye,std::uint32_t* x,std::uint32_t* y,std::uint32_t* w,std::uint32_t* h) override { *x=eye==vr::Eye_Left?0:1024;*y=0;*w=*h=1024; }
    void GetProjectionRaw(vr::EVREye,float* left,float* right,float* top,float* bottom) override { *left=*top=-1.f;*right=*bottom=1.f; }
    vr::DistortionCoordinates_t ComputeDistortion(vr::EVREye,float u,float v) override {
        vr::DistortionCoordinates_t result{};
        result.rfRed[0]=result.rfGreen[0]=result.rfBlue[0]=u;
        result.rfRed[1]=result.rfGreen[1]=result.rfBlue[1]=v; return result;
    }
    bool ComputeInverseDistortion(vr::HmdVector2_t* result,vr::EVREye,std::uint32_t channel,float u,float v) override {
        if(!result || channel>2 || !std::isfinite(u) || !std::isfinite(v)) return false;
        result->v[0]=u; result->v[1]=v; return true;
    }
};
class Provider final:public vr::IServerTrackedDeviceProvider {
    vrization::Mapping mapping_; PhoneHmd hmd_; bool registrationAttempted_=false;
public:
    vr::EVRInitError Init(vr::IVRDriverContext* context) override {
        VR_INIT_SERVER_DRIVER_CONTEXT(context); registrationAttempted_=false;
        // Discovery is repeated from RunFrame: runtime may start before the phone route.
        return vr::VRInitError_None;
    }
    void Cleanup() override {
        mapping_.close(); hmd_.update({}); hmd_.Deactivate(); registrationAttempted_=false;
        VR_CLEANUP_SERVER_DRIVER_CONTEXT();
    }
    const char* const* GetInterfaceVersions() override { return vr::k_InterfaceVersions; }
    void RunFrame() override {
        vrization::PoseHeader pose{};
        if(mapping_.open(vrization::kPoseMapName,sizeof(pose)) && vrization::snapshot_header(mapping_.data(),pose)) {
            const bool headerReady=vrization::pose_header(pose) && !(pose.flags & ~7U) &&
                vrization::fresh(pose.tickMs,GetTickCount64());
            if(headerReady && !registrationAttempted_) {
                registrationAttempted_=true;
                if(!vr::VRServerDriverHost()->TrackedDeviceAdded("VRizationPhone",vr::TrackedDeviceClass_HMD,&hmd_))
                    vr::VRDriverLog()->Log("VRization: HMD registration rejected; no existing headset was replaced.");
            }
            if(!headerReady || !(pose.flags & vrization::kActive)) { mapping_.close(); pose={}; }
        }
        hmd_.update(pose);
    }
    bool ShouldBlockStandbyMode() override { return false; }
    void EnterStandby() override { hmd_.update({}); }
    void LeaveStandby() override {}
};
Provider provider;
} // namespace

extern "C" __declspec(dllexport) void* HmdDriverFactory(const char* interfaceName,int* returnCode) {
    if(interfaceName && std::strcmp(interfaceName,vr::IServerTrackedDeviceProvider_Version)==0) {
        if(returnCode) *returnCode=vr::VRInitError_None; return &provider;
    }
    if(returnCode) *returnCode=vr::VRInitError_Init_InterfaceNotFound; return nullptr;
}

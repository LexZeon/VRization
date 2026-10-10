// Original VRization desktop-to-existing-HMD overlay, MIT. Valve API/sample ideas BSD-3-Clause.
#include "runtime.hpp"
#include "gpu.hpp"

namespace {
class OwnedOverlay {
    vr::IVROverlay* api_; vr::VROverlayHandle_t handle_=vr::k_ulOverlayHandleInvalid;
    bool visible_=false;
public:
    explicit OwnedOverlay(vr::IVROverlay* api):api_(api) {
        const std::string key="org.vrization.experimental.desktop."+std::to_string(GetCurrentProcessId())+"."+std::to_string(GetTickCount64());
        vrization::overlay_checked(api_->CreateOverlay(key.c_str(),"VRization Desktop (experimental)",&handle_),"CreateOverlay");
    }
    ~OwnedOverlay() { if(handle_!=vr::k_ulOverlayHandleInvalid) { hide(); api_->DestroyOverlay(handle_); } }
    void configure() {
        vrization::overlay_checked(api_->SetOverlayWidthInMeters(handle_,3.f),"SetOverlayWidthInMeters");
        vr::HmdMatrix34_t transform{}; transform.m[0][0]=transform.m[1][1]=transform.m[2][2]=1; transform.m[2][3]=-2.f;
        vrization::overlay_checked(api_->SetOverlayTransformTrackedDeviceRelative(handle_,vr::k_unTrackedDeviceIndex_Hmd,&transform),"Head relative overlay");
    }
    void hide() noexcept { api_->HideOverlay(handle_); api_->ClearOverlayTexture(handle_); visible_=false; }
    void show(ID3D11Texture2D* texture) {
        const vr::Texture_t submission{texture,vr::TextureType_DirectX,vr::ColorSpace_Gamma};
        vrization::overlay_checked(api_->SetOverlayTexture(handle_,&submission),"SetOverlayTexture");
        if(!visible_) { vrization::overlay_checked(api_->ShowOverlay(handle_),"ShowOverlay"); visible_=true; }
    }
};
}
int wmain(int argc,wchar_t** argv) {
    SetConsoleCtrlHandler(vrization::console_control,TRUE);
    try {
        const auto args=vrization::Arguments::parse(argc,argv,false);
        vrization::StopEvent stop(args.stopEvent);vrization::Runtime runtime;
        const auto deadline=GetTickCount64()+60000; bool waitingPrinted=false;
        while(!vrization::should_stop()) {
            const bool ready=runtime.try_init(vr::VRApplication_Overlay);
            const auto serial=ready?vrization::hmd_serial(runtime.system):std::string{};
            if(serial=="VRizationPhone") throw std::runtime_error("Existing-headset overlay refuses the phone HMD route");
            if(ready && !serial.empty() && vr::VROverlay()) break;
            if(!waitingPrinted) { std::cout<<"waiting: existing SteamVR HMD (up to 60s)"<<std::endl; waitingPrinted=true; }
            if(GetTickCount64()>=deadline) throw std::runtime_error("Existing SteamVR HMD not ready");
            runtime.quitting(); std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
        if(vrization::should_stop()) return 0;
        const auto selectedSerial=vrization::hmd_serial(runtime.system);
        int adapter=-1; runtime.system->GetDXGIOutputInfo(&adapter);
        if(adapter<0) throw std::runtime_error("SteamVR did not report a DXGI adapter");
        auto gpu=vrization::Device::adapter(adapter);
        vrization::Mapping mapping; vrization::FrameHeader frame{};
        std::vector<std::uint8_t> pixels; vrization::ComPtr<ID3D11Texture2D> texture;
        // Destruction order matters on exceptions too: hide/clear/destroy the
        // submitted overlay while its texture and D3D device are still alive.
        OwnedOverlay overlay(vr::VROverlay()); overlay.configure();
        UINT width=0,height=0; std::uint32_t lastSequence=0; bool haveFrame=false;
        std::cout<<"ready: existing-headset overlay; no mouse or tracking output"<<std::endl;
        while(!runtime.quitting()) {
            const auto serial=vrization::hmd_serial(runtime.system);
            if(serial.empty() || serial!=selectedSerial || serial=="VRizationPhone") throw std::runtime_error("Existing headset disconnected or changed");
            if(!mapping.open(args.map,vrization::kFrameMapBytes) ||
                !vrization::snapshot_frame(mapping.data(),frame,pixels) || !(frame.flags & vrization::kActive) ||
                !vrization::fresh(frame.tickMs,GetTickCount64())) {
                overlay.hide(); texture.Reset(); width=height=0; haveFrame=false;
                // Release stale ownership too, so host Stop can destroy its mapping.
                mapping.close(); std::this_thread::sleep_for(std::chrono::milliseconds(16)); continue;
            }
            if(!haveFrame || frame.seqlock!=lastSequence) {
                if(frame.width!=width || frame.height!=height) {
                    overlay.hide(); texture.Reset(); width=frame.width; height=frame.height;
                    D3D11_TEXTURE2D_DESC d{}; d.Width=width;d.Height=height;d.MipLevels=d.ArraySize=1;
                    d.Format=DXGI_FORMAT_B8G8R8A8_UNORM;d.SampleDesc.Count=1;d.Usage=D3D11_USAGE_DEFAULT;d.BindFlags=D3D11_BIND_SHADER_RESOURCE;
                    vrization::checked(gpu.device->CreateTexture2D(&d,nullptr,&texture),"Create overlay texture");
                }
                gpu.context->UpdateSubresource(texture.Get(),0,nullptr,pixels.data(),frame.stride,0);
                gpu.context->Flush(); overlay.show(texture.Get()); lastSequence=frame.seqlock; haveFrame=true;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(8));
        }
        overlay.hide(); return 0;
    } catch(const std::exception& error) { std::cerr<<"error: "<<error.what()<<std::endl; return 1; }
}

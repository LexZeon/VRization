// Original VRization D3D11 mirror/IPC bridge, MIT. Official Valve SDK (BSD-3-Clause).
#include "runtime.hpp"
#include "gpu.hpp"
#include <memory>

namespace {
class MirrorEyes {
    vr::IVRCompositor* compositor_; ID3D11ShaderResourceView* left_=nullptr,*right_=nullptr;
public:
    explicit MirrorEyes(vr::IVRCompositor* compositor):compositor_(compositor) {}
    ~MirrorEyes() {
        // These SRVs belong to OpenVR. COM Release alone violates its mirror contract.
        if(left_) compositor_->ReleaseMirrorTextureD3D11(left_);
        if(right_) compositor_->ReleaseMirrorTextureD3D11(right_);
    }
    bool acquire(ID3D11Device* device) {
        if(!left_) { void* view=nullptr;
            if(compositor_->GetMirrorTextureD3D11(vr::Eye_Left,device,&view)==vr::VRCompositorError_None) left_=static_cast<ID3D11ShaderResourceView*>(view);
        }
        if(!right_) { void* view=nullptr;
            if(compositor_->GetMirrorTextureD3D11(vr::Eye_Right,device,&view)==vr::VRCompositorError_None) right_=static_cast<ID3D11ShaderResourceView*>(view);
        }
        return left_ && right_;
    }
    ID3D11ShaderResourceView* left() const { return left_; }
    ID3D11ShaderResourceView* right() const { return right_; }
};
}
int wmain(int argc,wchar_t** argv) {
    SetConsoleCtrlHandler(vrization::console_control,TRUE);
    try {
        const auto args=vrization::Arguments::parse(argc,argv,true);
        vrization::StopEvent stop(args.stopEvent);
        vrization::Runtime runtime; vrization::FrameWriter writer(args.map);
        const auto deadline=GetTickCount64()+60000; bool waitingPrinted=false;
        while(!vrization::should_stop()) {
            const bool ready=runtime.try_init(vr::VRApplication_Background);
            const auto serial=ready?vrization::hmd_serial(runtime.system):std::string{};
            if(ready && !serial.empty() && (args.allowNative || serial=="VRizationPhone") && vr::VRCompositor()) break;
            if(!waitingPrinted) { std::cout<<"waiting: SteamVR and selected HMD (up to 60s)"<<std::endl; waitingPrinted=true; }
            if(GetTickCount64()>=deadline) throw std::runtime_error("Selected phone HMD/compositor not ready; verify driver installation. Headless behavior requires hardware testing.");
            if(ready && !serial.empty() && serial!="VRizationPhone" && !args.allowNative)
                throw std::runtime_error("Another HMD is active. Phone mirror refuses to capture a native headset.");
            runtime.quitting(); std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
        if(vrization::should_stop()) return 0;
        const auto selectedSerial=vrization::hmd_serial(runtime.system);
        int adapter=-1; runtime.system->GetDXGIOutputInfo(&adapter);
        if(adapter<0) throw std::runtime_error("SteamVR did not report a DXGI adapter");
        auto gpu=vrization::Device::adapter(adapter); vrization::EyePacker packer(gpu);
        MirrorEyes eyes(vr::VRCompositor());
        while(!vrization::should_stop() && !eyes.acquire(gpu.device.Get())) {
            if(GetTickCount64()>=deadline) throw std::runtime_error("SteamVR mirror eye textures not ready");
            runtime.quitting(); std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
        if(vrization::should_stop()) return 0;
        std::cout<<"ready: undistorted per-eye D3D11 mirror, GPU downsample then SBS BGRA"<<std::endl;
        const auto interval=std::chrono::microseconds(1000000/args.fps);
        while(!runtime.quitting()) {
            const auto start=std::chrono::steady_clock::now();
            const auto serial=vrization::hmd_serial(runtime.system);
            if(serial.empty() || serial!=selectedSerial || (!args.allowNative && serial!="VRizationPhone"))
                throw std::runtime_error("Selected HMD disconnected or changed; mirror stopped");
            const auto pixels=packer.pack(eyes.left(),eyes.right(),args.width);
            writer.publish(pixels.data(),packer.width(),packer.height());
            std::this_thread::sleep_until(start+interval);
        }
        writer.publish(nullptr,0,0,false); return 0;
    } catch(const std::exception& error) { std::cerr<<"error: "<<error.what()<<std::endl; return 1; }
}

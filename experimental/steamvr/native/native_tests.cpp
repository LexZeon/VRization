// Original VRization native fixture tests, MIT. No SteamVR runtime is started.
#include "pose.hpp"
#include "gpu.hpp"
#include "stop.hpp"
#include <functional>
#include <iostream>
#include <limits>
#include <memory>

namespace {
int checks=0;
void require(bool condition,const char* label) {
    ++checks; if(!condition) throw std::runtime_error(label);
}
std::wstring unique_map(const wchar_t* suffix) {
    return L"Local\\VRizationNativeTest-"+std::to_wstring(GetCurrentProcessId())+L"-"+
        std::to_wstring(GetTickCount64())+L"-"+suffix;
}
vrization::PoseHeader pose_fixture() {
    vrization::PoseHeader p{}; std::memcpy(p.magic,"VRP1",4);p.version=1;p.headerSize=128;
    p.tickMs=1000;p.poseSequence=0;p.quaternionXYZW[3]=1;p.positionXYZ[1]=1.6;
    p.flags=vrization::kActive|vrization::kTrackingValid; return p;
}
void pose_tests() {
    auto p=pose_fixture();
    require(vrization::valid_pose(p,1000),"sequence zero is a valid first negotiated pose");
    require(vrization::valid_pose(p,1500),"fresh boundary 500ms inclusive");
    require(!vrization::valid_pose(p,1501),"stale pose rejected");
    require(!vrization::valid_pose(p,999),"future tick rejected");
    auto result=vrization::driver_pose(p,1000);
    require(result.poseIsValid && result.deviceIsConnected && result.vecPosition[1]==1.6,"3DOF valid identity input accepted, not synthesized");
    p.quaternionXYZW[1]=std::sqrt(.5);p.quaternionXYZW[3]=std::sqrt(.5);
    result=vrization::driver_pose(p,1000);
    require(std::abs(result.qRotation.y-std::sqrt(.5))<1e-12 && std::abs(result.qRotation.w-std::sqrt(.5))<1e-12,"XYZW wire becomes WXYZ ABI without axis change");
    p.flags|=vrization::kPaused; result=vrization::driver_pose(p,1000);
    require(!result.poseIsValid && result.deviceIsConnected,"pause invalidates tracking without pretending device disappeared");
    p=pose_fixture();p.quaternionXYZW[3]=0;
    require(!vrization::valid_pose(p,1000),"zero quaternion never becomes valid identity");
    p=pose_fixture();p.quaternionXYZW[0]=std::numeric_limits<double>::quiet_NaN();
    require(!vrization::valid_pose(p,1000),"NaN quaternion rejected");
    p=pose_fixture();p.quaternionXYZW[3]=2;
    require(!vrization::valid_pose(p,1000),"nonunit quaternion rejected");
    p=pose_fixture();p.positionXYZ[2]=std::numeric_limits<double>::infinity();
    require(!vrization::valid_pose(p,1000),"nonfinite position rejected");
    p=pose_fixture();p.flags|=8;
    require(!vrization::valid_pose(p,1000),"unknown pose flags rejected");
    p=pose_fixture();p.flags=vrization::kActive;
    require(!vrization::driver_pose(p,1000).poseIsValid,"no sensor tracking-valid flag produces no valid pose");
    p=pose_fixture();p.seqlock=1;
    require(!vrization::pose_header(p),"odd in-progress pose rejected");
    p=pose_fixture();p.headerSize=64;
    require(!vrization::pose_header(p),"incompatible header rejected");
    p=pose_fixture();result=vrization::driver_pose(p,1501);
    require(!result.poseIsValid && !result.deviceIsConnected,"stale pose disconnected and invalid");
}
void ipc_tests() {
    // Windows mappings are page aligned, unlike an arbitrary stack-packed header.
    const auto name=unique_map(L"frame"); vrization::FrameWriter writer(name);
    vrization::Mapping reader; require(reader.open(name,vrization::kFrameMapBytes),"readonly reader opens writer mapping");
    vrization::FrameHeader f{}; std::vector<std::uint8_t> pixels;
    require(vrization::snapshot_frame(reader.data(),f,pixels) && f.flags==0 && pixels.empty(),"writer starts inactive");
    const std::uint8_t test[16]={0,0,255,255,255,0,0,255,7,11,19,255,99,31,61,255};
    writer.publish(test,2,2); require(vrization::snapshot_frame(reader.data(),f,pixels),"active frame snapshot succeeds");
    require(f.width==2 && f.height==2 && f.stride==8 && !(f.seqlock&1),"exact tight BGRA header");
    require(pixels==std::vector<std::uint8_t>(test,test+16),"payload bytes preserved");
    require(vrization::fresh(f.tickMs,GetTickCount64()),"native tick uses Windows uptime");
    const auto previous=f.seqlock;writer.publish(test,2,2);
    vrization::snapshot_frame(reader.data(),f,pixels);require(f.seqlock==previous+2,"seqlock increments per complete frame");
    bool refused=false;try { vrization::FrameWriter conflicting(name); } catch(const std::exception&) { refused=true; }
    require(refused,"existing map writer ownership rejected");
    writer.publish(nullptr,0,0,false);require(vrization::snapshot_frame(reader.data(),f,pixels) && !f.flags && pixels.empty(),"Stop publishes inactive and clears reader pixels");
    const std::uint8_t odd[12]={1,2,3,255,4,5,6,255,7,8,9,255};writer.publish(odd,3,1);
    require(vrization::snapshot_frame(reader.data(),f,pixels) && f.width==3 && f.stride==12,"mono overlay permits odd width");
    writer.publish(nullptr,0,0,false);
    require(!vrization::local_map_name(L"Global\\unsafe") && !vrization::local_map_name(L"Local\\a/b"),"bounded Local namespace only");
    const auto next=unique_map(L"new-generation"); vrization::FrameWriter nextWriter(next); vrization::Mapping nextReader;
    require(nextReader.open(next,vrization::kFrameMapBytes),"new generation uses separate map");
    nextWriter.publish(test,2,2);require(vrization::snapshot_frame(nextReader.data(),f,pixels) && (f.flags&1),"new generation independently active");
    require(vrization::snapshot_frame(reader.data(),f,pixels) && !f.flags,"old generation remains inactive");
    vrization::Mapping fixture;fixture.create(unique_map(L"fixture"),vrization::kFrameMapBytes);
    auto memory=static_cast<std::uint8_t*>(fixture.data());auto header=reinterpret_cast<vrization::FrameHeader*>(memory);
    std::memcpy(header->magic,"VRF1",4);header->version=1;header->headerSize=64;header->flags=1;header->width=1921;header->height=1;header->stride=7684;
    require(!vrization::snapshot_frame(memory,f,pixels),"oversized frame rejected before payload read");
    header->width=2;header->stride=7;
    require(!vrization::snapshot_frame(memory,f,pixels),"wrong row stride rejected");
    header->stride=8;header->seqlock=1;
    require(!vrization::snapshot_frame(memory,f,pixels),"in-progress frame not displayed");
    auto pp=reinterpret_cast<vrization::PoseHeader*>(memory); *pp=pose_fixture();
    vrization::PoseHeader snapshot{};
    require(vrization::snapshot_header(memory,snapshot) && snapshot.positionXYZ[1]==1.6,"128-byte pose IPC snapshot");
    pp->seqlock=1;require(!vrization::snapshot_header(memory,snapshot),"in-progress pose snapshot rejected");
}
void stop_tests() {
    vrization::stopping=false;const auto name=unique_map(L"stop");
    HANDLE event=CreateEventW(nullptr,TRUE,FALSE,name.c_str());require(event!=nullptr,"host-owned manual-reset Stop event fixture");
    struct Close { HANDLE handle;~Close(){CloseHandle(handle);} } close{event};
    {
        vrization::StopEvent observer(name);require(!vrization::should_stop(),"Stop reader initially quiet");
        require(SetEvent(event)!=FALSE,"host can signal owned Stop event");
        require(vrization::should_stop(),"native loop observes host Stop without blocking");
        ResetEvent(event);require(vrization::should_stop(),"Stop request remains latched after signal reset");
    }
    require(vrization::stopHandle==nullptr,"native event reader released on cleanup");
    vrization::stopping=false;bool refused=false;
    try { vrization::StopEvent missing(unique_map(L"missing-stop")); }catch(const std::exception&) { refused=true; }
    require(refused,"provided missing host Stop event refuses uncontrolled launch");
}
vrization::ComPtr<ID3D11ShaderResourceView> texture(vrization::Device& gpu,UINT w,UINT h,const std::vector<std::uint8_t>& pixels,bool srgb=false) {
    D3D11_TEXTURE2D_DESC d{}; d.Width=w;d.Height=h;d.MipLevels=d.ArraySize=1;d.SampleDesc.Count=1;
    d.Format=srgb?DXGI_FORMAT_R8G8B8A8_UNORM_SRGB:DXGI_FORMAT_R8G8B8A8_UNORM;
    d.Usage=D3D11_USAGE_IMMUTABLE;d.BindFlags=D3D11_BIND_SHADER_RESOURCE;
    D3D11_SUBRESOURCE_DATA data{};data.pSysMem=pixels.data();data.SysMemPitch=w*4;
    vrization::ComPtr<ID3D11Texture2D> source;vrization::checked(gpu.device->CreateTexture2D(&d,&data,&source),"Fixture texture");
    vrization::ComPtr<ID3D11ShaderResourceView> view;vrization::checked(gpu.device->CreateShaderResourceView(source.Get(),nullptr,&view),"Fixture SRV");return view;
}
void near_byte(std::uint8_t actual,int expected,const char* message) { require(std::abs(static_cast<int>(actual)-expected)<=2,message); }
void gpu_tests() {
    auto gpu=vrization::Device::warp(); vrization::EyePacker packer(gpu);
    std::vector<std::uint8_t> red(8*4*4),blue(red.size());
    for(std::size_t i=0;i<red.size();i+=4) { red[i]=255;red[i+3]=255;blue[i+2]=255;blue[i+3]=255; }
    auto left=texture(gpu,8,4,red),right=texture(gpu,8,4,blue);
    auto bgra=packer.pack(left.Get(),right.Get(),8);
    require(packer.width()==8 && packer.height()==2,"per-eye aspect preserved during downsample");
    for(UINT y=0;y<2;++y) for(UINT x=0;x<8;++x) {
        const auto i=(y*8+x)*4;require(bgra[i]==(x<4?0:255) && bgra[i+1]==0 && bgra[i+2]==(x<4?255:0) && bgra[i+3]==255,"red-left blue-right BGRA including seam and all edges");
    }
    std::vector<std::uint8_t> gradient(8*4*4);
    for(UINT y=0;y<4;++y) for(UINT x=0;x<8;++x) { const auto i=(y*8+x)*4;gradient[i]=static_cast<std::uint8_t>(20*x);gradient[i+1]=static_cast<std::uint8_t>(40*y);gradient[i+2]=37;gradient[i+3]=255; }
    auto grid=texture(gpu,8,4,gradient);bgra=packer.pack(grid.Get(),grid.Get(),16);
    require(packer.width()==16 && packer.height()==4,"one-to-one GPU output dimension");
    for(UINT y=0;y<4;++y) for(UINT x=0;x<16;++x) {
        const auto i=(y*16+x)*4;near_byte(bgra[i],37,"blue channel stays intact");near_byte(bgra[i+1],40*y,"vertical orientation preserved");near_byte(bgra[i+2],20*(x%8),"independent eye gradient including center edge");
    }
    bgra=packer.pack(grid.Get(),grid.Get(),8);
    for(UINT y=0;y<2;++y) for(UINT x=0;x<8;++x) {
        const auto i=(y*8+x)*4;near_byte(bgra[i+1],40*(2*y)+20,"linear half-size vertical samples");near_byte(bgra[i+2],20*(2*(x%4))+10,"linear half-size horizontal samples");
    }
    auto srgb=texture(gpu,8,4,gradient,true);bgra=packer.pack(srgb.Get(),srgb.Get(),16);
    for(UINT y=0;y<4;++y) for(UINT x=0;x<16;++x) { const auto i=(y*16+x)*4;near_byte(bgra[i+2],20*(x%8),"sRGB typed SRV reencoded exactly once"); }
    auto size=vrization::packed_size(641,1024,1024);require(size.first==640 && size.second==320,"odd requested width becomes even SBS");
    size=vrization::packed_size(1920,100,1000);require(size.first==216 && size.second==1080,"tall source fits maximum height preserving aspect");
    bool refused=false;try { auto other=texture(gpu,4,4,red);packer.pack(left.Get(),other.Get(),8); }catch(const std::exception&) { refused=true; }
    require(refused,"different eye aspects refused instead of silently stretching");
}
void factory_tests(const wchar_t* dll) {
    HMODULE module=LoadLibraryExW(dll,nullptr,LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR|LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
    require(module!=nullptr,"driver DLL loads without SteamVR runtime");
    struct Close { HMODULE module;~Close(){FreeLibrary(module);} } close{module};
    using Factory=void* (*)(const char*,int*);
    auto factory=reinterpret_cast<Factory>(GetProcAddress(module,"HmdDriverFactory"));require(factory!=nullptr,"factory symbol exported");
    int error=-1;auto provider=static_cast<vr::IServerTrackedDeviceProvider*>(factory(vr::IServerTrackedDeviceProvider_Version,&error));
    require(provider && error==vr::VRInitError_None,"pinned provider factory ABI");
    const auto versions=provider->GetInterfaceVersions();bool display=false;
    for(int i=0;versions && versions[i] && i<100;++i) if(std::strcmp(versions[i],vr::IVRDisplayComponent_Version)==0) display=true;
    require(display,"factory advertises pinned display ABI");
    require(!provider->ShouldBlockStandbyMode(),"driver does not keep unrelated runtime awake");
    require(!factory("unsupported_fixture_interface",&error) && error==vr::VRInitError_Init_InterfaceNotFound,"unknown interface fails correctly");
    require(!factory(nullptr,nullptr),"null factory arguments fail safely");
    // Deliberately do NOT call provider.Init with a fake context or treat runtime failure as a pass.
}
}
int wmain(int argc,wchar_t** argv) {
    try {
        if(argc!=2) throw std::runtime_error("Pass driver DLL path");
        pose_tests();ipc_tests();stop_tests();gpu_tests();factory_tests(argv[1]);
        std::cout<<"PASS: "<<checks<<" native fixture checks (IPC, pose, owned Stop, WARP pixels, factory ABI); no SteamVR/hardware test"<<std::endl;return 0;
    }catch(const std::exception& error){std::cerr<<"FAIL after "<<checks<<" checks: "<<error.what()<<std::endl;return 1;}
}

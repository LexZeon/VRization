// Original VRization D3D11 implementation, MIT. Uses Windows system APIs.
#pragma once
#include <d3d11.h>
#include <d3dcompiler.h>
#include <dxgi1_2.h>
#include <wrl/client.h>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
#include <cstdint>

namespace vrization {
using Microsoft::WRL::ComPtr;
inline void checked(HRESULT value, const char* operation) {
    if (FAILED(value)) throw std::runtime_error(std::string(operation)+" failed (HRESULT "+std::to_string(static_cast<unsigned long>(value))+")");
}
struct Device {
    ComPtr<ID3D11Device> device; ComPtr<ID3D11DeviceContext> context;
    static Device adapter(int index) {
        ComPtr<IDXGIFactory1> factory; checked(CreateDXGIFactory1(IID_PPV_ARGS(&factory)),"CreateDXGIFactory1");
        ComPtr<IDXGIAdapter1> selected; checked(factory->EnumAdapters1(static_cast<UINT>(index),&selected),"SteamVR DXGI adapter");
        Device result; const D3D_FEATURE_LEVEL levels[]={D3D_FEATURE_LEVEL_11_0};
        checked(D3D11CreateDevice(selected.Get(),D3D_DRIVER_TYPE_UNKNOWN,nullptr,D3D11_CREATE_DEVICE_BGRA_SUPPORT,
            levels,1,D3D11_SDK_VERSION,&result.device,nullptr,&result.context),"D3D11CreateDevice"); return result;
    }
    static Device warp() {
        Device result; const D3D_FEATURE_LEVEL levels[]={D3D_FEATURE_LEVEL_11_0};
        checked(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,D3D11_CREATE_DEVICE_BGRA_SUPPORT,
            levels,1,D3D11_SDK_VERSION,&result.device,nullptr,&result.context),"D3D11 WARP"); return result;
    }
};
inline D3D11_TEXTURE2D_DESC description(ID3D11ShaderResourceView* view) {
    if(!view) throw std::runtime_error("Missing mirror eye texture");
    D3D11_SHADER_RESOURCE_VIEW_DESC resourceView{};view->GetDesc(&resourceView);
    if(resourceView.ViewDimension!=D3D11_SRV_DIMENSION_TEXTURE2D || resourceView.Texture2D.MostDetailedMip!=0)
        throw std::runtime_error("Unsupported mirror SRV dimension/mip");
    ComPtr<ID3D11Resource> resource; view->GetResource(&resource); ComPtr<ID3D11Texture2D> texture;
    checked(resource.As(&texture),"Mirror texture type"); D3D11_TEXTURE2D_DESC desc{}; texture->GetDesc(&desc);
    if(desc.SampleDesc.Count!=1) throw std::runtime_error("Unsupported multisampled mirror texture"); return desc;
}
inline std::pair<UINT,UINT> packed_size(UINT requestedWidth, UINT sourceWidth, UINT sourceHeight) {
    if (!sourceWidth || !sourceHeight) throw std::runtime_error("Empty mirror texture");
    UINT eyeWidth=std::clamp(requestedWidth,2U,1920U)/2;
    UINT height=std::max(1U,static_cast<UINT>(std::llround(static_cast<double>(eyeWidth)*sourceHeight/sourceWidth)));
    if (height>1080) { eyeWidth=std::max(1U,static_cast<UINT>(1080.0*sourceWidth/sourceHeight)); height=std::max(1U,static_cast<UINT>(std::llround(static_cast<double>(eyeWidth)*sourceHeight/sourceWidth))); }
    if (height>1080) throw std::runtime_error("Unsupported eye aspect"); return {eyeWidth*2,height};
}
class EyePacker {
    Device& gpu_; ComPtr<ID3D11VertexShader> vertex_; ComPtr<ID3D11PixelShader> pixel_;
    ComPtr<ID3D11SamplerState> sampler_; ComPtr<ID3D11Buffer> constants_;
    ComPtr<ID3D11Texture2D> output_, staging_; ComPtr<ID3D11RenderTargetView> target_;
    UINT width_=0,height_=0;
public:
    explicit EyePacker(Device& gpu):gpu_(gpu) {
        const char shader[]=R"(
struct Vertex { float4 position:SV_POSITION; float2 uv:TEXCOORD0; };
Vertex vs(uint id:SV_VertexID) { Vertex v; v.uv=float2((id<<1)&2,id&2); v.position=float4(v.uv*float2(2,-2)+float2(-1,1),0,1); return v; }
Texture2D source:register(t0); SamplerState linearClamp:register(s0);
cbuffer Options:register(b0) { uint encodeSrgb; float3 padding; }
float4 ps(Vertex v):SV_TARGET { float4 c=source.Sample(linearClamp,v.uv);
 if(encodeSrgb) { c.rgb=lerp(12.92*c.rgb,1.055*pow(max(c.rgb,0),1.0/2.4)-0.055,step(0.0031308,c.rgb)); }
 return float4(c.rgb,1); })";
        ComPtr<ID3DBlob> vs,ps,error;
        checked(D3DCompile(shader,sizeof(shader)-1,nullptr,nullptr,nullptr,"vs","vs_5_0",D3DCOMPILE_ENABLE_STRICTNESS,0,&vs,&error),"Compile pack vertex shader");
        checked(D3DCompile(shader,sizeof(shader)-1,nullptr,nullptr,nullptr,"ps","ps_5_0",D3DCOMPILE_ENABLE_STRICTNESS,0,&ps,&error),"Compile pack pixel shader");
        checked(gpu.device->CreateVertexShader(vs->GetBufferPointer(),vs->GetBufferSize(),nullptr,&vertex_),"Create pack VS");
        checked(gpu.device->CreatePixelShader(ps->GetBufferPointer(),ps->GetBufferSize(),nullptr,&pixel_),"Create pack PS");
        D3D11_SAMPLER_DESC sample{}; sample.Filter=D3D11_FILTER_MIN_MAG_MIP_LINEAR; sample.AddressU=sample.AddressV=sample.AddressW=D3D11_TEXTURE_ADDRESS_CLAMP; sample.MaxLOD=D3D11_FLOAT32_MAX;
        checked(gpu.device->CreateSamplerState(&sample,&sampler_),"Create sampler");
        D3D11_BUFFER_DESC buffer{}; buffer.ByteWidth=16; buffer.Usage=D3D11_USAGE_DEFAULT; buffer.BindFlags=D3D11_BIND_CONSTANT_BUFFER;
        checked(gpu.device->CreateBuffer(&buffer,nullptr,&constants_),"Create pack options");
    }
    std::vector<std::uint8_t> pack(ID3D11ShaderResourceView* left, ID3D11ShaderResourceView* right, UINT requestedWidth) {
        const auto l=description(left), r=description(right);
        if (static_cast<std::uint64_t>(l.Width)*r.Height!=static_cast<std::uint64_t>(r.Width)*l.Height) throw std::runtime_error("Mirror eye aspects differ");
        const auto size=packed_size(requestedWidth,l.Width,l.Height);
        if (size.first!=width_ || size.second!=height_) {
            target_.Reset(); output_.Reset(); staging_.Reset(); width_=size.first; height_=size.second;
            D3D11_TEXTURE2D_DESC d{}; d.Width=width_;d.Height=height_;d.MipLevels=d.ArraySize=1;d.Format=DXGI_FORMAT_B8G8R8A8_UNORM;d.SampleDesc.Count=1;d.Usage=D3D11_USAGE_DEFAULT;d.BindFlags=D3D11_BIND_RENDER_TARGET;
            checked(gpu_.device->CreateTexture2D(&d,nullptr,&output_),"Create packed texture");
            checked(gpu_.device->CreateRenderTargetView(output_.Get(),nullptr,&target_),"Create packed RTV");
            d.Usage=D3D11_USAGE_STAGING; d.BindFlags=0; d.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
            checked(gpu_.device->CreateTexture2D(&d,nullptr,&staging_),"Create small staging texture");
        }
        auto context=gpu_.context.Get(); ID3D11RenderTargetView* target=target_.Get(); context->OMSetRenderTargets(1,&target,nullptr);
        context->IASetInputLayout(nullptr); context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
        context->VSSetShader(vertex_.Get(),nullptr,0); context->PSSetShader(pixel_.Get(),nullptr,0);
        ID3D11SamplerState* sampler=sampler_.Get();context->PSSetSamplers(0,1,&sampler);
        ID3D11Buffer* constants=constants_.Get();context->PSSetConstantBuffers(0,1,&constants);
        for (UINT eye=0;eye<2;++eye) {
            ID3D11ShaderResourceView* source=eye?right:left; D3D11_SHADER_RESOURCE_VIEW_DESC d{}; source->GetDesc(&d);
            const bool srgb=d.Format==DXGI_FORMAT_R8G8B8A8_UNORM_SRGB || d.Format==DXGI_FORMAT_B8G8R8A8_UNORM_SRGB || d.Format==DXGI_FORMAT_B8G8R8X8_UNORM_SRGB;
            const UINT options[4]={srgb?1U:0U,0,0,0}; context->UpdateSubresource(constants_.Get(),0,nullptr,options,0,0);
            D3D11_VIEWPORT viewport{static_cast<float>(eye*(width_/2)),0,static_cast<float>(width_/2),static_cast<float>(height_),0,1};
            context->RSSetViewports(1,&viewport);context->PSSetShaderResources(0,1,&source);context->Draw(3,0);
        }
        ID3D11ShaderResourceView* empty=nullptr;context->PSSetShaderResources(0,1,&empty);context->OMSetRenderTargets(0,nullptr,nullptr);
        context->CopyResource(staging_.Get(),output_.Get());D3D11_MAPPED_SUBRESOURCE mapped{};
        std::vector<std::uint8_t> bytes(static_cast<std::size_t>(width_)*height_*4);
        checked(context->Map(staging_.Get(),0,D3D11_MAP_READ,0,&mapped),"Read packed BGRA");
        for(UINT y=0;y<height_;++y) std::memcpy(bytes.data()+static_cast<std::size_t>(y)*width_*4,static_cast<const std::uint8_t*>(mapped.pData)+static_cast<std::size_t>(y)*mapped.RowPitch,width_*4);
        context->Unmap(staging_.Get(),0);return bytes;
    }
    UINT width() const { return width_; } UINT height() const { return height_; }
};
} // namespace vrization

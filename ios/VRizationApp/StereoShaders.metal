#include <metal_stdlib>
using namespace metal;

struct Raster { float4 position [[position]]; float2 uv; };
struct Uniforms { float4 optics; float4 placement; float4 scene; float4 flags; };
vertex Raster stereoVertex(uint id [[vertex_id]]) {
    const float2 positions[] = {float2(-1,-1),float2(1,-1),float2(-1,1),float2(1,1)};
    Raster out; out.position=float4(positions[id],0,1); out.uv=(positions[id]+1)*0.5; return out;
}
fragment float4 stereoFragment(Raster in [[stage_in]], constant Uniforms &u [[buffer(0)]],
                               texture2d<float> video [[texture(0)]]) {
    float aspect=u.optics.x, imageAspect=u.optics.y, scale=u.optics.z, offsetX=u.optics.w;
    float offsetY=u.placement.x, eyeShift=u.placement.y, distortion=u.placement.z, fov=u.placement.w;
    float distance=u.scene.x, yaw=u.scene.y, pitch=u.scene.z, roll=u.scene.w;
    float2 p=(in.uv-0.5)*2;
    p*=1+distortion*dot(p,p);
    p=(p-float2(offsetX+eyeShift,offsetY))/scale;
    float2 q;
    if(u.flags.x>0.5) {
        float f=tan(fov*(M_PI_F/180.0f)*0.5f);
        float3 r=normalize(float3(p.x*aspect*f,p.y*f,-1));
        float cr=cos(roll),sr=sin(roll); r=float3(cr*r.x+sr*r.y,-sr*r.x+cr*r.y,r.z);
        float cp=cos(pitch),sp=sin(pitch); r=float3(r.x,cp*r.y-sp*r.z,sp*r.y+cp*r.z);
        float cy=cos(yaw),sy=sin(yaw); r=float3(cy*r.x-sy*r.z,r.y,sy*r.x+cy*r.z);
        if(r.z>=-0.001) return float4(0,0,0,1);
        float2 hit=r.xy*(-distance/r.z)+float2(u.flags.y*0.032,0);
        q=hit/float2(2,2/imageAspect);
    } else {
        float2 fit=float2(min(1.0f,imageAspect/aspect),min(1.0f,aspect/imageAspect));
        q=p/fit;
    }
    if(abs(q.x)>1 || abs(q.y)>1) return float4(0,0,0,1);
    constexpr sampler linearSampler(coord::normalized,address::clamp_to_edge,filter::linear);
    return video.sample(linearSampler,float2(q.x*0.5+0.5,0.5-q.y*0.5));
}

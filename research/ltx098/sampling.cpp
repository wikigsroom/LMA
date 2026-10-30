// SPDX-License-Identifier: Apache-2.0
// Independent port of pinned Lightricks patch geometry and RF scheduler equations.
#include "sampling.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace lma::ltx098 {
static void require(bool value,const char* message) { if(!value) throw std::runtime_error(message); }
static bool finite(const std::vector<float>& values) { return std::all_of(values.begin(),values.end(),[](float x){return std::isfinite(x);}); }
Geometry geometry(int width,int height,int frames,float fps) {
    require(width>=32&&height>=32&&width<=2048&&height<=2048&&width%32==0&&height%32==0,"Video dimensions must be multiples of 32 within 32..2048");
    require(frames>=1&&frames<=257&&(frames-1)%8==0,"Video frame count must be 8n+1 within 1..257");
    require(std::isfinite(fps)&&fps>=1&&fps<=240,"Frame rate outside 1..240");
    Geometry result;result.width=width;result.height=height;result.frames=frames;result.fps=fps;
    result.latent_width=width/32;result.latent_height=height/32;result.latent_frames=(frames-1)/8+1;
    result.tokens=result.latent_width*result.latent_height*result.latent_frames;
    require(result.tokens<=4096,"Video geometry exceeds the reviewed 4096-token research budget");
    result.coordinates.resize(3*result.tokens);
    for(int t=0;t<result.latent_frames;++t) for(int y=0;y<result.latent_height;++y) for(int x=0;x<result.latent_width;++x) {
        int n=(t*result.latent_height+y)*result.latent_width+x;
        // Exact old checkpoint uses causal_temporal_positioning=False.
        // Match publisher multiply-by-reciprocal fractional-second conversion.
        result.coordinates[n]=float(t*8)*(1.f/fps);
        result.coordinates[result.tokens+n]=float(y*32);
        result.coordinates[2*result.tokens+n]=float(x*32);
    }
    return result;
}
std::array<float,8> distilled_sigmas() {
    // Publisher LinearQuadratic(8, threshold_noise=.025), not the metadata's
    // four-decimal allowed_inference_steps values.
    return {{1.f,.99375f,.9875f,.98125f,.975f,.909375f,.725f,.421875f}};
}
std::vector<float> multiscale_sigmas(bool second_pass) {
    // Explicit timesteps from configs/ltxv-2b-0.9.8-distilled.yaml.
    return second_pass?std::vector<float>{.9094f,.725f,.4219f}:std::vector<float>{1.f,.9937f,.9875f,.9812f,.975f,.9094f,.725f};
}
std::vector<float> multiscale_step(const std::vector<float>& sample,const std::vector<float>& velocity,float time,float next) {
    require(!sample.empty() && sample.size()==velocity.size() && finite(sample) && finite(velocity),"Invalid multiscale tensors");
    require(std::isfinite(time) && std::isfinite(next) && time>next && next>=0 && time<=1,"Invalid multiscale scheduler interval");
    auto result=sample;float dt=time-next;for(size_t i=0;i<result.size();++i)result[i]-=dt*velocity[i];
    require(finite(result),"Non-finite multiscale sampling update");return result;
}
std::vector<float> rf_step(const std::vector<float>& values,const std::vector<float>& velocity,const std::vector<float>& times,int channels,bool per_token) {
    require(channels>=1&&channels<=128&&!values.empty()&&values.size()%size_t(channels)==0,"Invalid rectified-flow channels/shape");
    require(values.size()==velocity.size()&&finite(values)&&finite(velocity)&&finite(times),"Invalid rectified-flow tensors");
    size_t tokens=values.size()/size_t(channels);require(times.size()==(per_token?tokens:1),"Sigma shape does not match its global/per-token mode");
    auto schedule=distilled_sigmas();std::vector<float> result(values.size());
    for(size_t n=0;n<tokens;++n) {
        float time=times[per_token?n:0];require(time>=0&&time<=1,"Rectified-flow sigma outside 0..1");
        require(per_token||time>1e-6f,"Global sigma has no lower scheduler time");
        float next=0;
        for(float candidate:schedule) if(candidate<time-1e-6f) { next=candidate;break; }
        float dt=time-next;
        for(int c=0;c<channels;++c) { size_t i=n*size_t(channels)+size_t(c);result[i]=values[i]-dt*velocity[i]; }
    }
    require(finite(result),"Non-finite rectified-flow update");return result;
}
std::vector<float> channels_first(const std::vector<float>& tokens,int channels,const Geometry& shape) {
    require(channels>=1&&channels<=128&&shape.tokens>=1&&tokens.size()==size_t(channels)*size_t(shape.tokens)&&finite(tokens),"Invalid latent unpatchify shape");
    std::vector<float> result(tokens.size());
    for(int n=0;n<shape.tokens;++n) for(int c=0;c<channels;++c) result[size_t(c)*size_t(shape.tokens)+size_t(n)]=tokens[size_t(n)*size_t(channels)+size_t(c)];
    return result;
}
SamplingResult sample(Transformer& model,Input input,const std::function<bool()>& cancelled,
                      const std::function<void(int,float)>& starting,const std::function<void(int,float,const std::vector<float>&)>& completed,
                      const std::vector<float>& explicit_schedule) {
    require(input.tokens>=1&&input.tokens<=4096&&!input.latents.empty()&&input.latents.size()%size_t(input.tokens)==0,"Invalid initial sample shape");
    int channels=int(input.latents.size()/size_t(input.tokens));require(channels>=1&&channels<=128,"Invalid sample channels");
    require(finite(input.latents),"Non-finite initial latent");SamplingResult result;
    auto check_cancel=[&](){if(cancelled&&cancelled()) throw std::runtime_error("Sampling cancelled");};
    auto legacy=distilled_sigmas();auto schedule=explicit_schedule.empty()?std::vector<float>(legacy.begin(),legacy.end()):explicit_schedule;
    require(!schedule.empty() && schedule.size()<=8 && finite(schedule),"Invalid explicit sampling schedule");
    float previous=2;for(float time:schedule){require(time>1e-6f && time<=1 && time<previous,"Non-decreasing or invalid schedule");previous=time;}
    for(int step=0;step<int(schedule.size());++step) {
        check_cancel();float sigma=schedule[size_t(step)];if(starting) starting(step,sigma);
        input.timesteps={sigma};auto forward=model.forward(input);check_cancel();
        if(explicit_schedule.empty())input.latents=rf_step(input.latents,forward.velocity,input.timesteps,channels);
        else {
            float next=step+1<int(schedule.size())?schedule[size_t(step+1)]:0;
            input.latents=multiscale_step(input.latents,forward.velocity,sigma,next);
        }
        result.compute_bytes.push_back(forward.compute_bytes);result.parameters=forward.parameters;result.layers=forward.layers;
        result.weight_bytes=forward.weight_bytes;result.backend=forward.backend;++result.steps;
        if(completed) completed(step,sigma,input.latents);check_cancel();
    }
    result.latents=std::move(input.latents);return result;
}
} // namespace lma::ltx098

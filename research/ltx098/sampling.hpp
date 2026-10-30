// SPDX-License-Identifier: Apache-2.0
// Old 0.9.8 latent geometry and deterministic distilled rectified-flow sampling.
#pragma once
#include "transformer.hpp"
#include <array>
#include <functional>

namespace lma::ltx098 {
struct Geometry {
    int width=0,height=0,frames=0,latent_width=0,latent_height=0,latent_frames=0,tokens=0;
    float fps=0;
    std::vector<float> coordinates;
};
Geometry geometry(int width,int height,int frames,float fps);
std::array<float,8> distilled_sigmas();
std::vector<float> multiscale_sigmas(bool second_pass);
std::vector<float> multiscale_step(const std::vector<float>& sample,const std::vector<float>& velocity,float time,float next);
std::vector<float> rf_step(const std::vector<float>& sample,const std::vector<float>& velocity,const std::vector<float>& times,int channels,bool per_token=false);
std::vector<float> channels_first(const std::vector<float>& tokens,int channels,const Geometry& shape);
struct SamplingResult {
    std::vector<float> latents;
    std::vector<uint64_t> compute_bytes;
    uint64_t parameters=0,weight_bytes=0;
    int layers=0,steps=0;
    std::string backend;
};
SamplingResult sample(Transformer& model,Input input,
    const std::function<bool()>& cancelled={},
    const std::function<void(int,float)>& starting={},
    const std::function<void(int,float,const std::vector<float>&)>& completed={},
    const std::vector<float>& explicit_schedule={});
} // namespace lma::ltx098

// SPDX-License-Identifier: MIT
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

namespace lma_sao {
inline void require(bool ok,const char* message) { if(!ok)throw std::runtime_error(message); }
constexpr size_t latent_size=64*256,decoded_frames=524288;
inline void bounds(int threads,int64_t seed,int seconds,int steps,int tokens) {
    require(threads>=1 && threads<=32 && seed>=0 && seed<=INT32_MAX,"Invalid CPU threads or resolved seed");
    require(seconds>=1 && seconds<=11 && steps>=1 && steps<=32 && tokens>=1 && tokens<=64,"Invalid duration, steps or prompt budget");
}
inline void prompt(const std::string& text) {require(!text.empty() && text.size()<=16000 && text.find('\0')==std::string::npos && text.find_first_not_of(" \r\n\t")!=std::string::npos,"Use a nonblank English audio description");}
inline void token_ids(std::vector<int>& ids,int budget,int vocab,int pad,int eos) {
    require(pad==0 && eos==1 && vocab==32000,"Tokenizer must match T5-base SentencePiece (32000 pieces, pad 0 / EOS 1)");
    for(int id:ids)require(id>=0 && id<vocab,"Tokenizer returned an invalid ID");
    if(ids.empty() || ids.back()!=1)ids.push_back(1);
    require(ids.size()<=size_t(budget) && ids.size()<=64,"Prompt exceeds effective T5 conditioning budget including EOS; shorten it");
}
// Arm reference fill_sigmas: sigmoid(-linspace(-6,2,N+1)), with exact endpoints.
inline std::vector<float> schedule(int steps) {
    require(steps>=1 && steps<=32,"Invalid step count");std::vector<float> out(size_t(steps)+1);
    float value=-6,delta=8.0f/steps;
    for(int i=0;i<=steps;i++){out[size_t(i)]=1.f/(1.f+std::exp(i==steps?2.f:value));value+=delta;}
    out.front()=1;out.back()=0;return out;
}
inline void random_normal(std::vector<float>& x,uint32_t seed) {std::mt19937 rng(seed);std::normal_distribution<float> normal(0,1);for(float& v:x)v=normal(rng);}
// Arm's caller gives each step seed + step + 4564; preserve this reference policy.
inline void advance(std::vector<float>& x,const std::vector<float>& velocity,float t,float next,uint32_t seed) {
    require(x.size()==velocity.size() && !x.empty() && std::isfinite(t) && std::isfinite(next) && t>next && t<=1 && next>=0,"Invalid sampler tensors or time");
    std::vector<float> noise(x.size());random_normal(noise,seed);
    for(size_t i=0;i<x.size();i++) {require(std::isfinite(x[i]) && std::isfinite(velocity[i]),"Nonfinite diffusion value");float denoised=x[i]-t*velocity[i];x[i]=(1-next)*denoised+next*noise[i];require(std::isfinite(x[i]),"Nonfinite sampled latent");}
}
inline std::string cpu_options(int threads) {require(threads>=1 && threads<=32,"Invalid CPU threads");return "kernel_mode = \"delegate\"\nnum_threads = "+std::to_string(threads)+"\n";}
inline std::vector<int16_t> pcm(const std::vector<float>& planar,int seconds) {
    require(seconds>=1 && seconds<=11 && planar.size()==2*decoded_frames,"Invalid decoder output");
    size_t frames=size_t(seconds)*44100;float peak=0;
    for(size_t i=0;i<planar.size();i++) {require(std::isfinite(planar[i]),"Nonfinite decoded audio");if(i%decoded_frames<frames)peak=std::max(peak,std::abs(planar[i]));}
    float gain=1/std::max(peak,1.f);std::vector<int16_t> out(frames*2);
    for(size_t i=0;i<frames;i++)for(size_t channel=0;channel<2;channel++)out[i*2+channel]=int16_t(std::round(std::clamp(planar[channel*decoded_frames+i]*gain,-1.f,1.f)*32767.f));
    return out;
}
inline void write_wave(const std::string& path,const std::vector<int16_t>& audio) {
    require(!audio.empty() && audio.size()%2==0 && audio.size()<=11*44100*2,"Invalid PCM length");std::ofstream out(path,std::ios::binary|std::ios::trunc);require(bool(out),"Cannot create private audio output");
    auto u16=[&](uint16_t value){char b[2]={char(value&255),char(value>>8)};out.write(b,2);};auto u32=[&](uint32_t value){u16(uint16_t(value));u16(uint16_t(value>>16));};
    uint32_t bytes=uint32_t(audio.size()*2);out.write("RIFF",4);u32(bytes+36);out.write("WAVEfmt ",8);u32(16);u16(1);u16(2);u32(44100);u32(44100*4);u16(4);u16(16);out.write("data",4);u32(bytes);for(int16_t v:audio)u16(uint16_t(v));out.close();require(bool(out),"Cannot finish audio output");
}
}

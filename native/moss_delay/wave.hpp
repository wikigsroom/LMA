#pragma once
#include "policy.hpp"
#include "../qwen_tts/wave.hpp"
namespace lma_moss {
inline std::vector<float> reference_wave(const std::string& path) {
    std::ifstream in(path,std::ios::binary|std::ios::ate);
    require(bool(in) && in.tellg()<=1024*1024,"MOSS reference WAV exceeds 1 MiB");in.close();
    auto samples=lma_qwen::reference_wave(path);
    require(samples.size()<=240000,"MOSS reference audio exceeds the 10 second application guard");return samples;
}
}

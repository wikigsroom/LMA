// SPDX-License-Identifier: MIT
#pragma once
#include "../soulx/dsp.hpp"
#include <cstdint>
#include <filesystem>
#include <string>

namespace lma::soulx {
// These files are USER model data, never application/runtime payloads.
// Each graph may reference only its own fixed '<filename>.data' sidecar.
struct AcousticModels { std::filesystem::path directory; };
struct AcousticInput {
    std::vector<int64_t> tokens; // reference codes followed by generated codes
    size_t prompt_tokens = 0;
    Matrix prompt_mel; // [80,2*prompt_tokens], exact aligned prefix
    Samples speaker; // CAMPPlus [192], not an arbitrary voice label
};
struct AcousticParams { int steps=15,threads=4; int64_t seed=0; float cfg=.7f; };
struct AcousticStats { size_t graph_runs=0,session_loads=0,session_unloads=0,max_live_sessions=0,terminated_runs=0; std::string runtime_version; };
using Progress = std::function<void(const std::string&,int,int)>;
using Noise = std::function<float()>;
using Trace = std::function<void(const std::string&,const Samples&,const std::vector<int64_t>&)>;
// Cancel can be polled from the ORT termination monitor: it must be thread-safe.
// Noise injection is for deterministic callers/checks; a seed-owned RNG is the
// default. Equal seeds do not promise bit-identical PyTorch/native RNG streams.
Samples synthesize_acoustic(const AcousticModels&,const AcousticInput&,const AcousticParams&,
    AcousticStats&,Cancel cancelled={},Progress progress={},Noise noise={},Trace trace={});
}

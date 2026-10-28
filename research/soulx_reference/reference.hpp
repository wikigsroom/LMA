// SPDX-License-Identifier: MIT
#pragma once
#include "../soulx_ort/types.hpp"

namespace lma::soulx {
struct ReferenceModels { std::filesystem::path directory; };
struct PreparedReference {
    std::vector<int64_t> tokens; // aligned reference semantic codes, no LM output
    Samples speaker; // unnormalized CAMPPlus [192], normalized by Flow encoder
    Matrix prompt_mel; // [80,2*tokens.size()], exact aligned reference prefix
    size_t source_samples=0,semantic_frames=0,speaker_frames=0,raw_tokens=0,raw_flow_frames=0;
};
// PCM has already been decoded to mono 24kHz, finite [-1,1], 1..15seconds.
// Cancel can be called concurrently by the ORT termination monitor.
// This function runs complete reference graphs, not the language/acoustic nets.
PreparedReference prepare_reference(const ReferenceModels&,const Samples& mono24k,int threads,
    OrtStats&,Cancel cancelled={},Progress progress={},Trace trace={});
}

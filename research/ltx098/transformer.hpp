// SPDX-License-Identifier: Apache-2.0
// Lightricks LTX-Video 0.9.8 architecture; LMA native GGML implementation, 2026.
#pragma once
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace lma::ltx098 {
struct Input {
    int tokens = 0, text_tokens = 0;
    std::vector<float> latents, context, coordinates, timesteps, text_mask;
};
struct Result {
    std::vector<float> velocity;
    int layers = 0;
    uint64_t parameters = 0, weight_bytes = 0, compute_bytes = 0;
    std::string backend;
};
class Transformer {
    struct Impl;
    std::unique_ptr<Impl> impl;
public:
    Transformer(const std::string& gguf, const std::string& backend, int threads, bool allow_fixture);
    ~Transformer();
    Transformer(const Transformer&) = delete;
    Transformer& operator=(const Transformer&) = delete;
    Result forward(const Input& input);
};
} // namespace lma::ltx098

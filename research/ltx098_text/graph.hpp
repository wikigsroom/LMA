// SPDX-License-Identifier: MIT
#pragma once
#include "encoder.hpp"
namespace lma::ltx098::text {
// An independent GGML encoder graph keeps F32 GELU explicit. The shared llama
// tokenizer remains unchanged; its stock CPU GEGLU uses an F16 lookup table.
class Graph {
public:
    Graph(const std::filesystem::path&,const Layout&,int,Cancel,Progress);
    ~Graph();
    std::vector<float> encode(const Tokens&);
    Buffers buffers() const;
private:
    struct State;
    std::unique_ptr<State> state_;
};
}

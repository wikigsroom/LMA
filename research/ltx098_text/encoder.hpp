// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
#include <filesystem>
#include <functional>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace lma::ltx098::text {
using Tokens = std::vector<int32_t>;
using Cancel = std::function<bool()>;
using Progress = std::function<void(const char*, int, int)>;
inline void require(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }
struct Options { int threads=4, max_tokens=256; bool fixture=false, vocabulary_only=false; std::vector<std::string> additional_special_tokens; };
struct Stats { int vocabulary_loads=0, vocabulary_unloads=0, model_loads=0, model_unloads=0, encode_calls=0, aborted_encodes=0; };
struct Tokenized { Tokens ids; bool truncated=false; };
struct Layout { int width=0, layers=0, heads=0, feed_forward=0, vocabulary=0, context=0; };
struct Buffers { uint64_t mapped_file_bytes=0, tensor_bytes=0, peak_compute_bytes=0; };
class Model {
public:
    Model(const std::filesystem::path&, const Options&, Stats&, Cancel={}, Progress={});
    ~Model();
    Model(const Model&)=delete;
    Model& operator=(const Model&)=delete;
    Tokenized tokenize(const std::string&) const;
    std::vector<float> encode(const Tokens&);
    const Layout& layout() const;
    Buffers buffers() const;
private:
    struct State;
    std::unique_ptr<State> state_;
};
}

// SPDX-License-Identifier: MIT
#pragma once
#include "policy.hpp"
#include <filesystem>
#include <memory>
namespace lma::soulx::language {
using Cancel=std::function<bool()>;
using Progress=std::function<void(const std::string&,int,int)>;
struct Options{int context=2048,threads=2,batch=128;bool vocabulary_only=false;};
struct Stats{int model_loads=0,model_unloads=0,decode_calls=0,decoded_tokens=0,aborted_decodes=0,generated_tokens=0,ras_resets=0,history_resets=0;};
struct Generated{int speaker=0;Tokens semantic,language_ids;bool eos=false,history_delimiter_inserted=false;size_t input_tokens=0;};
class Model{
    struct State;std::unique_ptr<State> state_;
public:
    Model(const std::filesystem::path& file,const Options& options,Stats& stats,Cancel cancelled={},Progress progress={});
    ~Model();Model(const Model&)=delete;Model& operator=(const Model&)=delete;
    Layout layout() const;Tokens tokenize(const std::string& text) const;
    std::vector<float> evaluate(Tokens input);
    std::vector<Generated> generate(const std::vector<Reference>& references,const std::vector<Turn>& turns,const Sampling& sampling,const Window& window,uint64_t seed);
};
}

// SPDX-License-Identifier: Apache-2.0
// Offline research probe. Not an App engine, inference provider or video generator.
#include "transformer.hpp"
#include "json.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#ifdef _WIN32
#include <codecvt>
#include <locale>
#endif
using json=nlohmann::json;
static int run(int argc,char** argv) {
    try {
        if(argc==2 && std::string(argv[1])=="--info") {
            std::cout<<json({{"architecture","ltx_video_2b_098_distilled_transformer"},{"engine_registered",false},{"complete_video_pipeline",false},{"model_data_embedded",false}})<<'\n'; return 0;
        }
        if(argc!=6 && argc!=7) throw std::runtime_error("Usage: lma_ltx098_probe MODEL.gguf CASE.json OUTPUT.f32 cpu|vulkan THREADS [--fixture]");
        bool fixture=argc==7 && std::string(argv[6])=="--fixture";
        if(argc==7 && !fixture) throw std::runtime_error("Unknown fixture flag");
        auto request_path=std::filesystem::u8path(argv[2]);
        if(std::filesystem::file_size(request_path)>32*1024*1024) throw std::runtime_error("Research request exceeds 32 MiB");
        std::ifstream request_file(request_path); auto request=json::parse(request_file);
        if(!request.at("tokens").is_number_integer() || !request.at("text_tokens").is_number_integer()) throw std::runtime_error("Token counts must be integers");
        // Check JSON integer bounds before narrowing; large unsigned counts
        // must not wrap back into otherwise valid small fixture dimensions.
        if(request.at("tokens")<1 || request.at("tokens")>4096 || request.at("text_tokens")<1 || request.at("text_tokens")>256) throw std::runtime_error("Token count outside research bounds");
        lma::ltx098::Input input; input.tokens=request.at("tokens").get<int>(); input.text_tokens=request.at("text_tokens").get<int>();
        input.latents=request.at("latents").get<std::vector<float>>(); input.context=request.at("context").get<std::vector<float>>();
        input.coordinates=request.at("coordinates").get<std::vector<float>>(); input.timesteps=request.at("timesteps").get<std::vector<float>>();
        input.text_mask=request.at("text_mask").get<std::vector<float>>();
        auto output=std::filesystem::u8path(argv[3]); if(std::filesystem::exists(output)) throw std::runtime_error("Output already exists");
        size_t consumed=0;int threads=std::stoi(argv[5],&consumed);
        if(consumed!=std::string(argv[5]).size()) throw std::runtime_error("Thread count must be an integer");
        lma::ltx098::Transformer model(argv[1],argv[4],threads,fixture); auto result=model.forward(input);
        std::ofstream stream(output,std::ios::binary); stream.write(reinterpret_cast<const char*>(result.velocity.data()),std::streamsize(result.velocity.size()*sizeof(float)));
        stream.close(); if(!stream) throw std::runtime_error("Unable to save output");
        std::cout<<json({{"ok",true},{"layers",result.layers},{"parameters",result.parameters},{"weight_bytes",result.weight_bytes},{"compute_bytes",result.compute_bytes},{"backend",result.backend},{"precision_policy",result.backend=="vulkan"?"baseline_f32_compute_optional_f16_weight_storage":"native_cpu"},{"values",result.velocity.size()},{"fixture",fixture},{"complete_video_pipeline",false},{"physical_android",false}})<<'\n';return 0;
    } catch(const std::exception& error) { std::cout<<json({{"ok",false},{"error",error.what()},{"complete_video_pipeline",false}})<<'\n'; return 2; }
}
#ifdef _WIN32
int wmain(int argc,wchar_t** argv) {
    std::wstring_convert<std::codecvt_utf8_utf16<wchar_t>> convert; std::vector<std::string> values; std::vector<char*> pointers;
    for(int i=0;i<argc;++i) values.push_back(convert.to_bytes(argv[i]));
    for(auto& value:values) pointers.push_back(value.data()); return run(argc,pointers.data());
}
#else
int main(int argc,char** argv) { return run(argc,argv); }
#endif

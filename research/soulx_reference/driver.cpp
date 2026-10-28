// SPDX-License-Identifier: MIT
// Developer PCM reference CLI; not a registered App worker or HTTP endpoint.
#include "reference.hpp"
#include "json.hpp"
#include <atomic>
#include <chrono>
#include <cstring>
#include <fstream>
#include <iostream>
#include <thread>
namespace fs=std::filesystem;
using namespace lma::soulx;
using json=nlohmann::json;
std::string read(const fs::path& path,size_t maximum) {
    auto n=fs::file_size(path);if(!n || n>maximum)throw std::runtime_error("Reference developer input exceeds bounds");
    std::string data(static_cast<size_t>(n),'\0');std::ifstream stream(path,std::ios::binary);
    if(!stream.read(data.data(),static_cast<std::streamsize>(n)))throw std::runtime_error("Cannot read reference input");return data;
}
template<typename T>void write(const fs::path& path,const std::vector<T>& values) {
    std::ofstream stream(path,std::ios::binary);stream.write(reinterpret_cast<const char*>(values.data()),static_cast<std::streamsize>(values.size()*sizeof(T)));
    if(!stream)throw std::runtime_error("Cannot write reference developer output");
}
int main(int argc,char** argv) {
    OrtStats stats;std::atomic<bool> cancelled{false};std::thread delayed;
    struct Join{std::thread& thread;~Join(){if(thread.joinable())thread.join();}}join{delayed};
    try {
        if(argc!=4)throw std::runtime_error("Usage: reference-cli MODEL_DIR INPUT_DIR NEW_OUTPUT_DIR");
        fs::path models=argv[1],directory=argv[2],output_dir=argv[3];
        if(fs::exists(output_dir))throw std::runtime_error("Reference output must be a new directory");
        auto manifest=json::parse(read(models/"soulx-reference.json",128*1024));
        if(manifest.at("format")!="lma.soulx-reference-onnx/1")throw std::runtime_error("Unknown reference model layout");
        auto request=json::parse(read(directory/"input.json",64*1024));
        if(request.at("format")!="lma.soulx-reference-input/1")throw std::runtime_error("Unknown reference input format");
        auto data=read(directory/"pcm.f32",4*kMaxReference24k+4);
        if(data.size()%4)throw std::runtime_error("Malformed PCM bytes");Samples pcm(data.size()/4);std::memcpy(pcm.data(),data.data(),data.size());
        std::string mode=request.value("mode",std::string("prepare"));bool traces=request.value("trace",false);
        std::vector<std::pair<std::string,Samples>> traced;json shapes=json::object();
        Trace trace;if(traces)trace=[&](const std::string& name,const Samples& values,const std::vector<int64_t>& shape){traced.emplace_back(name,values);shapes[name]=shape;};
        auto progress=[&](const std::string& stage,int done,int total){
            (void)total;
            if(mode=="cancel_before" && stage=="reference_features" && done==0)cancelled=true;
            if(mode=="cancel_after_s3" && stage=="s3_tokenizer" && done==1)cancelled=true;
            if((mode=="cancel_during_s3" && stage=="reference_s3_run" || mode=="cancel_during_speaker" && stage=="reference_speaker_run") && !delayed.joinable())
                delayed=std::thread([&]{std::this_thread::sleep_for(std::chrono::milliseconds(2));cancelled=true;});
        };
        auto result=prepare_reference({models},pcm,request.value("threads",2),stats,[&]{return cancelled.load();},progress,trace);
        if(mode!="prepare")throw std::runtime_error("Requested reference cancellation was not observed");
        fs::create_directory(output_dir);
        write(output_dir/"tokens.i64",result.tokens);write(output_dir/"speaker.f32",result.speaker);write(output_dir/"prompt-mel.f32",result.prompt_mel.values);
        for(const auto& item:traced)write(output_dir/(item.first+".f32"),item.second);
        auto receipt=json({{"ok",true},{"graph_runs",stats.graph_runs},{"session_loads",stats.session_loads},{"session_unloads",stats.session_unloads},
            {"max_live_sessions",stats.max_live_sessions},{"terminated_runs",stats.terminated_runs},{"runtime_version",stats.runtime_version},
            {"tokens",result.tokens.size()},{"speaker_dimensions",result.speaker.size()},{"prompt_mel_shape",{80,result.prompt_mel.cols}},
            {"raw_tokens",result.raw_tokens},{"raw_flow_frames",result.raw_flow_frames},{"semantic_frames",result.semantic_frames},{"speaker_frames",result.speaker_frames},
            {"publisher_hashes_declared",manifest.value("publisher_hashes_match",false)},{"trace_shapes",shapes},{"full_soulx_pipeline",false},{"apk_runtime",false}});
        std::ofstream record(output_dir/"reference.json");record<<receipt.dump(2)<<'\n';if(!record)throw std::runtime_error("Cannot write reference receipt");
        std::cout<<receipt.dump()<<'\n';return 0;
    } catch(const std::exception& error) {
        std::cout<<json({{"ok",false},{"error",error.what()},{"graph_runs",stats.graph_runs},{"session_loads",stats.session_loads},{"session_unloads",stats.session_unloads},
            {"max_live_sessions",stats.max_live_sessions},{"terminated_runs",stats.terminated_runs}}).dump()<<'\n';return 1;
    }
}

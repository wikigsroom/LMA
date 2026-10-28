// SPDX-License-Identifier: MIT
// Developer CLI for the unregistered acoustic module; not an App HTTP endpoint.
#include "acoustic.hpp"
#include "json.hpp"
#include <atomic>
#include <chrono>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <thread>
using namespace lma::soulx;
using json=nlohmann::json;
namespace fs=std::filesystem;
std::string read(const fs::path& path,size_t maximum) {
    auto n=fs::file_size(path);if(n>maximum)throw std::runtime_error("Fixture exceeds bounds");
    std::string data(static_cast<size_t>(n),'\0');std::ifstream f(path,std::ios::binary);
    if(!f.read(data.data(),static_cast<std::streamsize>(n)))throw std::runtime_error("Cannot read acoustic input");return data;
}
template<typename T>std::vector<T> tensor(const fs::path& path) {
    auto data=read(path,128*1024*1024);if(data.size()%sizeof(T))throw std::runtime_error("Malformed tensor bytes");
    std::vector<T> result(data.size()/sizeof(T));std::memcpy(result.data(),data.data(),data.size());return result;
}
void write(const fs::path& path,const Samples& samples) {
    std::ofstream stream(path,std::ios::binary);stream.write(reinterpret_cast<const char*>(samples.data()),static_cast<std::streamsize>(samples.size()*4));
    if(!stream)throw std::runtime_error("Cannot write acoustic output");
}
int main(int argc,char** argv) {
    AcousticStats stats;std::atomic<bool> cancel{false};std::thread delayed_cancel;
    struct Join {std::thread& thread;~Join(){if(thread.joinable())thread.join();}} join{delayed_cancel};
    try {
        if(argc!=4)throw std::runtime_error("Usage: acoustic-cli MODEL_DIR INPUT_DIR OUTPUT.f32");
        fs::path directory=argv[2],out=argv[3];auto request=json::parse(read(directory/"input.json",64*1024));
        if(fs::exists(out))throw std::runtime_error("Output must be a new file; existing results are preserved");
        auto model=json::parse(read(fs::path(argv[1])/"soulx-acoustic.json",128*1024));
        if(model.at("format")!="lma.soulx-acoustic-onnx/1")throw std::runtime_error("Unknown acoustic model layout");
        if(request.at("format")!="lma.soulx-acoustic-input/1")throw std::runtime_error("Unknown acoustic input layout");
        AcousticInput input;input.tokens=tensor<int64_t>(directory/"tokens.i64");input.speaker=tensor<float>(directory/"speaker.f32");
        input.prompt_tokens=request.at("prompt_tokens").get<size_t>();input.prompt_mel={80,input.prompt_tokens*2,tensor<float>(directory/"prompt-mel.f32")};
        AcousticParams params;params.steps=request.value("steps",15);params.threads=request.value("threads",4);params.seed=request.value("seed",int64_t(0));params.cfg=request.value("cfg",.7f);
        std::string mode=request.value("mode",std::string("synthesize"));
        Noise noise;Samples injected;size_t consumed=0;
        if(request.value("inject_noise",false)) {
            injected=tensor<float>(directory/"flow-noise.f32");auto nsf=tensor<float>(directory/"nsf-noise.f32");injected.insert(injected.end(),nsf.begin(),nsf.end());
            noise=[&]{if(consumed==injected.size())throw std::runtime_error("Acoustic noise fixture exhausted");return injected[consumed++];};
        }
        Trace trace;
        if(request.value("trace",false)) {
            trace=[&](const std::string& name,const Samples& data,const std::vector<int64_t>& shape) {
                write(out.parent_path()/(out.stem().string()+"-"+name+".f32"),data);
                (void)shape;
            };
        }
        auto progress=[&](const std::string& stage,int done,int total) {
            (void)total;
            if((mode=="cancel_flow" && stage=="flow_estimator" && done==1) ||
               (mode=="cancel_before_run" && stage=="flow_encoder" && done==0))cancel=true;
            if(mode=="cancel_during_run" && stage=="flow_estimator_step" && done==0 && !delayed_cancel.joinable())
                delayed_cancel=std::thread([&]{std::this_thread::sleep_for(std::chrono::milliseconds(2));cancel=true;});
        };
        auto wave=synthesize_acoustic({fs::path(argv[1])},input,params,stats,[&]{return cancel.load();},progress,noise,trace);
        if(noise && consumed!=injected.size())throw std::runtime_error("Unused acoustic noise fixture");
        if(mode!="synthesize")throw std::runtime_error("Requested cancellation was not observed");
        write(out,wave);
        std::cout<<json({{"ok",true},{"samples",wave.size()},{"graph_runs",stats.graph_runs},{"session_loads",stats.session_loads},
            {"session_unloads",stats.session_unloads},{"max_live_sessions",stats.max_live_sessions},{"runtime_version",stats.runtime_version},
            {"terminated_runs",stats.terminated_runs},
            {"noise_consumed",consumed},{"synthetic_parameters_declared",model.value("synthetic_parameters",json(nullptr))},
            {"complete_soulx_pipeline",false},{"apk_runtime",false}}).dump()<<'\n';return 0;
    } catch(const std::exception& error) {
        std::cout<<json({{"ok",false},{"error",error.what()},{"graph_runs",stats.graph_runs},{"session_loads",stats.session_loads},
            {"session_unloads",stats.session_unloads},{"max_live_sessions",stats.max_live_sessions},{"terminated_runs",stats.terminated_runs}}).dump()<<'\n';return 1;
    }
}

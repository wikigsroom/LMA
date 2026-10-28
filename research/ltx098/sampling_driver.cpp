// SPDX-License-Identifier: Apache-2.0
// Explicit local developer CLI. No text encoder, VAE, video output or App binding.
#include "sampling.hpp"
#include "json.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <set>
#include <stdexcept>
#ifdef _WIN32
#include <codecvt>
#include <locale>
#endif
using json=nlohmann::json;
using namespace lma::ltx098;
static void require(bool value,const char* text) { if(!value) throw std::runtime_error(text); }
static int integer(const json& request,const char* key,int minimum,int maximum) {
    const auto& value=request.at(key);require(value.is_number_integer()&&value>=minimum&&value<=maximum,"Integer request field outside bounds");return value.get<int>();
}
static void keys(const json& request,const std::set<std::string>& accepted) {
    require(request.is_object(),"Expected request object");for(const auto& item:request.items()) require(accepted.count(item.key())!=0,"Unknown or unsupported sampling setting");
}
static Geometry shape(const json& request) { return geometry(integer(request,"width",32,2048),integer(request,"height",32,2048),integer(request,"frames",1,257),request.at("fps").get<float>()); }
static void save(const std::filesystem::path& path,const std::vector<float>& values) {
    require(!std::filesystem::exists(path),"Output already exists");std::ofstream stream(path,std::ios::binary);
    stream.write(reinterpret_cast<const char*>(values.data()),std::streamsize(values.size()*sizeof(float)));stream.close();require(bool(stream),"Unable to save complete latent output");
}
static int run(int argc,char** argv) {
    try {
        if(argc==2&&std::string(argv[1])=="--info") {
            std::cout<<json({{"sampler","ltx098_linear_quadratic_8_euler"},{"operations",{"geometry","rf_step","unpatchify","sample"}},{"engine_registered",false},{"complete_video_pipeline",false},{"model_data_embedded",false}})<<'\n';return 0;
        }
        require(argc==6||argc==7,"Usage: lma_ltx098_sample MODEL.gguf|- REQUEST.json OUTPUT.f32 cpu|vulkan THREADS [--fixture]");
        bool fixture=argc==7&&std::string(argv[6])=="--fixture";require(argc!=7||fixture,"Unknown fixture flag");
        auto request_path=std::filesystem::u8path(argv[2]);require(std::filesystem::file_size(request_path)<=32*1024*1024,"Research request exceeds 32 MiB");
        std::ifstream stream(request_path);auto request=json::parse(stream);std::string operation=request.at("operation").get<std::string>();
        auto output=std::filesystem::u8path(argv[3]);require(!std::filesystem::exists(output),"Output already exists");
        size_t consumed=0;int threads=std::stoi(argv[5],&consumed);require(consumed==std::string(argv[5]).size()&&threads>=1&&threads<=32,"Thread count outside integer bounds");
        std::string backend=argv[4];require(backend=="cpu"||backend=="vulkan","Unsupported backend");
        json record={{"ok",true},{"operation",operation},{"model_executed",false},{"fixture",fixture},{"complete_video_pipeline",false},{"physical_android",false},{"engine_registered",false}};
        std::vector<float> values;
        if(operation=="geometry") {
            keys(request,{"operation","width","height","frames","fps"});auto layout=shape(request);values=layout.coordinates;
            record["tokens"]=layout.tokens;record["latent_shape"]={1,128,layout.latent_frames,layout.latent_height,layout.latent_width};record["sigmas"]=distilled_sigmas();
        } else if(operation=="rf_step") {
            keys(request,{"operation","sample","velocity","times","channels","per_token"});
            require(request.at("per_token").is_boolean(),"per_token must be boolean");
            values=rf_step(request.at("sample").get<std::vector<float>>(),request.at("velocity").get<std::vector<float>>(),request.at("times").get<std::vector<float>>(),integer(request,"channels",1,128),request.at("per_token").get<bool>());
        } else if(operation=="unpatchify") {
            keys(request,{"operation","width","height","frames","fps","channels","latents"});auto layout=shape(request);
            values=channels_first(request.at("latents").get<std::vector<float>>(),integer(request,"channels",1,128),layout);record["layout"]="batch_channels_frames_height_width";
        } else if(operation=="sample") {
            keys(request,{"operation","width","height","frames","fps","text_tokens","latents","context","text_mask","cancel_file","trace_dir"});
            auto layout=shape(request);Input input;input.tokens=layout.tokens;input.text_tokens=integer(request,"text_tokens",1,256);input.coordinates=layout.coordinates;
            input.latents=request.at("latents").get<std::vector<float>>();input.context=request.at("context").get<std::vector<float>>();input.text_mask=request.at("text_mask").get<std::vector<float>>();
            int channels=fixture?8:128,caption=fixture?32:4096;
            require(input.latents.size()==size_t(input.tokens)*size_t(channels)&&input.context.size()==size_t(input.text_tokens)*size_t(caption)&&input.text_mask.size()==size_t(input.text_tokens),"Sampling input does not match selected model dimensions");
            auto cancel=std::filesystem::u8path(request.value("cancel_file",std::string()));
            auto cancelled=[&](){return !cancel.empty()&&std::filesystem::exists(cancel);};require(!cancelled(),"Sampling cancelled before model load");
            auto trace=std::filesystem::u8path(request.value("trace_dir",std::string()));
            if(!trace.empty()) require(std::filesystem::create_directory(trace),"Trace directory must not already exist");
            Transformer model(argv[1],backend,threads,fixture);
            auto result=sample(model,std::move(input),cancelled,
                [](int step,float sigma){std::cerr<<json({{"event","step_start"},{"step",step},{"sigma",sigma}})<<std::endl;},
                [&](int step,float sigma,const std::vector<float>& latents){
                    if(!trace.empty()) save(trace/("step-"+std::to_string(step)+".f32"),latents);
                    std::cerr<<json({{"event","step_end"},{"step",step},{"sigma",sigma}})<<std::endl;
                });
            values=std::move(result.latents);record["model_executed"]=true;record["backend"]=result.backend;record["steps"]=result.steps;record["layers"]=result.layers;
            record["parameters"]=result.parameters;record["weight_bytes"]=result.weight_bytes;record["compute_bytes"]=result.compute_bytes;record["layout"]="batch_tokens_channels";
            record["precision_policy"]=backend=="vulkan"?"baseline_f32_compute_optional_f16_weight_storage":"native_cpu";
        } else throw std::runtime_error("Unsupported sampling operation");
        save(output,values);record["values"]=values.size();std::cout<<record<<'\n';return 0;
    } catch(const std::exception& error) { std::cout<<json({{"ok",false},{"error",error.what()},{"complete_video_pipeline",false},{"engine_registered",false}})<<'\n';return 2; }
}
#ifdef _WIN32
int wmain(int argc,wchar_t** argv) {
    std::wstring_convert<std::codecvt_utf8_utf16<wchar_t>> convert;std::vector<std::string> strings;std::vector<char*> pointers;
    for(int i=0;i<argc;++i) strings.push_back(convert.to_bytes(argv[i]));for(auto& value:strings) pointers.push_back(value.data());return run(argc,pointers.data());
}
#else
int main(int argc,char** argv) { return run(argc,argv); }
#endif

// SPDX-License-Identifier: MIT
// Research CLI only: external developer graphs, nine sequential CPU sessions.
#ifdef _WIN32
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#else
#include <fcntl.h>
#include <unistd.h>
#endif
#include "../soulx_ort/runtime.hpp"
#include "json.hpp"
#include <cstdio>
#include <iostream>
#include <set>
using Json = nlohmann::json;
namespace fs = std::filesystem;
using lma::soulx::Samples;
using lma::soulx::Cancel;
using lma::soulx::OrtStats;
using namespace lma::soulx::ort;
namespace {
void keys(const Json& value, const std::set<std::string>& allowed) {
    require(value.is_object(), "Expected JSON object");
    for (auto it=value.begin();it!=value.end();++it) require(allowed.count(it.key())!=0,"Unknown request key");
}
Json read_json(const fs::path& path, size_t maximum) {
    require(fs::is_regular_file(path) && fs::file_size(path)<=maximum,"Missing/oversized JSON");
    std::vector<std::set<std::string>> seen;
    auto callback=[&](int,Json::parse_event_t event,Json& value) {
        if(event==Json::parse_event_t::object_start) seen.emplace_back();
        else if(event==Json::parse_event_t::key) require(!seen.empty() && seen.back().insert(value.get<std::string>()).second,"Duplicate JSON key");
        else if(event==Json::parse_event_t::object_end) seen.pop_back();
        return true;
    };
    std::ifstream stream(path,std::ios::binary);return Json::parse(stream,callback);
}
int integer(const Json& value,int low,int high) {
    require(value.is_number_integer(),"Expected integer");auto n=value.get<int64_t>();
    require(n>=low && n<=high,"Integer outside research limits");return static_cast<int>(n);
}
float number(const Json& value,float low,float high) {
    require(value.is_number(),"Expected finite number");auto n=value.get<double>();
    require(std::isfinite(n) && n>=low && n<=high,"Number outside research limits");return static_cast<float>(n);
}
std::string filename(int i) { char buffer[32];std::snprintf(buffer,sizeof(buffer),"stage-%02d.onnx",i);return buffer; }
void validate_bundle(const fs::path& directory) {
    require(fs::is_directory(directory),"Missing developer VAE bundle");
    auto manifest=read_json(directory/"ltx098-vae.json",1024*1024);
    require(manifest.at("schema")=="lma.ltx098-vae/1" && manifest.at("precision")=="float32" &&
            manifest.at("decoder_tensors")==132 && manifest.at("decoder_parameters")==552814641,
            "Unsupported decoder profile");
    require(manifest.at("source").at("sha256")=="76aa8c4786af752fa6f951947129d5290c3c6c0b2fadcadea6b5e114ae2cad8f",
            "Different old-LTX checkpoint");
    require(manifest.at("stages").is_array() && manifest.at("stages").size()==9 &&
            manifest.at("assets").is_array() && manifest.at("assets").size()==18,"Incomplete decoder bundle");
    std::set<std::string> expected;
    for(int i=0;i<9;++i) {
        auto name=filename(i);expected.insert(name);expected.insert(name+".data");
        require(manifest["stages"][i].at("index")==i && manifest["stages"][i].at("file")==name,"Wrong decoder stage order");
    }
    for(const auto& asset:manifest["assets"]) {
        auto name=asset.at("file").get<std::string>();require(expected.erase(name)==1,"Unexpected/duplicate bundle asset");
        auto path=directory/name;
        require(fs::is_regular_file(path) && !fs::is_symlink(path) && fs::canonical(path).parent_path()==fs::canonical(directory),"Unsafe/missing decoder asset");
        require(asset.at("bytes").is_number_unsigned() && asset["bytes"].get<uint64_t>()==fs::file_size(path) &&
                fs::file_size(path)>0 && fs::file_size(path)<=1500000000ULL,"Decoder asset size mismatch");
    }
    require(expected.empty(),"Missing decoder asset");
    // Digests are checked by the offline test/asset manager before this research
    // CLI. This size/schema/path check is deliberately NOT a digest claim.
}
Samples read_floats(const Json& name,size_t count) {
    require(name.is_string(),"Expected local tensor path");auto path=fs::u8path(name.get<std::string>());
    require(fs::is_regular_file(path) && fs::file_size(path)==count*sizeof(float),"Truncated/oversized latent or noise tensor");
    Samples values(count);std::ifstream stream(path,std::ios::binary);
    require(static_cast<bool>(stream.read(reinterpret_cast<char*>(values.data()),static_cast<std::streamsize>(count*sizeof(float)))),"Cannot read tensor");
    finite(values);return values;
}
void write_exclusive(const fs::path& path,const Samples& values,Cancel cancel) {
    stop(cancel);const auto size=values.size()*sizeof(float);
#ifdef _WIN32
    auto handle=CreateFileW(path.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
    require(handle!=INVALID_HANDLE_VALUE,"Output already exists or cannot be created");
    DWORD done=0;bool ok=WriteFile(handle,values.data(),static_cast<DWORD>(size),&done,nullptr)!=0 && done==size;
    ok=FlushFileBuffers(handle)!=0 && ok;CloseHandle(handle);
#else
    int handle=::open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL,0600);require(handle>=0,"Output already exists or cannot be created");
    size_t done=0;bool ok=true;const auto* data=reinterpret_cast<const char*>(values.data());
    while(done<size) {auto n=::write(handle,data+done,size-done);if(n<=0){ok=false;break;}done+=static_cast<size_t>(n);}
    ok=::fsync(handle)==0 && ok;::close(handle);
#endif
    if(!ok || (cancel && cancel())) {fs::remove(path);throw std::runtime_error("VAE output write failed/cancelled");}
}
int run(const std::vector<std::string>& args) {
    OrtStats stats;std::vector<fs::path> created;fs::path trace_directory;bool made_trace=false;
    try {
        require(args.size()==4,"Usage: lma_ltx098_vae BUNDLE REQUEST.json OUTPUT.f32");
        auto request=read_json(fs::u8path(args[2]),32768);
        keys(request,{"operation","latent_shape","latents","noise","timestep","noise_scale","threads","cancel_file","trace_dir"});
        require(request.at("operation")=="decode","Unsupported VAE operation");
        auto dims=request.at("latent_shape");require(dims.is_array() && dims.size()==5,"Expected NCTHW latent shape");
        integer(dims[0],1,1);integer(dims[1],128,128);
        std::vector<int64_t> shape={1,128,integer(dims[2],1,5),integer(dims[3],1,8),integer(dims[4],1,8)};
        int threads=integer(request.value("threads",Json(4)),1,32);
        Samples timestep={number(request.value("timestep",Json(.05)),0,1)};
        Samples noise_scale={number(request.value("noise_scale",Json(.025)),0,1)};
        fs::path cancel_file;
        if(request.contains("cancel_file")) {require(request["cancel_file"].is_string(),"Invalid cancel path");cancel_file=fs::u8path(request["cancel_file"].get<std::string>());require(!cancel_file.empty(),"Empty cancel path");}
        Cancel cancel=[&]{return !cancel_file.empty() && fs::exists(cancel_file);};stop(cancel);
        auto target=fs::u8path(args[3]);require(!fs::exists(target),"Output already exists");
        if(request.contains("trace_dir")) {
            require(request["trace_dir"].is_string(),"Invalid trace directory");trace_directory=fs::u8path(request["trace_dir"].get<std::string>());
            require(!trace_directory.empty() && !fs::exists(trace_directory),"Trace directory already exists");
        }
        size_t count=1;for(auto n:shape)count*=static_cast<size_t>(n);
        auto value=read_floats(request.at("latents"),count),noise=read_floats(request.at("noise"),count);
        auto directory=fs::u8path(args[1]);validate_bundle(directory);
        initialize();Ort::Env env(ORT_LOGGING_LEVEL_FATAL,"LMA-LTX098-VAE");stats.runtime_version=OrtGetApiBase()->GetVersionString();
        std::vector<Samples> traces;
        for(int i=0;i<9;++i) {
            stop(cancel);std::cerr<<Json{{"stage","vae_load"},{"index",i}}.dump()<<std::endl;
            auto name=filename(i);auto expected=shape;
            if(i==0)expected[1]=1024;
            else if(i==2 || i==4 || i==6){expected[1]/=2;expected[2]=2*expected[2]-1;expected[3]*=2;expected[4]*=2;}
            else if(i==8){expected[1]=3;expected[3]*=4;expected[4]*=4;}
            {
                std::vector<Field> input_fields={{i==0?"latent":"sample",f32,{1,shape[1],-1,-1,-1}}};
                if(i==0){input_fields.push_back({"noise",f32,{1,128,-1,-1,-1}});input_fields.push_back({"noise_scale",f32,{1}});}
                else if(i==1 || i==3 || i==5 || i==7 || i==8)input_fields.push_back({"timestep",f32,{1}});
                Graph graph(env,directory,name.c_str(),threads,stats,input_fields,{{"output",f32,{1,expected[1],-1,-1,-1}}});
                std::vector<Ort::Value> feeds;feeds.push_back(floats(value,shape));
                if(i==0){feeds.push_back(floats(noise,shape));feeds.push_back(floats(noise_scale,{1}));}
                else if(input_fields.size()==2)feeds.push_back(floats(timestep,{1}));
                std::cerr<<Json{{"stage","vae_compute"},{"index",i}}.dump()<<std::endl;
                auto result=graph.run(feeds,cancel);value=output(result[0],expected);
            }
            shape=expected;if(!trace_directory.empty())traces.push_back(value);
            std::cerr<<Json{{"stage","vae_unloaded"},{"index",i}}.dump()<<std::endl;
        }
        stop(cancel);
        if(!trace_directory.empty()) {
            require(fs::create_directory(trace_directory),"Cannot create trace directory");made_trace=true;
            for(int i=0;i<9;++i){auto p=trace_directory/(filename(i)+".f32");write_exclusive(p,traces[i],cancel);created.push_back(p);}
        }
        write_exclusive(target,value,cancel);created.push_back(target);
        std::cout<<Json{{"ok",true},{"output_shape",shape},{"output_bytes",value.size()*sizeof(float)},
            {"graph_runs",stats.graph_runs},{"session_loads",stats.session_loads},{"session_unloads",stats.session_unloads},
            {"max_live_sessions",stats.max_live_sessions},{"runtime_version",stats.runtime_version},
            {"backend","cpu"},{"engine_registered",false},{"physical_android",false},{"complete_video_pipeline",false}}.dump()<<std::endl;
        return 0;
    } catch(const std::exception& error) {
        for(const auto& p:created){std::error_code ignored;fs::remove(p,ignored);}
        if(made_trace){std::error_code ignored;fs::remove(trace_directory,ignored);}
        std::cout<<Json{{"ok",false},{"error",error.what()},{"graph_runs",stats.graph_runs},
            {"session_loads",stats.session_loads},{"session_unloads",stats.session_unloads},
            {"max_live_sessions",stats.max_live_sessions},{"terminated_runs",stats.terminated_runs}}.dump()<<std::endl;
        return 1;
    }
}
}
#ifdef _WIN32
int wmain(int argc,wchar_t** argv) {
    std::vector<std::string> args;
    for(int i=0;i<argc;++i){int size=WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,argv[i],-1,nullptr,0,nullptr,nullptr);
        if(size<=0)return 2;std::string text(static_cast<size_t>(size),'\0');
        WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,argv[i],-1,text.data(),size,nullptr,nullptr);text.pop_back();args.push_back(text);}
    return run(args);
}
#else
int main(int argc,char** argv) {return run(std::vector<std::string>(argv,argv+argc));}
#endif

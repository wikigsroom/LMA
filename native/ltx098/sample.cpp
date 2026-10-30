// SPDX-License-Identifier: Apache-2.0
// File bridges keep large F32 tensors out of Java and JSON. Numerical core is unchanged.
#include "sampling.hpp"
#include "json.hpp"
#include <filesystem>
#include <cmath>
#include <fstream>
#include <iostream>
#include <set>
#include <stdexcept>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#else
#include <fcntl.h>
#include <unistd.h>
#endif
using Json=nlohmann::json;
namespace fs=std::filesystem;
namespace {
void demand(bool value,const char* message) {if(!value)throw std::runtime_error(message);}
int integer(const Json& value,int low,int high) {demand(value.is_number_integer() && value>=low && value<=high,"Integer outside old-LTX bounds");return value.get<int>();}
std::vector<float> tensor(const Json& value,size_t count) {
    demand(value.is_string(),"Expected private tensor path");auto path=fs::u8path(value.get<std::string>());
    demand(!fs::is_symlink(path) && fs::is_regular_file(path) && fs::file_size(path)==count*4,"Wrong tensor extent");
    std::vector<float> values(count);std::ifstream stream(path,std::ios::binary);
    demand(bool(stream.read(reinterpret_cast<char*>(values.data()),std::streamsize(count*4))),"Cannot read complete tensor");
    for(float item:values)demand(std::isfinite(item),"Non-finite bridge tensor");return values;
}
void save(const fs::path& path,const std::vector<float>& values) {
    const size_t bytes=values.size()*4;
#ifdef _WIN32
    auto handle=CreateFileW(path.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
    demand(handle!=INVALID_HANDLE_VALUE,"Output already exists");DWORD written=0;
    bool ok=WriteFile(handle,values.data(),static_cast<DWORD>(bytes),&written,nullptr)!=0 && written==bytes;
    ok=FlushFileBuffers(handle)!=0 && ok;CloseHandle(handle);
#else
    int handle=::open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);demand(handle>=0,"Output already exists");
    bool ok=true;size_t written=0;auto data=reinterpret_cast<const char*>(values.data());
    while(written<bytes){auto n=::write(handle,data+written,bytes-written);if(n<=0){ok=false;break;}written+=static_cast<size_t>(n);}
    ok=::fsync(handle)==0 && ok;::close(handle);
#endif
    if(!ok){fs::remove(path);throw std::runtime_error("Incomplete sampler output");}
}
int run(const std::vector<std::string>& args) {
    try {
        demand(args.size()==6,"Expected model, request, output, backend and threads");
        auto path=fs::u8path(args[2]);demand(fs::is_regular_file(path) && fs::file_size(path)<=32768,"Missing/oversized sampling request");
        std::vector<std::set<std::string>> objects;
        auto callback=[&](int,Json::parse_event_t event,Json& value){
            if(event==Json::parse_event_t::object_start)objects.emplace_back();
            else if(event==Json::parse_event_t::key)demand(!objects.empty() && objects.back().insert(value.get<std::string>()).second,"Duplicate request key");
            else if(event==Json::parse_event_t::object_end)objects.pop_back();return true;
        };
        std::ifstream in(path,std::ios::binary);auto request=Json::parse(in,callback);
        const std::set<std::string> allowed={"operation","width","height","frames","fps","latents","context","text_tokens"};
        demand(request.is_object() && request.size()==allowed.size(),"Incomplete sampling request");for(const auto& item:request.items())demand(allowed.count(item.key())!=0,"Unsupported sampling setting");
        auto operation=request.at("operation").get<std::string>();bool first=operation=="sample_multiscale_first",second=operation=="sample_multiscale_second";
        demand(operation=="sample_files" || first || second,"Unsupported operation");
        int maximum=first?160:second?320:256,minimum=second?128:64;
        int width=integer(request.at("width"),minimum,maximum),height=integer(request.at("height"),minimum,maximum),frames=integer(request.at("frames"),9,33),fps=integer(request.at("fps"),1,60);
        demand(width%32==0 && height%32==0 && (frames-1)%8==0,"Unsupported latent grid");
        int text_tokens=integer(request.at("text_tokens"),1,256);size_t consumed=0;int threads=std::stoi(args[5],&consumed);
        demand(consumed==args[5].size() && threads>=1 && threads<=8 && args[4]=="vulkan","Unsupported sampler backend or thread count");
        auto output=fs::u8path(args[3]);demand(!fs::exists(output),"Output already exists");
        using namespace lma::ltx098;
        auto layout=geometry(width,height,frames,float(fps));Input input;input.tokens=layout.tokens;input.text_tokens=text_tokens;input.coordinates=layout.coordinates;
        input.latents=tensor(request.at("latents"),static_cast<size_t>(layout.tokens)*128);
        input.context=tensor(request.at("context"),static_cast<size_t>(text_tokens)*4096);input.text_mask.assign(text_tokens,1);
        Transformer model(args[1],"vulkan",threads,false);
        auto result=sample(model,std::move(input),{},
            [](int step,float sigma){std::cerr<<Json{{"event","step_start"},{"step",step},{"sigma",sigma}}.dump()<<std::endl;},
            [](int step,float sigma,const std::vector<float>&){std::cerr<<Json{{"event","step_end"},{"step",step},{"sigma",sigma}}.dump()<<std::endl;},
            first||second?multiscale_sigmas(second):std::vector<float>{});
        demand(result.layers==28 && result.steps==(first?7:second?3:8) && result.parameters==1923385472ULL && result.backend=="vulkan","Incomplete old-LTX trajectory");
        for(float value:result.latents)demand(std::isfinite(value),"Non-finite sampled tensor");save(output,result.latents);
        std::cout<<Json{{"ok",true},{"operation",operation},{"model_executed",true},{"fixture",false},{"backend",result.backend},{"layers",result.layers},{"steps",result.steps},{"parameters",result.parameters},{"layout","batch_tokens_channels"},{"bytes",result.latents.size()*4},{"weight_bytes",result.weight_bytes},{"compute_bytes",result.compute_bytes}}.dump()<<std::endl;
        return 0;
    }catch(const std::exception& error){std::cout<<Json{{"ok",false},{"error",error.what()}}.dump(-1,' ',false,Json::error_handler_t::replace)<<std::endl;return 1;}
}
}
#ifdef _WIN32
int wmain(int argc,wchar_t** argv) {
    std::vector<std::string> args;
    for(int i=0;i<argc;++i){int n=WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,argv[i],-1,nullptr,0,nullptr,nullptr);if(n<=0)return 2;
        std::string text(static_cast<size_t>(n),'\0');WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,argv[i],-1,text.data(),n,nullptr,nullptr);text.pop_back();args.push_back(text);}
    return run(args);
}
#else
int main(int argc,char** argv){return run(std::vector<std::string>(argv,argv+argc));}
#endif

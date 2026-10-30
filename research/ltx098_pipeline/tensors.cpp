// SPDX-License-Identifier: MIT
// Portable tensor/RNG/frame primitives; no model loading or inference.
#ifdef _WIN32
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#else
#include <fcntl.h>
#include <unistd.h>
#endif
#include "json.hpp"
#include <cmath>
#include "../../native/ltx098/multiscale.hpp"
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <set>
#include <stdexcept>
#include <vector>
using Json=nlohmann::json;
namespace fs=std::filesystem;
namespace {
void require(bool value,const char* message) {if(!value)throw std::invalid_argument(message);}
void keys(const Json& value,const std::set<std::string>& allowed) {
    require(value.is_object(),"Expected JSON object");
    for(auto it=value.begin();it!=value.end();++it)require(allowed.count(it.key())!=0,"Unknown tensor request key");
}
Json parse(const fs::path& path) {
    require(fs::is_regular_file(path) && fs::file_size(path)<=32768,"Missing/oversized tensor request");
    std::vector<std::set<std::string>> seen;
    auto cb=[&](int,Json::parse_event_t event,Json& value) {
        if(event==Json::parse_event_t::object_start)seen.emplace_back();
        else if(event==Json::parse_event_t::key)require(!seen.empty() && seen.back().insert(value.get<std::string>()).second,"Duplicate JSON key");
        else if(event==Json::parse_event_t::object_end)seen.pop_back();
        return true;
    };
    std::ifstream stream(path,std::ios::binary);return Json::parse(stream,cb);
}
int integer(const Json& value,int low,int high) {
    require(value.is_number_integer(),"Expected integer");auto n=value.get<int64_t>();
    require(n>=low && n<=high,"Integer outside tensor bounds");return static_cast<int>(n);
}
fs::path path(const Json& value) {
    require(value.is_string() && !value.get_ref<const std::string&>().empty(),"Expected local path");
    return fs::u8path(value.get<std::string>());
}
struct Shape {
    int width,height,frames,fps;size_t tokens,count;
    explicit Shape(const Json& request) {
        width=integer(request.at("width"),64,320);height=integer(request.at("height"),64,320);
        frames=integer(request.at("frames"),1,33);fps=integer(request.at("fps"),1,60);
        require(width%32==0 && height%32==0 && (frames-1)%8==0,"Invalid old-LTX latent grid");
        tokens=static_cast<size_t>((frames-1)/8+1)*static_cast<size_t>(height/32)*static_cast<size_t>(width/32);
        count=tokens*128;
    }
    std::vector<int64_t> ncthw() const {return {1,128,(frames-1)/8+1,height/32,width/32};}
};
struct Cancel {
    fs::path file;
    explicit Cancel(const Json& request) {if(request.contains("cancel_file"))file=path(request.at("cancel_file"));}
    bool requested() const {return !file.empty() && fs::exists(file);}
    void check() const {require(!requested(),"Tensor operation cancelled");}
};
void save(const fs::path& target,const void* memory,size_t bytes,const Cancel& cancel) {
    cancel.check();require(bytes<=32*1024*1024,"Tensor output exceeds budget");
#ifdef _WIN32
    auto handle=CreateFileW(target.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
    require(handle!=INVALID_HANDLE_VALUE,"Output already exists or cannot be created");
    DWORD done=0;bool ok=WriteFile(handle,memory,static_cast<DWORD>(bytes),&done,nullptr)!=0 && done==bytes;
    ok=FlushFileBuffers(handle)!=0 && ok;CloseHandle(handle);
#else
    int handle=::open(target.c_str(),O_WRONLY|O_CREAT|O_EXCL,0600);require(handle>=0,"Output already exists or cannot be created");
    bool ok=true;size_t done=0;auto data=static_cast<const char*>(memory);
    while(done<bytes){auto n=::write(handle,data+done,bytes-done);if(n<=0){ok=false;break;}done+=static_cast<size_t>(n);}
    ok=::fsync(handle)==0 && ok;::close(handle);
#endif
    if(!ok || cancel.requested()){fs::remove(target);throw std::runtime_error("Tensor output write failed/cancelled");}
}
std::vector<float> read(const fs::path& source,size_t count,const Cancel& cancel) {
    cancel.check();require(count<=12*1024*1024 && fs::is_regular_file(source) && fs::file_size(source)==count*sizeof(float),"Wrong tensor byte count");
    std::vector<float> result(count);std::ifstream stream(source,std::ios::binary);
    require(static_cast<bool>(stream.read(reinterpret_cast<char*>(result.data()),static_cast<std::streamsize>(count*sizeof(float)))),"Tensor read failed");
    for(size_t i=0;i<count;++i){if(i%4096==0)cancel.check();require(std::isfinite(result[i]),"Non-finite tensor");}
    return result;
}
struct Normal {
    uint64_t state;
    explicit Normal(uint64_t seed):state(seed){}
    uint64_t next() {
        auto z=(state+=UINT64_C(0x9e3779b97f4a7c15));
        z=(z^(z>>30))*UINT64_C(0xbf58476d1ce4e5b9);z=(z^(z>>27))*UINT64_C(0x94d049bb133111eb);
        return z^(z>>31);
    }
    double uniform() {return (static_cast<double>(next()>>32)+.5)*(1.0/4294967296.0);}
    std::vector<float> draw(size_t count,const Cancel& cancel) {
        require(count%2==0,"Gaussian pair count must be even");std::vector<float> result(count);
        for(size_t i=0;i<count;i+=2) {
            if(i%4096==0)cancel.check();double radius=std::sqrt(-2.0*std::log(uniform()));
            double angle=6.283185307179586476925286766559*uniform();
            result[i]=static_cast<float>(radius*std::cos(angle));result[i+1]=static_cast<float>(radius*std::sin(angle));
        }
        return result;
    }
};
void u32(std::vector<unsigned char>& result,uint32_t value) {for(int i=0;i<4;++i)result.push_back(static_cast<unsigned char>(value>>(8*i)));}
int run(const std::vector<std::string>& args) {
    std::vector<fs::path> created;
    try {
        require(args.size()==2,"Usage: lma_ltx098_tensors REQUEST.json");
        uint32_t endian=1;require(*reinterpret_cast<unsigned char*>(&endian)==1,"Little-endian F32 is required");
        auto request=parse(fs::u8path(args[1]));require(request.is_object(),"Expected tensor request");
        auto operation=request.at("operation").get<std::string>();Shape shape(request);Cancel cancel(request);cancel.check();
        Json record={{"ok",true},{"operation",operation},{"model_inference",false},{"physical_android",false},{"engine_registered",false}};
        if(operation=="noise") {
            keys(request,{"operation","width","height","frames","fps","seed","latents","noise","cancel_file"});
            int seed=integer(request.at("seed"),0,2147483647);auto initial=path(request.at("latents")),noise=path(request.at("noise"));
            require(initial!=noise && !fs::exists(initial) && !fs::exists(noise),"Noise outputs must be new distinct files");
            Normal rng(static_cast<uint64_t>(seed));auto values=rng.draw(shape.count,cancel);
            save(initial,values.data(),values.size()*sizeof(float),cancel);created.push_back(initial);
            values=rng.draw(shape.count,cancel);save(noise,values.data(),values.size()*sizeof(float),cancel);created.push_back(noise);
            record["rng"]="lma_splitmix64_box_muller_f32_v1";record["seed"]=seed;
            record["initial_shape"]={1,shape.tokens,128};record["decode_noise_shape"]=shape.ncthw();record["values_each"]=shape.count;
            record["matches_pytorch_seed"]=false;
        } else if(operation=="refine_noise") {
            keys(request,{"operation","width","height","frames","fps","seed","input","latents","noise","cancel_file"});
            auto initial=path(request.at("latents")),noise=path(request.at("noise"));
            require(initial!=noise && !fs::exists(initial) && !fs::exists(noise),"Refinement outputs must be new distinct files");
            int seed=integer(request.at("seed"),0,2147483647);auto high=read(path(request.at("input")),shape.count,cancel);
            Normal rng(uint64_t(seed)^UINT64_C(0x4c54584d554c5449));auto values=rng.draw(shape.count,cancel);
            for(size_t p=0;p<shape.tokens;++p){cancel.check();for(size_t c=0;c<128;++c){auto i=p*128+c;values[i]=.9094f*values[i]+(1.f-.9094f)*high[c*shape.tokens+p];}}
            save(initial,values.data(),values.size()*4,cancel);created.push_back(initial);values=rng.draw(shape.count,cancel);
            save(noise,values.data(),values.size()*4,cancel);created.push_back(noise);
            record["timestep"]=.9094;record["matches_pytorch_seed"]=false;record["values_each"]=shape.count;
        } else if(operation=="unpatchify") {
            keys(request,{"operation","width","height","frames","fps","input","output","cancel_file"});
            auto target=path(request.at("output"));require(!fs::exists(target),"Output already exists");
            auto values=read(path(request.at("input")),shape.count,cancel);std::vector<float> restored(shape.count);
            for(size_t p=0;p<shape.tokens;++p){cancel.check();for(size_t c=0;c<128;++c)restored[c*shape.tokens+p]=values[p*128+c];}
            save(target,restored.data(),restored.size()*sizeof(float),cancel);created.push_back(target);record["shape"]=shape.ncthw();
        } else if(operation=="frames") {
            keys(request,{"operation","width","height","frames","fps","input","output","cancel_file","input_width","input_height"});
            auto target=path(request.at("output"));require(!fs::exists(target),"Output already exists");
            size_t pixels=static_cast<size_t>(shape.width)*shape.height,plane=pixels*shape.frames;
            int iw=request.contains("input_width")?integer(request.at("input_width"),64,320):shape.width,ih=request.contains("input_height")?integer(request.at("input_height"),64,320):shape.height;
            auto values=read(path(request.at("input")),size_t(iw)*ih*shape.frames*3,cancel);
            if(iw!=shape.width || ih!=shape.height) {
                // Publisher VaeImageProcessor clamps/denormalizes before the
                // outer multiscale pipeline resizes its decoded video.
                for(auto& value:values)value=std::max(-1.f,std::min(1.f,value));
                values=lma::ltx098::multiscale::resize_bilinear(values,shape.frames,ih,iw,shape.height,shape.width);
            }
            std::vector<unsigned char> rgb={'L','M','A','F','R','M','1',0};
            u32(rgb,shape.width);u32(rgb,shape.height);u32(rgb,shape.frames);u32(rgb,shape.fps);u32(rgb,3);rgb.reserve(28+plane*3);
            size_t clipped_low=0,clipped_high=0;float minimum=values[0],maximum=values[0];
            for(int frame=0;frame<shape.frames;++frame) {
                cancel.check();
                for(size_t pixel=0;pixel<pixels;++pixel)for(size_t channel=0;channel<3;++channel) {
                    float original=values[channel*plane+static_cast<size_t>(frame)*pixels+pixel];
                    minimum=std::min(minimum,original);maximum=std::max(maximum,original);
                    if(original<-1)++clipped_low;if(original>1)++clipped_high;
                    float normalized=std::max(0.0f,std::min(1.0f,original*.5f+.5f));
                    rgb.push_back(static_cast<unsigned char>(normalized*255.0f));
                }
            }
            save(target,rgb.data(),rgb.size(),cancel);created.push_back(target);
            record["bytes"]=rgb.size();record["shape"]={shape.frames,shape.height,shape.width,3};
            record["format"]="LMAFRM1_rgb24";record["rounding"]="float32_scale_then_truncate";
            record["minimum"]=minimum;record["maximum"]=maximum;record["clipped_low"]=clipped_low;record["clipped_high"]=clipped_high;
        } else throw std::invalid_argument("Unsupported tensor operation");
        std::cout<<record.dump()<<std::endl;return 0;
    } catch(const std::exception& error) {
        for(const auto& p:created){std::error_code ignored;fs::remove(p,ignored);}
        std::cout<<Json{{"ok",false},{"error",error.what()}}.dump()<<std::endl;return 1;
    }
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
int main(int argc,char** argv) {return run(std::vector<std::string>(argv,argv+argc));}
#endif

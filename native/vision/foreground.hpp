#pragma once
#include "../rf_shape/ort.hpp"
#define STB_IMAGE_STATIC
#define STB_IMAGE_WRITE_STATIC
#include "../rf_shape/image.hpp"
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"
#include <set>

namespace lma_vision {
using namespace lma_shape;
struct Image {int width=0,height=0;std::vector<uint8_t> rgba;};
inline Image load(const fs::path& file){
 int w=0,h=0,c=0;require(fs::file_size(file)<=16*1024*1024&&stbi_info(file.string().c_str(),&w,&h,&c)&&w>0&&h>0&&uint64_t(w)*h<=4194304&&(c==3||c==4),"Use a bounded RGB/RGBA PNG");
 std::unique_ptr<stbi_uc,decltype(&stbi_image_free)> data(stbi_load(file.string().c_str(),&w,&h,&c,4),stbi_image_free);require(bool(data),"Cannot decode image");return {w,h,std::vector<uint8_t>(data.get(),data.get()+size_t(w)*h*4)};
}
inline float bilinear(const std::vector<float>& values,int iw,int ih,int ow,int oh,int x,int y){
 float px=std::max(0.f,(x+.5f)*float(iw)/ow-.5f),py=std::max(0.f,(y+.5f)*float(ih)/oh-.5f);int x0=std::min(int(px),iw-1),x1=std::min(x0+1,iw-1),y0=std::min(int(py),ih-1),y1=std::min(y0+1,ih-1);float ax=px-x0,ay=py-y0;
 float a=values[size_t(y0)*iw+x0]*(1-ax)+values[size_t(y0)*iw+x1]*ax,b=values[size_t(y1)*iw+x0]*(1-ax)+values[size_t(y1)*iw+x1]*ax;return a*(1-ay)+b*ay;
}
inline Floats foreground_pixels(const Image& image,int side){
 Floats result(size_t(side)*side*3),channel(size_t(image.width)*image.height);
 for(int c=0;c<3;c++){for(size_t i=0;i<channel.size();i++)channel[i]=image.rgba[i*4+c];for(int y=0;y<side;y++)for(int x=0;x<side;x++){float resized=bilinear(channel,image.width,image.height,side,side,x,y);auto pixel=uint8_t(std::clamp(resized,0.f,255.f));result[(size_t(c)*side+y)*side+x]=float(pixel)/255.f-.5f;}}
 return result;
}
inline Image foreground_alpha(Image image,const Floats& mask,int side){
 require(mask.size()==size_t(side)*side,"Foreground mask shape mismatch");Floats alpha(size_t(image.width)*image.height);float lo=std::numeric_limits<float>::infinity(),hi=-lo;
 for(int y=0;y<image.height;y++)for(int x=0;x<image.width;x++){float value=bilinear(mask,side,side,image.width,image.height,x,y);require(std::isfinite(value),"Nonfinite predicted mask");alpha[size_t(y)*image.width+x]=value;lo=std::min(lo,value);hi=std::max(hi,value);}
 require(hi-lo>1e-12f,"Predicted mask is constant; no substitute matte was generated");
 for(size_t i=0;i<alpha.size();i++)image.rgba[i*4+3]=uint8_t(std::clamp((alpha[i]-lo)/(hi-lo)*255.f,0.f,255.f));return image;
}
inline void png(const fs::path& file,const Image& image){
 std::vector<uint8_t> encoded;auto append=[](void* opaque,void* data,int size){auto& out=*static_cast<std::vector<uint8_t>*>(opaque);require(size>=0&&out.size()+size<=32*1024*1024,"PNG size budget exceeded");auto* bytes=static_cast<uint8_t*>(data);out.insert(out.end(),bytes,bytes+size);};
 require(stbi_write_png_to_func(append,&encoded,image.width,image.height,4,image.rgba.data(),image.width*4)!=0,"Cannot encode foreground PNG");
 std::unique_ptr<FILE,decltype(&std::fclose)> stream(std::fopen(file.string().c_str(),"wb"),std::fclose);require(bool(stream),"Cannot create foreground PNG");require(std::fwrite(encoded.data(),1,encoded.size(),stream.get())==encoded.size()&&!std::fflush(stream.get())&&!LMA_SYNC(LMA_FILENO(stream.get())),"Cannot persist foreground PNG");
}
inline void foreground(const json& command){
 require(command.at("type")=="image.generate"&&command.at("pipeline")=="isnet_dis","Foreground recipe mismatch");auto parameters=command.at("parameters");for(auto it=parameters.begin();it!=parameters.end();it++)require(it.key()=="threads","Unknown foreground parameter");int threads=integer(parameters,"threads",2,1,16);
 fs::path workspace=command.at("workspace").get<std::string>(),output=command.at("output").get<std::string>();require(workspace.is_absolute()&&fs::is_directory(workspace)&&output.is_absolute()&&!fs::exists(output),"Invalid private foreground workspace");workspace=fs::canonical(workspace);
 const std::map<std::string,std::string> layout={{"config","vision-config.json"},{"foreground","foreground.onnx"},{"foreground_data","foreground.onnx.data"}};std::set<std::string> found;
 for(auto it=command.at("components").begin();it!=command.at("components").end();it++){require(layout.count(it.key()),"Unknown foreground asset");fs::path file=component(command,it.key().c_str());require(fs::canonical(file.parent_path())==workspace&&file.filename()==layout.at(it.key()),"Foreground asset escaped workspace");found.insert(it.key());}
 require(found.count("config")&&found.count("foreground"),"Missing foreground assets");auto cfg=json::parse(bytes(workspace/"vision-config.json",65536));require(cfg.at("schema")=="lma.foreground-export/1"&&cfg.at("pipeline")=="isnet_dis"&&cfg.at("dtype")=="float32"&&cfg.at("opset")==17,"Unmatched foreground export");
 require(cfg.at("source").at("repository")=="xuebinqin/DIS"&&cfg.at("source").at("revision")=="b6764e20381f6f42a70f83fa3324181529ed1403"&&cfg.at("preprocess")=="publisher_bilinear_uint8_mean_half"&&cfg.at("postprocess")=="publisher_bilinear_minmax_uint8","Unsupported foreground profile");require(cfg.at("imageSize").is_number_integer(),"Image size must be an integer");int side=cfg.at("imageSize");require(side==256||side==512||side==1024,"Foreground image size exceeds profile");
 auto image=load(regular(command,"referenceImage"));auto input=foreground_pixels(image,side);ort_init();Ort::Env env(ORT_LOGGING_LEVEL_FATAL,"lma_foreground");
 event({{"event","execution"},{"details",{{"pipeline","isnet_dis"},{"backend","cpu"},{"sourceRevision",cfg.at("source").at("revision")},{"effectiveParameters",parameters}}}});event({{"event","stage"},{"stage","segmenting_foreground"}});
 Graph graph(env,workspace,"foreground",threads,{{"pixels",{1,3,side,side}}},{"mask",{1,1,side,side}});std::vector<Ort::Value> args;args.push_back(tensor(input,{1,3,side,side}));auto result=graph.run(args);image=foreground_alpha(std::move(image),values(result,{1,1,side,side}),side);png(output,image);event({{"event","complete"},{"output",output.string()}});
}
}

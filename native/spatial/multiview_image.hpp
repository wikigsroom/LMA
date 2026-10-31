#pragma once
#include "image.hpp"
namespace lma_spatial {
// PIL-compatible separable 8-bit Lanczos3 path. Quantize between the horizontal
// and vertical passes as Pillow does; masks use its pixel-center nearest rule.
inline Floats lanczos_image(const Floats& source,int input,int output){
 require(input>=1&&input<=4096&&output>=1&&output<=1024&&source.size()==size_t(input)*input*3,"Invalid multiview resize");
 struct Kernel{int first;std::vector<int> coefficients;};std::vector<Kernel> kernels(output);double factor=double(input)/output,filter=std::max(1.,factor),support=3*filter;constexpr int precision=1<<22;
 auto sinc=[](double x){if(x==0)return 1.;x*=3.14159265358979323846;return std::sin(x)/x;};
 for(int x=0;x<output;x++){double center=(x+.5)*factor;int first=std::max(0,int(center-support+.5)),last=std::min(input,int(center+support+.5));std::vector<double> weights;double sum=0;for(int j=first;j<last;j++){double v=(j+.5-center)/filter,w=std::abs(v)<3?sinc(v)*sinc(v/3):0;weights.push_back(w);sum+=w;}require(std::abs(sum)>1e-12,"Empty Lanczos kernel");auto& k=kernels[x];k.first=first;for(double w:weights){double scaled=w/sum*precision;k.coefficients.push_back(int(scaled+(scaled<0?-.5:.5)));}}
 Floats horizontal(size_t(output)*input*3),result(size_t(output)*output*3);
 for(int y=0;y<input;y++)for(int x=0;x<output;x++)for(int c=0;c<3;c++){int64_t sum=precision/2;auto& k=kernels[x];for(size_t j=0;j<k.coefficients.size();j++)sum+=int64_t(source[(size_t(y)*input+k.first+j)*3+c])*k.coefficients[j];horizontal[(size_t(y)*output+x)*3+c]=float(std::clamp<int64_t>(sum>>22,0,255));}
 for(int y=0;y<output;y++)for(int x=0;x<output;x++)for(int c=0;c<3;c++){int64_t sum=precision/2;auto& k=kernels[y];for(size_t j=0;j<k.coefficients.size();j++)sum+=int64_t(horizontal[(size_t(k.first+j)*output+x)*3+c])*k.coefficients[j];result[(size_t(y)*output+x)*3+c]=float(std::clamp<int64_t>(sum>>22,0,255));}return result;
}
struct CascadeImages {Floats dino512,dino1024,vggt;std::vector<uint8_t> masks;int views=0;};
inline CascadeImages cascade_images(const std::vector<fs::path>& files){
 require(files.size()>=1&&files.size()<=4,"Select one to four ordered views");CascadeImages result;result.views=int(files.size());
 for(auto path:files){int w,h,c;require(fs::file_size(path)<=16*1024*1024&&stbi_info(path.string().c_str(),&w,&h,&c)&&w>0&&h>0&&uint64_t(w)*h<=4194304,"Invalid view PNG");std::unique_ptr<stbi_uc,decltype(&stbi_image_free)> rgba(stbi_load(path.string().c_str(),&w,&h,&c,4),stbi_image_free);require(bool(rgba),"Cannot decode view PNG");
  int x0=w,y0=h,x1=-1,y1=-1;bool opaque=true;for(int y=0;y<h;y++)for(int x=0;x<w;x++){int a=rgba.get()[(size_t(y)*w+x)*4+3];opaque=opaque&&a==255;if(a>0){x0=std::min(x0,x);x1=std::max(x1,x);y0=std::min(y0,y);y1=std::max(y1,y);}}
  require(x1>=x0&&y1>=y0&&!opaque,"Use a nonempty RGBA foreground mask; opaque views require an explicitly selected local segmentation stage");int side=std::max(x1-x0+1,y1-y0+1),left=int(std::floor((x0+x1+1-side)*.5)),top=int(std::floor((y0+y1+1-side)*.5));Floats crop(size_t(side)*side*3,0),alpha(size_t(side)*side,0);
  for(int y=0;y<side;y++)for(int x=0;x<side;x++){int xx=x+left,yy=y+top;if(xx<0||yy<0||xx>=w||yy>=h)continue;size_t from=(size_t(yy)*w+xx)*4,to=size_t(y)*side+x;alpha[to]=rgba.get()[from+3];for(int c=0;c<3;c++)crop[to*3+c]=float(int((rgba.get()[from+c]/255.f)*(rgba.get()[from+3]/255.f)*255.f));}
  for(int size:{512,1024,448}){auto pixels=lanczos_image(crop,side,size);Floats chw(size_t(size)*size*3);for(size_t i=0;i<size_t(size)*size;i++)for(int c=0;c<3;c++)chw[size_t(c)*size*size+i]=pixels[i*3+c]/255;auto& out=size==512?result.dino512:size==1024?result.dino1024:result.vggt;out.insert(out.end(),chw.begin(),chw.end());}
  for(int y=0;y<448;y++)for(int x=0;x<448;x++){int xx=std::min(side-1,int((x+.5)*side/448)),yy=std::min(side-1,int((y+.5)*side/448));result.masks.push_back(alpha[size_t(yy)*side+xx]>127);}
 }return result;
}
}

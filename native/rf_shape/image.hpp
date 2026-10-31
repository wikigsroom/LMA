#pragma once
#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_PNG
#include "stb_image.h"
#include "../worker_common.hpp"
namespace lma_shape {
using namespace lma_worker;
inline float cubic(float x){x=std::abs(x);return x<1?((1.5f*x-2.5f)*x)*x+1:x<2?((-.5f*x+2.5f)*x-4)*x+2:0;}
// Separable antialiased bicubic resize, then center crop. PNG alpha is
// explicitly composited over white; this is not an inferred foreground mask.
inline std::vector<float> pixels(const std::string& file,int crop,int edge,const json& mean,const json& stddev) {
 int w=0,h=0,c=0;require(std::filesystem::file_size(file)<=16*1024*1024&&stbi_info(file.c_str(),&w,&h,&c)&&w>0&&h>0&&uint64_t(w)*h<=4194304,"Use a bounded RGB/RGBA PNG");
 std::unique_ptr<stbi_uc,decltype(&stbi_image_free)> rgba(stbi_load(file.c_str(),&w,&h,&c,4),stbi_image_free);require(bool(rgba),"Cannot decode selected PNG");
 int nw=w<h?edge:int(int64_t(w)*edge/h),nh=w<h?int(int64_t(h)*edge/w):edge;require(nw>=crop&&nh>=crop&&uint64_t(nw)*nh<=16777216,"Image aspect ratio exceeds resize budget");
 std::vector<float> source(size_t(w)*h*3),temp(size_t(nw)*h*3),resized(size_t(nw)*nh*3);
 for(size_t i=0;i<size_t(w)*h;i++)for(int ch=0;ch<3;ch++)source[i*3+ch]=float((int(rgba.get()[i*4+ch])*rgba.get()[i*4+3]+255*(255-rgba.get()[i*4+3])+127)/255);
 auto resize_axis=[&](const std::vector<float>& in,std::vector<float>& out,int iw,int ih,int ow,int oh,bool vertical){int count=vertical?oh:ow,other=vertical?ow:oh,old=vertical?ih:iw;float scale=float(old)/count,support=2*std::max(1.f,scale);
  for(int i=0;i<count;i++){float center=(i+.5f)*scale;int begin=std::max(0,int(std::floor(center-support+.5f))),end=std::min(old,int(std::floor(center+support+.5f)));std::vector<float> weights(size_t(end-begin));float sum=0;
   for(int j=begin;j<end;j++){weights[size_t(j-begin)]=cubic((j+.5f-center)/std::max(1.f,scale));sum+=weights[size_t(j-begin)];}require(std::abs(sum)>1e-6,"Invalid resize weights");
   for(int k=0;k<other;k++)for(int ch=0;ch<3;ch++){float v=0;for(int j=begin;j<end;j++){size_t at=vertical?(size_t(j)*iw+k)*3+ch:(size_t(k)*iw+j)*3+ch;v+=in[at]*weights[size_t(j-begin)]/sum;}size_t to=vertical?(size_t(i)*ow+k)*3+ch:(size_t(k)*ow+i)*3+ch;out[to]=std::round(std::clamp(v,0.f,255.f));}
  }
 };
 resize_axis(source,temp,w,h,nw,h,false);resize_axis(temp,resized,nw,h,nw,nh,true);
 std::vector<float> result(size_t(crop)*crop*3);int left=(nw-crop)/2,top=(nh-crop)/2;
 for(int ch=0;ch<3;ch++){float m=mean.at(ch),s=stddev.at(ch);require(std::isfinite(m)&&std::isfinite(s)&&s>0&&s<=10,"Invalid image normalization");
  for(int y=0;y<crop;y++)for(int x=0;x<crop;x++)result[(size_t(ch)*crop+y)*crop+x]=(resized[(size_t(y+top)*nw+x+left)*3+ch]/255.f-m)/s;
 }return result;
}
}

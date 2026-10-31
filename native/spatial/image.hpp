#pragma once
#include "../rf_shape/image.hpp"
namespace lma_spatial {
using namespace lma_shape;
inline float cv_cubic(float x){x=std::abs(x);return x<=1?((1.25f*x-2.25f)*x)*x+1:x<2?((-.75f*x+3.75f)*x-6)*x+3:0;}
inline std::vector<float> resize(const std::vector<float>& source,int iw,int ih,int ow,int oh,int channels,const std::string& method,bool quantize){
 require(iw>0&&ih>0&&ow>0&&oh>0&&channels>=1&&channels<=4&&source.size()==size_t(iw)*ih*channels&&uint64_t(ow)*oh*channels<=32000000,"Resize exceeds bounds");
 std::vector<float> result(size_t(ow)*oh*channels);double sx=double(iw)/ow,sy=double(ih)/oh;
 if(method=="area"){sx=1/(double(ow)/iw);sy=1/(double(oh)/ih);}
 for(int y=0;y<oh;y++)for(int x=0;x<ow;x++){
  if(method=="nearest")for(int c=0;c<channels;c++)result[(size_t(y)*ow+x)*channels+c]=source[(size_t(std::min(ih-1,int(y*sy)))*iw+std::min(iw-1,int(x*sx)))*channels+c];
  else if(method=="area"&&(sx<1||sy<1)){
   // OpenCV INTER_AREA uses its two-tap area emulation when upsampling,
   // including float fractional coefficients at integer row boundaries.
   int bx=int(std::floor(x*sx)),by=int(std::floor(y*sy));float fx=float((x+1)-(bx+1)*(double(ow)/iw)),fy=float((y+1)-(by+1)*(double(oh)/ih));
   fx=fx<=0?0.f:fx-std::floor(fx);fy=fy<=0?0.f:fy-std::floor(fy);if(bx>=iw-1)fx=0;
   double wx[2]={1-fx,fx},wy[2]={1-fy,fy};if(quantize)for(int i=0;i<2;i++){wx[i]=std::nearbyint(wx[i]*2048)/2048;wy[i]=std::nearbyint(wy[i]*2048)/2048;}
   for(int c=0;c<channels;c++){double sum=0;for(int j=0;j<2;j++)for(int i=0;i<2;i++)sum+=source[(size_t(std::clamp(by+j,0,ih-1))*iw+std::clamp(bx+i,0,iw-1))*channels+c]*wx[i]*wy[j];result[(size_t(y)*ow+x)*channels+c]=float(sum);}
  }else if(method=="area"){
   double top=y*sy,bottom=(y+1)*sy,left=x*sx,right=(x+1)*sx;
   for(int c=0;c<channels;c++){double sum=0;for(int j=int(std::floor(top));j<int(std::ceil(bottom));j++)for(int i=int(std::floor(left));i<int(std::ceil(right));i++)
    sum+=source[(size_t(std::clamp(j,0,ih-1))*iw+std::clamp(i,0,iw-1))*channels+c]*std::max(0.,std::min(bottom,double(j+1))-std::max(top,double(j)))*std::max(0.,std::min(right,double(i+1))-std::max(left,double(i)));
    result[(size_t(y)*ow+x)*channels+c]=float(sum/(sx*sy));}
  }else{
   require(method=="cubic"||method=="bilinear"||method=="bilinear_aa","Unknown image resize");double centerx=(x+.5)*sx-.5,centery=(y+.5)*sy-.5;int bx=int(std::floor(centerx)),by=int(std::floor(centery));bool aa=method=="bilinear_aa";double rx=aa?std::max(1.,sx):1.,ry=aa?std::max(1.,sy):1.;
   int xlo=method=="cubic"?bx-1:aa?std::max(0,int(std::ceil(centerx-rx))):bx,xhi=method=="cubic"?bx+2:aa?std::min(iw-1,int(std::floor(centerx+rx))):bx+1;
   int ylo=method=="cubic"?by-1:aa?std::max(0,int(std::ceil(centery-ry))):by,yhi=method=="cubic"?by+2:aa?std::min(ih-1,int(std::floor(centery+ry))):by+1;
   for(int c=0;c<channels;c++){double sum=0,weight=0;for(int j=ylo;j<=yhi;j++)for(int i=xlo;i<=xhi;i++){
    double wx=method=="cubic"?cv_cubic(float(centerx-i)):std::max(0.,1-std::abs(centerx-i)/rx);double wy=method=="cubic"?cv_cubic(float(centery-j)):std::max(0.,1-std::abs(centery-j)/ry);double w=wx*wy;sum+=source[(size_t(std::clamp(j,0,ih-1))*iw+std::clamp(i,0,iw-1))*channels+c]*w;weight+=w;
   }require(std::abs(weight)>1e-8,"Empty interpolation kernel");result[(size_t(y)*ow+x)*channels+c]=float(sum/weight);}
  }
  for(int c=0;c<channels;c++){auto& value=result[(size_t(y)*ow+x)*channels+c];if(quantize)value=std::round(std::clamp(value,0.f,255.f));}
 }return result;
}
struct ImageFeatures {std::vector<float> pixels;std::vector<int> selected;std::vector<float> diagnostic_base;};
inline ImageFeatures shape_image(const std::filesystem::path& path,int processor_size,int encoder_size,float border,bool masked,bool diagnostic=false){
 int w,h,c;require(std::filesystem::file_size(path)<=16*1024*1024&&stbi_info(path.string().c_str(),&w,&h,&c)&&w>1&&h>1&&uint64_t(w)*h<=4194304,"Use a bounded PNG");
 std::unique_ptr<stbi_uc,decltype(&stbi_image_free)> rgba(stbi_load(path.string().c_str(),&w,&h,&c,4),stbi_image_free);require(bool(rgba),"Cannot decode input PNG");
 int x0=w,y0=h,x1=-1,y1=-1;for(int y=0;y<h;y++)for(int x=0;x<w;x++)if(rgba.get()[(size_t(y)*w+x)*4+3]){x0=std::min(x0,x);x1=std::max(x1,x);y0=std::min(y0,y);y1=std::max(y1,y);}
 int cw=x1-x0,ch=y1-y0,size=std::max(w,h),desired=int(size*(1-border));require(cw>0&&ch>0&&desired>0,"Input has no two-dimensional foreground");
 double scale=double(desired)/std::max(cw,ch);int nw=int(cw*scale),nh=int(ch*scale);require(nw>0&&nh>0,"Foreground aspect ratio is too narrow");
 std::vector<float> cropped(size_t(cw)*ch*4);for(int y=0;y<ch;y++)for(int x=0;x<cw;x++)for(int k=0;k<4;k++)cropped[(size_t(y)*cw+x)*4+k]=rgba.get()[(size_t(y+y0)*w+x+x0)*4+k];
 auto foreground=resize(cropped,cw,ch,nw,nh,4,"area",true);std::vector<float> centered(size_t(size)*size*3,255),alpha(size_t(size)*size,0);int left=(size-nw)/2,top=(size-nh)/2;
 for(int y=0;y<nh;y++)for(int x=0;x<nw;x++){size_t from=(size_t(y)*nw+x)*4,to=size_t(y+top)*size+x+left;float a=foreground[from+3]/255;alpha[to]=foreground[from+3];for(int k=0;k<3;k++)centered[to*3+k]=std::floor(std::clamp(foreground[from+k]*a+255*(1-a),0.f,255.f));}
 auto base=resize(centered,size,size,processor_size,processor_size,3,"cubic",true);auto input=resize(base,processor_size,processor_size,encoder_size,encoder_size,3,"bilinear_aa",false);
 ImageFeatures result;if(diagnostic)result.diagnostic_base=base;result.pixels.resize(size_t(encoder_size)*encoder_size*3);const float mean[3]={.485f,.456f,.406f},stddev[3]={.229f,.224f,.225f};
 for(size_t i=0;i<size_t(encoder_size)*encoder_size;i++)for(int k=0;k<3;k++)result.pixels[size_t(k)*encoder_size*encoder_size+i]=(input[i*3+k]/255-mean[k])/stddev[k];
 result.selected.push_back(0);int patches=encoder_size/14;
 if(masked){auto mask_base=resize(alpha,size,size,processor_size,processor_size,1,"nearest",true);auto mask=resize(mask_base,processor_size,processor_size,encoder_size,encoder_size,1,"nearest",false);
  for(int py=0;py<patches;py++)for(int px=0;px<patches;px++){bool valid=false;for(int y=py*14;y<(py+1)*14&&!valid;y++)for(int x=px*14;x<(px+1)*14;x++)if(mask[size_t(y)*encoder_size+x]>0){valid=true;break;}if(valid)result.selected.push_back(1+py*patches+px);}
 }else for(int i=1;i<=patches*patches;i++)result.selected.push_back(i);
 return result;
}
}

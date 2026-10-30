// SPDX-License-Identifier: Apache-2.0
// Pinned old LTX multi-scale equations. No learned constants or remote execution.
#pragma once
#include <cmath>
#include <stdexcept>
#include <utility>
#include <vector>
namespace lma::ltx098::multiscale {
inline void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
inline int first_extent(int requested) {
    require(requested>=128 && requested<=256 && requested%32==0,"Unsupported multiscale output extent");
    int scaled=int(double(requested)*0.6666666);return scaled-scaled%32;
}
inline std::pair<double,double> moments(const float* data,size_t n) {
    require(n>1,"AdaIN needs at least two spatial/temporal values");double mean=0,m2=0;
    for(size_t i=0;i<n;++i){require(std::isfinite(data[i]),"Non-finite AdaIN input");double delta=data[i]-mean;mean+=delta/double(i+1);m2+=delta*(data[i]-mean);}
    return {mean,std::sqrt(m2/double(n-1))}; // torch.std_mean default correction=1
}
template<class Check> void adain(std::vector<float>& high,const std::vector<float>& reference,int channels,Check check) {
    require(channels>=1 && high.size()%channels==0 && reference.size()%channels==0,"Invalid AdaIN channel layout");
    size_t hn=high.size()/channels,rn=reference.size()/channels;
    for(int c=0;c<channels;++c) {
        check();auto h=moments(high.data()+c*hn,hn),r=moments(reference.data()+c*rn,rn);
        require(h.second>0,"Singular AdaIN channel");
        for(size_t i=0;i<hn;++i) {auto& value=high[c*hn+i];value=float((double(value)-h.first)/h.second*r.second+r.first);require(std::isfinite(value),"Non-finite AdaIN output");}
    }
}
inline std::vector<float> resize_bilinear(const std::vector<float>& input,int frames,int ih,int iw,int oh,int ow) {
    require(frames>=1 && ih>=1 && iw>=1 && oh>=1 && ow>=1 && input.size()==size_t(3)*frames*ih*iw,"Invalid video resize extent");
    std::vector<float> result(size_t(3)*frames*oh*ow);
    for(int c=0;c<3;++c)for(int f=0;f<frames;++f)for(int y=0;y<oh;++y) {
        float sy=std::max(0.f,(float(y)+.5f)*(float(ih)/oh)-.5f);int y0=int(sy),y1=std::min(y0+1,ih-1);float fy=sy-y0;
        for(int x=0;x<ow;++x) {
            float sx=std::max(0.f,(float(x)+.5f)*(float(iw)/ow)-.5f);int x0=int(sx),x1=std::min(x0+1,iw-1);float fx=sx-x0;
            auto at=[&](int yy,int xx){return input[((size_t(c)*frames+f)*ih+yy)*iw+xx];};
            float a=at(y0,x0)*(1-fx)+at(y0,x1)*fx,b=at(y1,x0)*(1-fx)+at(y1,x1)*fx;
            result[((size_t(c)*frames+f)*oh+y)*ow+x]=a*(1-fy)+b*fy;
        }
    }
    return result;
}
}

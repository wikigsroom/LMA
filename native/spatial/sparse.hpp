#pragma once
#include "../worker_common.hpp"
#include <array>
#include <map>
#include <unordered_map>
#include <numeric>

// CPU building blocks, not complete UniForge/SAM/SUPRA model adapters.
// Coordinates are [batch,x,y,z]. Explicit policies preserve publisher differences.
namespace lma_sparse {
using lma_worker::require;
using Coord=std::array<int64_t,4>;
using Feats=std::vector<float>;
constexpr size_t tensor_limit=32000000, point_limit=262144;
inline size_t bounded(size_t n,size_t c){require(c>0&&c<=4096&&n<=point_limit&&n<=tensor_limit/c,"Sparse tensor exceeds limits");return n*c;}
struct Hash { size_t operator()(const Coord& p)const noexcept{size_t r=0;for(auto v:p)r^=std::hash<int64_t>{}(v)+size_t(0x9e3779b9)+(r<<6)+(r>>2);return r;} };
inline void coordinates(const std::vector<Coord>& c){
 require(c.size()<=point_limit,"Sparse coordinate count exceeds limits");std::unordered_map<Coord,size_t,Hash> seen;seen.reserve(c.size());
 for(const auto& p:c){require(p[0]>=0&&p[0]<32,"Invalid sparse batch");for(int i=1;i<4;i++)require(p[i]>=0&&p[i]<=1048575,"Invalid sparse coordinate");require(seen.emplace(p,seen.size()).second,"Duplicate sparse coordinate");}
}
inline void finite(const Feats& f){for(float x:f)require(std::isfinite(x),"Nonfinite sparse tensor");}
struct Packed {Feats feats;std::vector<Coord> coords;std::vector<int64_t> inverse,child;size_t channels=0;};
inline Packed pool(const Feats& f,const std::vector<Coord>& c,size_t channels,const std::array<int64_t,3>& factor,int mode){
 require(f.size()==bounded(c.size(),channels)&&mode>=0&&mode<=2,"Invalid sparse reduction");coordinates(c);finite(f);
 for(auto n:factor)require(n>=1&&n<=16,"Invalid sparse factor");
 std::map<Coord,size_t> unique;for(auto p:c){for(int k=0;k<3;k++)p[k+1]/=factor[k];unique.emplace(p,0);}
 Packed out;out.channels=channels;for(auto& v:unique){v.second=out.coords.size();out.coords.push_back(v.first);}out.feats.assign(bounded(unique.size(),channels),mode==2?-std::numeric_limits<float>::infinity():0);
 std::vector<size_t> count(unique.size(),mode==1?1:0);out.inverse.reserve(c.size());
 for(size_t i=0;i<c.size();i++){auto p=c[i];for(int k=0;k<3;k++)p[k+1]/=factor[k];size_t row=unique.at(p);out.inverse.push_back(int64_t(row));count[row]++;
  for(size_t j=0;j<channels;j++){float& dst=out.feats[row*channels+j];if(mode==2)dst=std::max(dst,f[i*channels+j]);else dst+=f[i*channels+j];}}
 if(mode!=2)for(size_t i=0;i<count.size();i++)for(size_t j=0;j<channels;j++)out.feats[i*channels+j]/=float(count[i]);finite(out.feats);return out;
}
inline Packed subdivide(const Feats& f,const std::vector<Coord>& c,size_t channels,const std::vector<int64_t>& mask,int order){
 require(f.size()==bounded(c.size(),channels)&&mask.size()==c.size()*8&&(order==0||order==1),"Invalid sparse subdivision");coordinates(c);finite(f);Packed out;out.channels=channels;
 size_t n=0;for(int64_t v:mask){require(v==0||v==1,"Subdivision mask must be boolean");n+=size_t(v);}bounded(n,channels);out.feats.reserve(n*channels);out.coords.reserve(n);out.inverse.reserve(n);out.child.reserve(n);
 for(size_t i=0;i<c.size();i++)for(int j=0;j<8;j++)if(mask[i*8+j]){Coord p=c[i];for(int k=0;k<3;k++)p[k+1]=2*p[k+1]+((j>>(order==0?2-k:k))&1);
  require(p[1]<=1048575&&p[2]<=1048575&&p[3]<=1048575,"Subdivision coordinate overflow");out.coords.push_back(p);out.inverse.push_back(int64_t(i));out.child.push_back(j);out.feats.insert(out.feats.end(),f.begin()+i*channels,f.begin()+(i+1)*channels);}return out;
}
inline Packed spatial_to_channel(const Feats& f,const std::vector<Coord>& c,size_t channels,int factor){
 require(factor>=1&&factor<=4,"Invalid spatial-channel factor");auto out=pool(f,c,channels,{factor,factor,factor},0);size_t blocks=size_t(factor)*factor*factor;
 out.feats.assign(bounded(out.coords.size(),channels*blocks),0);out.channels=channels*blocks;out.child.resize(c.size());
 for(size_t i=0;i<c.size();i++){size_t sub=0,power=1;for(int k=1;k<4;k++){sub+=size_t(c[i][k]%factor)*power;power*=factor;}out.child[i]=int64_t(sub);
  std::copy(f.begin()+i*channels,f.begin()+(i+1)*channels,out.feats.begin()+(size_t(out.inverse[i])*blocks+sub)*channels);}return out;
}
// Cross-correlation, weights [Cout,Kx,Ky,Kz,Cin], same active support and order.
inline Feats submanifold_conv(const Feats& f,const std::vector<Coord>& c,size_t ci,const Feats& weights,size_t co,const std::array<int64_t,3>& kernel,const Feats& bias,const std::array<int64_t,3>& dilation){
 require(f.size()==bounded(c.size(),ci)&&bias.size()==co,"Invalid sparse convolution features/bias");bounded(c.size(),co);coordinates(c);finite(f);finite(weights);finite(bias);size_t volume=1;
 for(int j=0;j<3;j++){require(kernel[j]>=1&&kernel[j]<=7&&kernel[j]%2==1&&dilation[j]>=1&&dilation[j]<=16,"Only odd submanifold kernels are supported");volume*=size_t(kernel[j]);}
 require(co>0&&co<=4096&&weights.size()==co*volume*ci&&weights.size()<=64000000,"Sparse convolution weights exceed limits");
 require(uint64_t(c.size())*volume*ci*co<=64000000000ULL,"Sparse convolution work budget exceeded");std::unordered_map<Coord,size_t,Hash> rows;rows.reserve(c.size());for(size_t i=0;i<c.size();i++)rows.emplace(c[i],i);
 Feats result(c.size()*co);for(size_t i=0;i<c.size();i++){std::copy(bias.begin(),bias.end(),result.begin()+i*co);size_t k=0;
  for(int64_t x=0;x<kernel[0];x++)for(int64_t y=0;y<kernel[1];y++)for(int64_t z=0;z<kernel[2];z++,k++){auto p=c[i];p[1]+=(x-kernel[0]/2)*dilation[0];p[2]+=(y-kernel[1]/2)*dilation[1];p[3]+=(z-kernel[2]/2)*dilation[2];auto row=rows.find(p);if(row==rows.end())continue;const float* src=f.data()+row->second*ci;
   for(size_t o=0;o<co;o++){const float* w=weights.data()+(o*volume+k)*ci;float sum=0;for(size_t j=0;j<ci;j++)sum+=src[j]*w[j];result[i*co+o]+=sum;}}}finite(result);return result;
}
// Packed [tokens,heads,width] attention; ranges are explicit [batch,start,end].
// Streaming rows bound auxiliary memory to O(K + D), rather than Q*K.
inline Feats attention(const Feats& q,const Feats& k,const Feats& v,size_t nq,size_t nk,size_t heads,size_t dim,size_t vd,const std::vector<int64_t>& qlen,const std::vector<int64_t>& klen){
 require(heads>=1&&heads<=64&&dim>=1&&dim<=256&&vd>=1&&vd<=256&&q.size()==bounded(nq,heads*dim)&&k.size()==bounded(nk,heads*dim)&&v.size()==bounded(nk,heads*vd),"Invalid packed attention dimensions");
 require(!qlen.empty()&&qlen.size()==klen.size()&&qlen.size()<=32,"Invalid packed attention lengths");finite(q);finite(k);finite(v);size_t tq=0,tk=0;
 for(size_t i=0;i<qlen.size();i++){require(qlen[i]>=0&&klen[i]>=0&&qlen[i]<=int64_t(nq)&&klen[i]<=int64_t(nk)&&(qlen[i]==0||klen[i]>0),"Empty attention key support");tq+=size_t(qlen[i]);tk+=size_t(klen[i]);}require(tq==nq&&tk==nk,"Packed attention lengths do not cover tensors");
 require(uint64_t(nq)*nk*heads*(dim+vd)<=64000000000ULL,"Packed attention work budget exceeded");Feats out(bounded(nq,heads*vd),0);size_t qs=0,ks=0;double scale=1/std::sqrt(double(dim));
 for(size_t batch=0;batch<qlen.size();batch++){size_t Q=size_t(qlen[batch]),K=size_t(klen[batch]);std::vector<double> scores(K);for(size_t i=0;i<Q;i++)for(size_t h=0;h<heads;h++){
   double mx=-std::numeric_limits<double>::infinity();for(size_t j=0;j<K;j++){double s=0;for(size_t d=0;d<dim;d++)s+=double(q[((qs+i)*heads+h)*dim+d])*k[((ks+j)*heads+h)*dim+d];scores[j]=s*scale;mx=std::max(mx,scores[j]);}
   double sum=0;for(double& s:scores){s=std::exp(s-mx);sum+=s;}require(sum>0&&std::isfinite(sum),"Nonfinite attention normalization");for(size_t d=0;d<vd;d++){double acc=0;for(size_t j=0;j<K;j++)acc+=scores[j]*v[((ks+j)*heads+h)*vd+d];out[((qs+i)*heads+h)*vd+d]=float(acc/sum);}}
  qs+=Q;ks+=K;}finite(out);return out;
}
}

#pragma once
#include "typed_graph.hpp"
#include "fdg.hpp"
#include <set>
namespace lma_spatial {
// Closed cascade primitives. Budgets reject work; they never truncate learned
// support, replace predictions or silently fall back to another architecture.
inline Integers flatten_coords(const std::vector<lma_sparse::Coord>& coords){Integers out;out.reserve(coords.size()*4);for(auto c:coords)out.insert(out.end(),c.begin(),c.end());return out;}
inline std::vector<lma_sparse::Coord> sparse_coords(Ort::Value& value,int grid){
 auto info=value.GetTensorTypeAndShapeInfo();auto shape=info.GetShape();require(info.GetElementType()==ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64&&shape.size()==2&&shape[1]==4&&shape[0]>0&&shape[0]<=int64_t(lma_sparse::point_limit),"Invalid cascade coordinates");
 auto p=value.GetTensorData<int64_t>();std::vector<lma_sparse::Coord> out(static_cast<size_t>(shape[0]));for(size_t i=0;i<out.size();i++)for(int j=0;j<4;j++){require(p[i*4+j]>=0&&p[i*4+j]<(j?grid:1),"Cascade requires one batch and in-grid coordinates");out[i][j]=int32_t(p[i*4+j]);}lma_sparse::coordinates(out);return out;
}
inline std::pair<std::vector<lma_sparse::Coord>,std::vector<lma_sparse::Coord>> occupancy_support(const Floats& logits,int grid,size_t max_rows){
 require(grid>=64&&grid<=256&&grid%64==0&&logits.size()==size_t(grid)*grid*grid,"Invalid structure occupancy output");std::set<lma_sparse::Coord> low,high;int factor=grid/64;
 for(int x=0;x<grid;x++)for(int y=0;y<grid;y++)for(int z=0;z<grid;z++){float v=logits[(size_t(x)*grid+y)*grid+z];require(std::isfinite(v),"Nonfinite occupancy");if(v>0){high.insert({0,x/factor,y/factor,z/factor});low.insert({0,x/(factor*2),y/(factor*2),z/(factor*2)});}}
 require(!low.empty()&&low.size()<=max_rows&&high.size()<=max_rows,"Empty or oversized learned structure; select a compatible export/input");return {{low.begin(),low.end()},{high.begin(),high.end()}};
}
inline std::vector<lma_sparse::Coord> surface_cells(const Mesh& mesh,int grid,size_t max_rows){
 require(grid>=8&&grid<=128&&mesh.indices.size()%3==0&&mesh.indices.size()/3<=300000,"Surface handoff exceeds bounds");
 using D=std::array<double,3>;auto dotd=[](D a,D b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];};auto crossd=[](D a,D b){return D{a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};};
 const double half=.5/grid,eps=std::numeric_limits<double>::epsilon()*32;size_t work=0;std::set<lma_sparse::Coord> out;
 for(size_t f=0;f<mesh.indices.size();f+=3){D tri[3];int lo[3],hi[3];for(int a=0;a<3;a++){lo[a]=grid-1;hi[a]=0;}
  for(int k=0;k<3;k++){require(mesh.indices[f+k]<mesh.vertices.size(),"Handoff face index out of range");for(int a=0;a<3;a++){double v=mesh.vertices[mesh.indices[f+k]][a];require(std::isfinite(v)&&v>=-.5&&v<=.5,"Handoff mesh must be normalized");tri[k][a]=v;int cell=std::clamp(int(std::floor((v+.5)*grid)),0,grid-1);lo[a]=std::min(lo[a],cell);hi[a]=std::max(hi[a],cell);}}
  D edges[3];for(int k=0;k<3;k++)for(int a=0;a<3;a++)edges[k][a]=tri[(k+1)%3][a]-tri[k][a];D normal=crossd(edges[0],D{tri[2][0]-tri[0][0],tri[2][1]-tri[0][1],tri[2][2]-tri[0][2]});
  for(int x=lo[0];x<=hi[0];x++)for(int y=lo[1];y<=hi[1];y++)for(int z=lo[2];z<=hi[2];z++){
   require(++work<=50000000,"Surface handoff work budget exceeded");D center={-.5+(x+.5)/grid,-.5+(y+.5)/grid,-.5+(z+.5)/grid},v[3];for(int k=0;k<3;k++)for(int a=0;a<3;a++)v[k][a]=tri[k][a]-center[a];bool hit=true;
   for(int a=0;a<3;a++)if(std::min({v[0][a],v[1][a],v[2][a]})>half+eps||std::max({v[0][a],v[1][a],v[2][a]})<-half-eps)hit=false;
   for(D e:edges){D axes[3]={{0,e[2],-e[1]},{-e[2],0,e[0]},{e[1],-e[0],0}};for(D axis:axes){double p[3]={dotd(v[0],axis),dotd(v[1],axis),dotd(v[2],axis)},r=half*(std::abs(axis[0])+std::abs(axis[1])+std::abs(axis[2]))+eps;if(std::min({p[0],p[1],p[2]})>r||std::max({p[0],p[1],p[2]})<-r)hit=false;}}
   if(std::abs(dotd(normal,v[0]))>half*(std::abs(normal[0])+std::abs(normal[1])+std::abs(normal[2]))+eps)hit=false;
   if(hit){out.insert({0,x,y,z});require(out.size()<=max_rows,"Surface handoff exceeds selected coordinate budget");}
  }
 }require(!out.empty(),"Empty surface handoff");return {out.begin(),out.end()};
}
inline float cascade_time(int i,int steps,float shift){double t=1-double(i)/steps;return float(shift*t/(1+(shift-1)*t));}
inline float cascade_std(const Floats& values,bool dense){
 require(!values.empty()&&(!dense||values.size()>1),"Invalid guidance statistics");double sum=0,square=0;for(float x:values){sum+=x;square+=double(x)*x;}double mean=sum/values.size();
 if(!dense)return float(std::sqrt(std::max(0.,square/values.size()-mean*mean)));
 double variance=0;for(float x:values)variance+=(x-mean)*(x-mean);return float(std::sqrt(variance/(values.size()-1)));
}
inline Floats cascade_guidance(const Floats& sample,const Floats& positive,const Floats& negative,float time,float strength,float rescale,bool dense){
 require(sample.size()==positive.size()&&sample.size()==negative.size()&&strength>=0&&strength<=30&&rescale>=0&&rescale<=1,"Invalid cascade prediction");Floats guided(sample.size());
 for(size_t i=0;i<guided.size();i++)guided[i]=dense?negative[i]+strength*(positive[i]-negative[i]):strength*positive[i]+(1-strength)*negative[i];
 if(rescale>0&&strength!=0&&strength!=1){constexpr float sigma=1e-5f;float denominator=sigma+(1-sigma)*time;Floats a(sample.size()),b(sample.size());for(size_t i=0;i<a.size();i++){a[i]=(1-sigma)*sample[i]-denominator*positive[i];b[i]=(1-sigma)*sample[i]-denominator*guided[i];}float scale=cascade_std(a,dense)/std::max(cascade_std(b,dense),1e-6f);for(size_t i=0;i<guided.size();i++)guided[i]=((1-sigma)*sample[i]-(rescale*b[i]*scale+(1-rescale)*b[i]))/denominator;}
 return guided;
}
inline void cascade_update(Floats& sample,const Floats& velocity,float delta){require(sample.size()==velocity.size(),"Cascade velocity shape mismatch");for(size_t i=0;i<sample.size();i++){sample[i]-=delta*velocity[i];require(std::isfinite(sample[i]),"Nonfinite cascade sample");}}
inline void denormalize(Floats& values,const json& stats,int channels){require(values.size()%channels==0&&stats.at("mean").size()==size_t(channels)&&stats.at("std").size()==size_t(channels),"Unmatched latent statistics");for(size_t i=0;i<values.size();i++){float mean=stats.at("mean")[i%channels],sd=stats.at("std")[i%channels];require(std::isfinite(mean)&&std::isfinite(sd)&&sd>0,"Invalid latent statistics");values[i]=values[i]*sd+mean;require(std::isfinite(values[i]),"Nonfinite denormalized latent");}}
}

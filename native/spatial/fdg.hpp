#pragma once
#include "mesh.hpp"
#include "sparse.hpp"
namespace lma_spatial {
// Inference-only flexible dual-grid extraction. Source topology and learned
// diagonal weights are retained; only the CUDA coordinate hash is replaced.
inline Mesh dual_grid(const std::vector<lma_sparse::Coord>& coords,const Floats& vertices,
                      const std::vector<int64_t>& flags,const Floats& weights,int grid,size_t max_triangles){
 using lma_sparse::Coord;using lma_sparse::Hash;
 lma_sparse::coordinates(coords);size_t n=coords.size();require(n>0&&n<=3000000&&vertices.size()==n*3&&flags.size()==n*3&&weights.size()==n&&grid>=2&&grid<=4096,"Invalid dual-grid fields");
 Mesh mesh;mesh.vertices.resize(n);std::unordered_map<Coord,uint32_t,Hash> rows;rows.reserve(n);
 for(size_t i=0;i<n;i++){
  require(coords[i][0]==0&&std::isfinite(weights[i])&&weights[i]>0,"Dual grid requires one batch and positive diagonal weights");
  rows.emplace(coords[i],uint32_t(i));
  for(int j=0;j<3;j++){
   require(coords[i][j+1]<grid&&std::isfinite(vertices[i*3+j])&&std::abs(vertices[i*3+j])<=16&&(flags[i*3+j]==0||flags[i*3+j]==1),"Invalid dual-grid coordinate/offset/edge");
   mesh.vertices[i][j]=(float(coords[i][j+1])+vertices[i*3+j])/float(grid)-.5f;
  }
 }
 constexpr int neighbors[3][4][3]={{{0,0,0},{0,0,1},{0,1,1},{0,1,0}},{{0,0,0},{1,0,0},{1,0,1},{0,0,1}},{{0,0,0},{0,1,0},{1,1,0},{1,0,0}}};
 constexpr int split[2][6]={{0,1,2,0,2,3},{0,1,3,3,1,2}};
 for(size_t i=0;i<n;i++)for(int axis=0;axis<3;axis++)if(flags[i*3+axis]){
  std::array<uint32_t,4> quad{};bool valid=true;
  for(int k=0;k<4;k++){
   auto c=coords[i];for(int j=0;j<3;j++)c[j+1]+=neighbors[axis][k][j];auto found=rows.find(c);
   if(found==rows.end()){valid=false;break;}quad[k]=found->second;
  }
  if(!valid)continue;
  require(mesh.indices.size()/3+2<=max_triangles,"Dual-grid mesh exceeds the selected triangle limit");
  // The released decoder and reference compare FP32 products. Promoting these
  // products to double changes near-tie diagonals and therefore the topology.
  float diagonal02=weights[quad[0]]*weights[quad[2]],diagonal13=weights[quad[1]]*weights[quad[3]];
  int diagonal=diagonal02>diagonal13?0:1;
  for(int k:split[diagonal])mesh.indices.push_back(quad[k]);
 }
 require(!mesh.indices.empty(),"Dual-grid decoder produced no connected surface");return mesh;
}
inline Mesh decode_dual_grid(const std::vector<lma_sparse::Coord>& coords,const Floats& features,int grid,float margin,size_t max_triangles){
 require(features.size()==coords.size()*7&&margin>=0&&margin<=4,"Invalid learned dual-grid output");
 Floats v(coords.size()*3),w(coords.size());std::vector<int64_t> flags(v.size());
 for(size_t i=0;i<coords.size();i++){
  for(int j=0;j<7;j++)require(std::isfinite(features[i*7+j]),"Nonfinite learned dual-grid field");
  for(int j=0;j<3;j++){double x=features[i*7+j];v[i*3+j]=float((1+2*margin)/(1+std::exp(-x))-margin);flags[i*3+j]=features[i*7+3+j]>0?1:0;}
  double x=features[i*7+6];w[i]=float(std::max(x,0.)+std::log1p(std::exp(-std::abs(x))));require(w[i]>0,"Underflowed learned diagonal weight");
 }
 return dual_grid(coords,v,flags,w,grid,max_triangles);
}
}

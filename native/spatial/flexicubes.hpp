#pragma once
#include "sparse.hpp"
#include "../rf_shape/geometry.hpp"
#include "flexicubes_tables.hpp"
#include <map>
#include <set>
namespace lma_spatial {
// CPU inference port of the locked SAM 3D / NVIDIA FlexiCubes path. Learned
// corner fields and all DMC cases, ambiguity checks and gamma splits remain
// source-defined. Sparse enumeration replaces dense res^3 storage only.
struct FlexMesh {lma_shape::Mesh mesh;std::vector<std::array<float,6>> colors;};
inline FlexMesh flexicubes(const std::vector<lma_sparse::Coord>& coords,const std::vector<float>& fields,int channels,int res,size_t max_triangles){
 using namespace lma_shape;using C=std::array<int64_t,3>;using namespace lma_flexicubes_tables;
 require(res>=2&&res<=1024&&(channels==53||channels==101)&&max_triangles>=1&&max_triangles<=1000000,"Invalid FlexiCubes profile");
 lma_sparse::coordinates(coords);require(!coords.empty()&&fields.size()==lma_sparse::bounded(coords.size(),size_t(channels)),"Invalid FlexiCubes fields");lma_sparse::finite(fields);
 constexpr int ep[12][2]={{0,1},{1,5},{4,5},{0,4},{2,3},{3,7},{6,7},{2,6},{2,0},{3,1},{7,5},{6,4}};
 auto corner=[](C p,int i){for(int a=0;a<3;a++)p[a]+=(i>>a)&1;return p;};
 struct Attr {std::array<float,10> values{};size_t count=0;};
 std::map<C,Attr> attributes;std::map<C,size_t> weights;
 for(size_t row=0;row<coords.size();row++){
  const auto& c=coords[row];require(c[0]==0&&c[1]>=0&&c[2]>=0&&c[3]>=0&&c[1]<res&&c[2]<res&&c[3]<res,"FlexiCubes coordinate outside grid");
  C p={c[1],c[2],c[3]};require(weights.emplace(p,row).second,"Repeated FlexiCubes cube");const float* f=fields.data()+row*channels;
  for(int i=0;i<8;i++){auto& v=attributes[corner(p,i)];v.count++;v.values[0]+=f[i]-1.f/res;for(int a=0;a<3;a++)v.values[1+a]+=f[8+i*3+a];if(channels==101)for(int a=0;a<6;a++)v.values[4+a]+=f[53+i*6+a];}
  require(attributes.size()<=2097152,"FlexiCubes vertex support budget exceeded");
 }
 std::set<C> candidates;
 for(auto& item:attributes){for(float& x:item.second.values)x/=float(item.second.count);if(item.second.values[0]<0)for(int i=0;i<8;i++){C p=item.first;bool inside=true;for(int a=0;a<3;a++){p[a]-=(i>>a)&1;inside=inside&&p[a]>=0&&p[a]<res;}if(inside)candidates.insert(p);}}
 require(candidates.size()<=2097152,"FlexiCubes candidate cube budget exceeded");
 auto attr=[&](const C& p){auto found=attributes.find(p);if(found!=attributes.end())return found->second.values;std::array<float,10> v{};v[0]=1;return v;};
 auto position=[&](const C& p,const std::array<float,10>& v){Point out{};for(int a=0;a<3;a++)out[a]=float(p[a])/res-.5f+float((1.-1e-8)/(res*2))*std::tanh(v[1+a]);return out;};
 auto sigmoid=[](float x){return x>=0?1.f/(1.f+std::exp(-x)):std::exp(x)/(1.f+std::exp(x));};
 struct Cube {C pos;int code;std::array<float,21> w{};std::array<int64_t,12> dual{};};
 std::vector<Cube> cubes;std::map<C,size_t> cube_index;
 for(const auto& p:candidates){int code=0;for(int i=0;i<8;i++)if(attr(corner(p,i))[0]<0)code|=1<<i;if(code==0||code==255)continue;
  Cube c;c.pos=p;c.code=code;c.dual.fill(-1);auto found=weights.find(p);if(found!=weights.end())std::copy_n(fields.data()+found->second*channels+32,21,c.w.begin());cube_index.emplace(p,cubes.size());cubes.push_back(c);}
 require(!cubes.empty(),"FlexiCubes field has no surface");
 std::vector<int> resolved(cubes.size());
 for(size_t i=0;i<cubes.size();i++){int code=cubes[i].code;auto check=check_table[code];if(check[0]==1){C adjacent=cubes[i].pos;for(int a=0;a<3;a++)adjacent[a]+=check[1+a];auto found=cube_index.find(adjacent);if(found!=cube_index.end()&&check_table[cubes[found->second].code][0]==1)code=check[4];}resolved[i]=code;}
 FlexMesh out;std::vector<float> gamma;
 using Edge=std::pair<C,C>;struct Incident {size_t cube;int edge;};std::map<Edge,std::vector<Incident>> edge_map;
 for(size_t i=0;i<cubes.size();i++)for(int e=0;e<12;e++){C a=corner(cubes[i].pos,ep[e][0]),b=corner(cubes[i].pos,ep[e][1]);if((attr(a)[0]<0)!=(attr(b)[0]<0))edge_map[{a,b}].push_back({i,e});}
 for(int count=1;count<=4;count++)for(size_t i=0;i<cubes.size();i++)if(num_vd_table[resolved[i]]==count){auto& c=cubes[i];
  for(int group=0;group<count;group++){
   uint32_t id=uint32_t(out.mesh.vertices.size());require(id<3000000,"FlexiCubes dual vertex budget exceeded");Point sum{};std::array<float,6> color{};float total=0;
   for(int k=0;k<7;k++){int e=dmc_table[resolved[i]][group][k];if(e<0)continue;require(e<12&&c.dual[e]<0,"Invalid DMC dual assignment");c.dual[e]=id;
    int ia=ep[e][0],ib=ep[e][1];C ca=corner(c.pos,ia),cb=corner(c.pos,ib);auto a=attr(ca),b=attr(cb);require((a[0]<0)!=(b[0]<0),"DMC table referenced a non-crossing edge");
    float s0=a[0]*(std::tanh(c.w[12+ia])*.99f+1.f),s1=b[0]*(std::tanh(c.w[12+ib])*.99f+1.f),denominator=s1-s0;
    require(std::isfinite(denominator)&&denominator!=0,"Degenerate FlexiCubes edge");float beta=std::tanh(c.w[e])*.99f+1.f;
    auto pa=position(ca,a),pb=position(cb,b);for(int axis=0;axis<3;axis++)sum[axis]+=((pa[axis]*s1+pb[axis]*(-s0))/denominator)*beta;
    if(channels==101)for(int axis=0;axis<6;axis++)color[axis]+=((sigmoid(a[4+axis])*s1+sigmoid(b[4+axis])*(-s0))/denominator)*beta;
    total+=beta;
   }
   require(total>0,"Empty FlexiCubes dual support");for(float& x:sum){x/=total;require(std::isfinite(x),"Nonfinite FlexiCubes vertex");}for(float& x:color){x/=total;require(std::isfinite(x),"Nonfinite FlexiCubes attribute");}
   out.mesh.vertices.push_back(sum);if(channels==101)out.colors.push_back(color);gamma.push_back(sigmoid(c.w[20])*.99f+.005f);
  }
 }
 std::vector<std::array<uint32_t,4>> positive,negative;
 for(const auto& item:edge_map){const auto& inc=item.second;if(inc.size()!=4)continue;std::array<uint32_t,4> q{};for(int i=0;i<4;i++){auto id=cubes[inc[i].cube].dual[inc[i].edge];require(id>=0&&size_t(id)<gamma.size(),"Unassigned FlexiCubes edge");q[i]=uint32_t(id);}
  if(attr(item.first.first)[0]>0)positive.push_back({q[0],q[1],q[3],q[2]});else negative.push_back({q[2],q[3],q[1],q[0]});}
 positive.insert(positive.end(),negative.begin(),negative.end());require(positive.size()<=max_triangles/2,"FlexiCubes triangle budget exceeded");
 constexpr int split1[6]={0,1,2,0,2,3},split2[6]={0,1,3,3,1,2};for(const auto& q:positive){const int* split=gamma[q[0]]*gamma[q[2]]>gamma[q[1]]*gamma[q[3]]?split1:split2;for(int i=0;i<6;i++)out.mesh.indices.push_back(q[split[i]]);}
 require(!out.mesh.indices.empty(),"FlexiCubes has no connected surface; no replacement mesh was produced");return out;
}
}

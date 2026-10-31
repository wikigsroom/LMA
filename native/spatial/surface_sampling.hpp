#pragma once
#include "mesh.hpp"
namespace lma_spatial {
using PrecisePoint=std::array<double,3>;
struct SharpSurface { std::vector<PrecisePoint> normals; std::vector<std::array<uint32_t,2>> edges; std::vector<double> cumulative; };
inline double precise_dot(const PrecisePoint& a,const PrecisePoint& b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
inline PrecisePoint precise_direction(Point a,Point b){return {double(a[0])-b[0],double(a[1])-b[1],double(a[2])-b[2]};}
inline PrecisePoint unit(PrecisePoint p){double n=std::sqrt(precise_dot(p,p));if(n>1e-15)for(double& v:p)v/=n;else p={0,0,0};return p;}
inline SharpSurface sharp_surface(const Mesh& mesh){
 require(!mesh.vertices.empty()&&mesh.vertices.size()<=3000000&&mesh.indices.size()%3==0&&mesh.indices.size()/3<=1000000,"Invalid sharp surface budget");
 SharpSurface result;result.normals.resize(mesh.vertices.size());std::vector<PrecisePoint> faces;faces.reserve(mesh.indices.size()/3);
 // Trimesh uses corner-angle weighted vertex normals. Keeping shared mesh
 // indices is necessary: triangle-local flat normals would hide every edge.
 for(size_t f=0;f<mesh.indices.size();f+=3){
  Point v[3]={mesh.vertices.at(mesh.indices[f]),mesh.vertices.at(mesh.indices[f+1]),mesh.vertices.at(mesh.indices[f+2])};
  auto a=precise_direction(v[1],v[0]),b=precise_direction(v[2],v[0]);auto normal=unit({a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]});faces.push_back(normal);
  for(int j=0;j<3;j++){auto u=unit(precise_direction(v[(j+1)%3],v[j])),w=unit(precise_direction(v[(j+2)%3],v[j]));double angle=std::acos(std::clamp(precise_dot(u,w),-1.,1.));for(int k=0;k<3;k++)result.normals[mesh.indices[f+j]][k]+=normal[k]*angle;}
 }
 for(auto& normal:result.normals)normal=unit(normal);
 std::vector<double> score(mesh.vertices.size(),1.);
 // Preserve the publisher's advanced-index assignment, including its last
 // repeated-index write per corner pass, rather than inventing a scatter-min.
 for(int j=0;j<3;j++){auto previous=score;for(size_t f=0;f<faces.size();f++){auto v=mesh.indices[f*3+j];score[v]=std::min(previous[v],precise_dot(result.normals[v],faces[f]));}}
 double total=0;
 for(int j=0;j<3;j++)for(size_t f=0;f<faces.size();f++){uint32_t a=mesh.indices[f*3+j],b=mesh.indices[f*3+(j+1)%3];if(score[a]>=.985||score[b]>=.985)continue;
  auto delta=precise_direction(mesh.vertices[a],mesh.vertices[b]);double length=std::sqrt(precise_dot(delta,delta));if(length<=1e-15)continue;
  total+=length;result.edges.push_back({a,b});result.cumulative.push_back(total);
 }
 require(std::isfinite(total)&&total>1e-12&&!result.edges.empty(),"Coarse mesh has no usable sharp edges; supply a connected coarse surface");return result;
}
inline float surface_half(float value){
 // SurfaceLoader rounds sampled positions through float16 before voxelisation.
 // Coordinates are bounded by mesh normalisation, so only finite half values
 // occur. nearbyint is not used because a caller can change the FP environment.
 require(std::isfinite(value)&&std::abs(value)<=1.001f,"Unnormalised sampled point");
 double magnitude=std::abs(double(value));if(magnitude==0)return value;
 int exponent=0;std::frexp(magnitude,&exponent);double quantum=std::ldexp(1.,std::max(-24,exponent-11));double q=magnitude/quantum,lo=std::floor(q),fraction=q-lo;
 if(fraction>.5||(fraction==.5&&std::fmod(lo,2.)!=0))lo+=1;
 return std::copysign(float(lo*quantum),value);
}
inline std::vector<Point> refine_surface(const Mesh& mesh,size_t samples,std::mt19937& random){
 require(samples>=2&&samples<=409600,"Refinement surface budget exceeded");auto edges=sharp_surface(mesh);size_t count=samples/2;
 auto result=sample_surface(mesh,samples-count,random);result.reserve(samples);std::uniform_real_distribution<double> uniform(0,1);
 // Selecting a uniform subset of the publisher's independent random pools
 // has the same distribution; avoid allocating its 819,200 intermediate rows.
 for(size_t i=0;i<count;i++){size_t index=size_t(std::upper_bound(edges.cumulative.begin(),edges.cumulative.end(),uniform(random)*edges.cumulative.back())-edges.cumulative.begin());require(index<edges.edges.size(),"Sharp edge sampler overflow");
  auto edge=edges.edges[index];double w=uniform(random);Point point{};for(int j=0;j<3;j++)point[j]=float(w*mesh.vertices[edge[0]][j]+(1-w)*mesh.vertices[edge[1]][j]);result.push_back(point);
 }
 for(auto& point:result)for(float& value:point)value=surface_half(value);return result;
}
}

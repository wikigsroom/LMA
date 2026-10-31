#pragma once
#include "fdg.hpp"
#include "lma_fdg_source.hpp"
namespace lma_spatial {
struct DualGridFields {std::vector<lma_sparse::Coord> coords;Floats vertices;std::vector<int64_t> flags;};
inline DualGridFields voxelize_dual_grid(const Mesh& mesh,int grid){
 require(grid>=8&&grid<=1024&&mesh.vertices.size()<=3000000&&mesh.indices.size()%3==0&&mesh.indices.size()/3<=300000,"FDG mesh input exceeds phone bounds");
 Floats vertices;vertices.reserve(mesh.vertices.size()*3);for(auto p:mesh.vertices)for(float x:p){require(std::isfinite(x)&&x>-.5f&&x<.5f,"FDG input must be inside the declared normalized cube");vertices.push_back(x+.5f);}
 std::vector<int> faces;faces.reserve(mesh.indices.size());for(size_t f=0;f<mesh.indices.size();f+=3){
  for(int j=0;j<3;j++)require(mesh.indices[f+j]<mesh.vertices.size(),"FDG mesh index out of bounds");
  auto a=mesh.vertices[mesh.indices[f]],b=mesh.vertices[mesh.indices[f+1]],c=mesh.vertices[mesh.indices[f+2]];auto n=cross(subtract(b,a),subtract(c,a));
  if(dot(n,n)>1e-24f)for(int j=0;j<3;j++)faces.push_back(int(mesh.indices[f+j]));
 }
 require(!faces.empty(),"FDG source mesh has no nondegenerate faces");float size[3]={1.f/grid,1.f/grid,1.f/grid};int range[6]={0,0,0,grid,grid,grid};
 auto fields=lma_fdg_source::convert(vertices.data(),faces.data(),int(faces.size()/3),size,range,1,.2f,.01f);
 require(!fields.coords.empty()&&fields.coords.size()<=lma_sparse::point_limit,"FDG source produced empty or oversized support");DualGridFields out;
 for(size_t i=0;i<fields.coords.size();i++){
  const auto& c=fields.coords[i];require(c.x>=0&&c.y>=0&&c.z>=0&&c.x<grid&&c.y<grid&&c.z<grid,"FDG source produced an out-of-grid cell");out.coords.push_back({0,c.x,c.y,c.z});
  const auto& p=fields.vertices[i];const auto& flags=fields.intersected[i];float point[3]={p.x,p.y,p.z};int coord[3]={c.x,c.y,c.z};bool edge[3]={flags.x,flags.y,flags.z};
  for(int j=0;j<3;j++){require(std::isfinite(point[j]),"Nonfinite FDG constrained solve");out.vertices.push_back(std::clamp(point[j]*grid-coord[j],0.f,1.f));out.flags.push_back(edge[j]?1:0);}
 }
 lma_sparse::coordinates(out.coords);return out;
}
}

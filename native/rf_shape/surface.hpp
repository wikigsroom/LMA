#pragma once
#include "geometry.hpp"
#include "lewiner.h"
#include "diso_cpu.hpp"
#include <functional>
#include <set>
#include <numeric>

namespace lma_shape {
inline float surface_fp16(float value){
 require(std::isfinite(value)&&std::abs(value)<=65504,"Field exceeds finite FP16 source profile");double a=std::abs(double(value));if(a==0)return value;int e=0;std::frexp(a,&e);double quantum=std::ldexp(1.,std::max(-24,e-11)),q=a/quantum,lo=std::floor(q),f=q-lo;if(f>.5||(f==.5&&std::fmod(lo,2.)!=0))lo++;return std::copysign(float(lo*quantum),value);
}
inline Mesh lewiner(const std::vector<float>& field,int n,float box,int divisor,size_t triangles){
 require(n>=2&&n<=256&&field.size()==size_t(n)*n*n,"Lewiner field budget exceeded");std::vector<float> reordered=field;for(float v:field)require(std::isfinite(v),"Lewiner requires a finite field");
 MarchingCubes mc(n,n,n);mc.set_ext_data(reordered.data());mc.init_all();mc.run(0);require(mc.ntrigs()>0&&size_t(mc.ntrigs())<=triangles&&mc.nverts()<=2000000,"Lewiner produced no surface or exceeded selected limits");Mesh result;
 // skimage passes its C-contiguous volume directly to a fast-X C++ cell,
 // then flips returned coordinate columns. Preserve that case orientation.
 for(int i=0;i<mc.nverts();i++){auto v=mc.vert(i);result.vertices.push_back({v->z*2*box/divisor-box,v->y*2*box/divisor-box,v->x*2*box/divisor-box});}
 // skimage's default gradient_direction=descent reverses the original C++
 // winding. The actual table/case and interpolation algorithm is retained.
 for(int i=0;i<mc.ntrigs();i++){auto f=mc.trig(i);result.indices.insert(result.indices.end(),{uint32_t(f->v3),uint32_t(f->v2),uint32_t(f->v1)});}return result;
}
inline Mesh diso_surface(const std::vector<float>& field,int n,float box,int divisor,size_t triangles){
 namespace d=lma_dmc_cpu;require(n>=2&&n<=256&&field.size()==size_t(n)*n*n,"DISO field budget exceeded");int side=n+2;std::vector<float> data(size_t(side)*side*side,1.f);
 for(int x=0;x<n;x++)for(int y=0;y<n;y++)for(int z=0;z<n;z++)data[(size_t(x+1)*side+y+1)*side+z+1]=field[(size_t(x)*n+y)*n+z];
 d::CUDualMC<float,int> model{};model.dims[0]=model.dims[1]=model.dims[2]=side;model.n_cells=side*side*side;
 std::vector<int> cells(size_t(model.n_cells)+1,0);model.first_cell_used=cells.data();
 for(d::thread_index=0;d::thread_index<model.n_cells;d::thread_index++)d::count_used_cells_kernel(model,data.data(),0.f);
 auto scan=[](std::vector<int>& a){int sum=0;for(auto& v:a){int before=sum;require(v>=0&&sum<=4000000-v,"DISO allocation budget exceeded");sum+=v;v=before;}};scan(cells);model.n_used_cells=cells.back();require(model.n_used_cells>0&&model.n_used_cells<=2000000,"DISO active-cell budget exceeded or empty field");
 std::vector<int> used(model.n_used_cells),first_edge(size_t(model.n_used_cells)+1,0),first_patch(size_t(model.n_used_cells)+1,0);std::vector<uint8_t> codes(model.n_used_cells);model.used_cell_index=used.data();model.used_to_first_mc_vert=first_edge.data();model.used_to_first_mc_patch=first_patch.data();model.used_cell_code=codes.data();
 for(d::thread_index=0;d::thread_index<model.n_cells;d::thread_index++)d::index_used_cells_kernel(model);
 for(d::thread_index=0;d::thread_index<model.n_used_cells;d::thread_index++)d::count_cell_mc_verts_kernel(model,data.data(),0.f);scan(first_edge);model.n_quads=first_edge.back();require(size_t(model.n_quads)*2<=triangles,"DISO exceeds selected triangle limit");
 std::vector<int> edge_cell(model.n_quads);std::vector<uint8_t> edge_type(model.n_quads);std::vector<d::Quad<int>> quads(model.n_quads);model.mc_vert_to_cell=edge_cell.data();model.mc_vert_type=edge_type.data();model.quads=quads.data();
 for(d::thread_index=0;d::thread_index<model.n_used_cells;d::thread_index++)d::index_cell_mc_verts_kernel(model,data.data(),0.f);
 for(d::thread_index=0;d::thread_index<model.n_used_cells;d::thread_index++)d::count_cell_patches_kernel(model,data.data(),0.f);scan(first_patch);model.n_verts=first_patch.back();require(model.n_verts>0&&model.n_verts<=2000000,"DISO vertex budget exceeded");std::vector<d::Vertex<float>> vertices(model.n_verts);model.verts=vertices.data();
 for(d::thread_index=0;d::thread_index<model.n_used_cells;d::thread_index++)d::create_dmc_verts_kernel(model,data.data(),static_cast<const d::Vertex<float>*>(nullptr),0.f);
 for(d::thread_index=0;d::thread_index<model.n_quads;d::thread_index++)d::create_quads_kernel(model);
 Mesh result;for(auto v:vertices){require(std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z),"DISO encountered a nonfinite boundary surface");result.vertices.push_back({(v.x-1)*2*box/divisor-box,(v.y-1)*2*box/divisor-box,(v.z-1)*2*box/divisor-box});}
 auto score=[&](const std::array<uint32_t,3>& t){float out=-1;for(int i=0;i<3;i++){auto a=subtract(result.vertices[t[(i+1)%3]],result.vertices[t[i]]),b=subtract(result.vertices[t[(i+2)%3]],result.vertices[t[i]]);float na=std::max(std::sqrt(dot(a,a)),1e-12f),nb=std::max(std::sqrt(dot(b,b)),1e-12f);out=std::max(out,dot(a,b)/(na*nb));}return out;};
 std::vector<std::array<uint32_t,3>> first,second;
 for(auto q:quads){uint32_t a=uint32_t(q.i),b=uint32_t(q.j),c=uint32_t(q.k),e=uint32_t(q.l);for(auto v:{a,b,c,e})require(v<result.vertices.size(),"DISO quad index outside source topology");
  std::array<uint32_t,3> a1={a,b,e},a2={b,c,e},b1={a,b,c},b2={a,c,e};bool one=std::max(score(a1),score(a2))<std::max(score(b1),score(b2));auto& dest=one?first:second;dest.push_back(one?a1:b1);dest.push_back(one?a2:b2);}
 // Same angle decision and grouped face order as diso.DiffDMC.forward; the
 // TripoSG Flash caller reverses its triangle winding after extraction.
 for(auto* list:{&first,&second})for(auto f:*list)result.indices.insert(result.indices.end(),{f[2],f[1],f[0]});return result;
}
using SurfaceQuery=std::function<std::vector<float>(const std::vector<float>&)>;
struct AdaptiveField {std::vector<float> values;int size=0,divisor=0;size_t queried=0;};
inline std::vector<uint8_t> surface_dilate(std::vector<uint8_t> mask,int n,int times){
 for(int t=0;t<times;t++){std::vector<uint8_t> out(mask.size(),0);for(int x=0;x<n;x++)for(int y=0;y<n;y++)for(int z=0;z<n;z++)if(mask[(size_t(x)*n+y)*n+z])for(int a=std::max(0,x-1);a<=std::min(n-1,x+1);a++)for(int b=std::max(0,y-1);b<=std::min(n-1,y+1);b++)for(int c=std::max(0,z-1);c<=std::min(n-1,z+1);c++)out[(size_t(a)*n+b)*n+c]=1;mask.swap(out);}return mask;
}
inline std::vector<uint8_t> flash_band(const std::vector<float>& values,int n){
 require(values.size()==size_t(n)*n*n,"Flash volume shape mismatch");std::vector<uint8_t> mask(values.size());auto sign=[](float v){return int(v>0)-int(v<0);};
 for(int x=0;x<n;x++)for(int y=0;y<n;y++)for(int z=0;z<n;z++){size_t id=(size_t(x)*n+y)*n+z;float v=values[id];bool edge=false;
  for(int axis=0;axis<3;axis++)for(int delta:{-1,1}){int xyz[3]={x,y,z};xyz[axis]=std::clamp(xyz[axis]+delta,0,n-1);float other=values[(size_t(xyz[0])*n+xyz[1])*n+xyz[2]];if(other<=-9000)other=v;edge|=sign(v)!=sign(other);}
  mask[id]=uint8_t((v>-9000&&edge)||std::abs(v)<.95f);
 }return mask;
}
inline AdaptiveField adaptive_field(const SurfaceQuery& query,const std::string& mode,int depth,int dense_depth,int chunk,float box){
 require((mode=="publisher_octree"||mode=="publisher_flash")&&depth>=5&&depth<=8&&dense_depth>=3&&dense_depth<=depth&&chunk>=1&&chunk<=4096,"Invalid original adaptive surface profile");bool flash=mode=="publisher_flash";AdaptiveField field;int initial=flash?std::min(depth,6):dense_depth;
 std::vector<int> resolutions;for(int d=initial;d<=depth;d++)resolutions.push_back(flash?((1<<initial)-1)*(1<<(d-initial)):(1<<d));field.size=flash?resolutions[0]+1:resolutions[0];field.divisor=1<<depth;
 auto evaluate=[&](const std::vector<size_t>& ids,int n,int denominator,bool half){std::vector<float> out;out.reserve(ids.size());for(size_t start=0;start<ids.size();start+=chunk){size_t count=std::min(size_t(chunk),ids.size()-start);std::vector<float> points(count*3);for(size_t j=0;j<count;j++){size_t id=ids[start+j];int xyz[3]={int(id/(size_t(n)*n)),int((id/n)%n),int(id%n)};for(int a=0;a<3;a++){float v=float(xyz[a])*2*box/denominator-box;points[j*3+a]=half?surface_fp16(v):v;}}auto values=query(points);require(values.size()==count,"Adaptive query count mismatch");for(float v:values){require(std::isfinite(v),"Nonfinite adaptive query");out.push_back(half?surface_fp16(v):v);}}field.queried+=ids.size();return out;};
 size_t count=size_t(field.size)*field.size*field.size;std::vector<size_t> all(count);std::iota(all.begin(),all.end(),0);field.values=evaluate(all,field.size,flash?resolutions[0]:field.size-1,!flash);
 for(size_t stage=1;stage<resolutions.size();stage++){int old=field.size,n=flash?resolutions[stage]+1:resolutions[stage];require(n<=256,"Adaptive volume exceeds phone application guard");std::vector<uint8_t> mask;
  if(flash){mask=flash_band(field.values,old);int expand=stage+1==resolutions.size()?0:1;mask=surface_dilate(std::move(mask),old,2*expand);std::vector<uint8_t> next(size_t(n)*n*n,0);for(int x=0;x<old;x++)for(int y=0;y<old;y++)for(int z=0;z<old;z++)if(mask[(size_t(x)*old+y)*old+z])next[(size_t(x*2)*n+y*2)*n+z*2]=1;mask=surface_dilate(std::move(next),n,2-expand);}
  else{mask.assign(field.values.size(),0);for(int x=1;x<old-1;x++)for(int y=1;y<old-1;y++)for(int z=1;z<old-1;z++){float v=field.values[(size_t(x)*old+y)*old+z],s=surface_fp16(float(1/(1+std::exp(-double(v)))));float b=surface_fp16(surface_fp16(s*2)-1);mask[(size_t(x)*old+y)*old+z]=std::abs(b)<1;}
   mask=surface_dilate(std::move(mask),old,old<512?2:1);std::vector<uint8_t> next(size_t(n)*n*n,0);for(int x=0;x<old;x++)for(int y=0;y<old;y++)for(int z=0;z<old;z++)if(mask[(size_t(x)*old+y)*old+z])for(int a=0;a<2;a++)for(int b=0;b<2;b++)for(int c=0;c<2;c++)next[(size_t(x*2+a)*n+y*2+b)*n+z*2+c]=1;mask.swap(next);}
  std::vector<size_t> ids;for(size_t i=0;i<mask.size();i++)if(mask[i])ids.push_back(i);require(!ids.empty(),"Adaptive source found no surface candidates");
  std::vector<float> next(size_t(n)*n*n,flash?-10000.f:0.f);if(!flash)for(int x=0;x<n;x++)for(int y=0;y<n;y++)for(int z=0;z<n;z++)next[(size_t(x)*n+y)*n+z]=field.values[(size_t(x/2)*old+y/2)*old+z/2];
  auto selected=evaluate(ids,n,flash?resolutions[stage]:n,!flash);
  for(size_t i=0;i<ids.size();i++)next[ids[i]]=selected[i];field.values.swap(next);field.size=n;
 }
 if(flash)for(auto& v:field.values){if(v==-10000.f)v=std::numeric_limits<float>::quiet_NaN();else v=-v/float(1<<depth);}return field;
}
inline Mesh adaptive_surface(const SurfaceQuery& query,const std::string& mode,int depth,int dense,int chunk,float box,size_t triangles){
 auto volume=adaptive_field(query,mode,depth,dense,chunk,box);return mode=="publisher_flash"?diso_surface(volume.values,volume.size,box,volume.divisor,triangles):lewiner(volume.values,volume.size,box,volume.divisor,triangles);
}
}

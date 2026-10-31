#pragma once
#include "texture.hpp"
#include "sparse.hpp"
namespace lma_spatial {
// CPU port of the fixed FlexGEMM trilinear map: voxel centers, floor(q-.5),
// x-fast neighbor enumeration, renormalize only present in-bounds neighbors.
// Source CUDA kernel blob 165c09863c4db66137fc460c62008a08ff95c501.
class MaterialVolume {
 std::unordered_map<lma_sparse::Coord,size_t,lma_sparse::Hash> rows_;const Floats& values_;int grid_,channels_;
public:
 MaterialVolume(const std::vector<lma_sparse::Coord>& coords,const Floats& values,int grid,int channels):values_(values),grid_(grid),channels_(channels){
  lma_sparse::coordinates(coords);require(!coords.empty()&&grid>=8&&grid<=4096&&channels>=5&&channels<=64&&values.size()==coords.size()*channels,"Invalid material volume");
  for(size_t i=0;i<coords.size();i++){for(int a=0;a<4;a++)require(coords[i][a]>=0&&coords[i][a]<(a?grid:1),"Material volume must have one in-grid batch");rows_.emplace(coords[i],i);}for(float x:values)require(std::isfinite(x),"Nonfinite material volume");
 }
 std::array<float,6> sample(Point point)const{
  float q[3];int base[3];for(int a=0;a<3;a++){require(std::isfinite(point[a])&&std::abs(point[a])<2,"Invalid volume query");q[a]=(point[a]+.5f)*grid_;base[a]=int(std::floor(q[a]-.5f));}
  std::array<float,6> result{};float sum=0;for(int k=0;k<8;k++){
   lma_sparse::Coord c={0,base[0]+(k&1),base[1]+((k>>1)&1),base[2]+((k>>2)&1)};bool valid=true;for(int a=1;a<4;a++)valid=valid&&c[a]>=0&&c[a]<grid_;if(!valid)continue;
   auto row=rows_.find(c);if(row==rows_.end())continue;float weight=1;for(int a=0;a<3;a++)weight*=1-std::abs(q[a]-c[a+1]-.5f);sum+=weight;for(int a=0;a<std::min(channels_,6);a++)result[a]+=weight*values_[row->second*channels_+a];
  }for(auto& x:result)x/=std::max(sum,1e-12f);if(channels_==5)result[5]=sum>0?1:0;return result;
 }
};
inline BakedMaterial bake_volume(const Atlas& atlas,const MaterialVolume& volume){
 require(atlas.width>=1&&atlas.height>=1&&atlas.width<=4096&&atlas.height<=4096&&atlas.uv.size()==atlas.mesh.vertices.size(),"Invalid volume atlas");size_t count=size_t(atlas.width)*atlas.height;BakedMaterial r;r.albedo.assign(count*4,255);r.mr.assign(count*4,255);std::vector<uint8_t> valid(count);uint64_t budget=250000000;
 for(size_t f=0;f<atlas.mesh.indices.size();f+=3){uint32_t ids[3];std::array<std::array<float,3>,3> uv;for(int k=0;k<3;k++){ids[k]=atlas.mesh.indices[f+k];require(ids[k]<atlas.mesh.vertices.size(),"Volume atlas index out of bounds");uv[k]={atlas.uv[ids[k]][0]*atlas.width,atlas.uv[ids[k]][1]*atlas.height,0};}
  raster_triangle(uv,atlas.width,atlas.height,budget,[&](int x,int y,std::array<float,3> bary){Point p={};for(int k=0;k<3;k++)p=add(p,scale(atlas.mesh.vertices[ids[k]],bary[k]));auto material=volume.sample(p);size_t at=size_t(y)*atlas.width+x;auto byte=[](float x){return uint8_t(std::round(std::clamp(x,0.f,1.f)*255));};for(int c=0;c<3;c++)r.albedo[at*4+c]=byte(material[c]);r.albedo[at*4+3]=255;r.mr[at*4]=255;r.mr[at*4+1]=byte(material[4]);r.mr[at*4+2]=byte(material[3]);valid[at]=1;});
 }
 std::queue<uint32_t> frontier;for(uint32_t i=0;i<count;i++)if(valid[i]){frontier.push(i);r.covered++;}require(!frontier.empty(),"No volume atlas coverage");
 while(!frontier.empty()){auto at=frontier.front();frontier.pop();int x=at%atlas.width,y=at/atlas.width;const int dx[4]={-1,1,0,0},dy[4]={0,0,-1,1};for(int k=0;k<4;k++){int xx=x+dx[k],yy=y+dy[k];if(xx<0||yy<0||xx>=atlas.width||yy>=atlas.height)continue;uint32_t to=yy*atlas.width+xx;if(valid[to])continue;valid[to]=1;for(int c=0;c<4;c++){r.albedo[to*4+c]=r.albedo[at*4+c];r.mr[to*4+c]=r.mr[at*4+c];}frontier.push(to);}}
 return r;
}
}

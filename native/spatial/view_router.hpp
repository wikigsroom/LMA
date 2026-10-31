#pragma once
#include "sparse.hpp"
#include <map>
#include <algorithm>
#include <cmath>
namespace lma_spatial {
// Fixed UniForge source router, B=1. Preserve confidence-stable filtering,
// bounded component label propagation and direct-only one-hop inheritance.
inline std::vector<int64_t> route_views(const std::vector<float>& points,const std::vector<float>& confidence,
 const std::vector<uint8_t>& mask,int views,int grid,const std::vector<lma_sparse::Coord>& targets){
 using lma_sparse::require;require((grid==32||grid==64)&&views>=1&&views<=8,"Invalid UniForge view router geometry");
 constexpr size_t pixels=448*448;size_t total=pixels*size_t(views),volume=size_t(grid)*grid*grid;
 require(points.size()==total*3&&confidence.size()==total&&mask.size()==total,"UniForge point/confidence/mask shape mismatch");
 lma_sparse::coordinates(targets);for(auto c:targets)require(c[0]==0&&c[1]<grid&&c[2]<grid&&c[3]<grid,"UniForge target is outside one-batch query grid");
 struct Entry {int patch;int count=0;float confidence=0;};
 struct Summary {int view=-1;int count=0;float confidence=0;};
 std::vector<Summary> direct(volume);int patch_pixels=448/grid;
 auto better=[](const Summary& a,const Summary& b){
  if(a.count!=b.count)return a.count>b.count;
  if((a.view==0)!=(b.view==0))return a.view==0;
  if(a.confidence!=b.confidence)return a.confidence>b.confidence;
  return a.view<b.view;
 };
 for(int view=0;view<views;view++){
  std::vector<size_t> valid;valid.reserve(pixels);
  for(size_t p=0;p<pixels;p++){
   size_t row=size_t(view)*pixels+p;bool ok=mask[row]&&std::isfinite(confidence[row]);
   for(int axis=0;axis<3;axis++){float x=points[row*3+axis];ok=ok&&std::isfinite(x)&&x>=-.5f&&x<.5f;}
   if(ok)valid.push_back(p);
  }
  std::stable_sort(valid.begin(),valid.end(),[&](size_t a,size_t b){return confidence[size_t(view)*pixels+a]>confidence[size_t(view)*pixels+b];});
  valid.resize(size_t(std::ceil(double(valid.size())*.95)));
  // Sorting by (voxel,patch,pixel) restores the source stable key order.
  struct Pixel {int voxel;int patch;size_t pixel;};std::vector<Pixel> selected;selected.reserve(valid.size());
  for(auto p:valid){size_t row=size_t(view)*pixels+p;int xyz[3];for(int a=0;a<3;a++){xyz[a]=int(std::floor((points[row*3+a]+.5f)*grid));require(xyz[a]>=0&&xyz[a]<grid,"Rounded UniForge point falls outside the routing grid");}
   selected.push_back({(xyz[0]*grid+xyz[1])*grid+xyz[2],int((p/448)/patch_pixels)*grid+int((p%448)/patch_pixels),p});}
  std::sort(selected.begin(),selected.end(),[](const Pixel& a,const Pixel& b){return std::tie(a.voxel,a.patch,a.pixel)<std::tie(b.voxel,b.patch,b.pixel);});
  for(size_t begin=0;begin<selected.size();){
   size_t end=begin+1;while(end<selected.size()&&selected[end].voxel==selected[begin].voxel)end++;
   std::vector<Entry> entries;for(size_t j=begin;j<end;j++){
    const auto& pixel=selected[j];if(entries.empty()||entries.back().patch!=pixel.patch)entries.push_back({pixel.patch,0,0});
    entries.back().count++;entries.back().confidence+=confidence[size_t(view)*pixels+pixel.pixel];
   }
   std::map<int,int> patch_rows;std::vector<int> labels(entries.size());for(size_t j=0;j<entries.size();j++){patch_rows[entries[j].patch]=int(j);labels[j]=int(j);}
   for(int step=0;step<64;step++){
    auto next=labels;
    for(size_t j=0;j<entries.size();j++){
     int y=entries[j].patch/grid,x=entries[j].patch%grid;
     for(int dy=-1;dy<=1;dy++)for(int dx=-1;dx<=1;dx++)if(x+dx>=0&&x+dx<grid&&y+dy>=0&&y+dy<grid){
      auto row=patch_rows.find((y+dy)*grid+x+dx);if(row!=patch_rows.end())next[j]=std::min(next[j],labels[size_t(row->second)]);
     }
    }
    auto jumped=next;for(size_t j=0;j<next.size();j++)jumped[j]=next[size_t(next[j])];
    if(jumped==labels)break;labels=std::move(jumped);
   }
   std::vector<int> counts(entries.size());std::vector<float> sums(entries.size());
   for(size_t j=0;j<entries.size();j++){counts[size_t(labels[j])]+=entries[j].count;sums[size_t(labels[j])]+=entries[j].confidence;}
   int chosen=-1;for(size_t j=0;j<entries.size();j++)if(labels[j]==int(j)){
    if(chosen<0||counts[j]>counts[size_t(chosen)]||(counts[j]==counts[size_t(chosen)]&&sums[j]/counts[j]>sums[size_t(chosen)]/counts[size_t(chosen)]))chosen=int(j);
   }
   require(chosen>=0,"UniForge router has no component root");Summary value{view,counts[size_t(chosen)],sums[size_t(chosen)]/counts[size_t(chosen)]};
   auto& old=direct[size_t(selected[begin].voxel)];if(old.view<0||better(value,old))old=value;begin=end;
  }
 }
 std::vector<int64_t> result;result.reserve(targets.size());
 for(auto c:targets){size_t key=(size_t(c[1])*grid+size_t(c[2]))*grid+size_t(c[3]);Summary value=direct[key];
  if(value.view<0)for(int dx=-1;dx<=1;dx++)for(int dy=-1;dy<=1;dy++)for(int dz=-1;dz<=1;dz++)if(dx||dy||dz){
   int x=int(c[1])+dx,y=int(c[2])+dy,z=int(c[3])+dz;if(x<0||x>=grid||y<0||y>=grid||z<0||z>=grid)continue;
   auto candidate=direct[(size_t(x)*grid+size_t(y))*grid+size_t(z)];if(candidate.view>=0&&(value.view<0||better(candidate,value)))value=candidate;
  }
  result.push_back(value.view>=0?value.view:0);
 }
 return result;
}
}

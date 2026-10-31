#pragma once
#include "cascade.hpp"
#include <queue>
namespace lma_spatial {
struct SupraCamera {std::array<double,16> external;std::array<double,9> intrinsic;};
inline SupraCamera supra_camera(const json& c){
 SupraCamera out{};
 if(c.contains("extrinsic")){
  auto e=c.at("extrinsic"),k=c.contains("projection_intrinsic")?c.at("projection_intrinsic"):c.at("intrinsic");require(e.is_array()&&e.size()==4&&k.is_array()&&k.size()==3,"Camera matrices must be 4x4 and 3x3");
  for(int i=0;i<4;i++){require(e[i].is_array()&&e[i].size()==4,"Invalid camera extrinsic");for(int j=0;j<4;j++)out.external[i*4+j]=e[i][j].get<double>();}
  for(int i=0;i<3;i++){require(k[i].is_array()&&k[i].size()==3,"Invalid camera intrinsic");for(int j=0;j<3;j++)out.intrinsic[i*3+j]=k[i][j].get<double>();}
 }else{
  double distance=c.at("distance"),fov=c.at("camera_angle_x"),scale=c.value("mesh_scale",1.);require(distance>0&&distance<=100&&fov>.01&&fov<3.1&&scale>0&&scale<=100,"Invalid canonical camera");
  out.external={1,0,0,0,0,-1,0,0,0,0,-1,distance*scale,0,0,0,1};double f=.5/std::tan(fov*.5);out.intrinsic={f,0,.5,0,f,.5,0,0,1};
 }
 for(double v:out.external)require(std::isfinite(v),"Nonfinite camera");for(double v:out.intrinsic)require(std::isfinite(v),"Nonfinite camera");
 require(std::abs(out.external[12])+std::abs(out.external[13])+std::abs(out.external[14])+std::abs(out.external[15]-1)<1e-6,"Use a rigid world-to-camera matrix");
 for(int i=0;i<3;i++)for(int j=0;j<3;j++){double v=0;for(int a=0;a<3;a++)v+=out.external[i*4+a]*out.external[j*4+a];require(std::abs(v-(i==j))<1e-5,"Camera rotation is not orthonormal");}
 require(out.intrinsic[0]>0&&out.intrinsic[4]>0&&std::abs(out.intrinsic[3])+std::abs(out.intrinsic[6])+std::abs(out.intrinsic[7])+std::abs(out.intrinsic[8]-1)<1e-8,"Use normalized pinhole intrinsics");return out;
}
inline std::array<double,3> camera_point(const SupraCamera& camera,std::array<double,3> point){std::array<double,3> result;for(int a=0;a<3;a++){result[a]=camera.external[a*4+3];for(int b=0;b<3;b++)result[a]+=camera.external[a*4+b]*point[b];}return result;}
inline std::array<double,2> camera_uv(const SupraCamera& camera,std::array<double,3> point){auto v=camera_point(camera,point);double z=std::max(v[2],1e-8);return {(camera.intrinsic[0]*v[0]+camera.intrinsic[1]*v[1]+camera.intrinsic[2]*v[2])/z,(camera.intrinsic[4]*v[1]+camera.intrinsic[5]*v[2])/z};}
inline std::vector<uint8_t> supra_visible(const std::vector<lma_sparse::Coord>& coords,const std::vector<uint8_t>& alpha,const SupraCamera& camera,int size=1024,int grid=1024){
 require(size>=8&&size<=1024&&grid>=8&&grid<=1024&&alpha.size()==size_t(size)*size,"Invalid observation image");lma_sparse::coordinates(coords);std::unordered_map<lma_sparse::Coord,int,lma_sparse::Hash> rows;for(size_t i=0;i<coords.size();i++)rows.emplace(coords[i],int(i));
 std::array<double,3> eye={0,0,0};for(int a=0;a<3;a++)for(int b=0;b<3;b++)eye[a]-=camera.external[b*4+a]*camera.external[b*4+3];
 std::vector<int> owners(size_t(size)*size,-1);Floats depths(owners.size(),std::numeric_limits<float>::quiet_NaN());size_t work=0,trusted=0;
 for(int y=0;y<size;y++)for(int x=0;x<size;x++){
  bool good=true;for(int yy=-2;yy<=2;yy++)for(int xx=-2;xx<=2;xx++)good=good&&alpha[size_t(std::clamp(y+yy,0,size-1))*size+std::clamp(x+xx,0,size-1)]>=254;if(!good)continue;trusted++;
  double cy=((y+.5)/size-camera.intrinsic[5])/camera.intrinsic[4],cx=((x+.5)/size-camera.intrinsic[2]-camera.intrinsic[1]*cy)/camera.intrinsic[0];std::array<double,3> d;for(int a=0;a<3;a++)d[a]=camera.external[a]*cx+camera.external[4+a]*cy+camera.external[8+a];
  double enter=-INFINITY,leave=INFINITY;bool intersects=true;for(int a=0;a<3;a++){if(std::abs(d[a])<1e-14){if(eye[a]<-.5||eye[a]>.5)intersects=false;}else{double t1=(-.5-eye[a])/d[a],t2=(.5-eye[a])/d[a];if(t1>t2)std::swap(t1,t2);enter=std::max(enter,t1);leave=std::min(leave,t2);}}if(!intersects||enter>leave||leave<0)continue;
  double start=std::max(enter,0.),epsilon=std::max(1e-12,std::abs(start)*1e-12);lma_sparse::Coord cell={0,0,0,0};int step[3];double delta[3],next[3];
  for(int a=0;a<3;a++){cell[a+1]=std::clamp(int(std::floor((eye[a]+(start+epsilon)*d[a]+.5)*grid)),0,grid-1);step[a]=d[a]>1e-14?1:d[a]<-1e-14?-1:0;delta[a]=step[a]?1./grid/std::abs(d[a]):INFINITY;next[a]=step[a]?(-.5+(cell[a+1]+(step[a]>0))/double(grid)-eye[a])/d[a]:INFINITY;}
  for(int i=0;i<3*grid+3;i++){
   require(++work<=500000000,"Observation ray work budget exceeded");auto hit=rows.find(cell);if(hit!=rows.end()){size_t pixel=size_t(y)*size+x;owners[pixel]=hit->second;std::array<double,3> p;for(int a=0;a<3;a++)p[a]=(cell[a+1]+.5)/grid-.5;double depth=camera_point(camera,p)[2];require(depth>0&&std::isfinite(depth),"First hit is behind the camera");depths[pixel]=float(depth);break;}
   double t=std::min({next[0],next[1],next[2]});if(!std::isfinite(t)||t>leave+1e-12)break;bool inside=true;double tolerance=1e-12*std::max(1.,std::abs(t));for(int a=0;a<3;a++)if(std::abs(next[a]-t)<=tolerance){cell[a+1]+=step[a];next[a]+=delta[a];inside=inside&&cell[a+1]>=0&&cell[a+1]<grid;}if(!inside)break;
  }
 }
 require(trusted>0,"Trusted alpha gate leaves no rays");std::vector<uint8_t> visible(coords.size(),0);for(int y=0;y<size;y++)for(int x=0;x<size;x++){size_t pixel=size_t(y)*size+x;if(owners[pixel]<0)continue;float lo=INFINITY,hi=-INFINITY;for(int yy=std::max(0,y-1);yy<=std::min(size-1,y+1);yy++)for(int xx=std::max(0,x-1);xx<=std::min(size-1,x+1);xx++){float z=depths[size_t(yy)*size+xx];if(std::isfinite(z)){lo=std::min(lo,z);hi=std::max(hi,z);}}if((hi-lo)/depths[pixel]<=.04f)visible[owners[pixel]]=1;}
 require(std::find(visible.begin(),visible.end(),1)!=visible.end(),"No trusted observed material surface");return visible;
}
inline int supra_key(const lma_sparse::Coord& c,int divisor=1){require(c[0]==0&&c[1]>=0&&c[2]>=0&&c[3]>=0&&c[1]/divisor<64&&c[2]/divisor<64&&c[3]/divisor<64,"SUPRA latent coordinate outside one batch/grid");return ((c[1]/divisor)*64+c[2]/divisor)*64+c[3]/divisor;}
inline Floats supra_messages(Floats raw,const std::vector<lma_sparse::Coord>& observed,const std::vector<lma_sparse::Coord>& surface,const std::vector<uint8_t>& visible,const std::vector<lma_sparse::Coord>& shape,const json& normalization){
 require(raw.size()==observed.size()*32&&surface.size()==visible.size(),"Invalid observation latent");std::vector<int> counts(64*64*64),seen(counts.size()),distance(counts.size(),-1);for(size_t i=0;i<surface.size();i++){int key=supra_key(surface[i],16);counts[key]++;if(visible[i])seen[key]++;}
 std::set<int> expected,actual;std::queue<int> frontier;for(int i=0;i<int(counts.size());i++)if(counts[i]){expected.insert(i);if(!seen[i]){distance[i]=0;frontier.push(i);}}for(auto c:shape)actual.insert(supra_key(c));require(actual.size()==shape.size()&&actual==expected,"Shape encoder support differs from floor(surface/16)");
 while(!frontier.empty()){int key=frontier.front();frontier.pop();int xyz[3]={key/4096,(key/64)%64,key%64},stride[3]={4096,64,1};for(int a=0;a<3;a++)for(int d:{-1,1})if(xyz[a]+d>=0&&xyz[a]+d<64){int q=key+d*stride[a];if(counts[q]&&distance[q]<0){distance[q]=distance[key]+1;frontier.push(q);}}}
 expected.clear();actual.clear();for(int i=0;i<int(seen.size());i++)if(seen[i])expected.insert(i);for(auto c:observed)actual.insert(supra_key(c));require(actual.size()==observed.size()&&actual==expected,"Observation encoder support differs from floor(visible_surface/16)");
 require(normalization.at("mean").size()==32&&normalization.at("std").size()==32,"Invalid partial normalization");Floats result(observed.size()*34);for(size_t i=0;i<observed.size();i++){int key=supra_key(observed[i]);for(int ch=0;ch<32;ch++){float mean=normalization.at("mean")[ch],sd=normalization.at("std")[ch];require(std::isfinite(mean)&&std::isfinite(sd)&&sd>0,"Invalid observation normalization");result[i*34+ch]=(raw[i*32+ch]-mean)/sd;}result[i*34+32]=float(seen[key])/counts[key];result[i*34+33]=float(distance[key]);require(distance[key]!=0,"Observed latent cannot have zero boundary distance");}return result;
}
}

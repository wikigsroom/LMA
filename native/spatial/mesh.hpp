#pragma once
#include "../rf_shape/geometry.hpp"
#include <set>
#include <sstream>
#include <random>
#include <numeric>
#include <functional>
namespace lma_spatial {
using namespace lma_shape;
using Matrix=std::array<double,16>;
inline Matrix identity(){return {1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};}
inline Matrix multiply(const Matrix& a,const Matrix& b){Matrix c{};for(int j=0;j<4;j++)for(int i=0;i<4;i++)for(int k=0;k<4;k++)c[j*4+i]+=a[k*4+i]*b[j*4+k];return c;}
inline Point transform(const Matrix& m,Point p){Point q{};for(int i=0;i<3;i++)q[i]=float(m[i]*p[0]+m[4+i]*p[1]+m[8+i]*p[2]+m[12+i]);return q;}
inline Matrix node_matrix(const json& n){
 Matrix m=identity();
 if(n.contains("matrix")){require(n["matrix"].size()==16,"Invalid GLB node matrix");for(int i=0;i<16;i++)m[i]=n["matrix"][i];}
 else{
  std::array<double,4> q={0,0,0,1};std::array<double,3> s={1,1,1},t={0,0,0};
  if(n.contains("rotation")){require(n["rotation"].size()==4,"Invalid node quaternion");q=n["rotation"].get<std::array<double,4>>();}
  if(n.contains("scale")){require(n["scale"].size()==3,"Invalid node scale");s=n["scale"].get<std::array<double,3>>();}
  if(n.contains("translation")){require(n["translation"].size()==3,"Invalid node translation");t=n["translation"].get<std::array<double,3>>();}
  double x=q[0],y=q[1],z=q[2],w=q[3],norm=x*x+y*y+z*z+w*w;require(std::abs(norm-1)<1e-3,"Node quaternion is not normalized");
  m={(1-2*y*y-2*z*z)*s[0],(2*x*y+2*z*w)*s[0],(2*x*z-2*y*w)*s[0],0,
     (2*x*y-2*z*w)*s[1],(1-2*x*x-2*z*z)*s[1],(2*y*z+2*x*w)*s[1],0,
     (2*x*z+2*y*w)*s[2],(2*y*z-2*x*w)*s[2],(1-2*x*x-2*y*y)*s[2],0,t[0],t[1],t[2],1};
 }
 for(double v:m)require(std::isfinite(v)&&std::abs(v)<=1e9,"Nonfinite/extreme node transform");
 require(std::abs(m[3])+std::abs(m[7])+std::abs(m[11])<1e-12&&std::abs(m[15]-1)<1e-12,"Projective node transform unsupported");return m;
}
inline uint32_t little(const std::string& s,size_t at){require(at<=s.size()&&s.size()-at>=4,"Truncated GLB");uint32_t r;std::memcpy(&r,s.data()+at,4);return r;}
inline Mesh read_glb(const std::filesystem::path& path,size_t max_triangles=1000000){
 require(std::filesystem::file_size(path)<=256*1024*1024,"Input mesh exceeds 256 MiB");std::ifstream in(path,std::ios::binary);std::string data((std::istreambuf_iterator<char>(in)),{});
 require(data.size()>=28&&little(data,0)==0x46546c67&&little(data,4)==2&&little(data,8)==data.size(),"Need a self-contained glTF2 GLB");
 size_t jsize=little(data,12);require(jsize>0&&jsize<=8*1024*1024&&jsize%4==0&&20+jsize+8<=data.size()&&little(data,16)==0x4e4f534a,"Invalid GLB JSON chunk");
 json root=json::parse(data.substr(20,jsize));size_t bstart=28+jsize,bsize=little(data,20+jsize);require(little(data,24+jsize)==0x004e4942&&bstart+bsize==data.size(),"Invalid GLB BIN chunk");
 require(root.at("asset").at("version")=="2.0"&&root.at("buffers").size()==1&&!root["buffers"][0].contains("uri")&&root["buffers"][0].at("byteLength").get<size_t>()<=bsize&&bsize-root["buffers"][0].at("byteLength").get<size_t>()<=3&&bsize%4==0,"External GLB buffers forbidden");
 require(!root.contains("skins")&&!root.contains("animations")&&root.value("extensionsRequired",json::array()).empty(),"Bake skin/animation/compressed mesh before importing");
 bsize=root["buffers"][0].at("byteLength").get<size_t>();
 const auto& accessors=root.at("accessors");const auto& views=root.at("bufferViews");Mesh result;
 auto accessor=[&](int index,int components,const char* type,std::vector<double>& out){
  require(index>=0&&size_t(index)<accessors.size(),"Bad mesh accessor");const auto& a=accessors[index];require(!a.contains("sparse")&&!a.value("normalized",false)&&a.at("type")==type,"Unsupported mesh accessor layout");
  int vi=a.at("bufferView"),ct=a.at("componentType");require(vi>=0&&size_t(vi)<views.size(),"Bad mesh buffer view");const auto& v=views[vi];require(v.at("buffer")==0,"External mesh buffer forbidden");
  int width=ct==5121?1:ct==5123?2:(ct==5125||ct==5126)?4:0;require(width&&((components==3&&ct==5126)||(components==1&&ct!=5126)),"Need float32 positions and unsigned indices");
  size_t count=a.at("count"),vo=v.value("byteOffset",size_t(0)),vl=v.at("byteLength"),ao=a.value("byteOffset",size_t(0)),stride=v.value("byteStride",size_t(width*components));
  require(count>0&&count<=3000000&&vo<=bsize&&vl<=bsize-vo&&ao<=vl&&stride>=size_t(width*components)&&stride<=252&&stride%size_t(width)==0&&
    count-1<=(vl-ao)/stride&&size_t(width*components)<=vl-ao-(count-1)*stride,"Mesh accessor exceeds its buffer");
  out.resize(count*components);for(size_t i=0;i<count;i++)for(int c=0;c<components;c++){
   const char* p=data.data()+bstart+vo+ao+i*stride+c*width;double value=0;
   if(ct==5126){float f;std::memcpy(&f,p,4);value=f;}else if(width==4){uint32_t f;std::memcpy(&f,p,4);value=f;}else if(width==2){uint16_t f;std::memcpy(&f,p,2);value=f;}else value=uint8_t(*p);
   require(std::isfinite(value)&&std::abs(value)<=1e9,"Nonfinite/extreme mesh values");out[i*components+c]=value;
  }
 };
 auto append=[&](int mi,const Matrix& world){
  require(mi>=0&&size_t(mi)<root.at("meshes").size(),"Bad node mesh");for(const auto& p:root["meshes"][mi].at("primitives")){
   require(p.value("mode",4)==4&&!p.contains("targets")&&!p.contains("extensions"),"Only uncompressed static triangles are supported");
   std::vector<double> vertices,indices;accessor(p.at("attributes").at("POSITION"),3,"VEC3",vertices);
   if(p.contains("indices"))accessor(p.at("indices"),1,"SCALAR",indices);else{indices.resize(vertices.size()/3);std::iota(indices.begin(),indices.end(),0.);}
   require(indices.size()%3==0&&indices.size()/3<=max_triangles-result.indices.size()/3&&vertices.size()/3<=3000000-result.vertices.size(),"Input mesh budget exceeded");
   uint32_t base=uint32_t(result.vertices.size());for(size_t i=0;i<vertices.size();i+=3)result.vertices.push_back(transform(world,{float(vertices[i]),float(vertices[i+1]),float(vertices[i+2])}));
   // A reflected node must also reverse winding.
   double det=world[0]*(world[5]*world[10]-world[9]*world[6])-world[4]*(world[1]*world[10]-world[9]*world[2])+world[8]*(world[1]*world[6]-world[5]*world[2]);
   for(size_t i=0;i<indices.size();i+=3){uint32_t ids[3];for(int c=0;c<3;c++){require(indices[i+c]>=0&&indices[i+c]<vertices.size()/3,"Mesh index out of range");ids[c]=base+uint32_t(indices[i+c]);}if(det<0)std::swap(ids[1],ids[2]);result.indices.insert(result.indices.end(),ids,ids+3);}
  }
 };
 const auto& nodes=root.at("nodes");require(nodes.size()<=100000,"Too many GLB nodes");std::set<int> active;size_t visits=0;
 std::function<void(int,Matrix,int)> visit=[&](int id,Matrix parent,int depth){require(id>=0&&size_t(id)<nodes.size()&&depth<=64&&++visits<=100000&&active.insert(id).second,"Cyclic/oversized mesh scene");const auto& n=nodes[id];auto world=multiply(parent,node_matrix(n));if(n.contains("mesh"))append(n["mesh"],world);for(const auto& c:n.value("children",json::array()))visit(c,world,depth+1);active.erase(id);};
 int scene=root.value("scene",0);require(scene>=0&&size_t(scene)<root.at("scenes").size(),"Missing GLB scene");for(const auto& n:root["scenes"][scene].at("nodes"))visit(n,identity(),0);
 require(!result.vertices.empty()&&!result.indices.empty(),"Input GLB has no triangle surface");return result;
}
inline void normalize(Mesh& m,float scale=.99f){
 require(!m.vertices.empty()&&std::isfinite(scale)&&scale>0&&scale<=1,"Invalid mesh normalization");Point low=m.vertices[0],high=low;
 for(auto p:m.vertices)for(int i=0;i<3;i++){low[i]=std::min(low[i],p[i]);high[i]=std::max(high[i],p[i]);}
 float extent=std::max({high[0]-low[0],high[1]-low[1],high[2]-low[2]});require(std::isfinite(extent)&&extent>1e-8,"Degenerate coarse mesh");
 for(auto& p:m.vertices)for(int i=0;i<3;i++)p[i]=(p[i]-(low[i]+high[i])*.5f)*2*scale/extent;
}
inline std::vector<Point> sample_surface(const Mesh& m,size_t samples,std::mt19937& rng){
 require(samples>0&&samples<=1000000,"Surface sample budget exceeded");std::vector<double> weights;double total=0;
 for(size_t i=0;i<m.indices.size();i+=3){Point a=m.vertices.at(m.indices[i]),b=m.vertices.at(m.indices[i+1]),c=m.vertices.at(m.indices[i+2]);Point n=cross(subtract(b,a),subtract(c,a));total+=std::sqrt(double(dot(n,n)))*.5;weights.push_back(total);}
 require(total>1e-12&&std::isfinite(total),"Coarse mesh has no nondegenerate surface");std::uniform_real_distribution<double> u(0,1);std::vector<Point> points;points.reserve(samples);
 for(size_t i=0;i<samples;i++){size_t f=size_t(std::lower_bound(weights.begin(),weights.end(),u(rng)*total)-weights.begin())*3;require(f+2<m.indices.size(),"Surface sampler overflow");double a=std::sqrt(u(rng)),b=u(rng);Point p{};for(int j=0;j<3;j++)p[j]=float((1-a)*m.vertices[m.indices[f]][j]+a*(1-b)*m.vertices[m.indices[f+1]][j]+a*b*m.vertices[m.indices[f+2]][j]);points.push_back(p);}return points;
}
inline std::vector<float> voxel_indices(const std::vector<Point>& points,int count,int resolution,std::mt19937& rng){
 require(count>0&&count<=32768&&resolution>=8&&resolution<=256&&!points.empty(),"Invalid coarse voxel request");std::set<std::array<int,3>> unique;
 for(auto p:points){std::array<int,3> v;for(int i=0;i<3;i++)v[i]=std::clamp(int(std::floor((p[i]+1)*.5f*resolution)),0,resolution-1);unique.insert(v);}
 std::vector<std::array<int,3>> voxels(unique.begin(),unique.end());require(!voxels.empty(),"No coarse mesh voxels");std::shuffle(voxels.begin(),voxels.end(),rng);std::vector<float> result(size_t(count)*3);
 for(int i=0;i<count;i++)for(int j=0;j<3;j++)result[size_t(i)*3+j]=float(voxels[size_t(i)%voxels.size()][j]);return result;
}
}

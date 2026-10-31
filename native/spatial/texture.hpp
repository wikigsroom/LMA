#pragma once
#include "mesh.hpp"
#include "xatlas.h"
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"
#include <queue>
namespace lma_spatial {
// Shared bounded CPU material geometry. Coordinates remain those of the input
// GLB; Hunyuan's reflected/centered render transform is applied only to views.
struct Camera { Point eye,right,up,back;float extent=1.2f; };
inline Point scale(Point p,float a){for(auto& v:p)v*=a;return p;}
inline Point add(Point p,Point q){for(int i=0;i<3;i++)p[i]+=q[i];return p;}
inline Point direction(Point p){float length=std::sqrt(dot(p,p));require(length>1e-12f,"Degenerate material geometry direction");return scale(p,1/length);}
inline Camera paint_camera(double elev,double azim){
 constexpr double pi=3.14159265358979323846;double e=-elev*pi/180,a=(azim+90)*pi/180;
 // Preserve double trigonometry at the two polar cameras before normalizing.
 std::array<double,3> eye={1.45*std::cos(e)*std::cos(a),1.45*std::cos(e)*std::sin(a),1.45*std::sin(e)};
 double len=std::sqrt(eye[0]*eye[0]+eye[1]*eye[1]+eye[2]*eye[2]);std::array<double,3> back={eye[0]/len,eye[1]/len,eye[2]/len};
 double xy=std::sqrt(back[0]*back[0]+back[1]*back[1]);require(xy>0,"Undefined polar view");
 Point right={float(-back[1]/xy),float(back[0]/xy),0},b={float(back[0]),float(back[1]),float(back[2])};
 return {{float(eye[0]),float(eye[1]),float(eye[2])},right,cross(b,right),b,1.2f};
}
inline Mesh paint_geometry(const Mesh& m){
 require(m.vertices.size()>=3&&m.vertices.size()<=3000000&&!m.indices.empty()&&m.indices.size()%3==0&&m.indices.size()/3<=1000000,"Material mesh exceeds budget");
 Mesh r=m;Point lo={INFINITY,INFINITY,INFINITY},hi={-INFINITY,-INFINITY,-INFINITY};
 for(auto& p:r.vertices){for(float v:p)require(std::isfinite(v),"Nonfinite material vertex");p={-p[0],p[2],-p[1]};for(int i=0;i<3;i++){lo[i]=std::min(lo[i],p[i]);hi[i]=std::max(hi[i],p[i]);}}
 Point center=scale(add(lo,hi),.5f);float radius=0;for(auto& p:r.vertices){p=subtract(p,center);radius=std::max(radius,std::sqrt(dot(p,p)));}
 require(radius>1e-12f,"Zero extent material mesh");for(auto& p:r.vertices)p=scale(p,1.15f/(2*radius));for(uint32_t i:r.indices)require(i<r.vertices.size(),"Material index out of range");return r;
}
struct GBuffer {int size=0;std::vector<int32_t> face;std::vector<float> depth;std::vector<Point> position,normal;};
inline std::array<float,3> project(Point p,const Camera& c,int size){Point d=subtract(p,c.eye);return {(dot(d,c.right)/c.extent+.5f)*size,(.5f-dot(d,c.up)/c.extent)*size,-dot(d,c.back)};}
inline float edge(float ax,float ay,float bx,float by,float x,float y){return (bx-ax)*(y-ay)-(by-ay)*(x-ax);}
template<class Pixel> inline void raster_triangle(std::array<std::array<float,3>,3> v,int w,int h,uint64_t& budget,Pixel emit){
 float area=edge(v[0][0],v[0][1],v[1][0],v[1][1],v[2][0],v[2][1]);if(std::abs(area)<1e-12f)return;
 float minx=std::min({v[0][0],v[1][0],v[2][0]}),maxx=std::max({v[0][0],v[1][0],v[2][0]}),miny=std::min({v[0][1],v[1][1],v[2][1]}),maxy=std::max({v[0][1],v[1][1],v[2][1]});
 if(maxx<.5f||maxy<.5f||minx>w-.5f||miny>h-.5f)return;
 int x0=int(std::ceil(std::clamp(minx-.5f,0.f,float(w-1)))),x1=int(std::floor(std::clamp(maxx-.5f,0.f,float(w-1))));
 int y0=int(std::ceil(std::clamp(miny-.5f,0.f,float(h-1)))),y1=int(std::floor(std::clamp(maxy-.5f,0.f,float(h-1))));
 if(x1<x0||y1<y0)return;uint64_t cost=uint64_t(x1-x0+1)*(y1-y0+1);require(cost<=budget,"CPU raster work budget exceeded; simplify mesh or reduce image size");budget-=cost;
 for(int y=y0;y<=y1;y++)for(int x=x0;x<=x1;x++){
  float a=edge(v[1][0],v[1][1],v[2][0],v[2][1],x+.5f,y+.5f)/area,b=edge(v[2][0],v[2][1],v[0][0],v[0][1],x+.5f,y+.5f)/area,c=1-a-b;
  if(a>=-1e-6f&&b>=-1e-6f&&c>=-1e-6f)emit(x,y,std::array<float,3>{a,b,c});
 }
}
inline GBuffer render_material(const Mesh& m,const Camera& camera,int size){
 require(size>=16&&size<=2048,"Render image outside bounds");GBuffer g;g.size=size;size_t count=size_t(size)*size;g.face.assign(count,-1);g.depth.assign(count,INFINITY);g.position.resize(count);g.normal.resize(count);
 std::vector<std::array<float,3>> projected;projected.reserve(m.vertices.size());for(auto p:m.vertices)projected.push_back(project(p,camera,size));uint64_t budget=250000000;
 for(size_t face=0;face<m.indices.size()/3;face++){
  uint32_t a=m.indices[face*3],b=m.indices[face*3+1],c=m.indices[face*3+2];Point n=cross(subtract(m.vertices[b],m.vertices[a]),subtract(m.vertices[c],m.vertices[a]));if(dot(n,n)<1e-20f)continue;n=direction(n);
  std::array<std::array<float,3>,3> v={projected[a],projected[b],projected[c]};
  raster_triangle(v,size,size,budget,[&](int x,int y,std::array<float,3> bary){size_t at=size_t(y)*size+x;float z=0;for(int k=0;k<3;k++)z+=bary[k]*v[k][2];if(z<0||z>2||z>=g.depth[at])return;
   g.depth[at]=z;g.face[at]=int32_t(face);g.normal[at]=n;g.position[at]=add(add(scale(m.vertices[a],bary[0]),scale(m.vertices[b],bary[1])),scale(m.vertices[c],bary[2]));});
 }
 return g;
}
inline std::vector<float> condition_rgb(const GBuffer& g,bool normal){
 std::vector<float> r(g.face.size()*3,1);for(size_t i=0;i<g.face.size();i++)if(g.face[i]>=0)for(int c=0;c<3;c++){
  float f=normal?(g.normal[i][c]+1)*.5f:.5f-g.position[i][c]/1.15f;
  // Publisher conditions pass through an 8-bit PIL image before VAE input.
  r[i*3+c]=std::floor(std::clamp(f,0.f,1.f)*255)/255;
 }return r;
}
struct Atlas {Mesh mesh;std::vector<std::array<float,2>> uv;int width=0,height=0;};
inline Atlas unwrap(const Mesh& m,int requested){
 require(requested>=64&&requested<=4096&&m.indices.size()/3<=300000,"UV unwrap exceeds CPU mesh/atlas budget");
 xatlas::SetPrint(nullptr,false);std::unique_ptr<xatlas::Atlas,decltype(&xatlas::Destroy)> a(xatlas::Create(),xatlas::Destroy);require(bool(a),"Cannot allocate UV atlas");
 xatlas::MeshDecl d;d.vertexPositionData=m.vertices.data();d.vertexPositionStride=sizeof(Point);d.vertexCount=uint32_t(m.vertices.size());d.indexData=m.indices.data();d.indexCount=uint32_t(m.indices.size());d.indexFormat=xatlas::IndexFormat::UInt32;
 require(xatlas::AddMesh(a.get(),d)==xatlas::AddMeshError::Success,"UV topology rejected");xatlas::PackOptions pack;pack.resolution=requested;pack.padding=4;pack.bilinear=true;xatlas::Generate(a.get(),{},pack);
 require(a->meshCount==1&&a->atlasCount==1&&a->width>0&&a->height>0&&a->width<=4096&&a->height<=4096,"UV requires multiple/oversized atlases");
 Atlas out;out.width=int(a->width);out.height=int(a->height);auto& result=a->meshes[0];require(result.vertexCount<=3000000&&result.indexCount==m.indices.size(),"UV output exceeds budget");
 for(uint32_t i=0;i<result.vertexCount;i++){auto v=result.vertexArray[i];require(v.xref<m.vertices.size()&&v.atlasIndex==0,"UV source mapping mismatch");out.mesh.vertices.push_back(m.vertices[v.xref]);out.uv.push_back({v.uv[0]/out.width,v.uv[1]/out.height});}
 out.mesh.indices.assign(result.indexArray,result.indexArray+result.indexCount);return out;
}
struct ViewMaterial {Camera camera;GBuffer geometry;std::vector<float> albedo,mr;float weight=1;};
struct BakedMaterial {std::vector<uint8_t> albedo,mr;size_t covered=0,unobserved=0;};
inline BakedMaterial bake_material(const Atlas& atlas,const Mesh& render_mesh,const std::vector<ViewMaterial>& views){
 require(atlas.uv.size()==atlas.mesh.vertices.size()&&atlas.mesh.vertices.size()==render_mesh.vertices.size()&&!views.empty()&&views.size()<=30,"Invalid material bake inputs");
 size_t count=size_t(atlas.width)*atlas.height;require(count<=16777216,"Atlas pixel budget exceeded");BakedMaterial r;r.albedo.assign(count*4,255);r.mr.assign(count*4,255);std::vector<uint8_t> valid(count),surface(count);uint64_t budget=250000000;
 for(auto& view:views)require(view.geometry.size>=16&&view.albedo.size()==view.geometry.face.size()*3&&view.mr.size()==view.albedo.size()&&std::isfinite(view.weight)&&view.weight>0,"Invalid material view");
 for(size_t f=0;f<atlas.mesh.indices.size()/3;f++){
  uint32_t id[3]={atlas.mesh.indices[f*3],atlas.mesh.indices[f*3+1],atlas.mesh.indices[f*3+2]};std::array<std::array<float,3>,3> uv;
  for(int k=0;k<3;k++)uv[k]={atlas.uv[id[k]][0]*atlas.width,atlas.uv[id[k]][1]*atlas.height,0};
  Point n=cross(subtract(render_mesh.vertices[id[1]],render_mesh.vertices[id[0]]),subtract(render_mesh.vertices[id[2]],render_mesh.vertices[id[0]]));if(dot(n,n)<1e-20f)continue;n=direction(n);
  raster_triangle(uv,atlas.width,atlas.height,budget,[&](int x,int y,std::array<float,3> bary){size_t at=size_t(y)*atlas.width+x;surface[at]=1;Point p={0,0,0};for(int k=0;k<3;k++)p=add(p,scale(render_mesh.vertices[id[k]],bary[k]));
   double sum=0,color[6]={};for(auto& view:views){int size=view.geometry.size;auto q=project(p,view.camera,size);int px=int(std::floor(q[0])),py=int(std::floor(q[1]));if(px<0||py<0||px>=size||py>=size)continue;size_t sample=size_t(py)*size+px;
    // Depth agreement prevents painting hidden surfaces. Both face directions
    // are accepted because the publisher's render transform is a reflection.
    if(view.geometry.face[sample]<0||std::abs(view.geometry.depth[sample]-q[2])>std::max(.002f,2.4f/size))continue;
    double cosine=std::abs(dot(n,view.camera.back)),weight=std::pow(cosine,4)*view.weight;if(cosine<.1)continue;
    for(int c=0;c<3;c++){float a=view.albedo[sample*3+c],m=view.mr[sample*3+c];require(std::isfinite(a)&&std::isfinite(m),"Nonfinite generated material");color[c]+=weight*a;color[c+3]+=weight*m;}sum+=weight;
   }
   if(sum>1e-12){for(int c=0;c<3;c++){r.albedo[at*4+c]=uint8_t(std::round(std::clamp(color[c]/sum,0.,1.)*255));r.mr[at*4+c]=uint8_t(std::round(std::clamp(color[c+3]/sum,0.,1.)*255));}valid[at]=1;}
  });
 }
 // Deterministic nearest observed texel fill repairs seams/atlas padding. It
 // is geometric dilation, not a neural completion or a CUDA raster substitute.
 std::queue<uint32_t> frontier;for(uint32_t i=0;i<count;i++){if(surface[i]){r.covered++;if(!valid[i])r.unobserved++;}if(valid[i])frontier.push(i);}
 require(!frontier.empty(),"No visible material samples; no placeholder texture produced");
 while(!frontier.empty()){uint32_t at=frontier.front();frontier.pop();int x=int(at%atlas.width),y=int(at/atlas.width);const int dx[4]={-1,1,0,0},dy[4]={0,0,-1,1};for(int k=0;k<4;k++){int xx=x+dx[k],yy=y+dy[k];if(xx<0||yy<0||xx>=atlas.width||yy>=atlas.height)continue;uint32_t next=uint32_t(yy*atlas.width+xx);if(valid[next])continue;valid[next]=1;for(int c=0;c<4;c++){r.albedo[next*4+c]=r.albedo[at*4+c];r.mr[next*4+c]=r.mr[at*4+c];}frontier.push(next);}}
 return r;
}
inline void material_glb(const std::filesystem::path& path,const Atlas& atlas,const BakedMaterial& material){
 require(!std::filesystem::exists(path)&&atlas.width>0&&atlas.height>0&&material.albedo.size()==size_t(atlas.width)*atlas.height*4&&material.mr.size()==material.albedo.size(),"Invalid/new material output required");
 std::vector<uint8_t> binary;json root={{"asset",{{"version","2.0"},{"generator","LMA local CPU material"}}},{"bufferViews",json::array()},{"accessors",json::array()}};
 auto append=[&](const void* data,size_t length,int target=0){while(binary.size()%4)binary.push_back(0);json view={{"buffer",0},{"byteOffset",binary.size()},{"byteLength",length}};if(target)view["target"]=target;size_t index=root["bufferViews"].size();root["bufferViews"].push_back(view);auto p=static_cast<const uint8_t*>(data);binary.insert(binary.end(),p,p+length);require(binary.size()<=512*1024*1024,"Material GLB exceeds byte budget");return index;};
 Point lo=atlas.mesh.vertices.at(0),hi=lo;for(auto p:atlas.mesh.vertices)for(int c=0;c<3;c++){lo[c]=std::min(lo[c],p[c]);hi[c]=std::max(hi[c],p[c]);}
 root["accessors"].push_back({{"bufferView",append(atlas.mesh.vertices.data(),atlas.mesh.vertices.size()*sizeof(Point),34962)},{"componentType",5126},{"count",atlas.mesh.vertices.size()},{"type","VEC3"},{"min",lo},{"max",hi}});
 root["accessors"].push_back({{"bufferView",append(atlas.uv.data(),atlas.uv.size()*sizeof(atlas.uv[0]),34962)},{"componentType",5126},{"count",atlas.uv.size()},{"type","VEC2"}});
 root["accessors"].push_back({{"bufferView",append(atlas.mesh.indices.data(),atlas.mesh.indices.size()*sizeof(uint32_t),34963)},{"componentType",5125},{"count",atlas.mesh.indices.size()},{"type","SCALAR"}});
 root["images"]=json::array();for(auto pixels:{&material.albedo,&material.mr}){std::vector<uint8_t> png;auto write=[](void* ctx,void* data,int n){auto& out=*static_cast<std::vector<uint8_t>*>(ctx);auto p=static_cast<uint8_t*>(data);require(n>=0&&out.size()+n<=128*1024*1024,"Encoded texture exceeds budget");out.insert(out.end(),p,p+n);};require(stbi_write_png_to_func(write,&png,atlas.width,atlas.height,4,pixels->data(),atlas.width*4),"Cannot encode material PNG");root["images"].push_back({{"bufferView",append(png.data(),png.size())},{"mimeType","image/png"}});}
 root["samplers"]=json::array({{{"magFilter",9729},{"minFilter",9729},{"wrapS",33071},{"wrapT",33071}}});root["textures"]=json::array({{{"sampler",0},{"source",0}},{{"sampler",0},{"source",1}}});
 root["materials"]=json::array({{{"name","generated_pbr"},{"doubleSided",true},{"pbrMetallicRoughness",{{"baseColorTexture",{{"index",0}}},{"metallicRoughnessTexture",{{"index",1}}},{"metallicFactor",1},{"roughnessFactor",1}}}}});
 root["meshes"]=json::array({{{"primitives",json::array({{{"attributes",{{"POSITION",0},{"TEXCOORD_0",1}}},{"indices",2},{"material",0},{"mode",4}}})}}});root["nodes"]=json::array({{{"mesh",0}}});root["scenes"]=json::array({{{"nodes",json::array({0})}}});root["scene"]=0;
 root["buffers"]=json::array({{{"byteLength",binary.size()}}});std::string metadata=root.dump();while(metadata.size()%4)metadata+=' ';while(binary.size()%4)binary.push_back(0);require(metadata.size()+binary.size()+28<=512*1024*1024,"Material output budget exceeded");
 std::unique_ptr<FILE,decltype(&std::fclose)> file(std::fopen(path.string().c_str(),"wb"),std::fclose);require(bool(file),"Cannot create material GLB");u32(file.get(),0x46546c67);u32(file.get(),2);u32(file.get(),uint32_t(28+metadata.size()+binary.size()));u32(file.get(),uint32_t(metadata.size()));u32(file.get(),0x4e4f534a);std::fwrite(metadata.data(),1,metadata.size(),file.get());u32(file.get(),uint32_t(binary.size()));u32(file.get(),0x004e4942);std::fwrite(binary.data(),1,binary.size(),file.get());require(!std::ferror(file.get())&&!std::fflush(file.get())&&!LMA_SYNC(LMA_FILENO(file.get())),"Cannot persist material GLB");
}
}

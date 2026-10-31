#pragma once
#include "../worker_common.hpp"
#include <array>
#include <unordered_map>
namespace lma_shape {
using namespace lma_worker;
using Point=std::array<float,3>;
struct Mesh {std::vector<Point> vertices;std::vector<uint32_t> indices;};
inline Point subtract(Point a,Point b){return {a[0]-b[0],a[1]-b[1],a[2]-b[2]};}
inline Point cross(Point a,Point b){return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};}
inline float dot(Point a,Point b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
// Six consistent tetrahedra per cell avoid a GPU mesher and share vertices
// across tetrahedra/cells. Positive decoder logits are the occupied side.
inline Mesh surface(const std::vector<float>& field,int cells,size_t triangle_limit) {
 size_t n=size_t(cells+1);require(cells>=2&&cells<=256&&field.size()==n*n*n,"Invalid SDF grid");
 for(float f:field)require(std::isfinite(f),"Nonfinite SDF grid");
 Mesh m;std::unordered_map<uint64_t,uint32_t> edges;
 const int corners[8][3]={{0,0,0},{1,0,0},{1,1,0},{0,1,0},{0,0,1},{1,0,1},{1,1,1},{0,1,1}};
 const int tetra[6][4]={{0,5,1,6},{0,1,2,6},{0,2,3,6},{0,3,7,6},{0,7,4,6},{0,4,5,6}};
 auto position=[&](uint32_t i){int z=int(i%n),y=int((i/n)%n),x=int(i/(n*n));return Point{float(x)*2.01f/cells-1.005f,float(y)*2.01f/cells-1.005f,float(z)*2.01f/cells-1.005f};};
 auto vertex=[&](uint32_t a,uint32_t b){if(a>b)std::swap(a,b);uint64_t key=(uint64_t(a)<<32)|b;auto found=edges.find(key);if(found!=edges.end())return found->second;
  float delta=field[a]-field[b],t=std::abs(delta)>1e-20f?field[a]/delta:.5f;t=std::clamp(t,0.f,1.f);Point p=position(a),q=position(b);for(int j=0;j<3;j++)p[j]+=(q[j]-p[j])*t;
  require(m.vertices.size()<3000000,"Mesh vertex budget exceeded");uint32_t id=uint32_t(m.vertices.size());m.vertices.push_back(p);edges.emplace(key,id);return id;};
 auto triangle=[&](uint32_t a,uint32_t b,uint32_t c,Point outward){Point normal=cross(subtract(m.vertices[b],m.vertices[a]),subtract(m.vertices[c],m.vertices[a]));
  if(dot(normal,normal)<1e-20f)return;if(dot(normal,outward)<0)std::swap(b,c);require(m.indices.size()/3<triangle_limit,"Mesh triangle budget exceeded; reduce grid/parts or raise the explicit limit");m.indices.insert(m.indices.end(),{a,b,c});};
 for(int x=0;x<cells;x++)for(int y=0;y<cells;y++)for(int z=0;z<cells;z++){
  uint32_t ids[8];for(int i=0;i<8;i++)ids[i]=uint32_t(((x+corners[i][0])*n+y+corners[i][1])*n+z+corners[i][2]);
  for(auto& t:tetra){uint32_t inside[4],outside[4];int ni=0,no=0;for(int j:t){if(field[ids[j]]>0)inside[ni++]=ids[j];else outside[no++]=ids[j];}if(!ni||!no)continue;
   Point out=subtract(position(outside[0]),position(inside[0]));
   if(ni==1){triangle(vertex(inside[0],outside[0]),vertex(inside[0],outside[1]),vertex(inside[0],outside[2]),out);}
   else if(ni==3){triangle(vertex(outside[0],inside[0]),vertex(outside[0],inside[1]),vertex(outside[0],inside[2]),out);}
   else{auto a=vertex(inside[0],outside[0]),b=vertex(inside[0],outside[1]),c=vertex(inside[1],outside[0]),d=vertex(inside[1],outside[1]);triangle(a,b,c,out);triangle(b,d,c,out);}
  }
 }
 require(!m.indices.empty(),"Decoder field has no surface; no placeholder mesh was produced");return m;
}
inline void glb(const std::filesystem::path& path,const std::vector<Mesh>& parts) {
 require(!parts.empty()&&parts.size()<=16,"Invalid part result count");
 json root={{"asset",{{"version","2.0"},{"generator","LMA RF Shape CPU"}}},{"scene",0},{"scenes",json::array({{{"nodes",json::array()}}})},
  {"nodes",json::array()},{"meshes",json::array()},{"materials",json::array()},{"bufferViews",json::array()},{"accessors",json::array()}};
 std::vector<uint8_t> binary;auto append=[&](const void* p,size_t count){const auto* b=static_cast<const uint8_t*>(p);binary.insert(binary.end(),b,b+count);};
 for(size_t i=0;i<parts.size();i++){
  const auto& p=parts[i];require(!p.vertices.empty()&&!p.indices.empty(),"Cannot export an empty part");Point low=p.vertices[0],high=low;
  for(auto& v:p.vertices)for(int j=0;j<3;j++){require(std::isfinite(v[j]),"Nonfinite mesh vertex");low[j]=std::min(low[j],v[j]);high[j]=std::max(high[j],v[j]);}
  size_t offset=binary.size();append(p.vertices.data(),p.vertices.size()*sizeof(Point));size_t index_offset=binary.size();append(p.indices.data(),p.indices.size()*sizeof(uint32_t));
  root["bufferViews"].push_back({{"buffer",0},{"byteOffset",offset},{"byteLength",index_offset-offset},{"target",34962}});
  root["bufferViews"].push_back({{"buffer",0},{"byteOffset",index_offset},{"byteLength",binary.size()-index_offset},{"target",34963}});
  root["accessors"].push_back({{"bufferView",i*2},{"componentType",5126},{"count",p.vertices.size()},{"type","VEC3"},{"min",low},{"max",high}});
  root["accessors"].push_back({{"bufferView",i*2+1},{"componentType",5125},{"count",p.indices.size()},{"type","SCALAR"}});
  root["materials"].push_back({{"name","part_"+std::to_string(i+1)},{"pbrMetallicRoughness",{{"baseColorFactor",{.35+.35*std::sin(float(i)+1),.5+.3*std::cos(float(i)),.65,1.}},{"metallicFactor",0},{"roughnessFactor",.8}}},{"doubleSided",true}});
  root["meshes"].push_back({{"name","part_"+std::to_string(i+1)},{"primitives",json::array({{{"attributes",{{"POSITION",i*2}}},{"indices",i*2+1},{"material",i},{"mode",4}}})}});
  root["nodes"].push_back({{"name","part_"+std::to_string(i+1)},{"mesh",i}});root["scenes"][0]["nodes"].push_back(i);
 }
 root["buffers"]=json::array({{{"byteLength",binary.size()}}});std::string j=root.dump();while(j.size()%4)j+=' ';while(binary.size()%4)binary.push_back(0);
 require(j.size()<8*1024*1024&&j.size()+binary.size()+28<=512*1024*1024,"GLB exceeds application bounds");
 std::unique_ptr<FILE,decltype(&std::fclose)> file(std::fopen(path.string().c_str(),"wb"),std::fclose);require(bool(file),"Cannot create GLB");
 u32(file.get(),0x46546c67);u32(file.get(),2);u32(file.get(),uint32_t(28+j.size()+binary.size()));u32(file.get(),uint32_t(j.size()));u32(file.get(),0x4e4f534a);std::fwrite(j.data(),1,j.size(),file.get());u32(file.get(),uint32_t(binary.size()));u32(file.get(),0x004e4942);std::fwrite(binary.data(),1,binary.size(),file.get());
 require(!std::ferror(file.get())&&!std::fflush(file.get())&&!LMA_SYNC(LMA_FILENO(file.get())),"Cannot persist GLB");
}
}

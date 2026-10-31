#include "../../native/spatial/texture.hpp"
#include "../../native/spatial/linear_sampler.hpp"
#include <iostream>
using namespace lma_spatial;
int main(int argc,char** argv){try{
 require(argc==2,"Need one material fixture");std::ifstream input(argv[1]);json p;input>>p;
 if(p.value("type","")=="sampler"){
  std::ifstream f(p.at("sampler").get<std::string>());json program;f>>program;std::vector<float> sample=p.at("sample");std::vector<std::vector<float>> noise=p.at("noise");LinearSampler sampler(program,int(noise.size()),sample.size());json states=json::array(),times=json::array();
  for(auto n:noise){times.push_back(sampler.time());sampler.update(sample,n);states.push_back(sample);}std::cout<<json({{"states",states},{"times",times}}).dump()<<std::endl;return 0;
 }
 Mesh m;m.vertices=p.at("vertices").get<std::vector<Point>>();m.indices=p.at("indices").get<std::vector<uint32_t>>();
 auto transformed=paint_geometry(m);auto camera=paint_camera(p.value("elevation",0.),p.value("azimuth",0.));auto g=render_material(transformed,camera,p.value("size",32));std::vector<float> depth=g.depth;for(float& v:depth)if(!std::isfinite(v))v=-1;
 json out={{"vertices",transformed.vertices},{"eye",camera.eye},{"right",camera.right},{"up",camera.up},{"back",camera.back},{"face",g.face},{"depth",depth},{"normal",condition_rgb(g,true)},{"position",condition_rgb(g,false)}};
 if(p.value("bake",false)){
  auto atlas=unwrap(m,p.value("atlas",128));auto geometry=paint_geometry(atlas.mesh);std::vector<ViewMaterial> views;double elevs[6]={0,0,0,0,90,-90},azims[6]={0,90,180,270,0,180};float weights[6]={1,.1f,.5f,.1f,.05f,.05f};
  for(int i=0;i<6;i++){ViewMaterial v;v.camera=paint_camera(elevs[i],azims[i]);v.geometry=render_material(geometry,v.camera,64);v.weight=weights[i];v.albedo.assign(64*64*3,0);v.mr.assign(64*64*3,0);for(size_t j=0;j<64*64;j++){v.albedo[j*3]=.25f;v.albedo[j*3+1]=.5f;v.albedo[j*3+2]=.75f;v.mr[j*3+1]=.8f;v.mr[j*3+2]=.2f;}views.push_back(std::move(v));}
  auto baked=bake_material(atlas,geometry,views);material_glb(p.at("output").get<std::string>(),atlas,baked);out.update({{"atlasWidth",atlas.width},{"atlasHeight",atlas.height},{"uv",atlas.uv},{"uvVertices",atlas.mesh.vertices},{"uvIndices",atlas.mesh.indices},{"covered",baked.covered},{"unobserved",baked.unobserved}});
 }
 std::cout<<out.dump()<<std::endl;return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<std::endl;return 1;}}

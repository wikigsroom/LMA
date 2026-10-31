#include "../../native/spatial/image.hpp"
#include "../../native/spatial/surface_sampling.hpp"
#include "../../native/spatial/math.hpp"
#include <iostream>
using namespace lma_spatial;
int main(int argc,char** argv){
 try {
  require(argc==2,"Need one fixture request");std::ifstream in(argv[1]);json p;in>>p;std::string type=p.at("type");json out;
  if(type=="image"){
   auto r=shape_image(p.at("path").get<std::string>(),p.at("processorSize"),p.at("imageSize"),p.value("borderRatio",.15f),p.value("masked",false),p.value("diagnostic",false));
   out={{"pixels",r.pixels},{"selected",r.selected},{"base",r.diagnostic_base}};
  }else if(type=="schedule"){
   int steps=p.at("steps");float shift=p.at("shift");std::vector<float> times,state=p.at("state"),velocity=p.at("velocity");require(state.size()==velocity.size(),"Bad test velocity");
   for(int i=0;i<steps;i++){float a=spatial_sigma(i,steps,shift),b=spatial_sigma(i+1,steps,shift);times.push_back(a);for(size_t j=0;j<state.size();j++)state[j]+=(b-a)*velocity[j];}
   out={{"state",state},{"times",times}};
  }else if(type=="resize")out["values"]=resize(p.at("values").get<std::vector<float>>(),p.at("iw"),p.at("ih"),p.at("ow"),p.at("oh"),p.at("channels"),p.at("method"),p.value("quantize",true));
  else if(type=="mesh"){
   auto m=read_glb(p.at("path").get<std::string>());normalize(m,p.value("scale",.99f));std::mt19937 rng{1234};
   auto sample=sample_surface(m,p.value("samples",4096),rng);auto v=voxel_indices(sample,p.value("tokens",512),p.value("resolution",128),rng);
   out={{"vertices",m.vertices},{"indices",m.indices},{"samples",sample},{"voxels",v}};
  }else if(type=="sharp"){
   auto mesh=read_glb(p.at("path").get<std::string>());normalize(mesh,p.value("scale",.99f));auto sharp=sharp_surface(mesh);std::mt19937 rng{1234};
   out={{"vertices",mesh.vertices},{"normals",sharp.normals},{"edges",sharp.edges},{"cumulative",sharp.cumulative},{"samples",refine_surface(mesh,p.value("samples",4096),rng)}};
  }else if(type=="half"){
   std::vector<float> values=p.at("values");for(float& value:values)value=surface_half(value);out["values"]=values;
  }else throw std::runtime_error("Unknown test request");
  std::cout<<out.dump()<<std::endl;return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<std::endl;return 1;}
}

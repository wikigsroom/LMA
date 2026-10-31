#include "../../native/rf_shape/surface.hpp"
#include <iostream>
int main(int argc,char** argv){
 try{lma_worker::require(argc==2,"Request required");std::ifstream in(argv[1]);lma_worker::json r;in>>r;using namespace lma_shape;
  if(r.at("operation")=="volume"){
   float box=r.at("box"),radius=r.value("radius",.5f);auto query=[&](const std::vector<float>& points){std::vector<float> out;for(size_t i=0;i<points.size();i+=3){float x=points[i],y=points[i+1],z=points[i+2];float value=radius-x*x-y*y-z*z;if(r.value("function",std::string("sphere"))=="plane")value=x+.375f*y-.2f*z+.03125f;out.push_back(value);}return out;};
   auto v=adaptive_field(query,r.at("mode"),r.at("depth"),r.at("dense"),r.at("chunk"),box);std::cout<<json({{"size",v.size},{"divisor",v.divisor},{"queried",v.queried},{"values",v.values}}).dump();
  }else{
   Mesh mesh=r.at("operation")=="dmc"?diso_surface(r.at("field").get<std::vector<float>>(),r.at("n"),r.value("box",1.f),r.at("divisor"),r.value("triangles",1000000)):lewiner(r.at("field").get<std::vector<float>>(),r.at("n"),r.value("box",1.f),r.at("divisor"),r.value("triangles",1000000));
   std::cout<<json({{"vertices",mesh.vertices},{"indices",mesh.indices}}).dump();
  }return 0;
 }catch(const std::exception& e){std::fprintf(stderr,"%s",e.what());return 1;}
}

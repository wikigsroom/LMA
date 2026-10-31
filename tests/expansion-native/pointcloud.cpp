#include "../../native/rf_shape/pointcloud.hpp"
int main(int argc,char** argv){
 try{lma_worker::require(argc==2,"Request path required");std::ifstream stream(argv[1]);lma_worker::json r;stream>>r;auto result=lma_shape::point_fps(r.at("points").get<lma_shape::Floats>(),r.at("candidates").get<std::vector<size_t>>(),r.at("tokens"));std::puts(lma_worker::json({{"queries",result}}).dump().c_str());return 0;}catch(const std::exception& e){std::fprintf(stderr,"%s",e.what());return 1;}
}

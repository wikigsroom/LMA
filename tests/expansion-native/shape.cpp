#include "../../native/rf_shape/math.hpp"
#include "../../native/rf_shape/image.hpp"
#include "../../native/rf_shape/geometry.hpp"
#include <iostream>
using namespace lma_shape;
int main(int argc,char**argv){
 try{
  lma_worker::require(argc==2,"Need fixture file");std::ifstream in(argv[1]);lma_worker::json p;in>>p;
  std::vector<float> state=p.at("state"),velocity=p.at("velocity");int steps=p.at("steps");float shift=p.at("shift");
  std::vector<float> times;for(int i=0;i<steps;i++){times.push_back(sigma(i,steps,shift)*1000);flow_step(state,velocity,i,steps,shift);}
  auto image=pixels(p.at("image"),28,32,{.485,.456,.406},{.229,.224,.225});
  std::cout<<lma_worker::json{{"state",state},{"timesteps",times},{"pixels",image}}.dump()<<std::endl;return 0;
 }catch(const std::exception&){return 1;}
}

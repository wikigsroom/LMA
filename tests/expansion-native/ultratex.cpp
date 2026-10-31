#include "../../native/spatial/ultratex.hpp"
#include <iostream>
// Host-only diagnostics. Android continues to expose sanitized errors only.
int main(int argc,char** argv){using namespace lma_spatial;try{
 require(argc==2,"Supply a private UltraTex fixture");events=stdout;
 auto c=request(argv[1]);
 if(c.contains("operation")){
  json r;std::string operation=c.at("operation");
  if(operation=="mask")r["mask"]=ultra_mask(c.at("alpha").get<Floats>(),c.at("size"),c.at("side"),false);
  else if(operation=="schedule"){Floats v;int steps=c.at("steps");for(int i=0;i<=steps;i++)v.push_back(ultra_sigma(i,steps,c.at("size")));r["schedule"]=v;}
  else if(operation=="layout"){
   auto tiles=c.at("tiles").get<std::vector<Floats>>();int s=c.at("side"),ch=c.at("channels");auto atlas=ultra_atlas(tiles,s,ch),tokens=ultra_tokens(atlas,s*2,s*3,ch);r["atlas"]=atlas;r["tokens"]=tokens;
   for(int i=0;i<6;i++)r["tiles"].push_back(ultra_tile(tokens,i,s,ch));
   r["ids"]=ultra_ids(s*2,s*3,3,0,s*2,s*3);
  }else throw std::runtime_error("Unknown host operation");
  std::cout<<r.dump()<<std::endl;return 0;
 }
 ultratex_generate(c);return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<std::endl;return 1;}}

#include "../../native/spatial/text_tokens.hpp"
#include <iostream>
int main(int argc,char** argv){using namespace lma_spatial;try{
 require(argc==2,"Supply a text fixture request");std::ifstream in(argv[1]);json p;in>>p;
 auto v=p.at("kind")=="t5"?t5_tokens(p.at("path").get<std::string>(),p.at("text"),p.at("length"),p.at("vocab")):
  bpe_tokens(p.at("path").get<std::string>(),p.at("text"),p.at("length"),p.at("vocab"),p.at("pad"),p.at("qwen"));
 std::cout<<json({{"ids",v.ids},{"mask",v.mask}}).dump()<<std::endl;return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<std::endl;return 1;}}

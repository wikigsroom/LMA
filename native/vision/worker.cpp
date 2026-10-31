#include "foreground.hpp"
#include "vlm.hpp"
using namespace lma_worker;
int main(int argc,char** argv){
 if(argc==2&&!std::strcmp(argv[1],"--info")){std::puts("{\"engine\":\"vision_cpu\",\"backend\":\"cpu\",\"pipelines\":[\"isnet_dis\",\"vlm_parts\"],\"modelDownloads\":false}");return 0;}
 try{initialize();require(argc==2,"Supply one private vision request");auto c=request(argv[1]);if(c.at("pipeline")=="isnet_dis")lma_vision::foreground(c);else lma_vision::identify_parts(c);return 0;}
 catch(const std::exception&){if(events)event({{"event","error"},{"message","Local vision failed. Check the selected matched model components, input image, context/output limits and available memory."}});return 1;}
}

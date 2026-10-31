#include "../../native/vision/foreground.hpp"
#include "../../native/vision/vlm.hpp"
using namespace lma_vision;
int main(int argc,char** argv){try{require(argc==2,"One local fixture");auto c=json::parse(bytes(argv[1],1024*1024));auto operation=c.at("operation");json out;
 if(operation=="parts")out=validate_parts(c.at("text"));
 else {Image image;image.width=c.at("width");image.height=c.at("height");image.rgba=c.at("rgba").get<std::vector<uint8_t>>();require(image.width>0&&image.height>0&&image.rgba.size()==size_t(image.width)*image.height*4,"Fixture bounds");int side=c.at("side");require(side>=1&&side<=1024,"Fixture side");if(operation=="pixels")out=foreground_pixels(image,side);else if(operation=="alpha")out=foreground_alpha(image,c.at("mask").get<Floats>(),side).rgba;else throw std::runtime_error("Unknown fixture");}
 std::puts(out.dump().c_str());return 0;
}catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 1;}}

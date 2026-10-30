#include "../../native/mnn/policy.hpp"
#include "../../native/mnn/image.hpp"
#include <iostream>
#include <limits>
#include <vector>
int main(int argc, char** argv) {
    int passed = 0;
    auto valid = [&](int w,int h,int steps,int threads,int tokens,bool cfg,float scale,const std::string& negative) {
        lma_mnn::parameters(w,h,steps,threads,tokens,cfg,scale,negative); ++passed;
    };
    auto reject = [&](int w,int h,int steps,int threads,int tokens,bool cfg,float scale,const std::string& negative) {
        try { lma_mnn::parameters(w,h,steps,threads,tokens,cfg,scale,negative); } catch (const std::exception&) { ++passed; return; } throw std::runtime_error("Policy accepted an invalid request");
    };
    valid(256,256,1,1,1,false,0,""); valid(2048,2048,50,32,1792,true,30,"negative");
    reject(255,512,10,4,512,false,4,""); reject(512,511,10,4,512,false,4,""); reject(2080,512,10,4,512,false,4,"");
    reject(512,512,0,4,512,false,4,""); reject(512,512,51,4,512,false,4,"");
    reject(512,512,10,0,512,false,4,""); reject(512,512,10,33,512,false,4,"");
    reject(512,512,10,4,0,false,4,""); reject(512,512,10,4,1793,false,4,"");
    reject(512,512,10,4,512,false,4,"negative"); reject(512,512,10,4,512,true,-1,""); reject(512,512,10,4,512,true,31,"");
    reject(512,512,10,4,512,true,std::numeric_limits<float>::quiet_NaN(),"");
    lma_mnn::edit_parameters(512,512,false,lma_mnn::EDIT_PROMPT,""); ++passed;
    auto edit_reject = [&](int w,int h,bool cfg,const std::string& prompt,const std::string& negative) {
        try { lma_mnn::edit_parameters(w,h,cfg,prompt,negative); } catch(const std::exception&) { ++passed; return; }
        throw std::runtime_error("Fixed edit contract accepted an incompatible request");
    };
    edit_reject(256,512,false,lma_mnn::EDIT_PROMPT,""); edit_reject(512,1024,false,lma_mnn::EDIT_PROMPT,"");
    edit_reject(512,512,true,lma_mnn::EDIT_PROMPT,""); edit_reject(512,512,false,"a teapot","");
    edit_reject(512,512,false,lma_mnn::EDIT_PROMPT,"negative");
    if (argc != 2 || lma_mnn::image_dimensions(argv[1]) != std::make_pair(512,512)) throw std::runtime_error("Actual selected PNG dimensions differ"); ++passed;
    auto image_reject = [&](const std::vector<unsigned char>& data) {
        { std::ofstream out("invalid-image.fixture", std::ios::binary); out.write(reinterpret_cast<const char*>(data.data()), data.size()); }
        try { lma_mnn::image_dimensions("invalid-image.fixture"); } catch(const std::exception&) { ++passed; return; }
        throw std::runtime_error("Oversized or malformed selected media passed the allocation guard");
    };
    image_reject({1,2,3}); image_reject(std::vector<unsigned char>(24,0));
    std::vector<unsigned char> png = {137,80,78,71,13,10,26,10,0,0,0,13,'I','H','D','R',0,0,16,0,0,0,16,0};
    image_reject(png); png[18]=0; image_reject(png); png[18]=2; png[11]=12; image_reject(png);
    image_reject(std::vector<unsigned char>(16*1024*1024+1,0));
    std::vector<unsigned char> jpeg = {255,216,255,192,0,8,8,2,0,2,0,1}; jpeg.resize(24,0);
    { std::ofstream out("jpeg-header.fixture",std::ios::binary); out.write(reinterpret_cast<const char*>(jpeg.data()),jpeg.size()); }
    if (lma_mnn::image_dimensions("jpeg-header.fixture") != std::make_pair(512,512)) throw std::runtime_error("JPEG header dimensions differ"); ++passed;
    jpeg[7]=16; jpeg[9]=16; image_reject(jpeg); jpeg[4]=255; jpeg[5]=255; image_reject(jpeg);
    std::cout << "{\"passed\":" << passed << ",\"model_inference\":false}";
}

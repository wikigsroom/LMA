#include "../../native/mnn/policy.hpp"
#include <iostream>
#include <limits>
int main() {
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
    std::cout << "{\"passed\":" << passed << ",\"model_inference\":false}";
}

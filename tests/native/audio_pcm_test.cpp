#include "../../native/audio_pcm.hpp"
#include <iostream>
#include <limits>

int main(){using namespace lma_audio;int passed=0;auto check=[&](bool ok){if(!ok)throw std::runtime_error("PCM assertion failed");passed++;};auto rejects=[&](auto fn){bool rejected=false;try{fn();}catch(const std::exception&){rejected=true;}check(rejected);};
    check(base64({0,0,255,127,1,128})=="AAD/fwGA");check(base64({0})=="AA==");check(base64({0,0})=="AAA=");
    int count=0;Stream stream(24000,1,6,3,[&](int sequence,int start,int frames,const std::string& data){check(sequence==count && start==count*3 && frames==3);if(count==0)check(data=="AAD/fwGA");count++;});
    stream.write({0,1,-1},24000);stream.write({0.5f,-0.5f,2},24000);check(stream.frames()==6 && stream.next()==2);rejects([&]{stream.write({0},24000);});stream.finish();rejects([&]{stream.finish();});rejects([&]{stream.write({0},24000);});
    auto emit=[](int,int,int,const std::string&){};rejects([&]{Stream bad(24000,3,10,1,emit);});rejects([&]{Stream bad(24000,1,24000*121,1,emit);});rejects([&]{Stream bad(24000,1,10,4801,emit);});
    Stream checked(24000,1,10,2,emit);rejects([&]{checked.write({},24000);});rejects([&]{checked.write({0},48000);});rejects([&]{checked.write({0,0,0},24000);});rejects([&]{checked.write({std::numeric_limits<float>::quiet_NaN()},24000);});rejects([&]{checked.finish();});
    std::cout<<"{\"passed\":"<<passed<<",\"model_inference\":false}"<<std::endl;
}

#include "../../native/qwen_tts/wave.hpp"
#include <iostream>
#include <limits>
#include <functional>
static int passed;
static void check(bool ok) { if(!ok) throw std::runtime_error("Native contract assertion failed");++passed; }
static void rejects(std::function<void()> action) { try{action();}catch(const std::exception&){++passed;return;}throw std::runtime_error("Invalid native input accepted"); }
static void put(std::vector<unsigned char>& b,size_t p,uint32_t value,int n=4){for(int i=0;i<n;++i)b[p+i]=static_cast<unsigned char>(value>>(8*i));}
static std::vector<unsigned char> wave(unsigned format=1,unsigned bits=16){std::vector<unsigned char>b(44+24000*bits/8);std::memcpy(b.data(),"RIFF",4);put(b,4,uint32_t(b.size()-8));std::memcpy(b.data()+8,"WAVEfmt ",8);put(b,16,16);put(b,20,format,2);put(b,22,1,2);put(b,24,24000);put(b,28,24000*bits/8);put(b,32,bits/8,2);put(b,34,bits,2);std::memcpy(b.data()+36,"data",4);put(b,40,uint32_t(b.size()-44));return b;}
static void save(const std::vector<unsigned char>& b){std::ofstream f("reference-fixture.wav",std::ios::binary);f.write(reinterpret_cast<const char*>(b.data()),b.size());}
int main(){
    using namespace lma_qwen;
    auto valid=[](){parameters(4,512,375,.9f,1,50,1.05f,42);};valid();check(true);
    rejects([](){parameters(0,512,375,.9f,1,50,1.05f,42);});rejects([](){parameters(33,512,375,.9f,1,50,1.05f,42);});
    rejects([](){parameters(4,2049,375,.9f,1,50,1.05f,42);});rejects([](){parameters(4,512,1501,.9f,1,50,1.05f,42);});
    rejects([](){parameters(4,512,375,std::numeric_limits<float>::quiet_NaN(),1,50,1.05f,42);});rejects([](){parameters(4,512,375,.9f,0,50,1.05f,42);});
    rejects([](){parameters(4,512,375,.9f,1,0,1.05f,42);});rejects([](){parameters(4,512,375,.9f,1,50,.9f,42);});rejects([](){parameters(4,512,375,.9f,1,50,1.05f,-1);});
    for(const std::string& s:{"auto","en","zh","ja","ko","de","fr","ru","pt","es","it"}){language(s);check(true);}rejects([](){language("unknown");});
    auto b=wave();save(b);check(reference_wave("reference-fixture.wav").size()==24000);
    b=wave(3,32);save(b);check(reference_wave("reference-fixture.wav").size()==24000);
    put(b,44,0x7fc00000);save(b);rejects([](){reference_wave("reference-fixture.wav");});
    put(b,44,0x40000000);save(b);rejects([](){reference_wave("reference-fixture.wav");});
    for(int mode=0;mode<6;++mode){b=wave();if(mode==0)put(b,4,1);if(mode==1)put(b,24,16000);if(mode==2)put(b,22,2,2);if(mode==3)put(b,40,0x7fffffff);if(mode==4)put(b,32,1,2);if(mode==5)b.pop_back();save(b);rejects([](){reference_wave("reference-fixture.wav");});}
    rejects([](){reference_wave("missing.wav");});std::remove("reference-fixture.wav");
    std::cout<<"{\"passed\":"<<passed<<",\"native_host_execution\":true,\"model_inference\":false}"<<std::endl;
}

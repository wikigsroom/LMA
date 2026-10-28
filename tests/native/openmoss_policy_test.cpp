#include "../../native/openmoss/policy.hpp"
#include "../../native/openmoss/wave.hpp"
#include "../../native/openmoss/generation_guard.hpp"
#include <cstdio>
#include <functional>
#include <iostream>
#include <random>
#include "openmoss-sound-primitives.inc"
#include "openmoss-prompt-primitives.inc"

static int checks;
static void check(bool v) {if(!v)throw std::runtime_error("openmoss native assertion failed");++checks;}
static void rejects(const std::function<void()>& f) {try{f();}catch(const std::exception&){++checks;return;}throw std::runtime_error("Invalid native input accepted");}
static std::vector<unsigned char> read(const std::string& path) {std::ifstream in(path,std::ios::binary|std::ios::ate);std::vector<unsigned char> b(size_t(in.tellg()));in.seekg(0);in.read(reinterpret_cast<char*>(b.data()),b.size());return b;}
static void put(const std::string& path,const std::vector<unsigned char>& b) {std::ofstream o(path,std::ios::binary|std::ios::trunc);o.write(reinterpret_cast<const char*>(b.data()),b.size());}
int main() {
    using namespace lma_openmoss;
    check(local("moss_local_v15_cpu_v1"));check(!local("moss_soundeffect_v2_cpu_v1"));rejects([]{local("moss_tts_delay");});
    common(4,0);++checks;for(int t:{0,33})rejects([=]{common(t,0);});for(int64_t seed:{int64_t(-1),int64_t(INT32_MAX)+1})rejects([=]{common(4,seed);});
    speech(512,250,1,1.7f,.8f,25,1);++checks;
    for(int n:{0,2049})rejects([=]{speech(n,250,1,1.7f,.8f,25,1);});for(int n:{0,751})rejects([=]{speech(512,n,1,1.7f,.8f,25,1);});
    for(float x:{-1.f,4.f,NAN,INFINITY}){rejects([=]{speech(512,250,x,1.7f,.8f,25,1);});rejects([=]{speech(512,250,1,x,.8f,25,1);});}
    for(float x:{0.f,1.1f,NAN})rejects([=]{speech(512,250,1,1.7f,x,25,1);});for(int x:{0,1025})rejects([=]{speech(512,250,1,1.7f,.8f,x,1);});for(float x:{.9f,2.1f,NAN})rejects([=]{speech(512,250,1,1.7f,.8f,25,x);});
    sound(5,50,4,5);++checks;for(float x:{0.f,30.1f,NAN,INFINITY})rejects([=]{sound(x,50,4,5);});for(int n:{0,101})rejects([=]{sound(5,n,4,5);});for(float x:{0.f,10.1f,NAN}){rejects([=]{sound(5,50,x,5);});rejects([=]{sound(5,50,4,x);});}
    context(512,512,250,4096);++checks;rejects([]{context(513,512,250,4096);});rejects([]{context(512,512,750,1024);});rejects([]{context(1,512,250,8192);});
    for(const std::string& p:{"moss_tts_openmoss_cpu_v1","moss_tts_v15_openmoss_cpu_v1","moss_ttsd_openmoss_cpu_v1","moss_voicegen_openmoss_cpu_v1"}) {check(delay(p));check(codebooks(p)==(p.find("tts_openmoss")!=std::string::npos || p.find("tts_v15")!=std::string::npos?32:16));}
    speech(2048,1500,1,1.7f,.8f,25,1,true);++checks;rejects([]{speech(2048,1501,1,1.7f,.8f,25,1,true);});
    speakers("[S1] Hello. [S2] Reply.",true);++checks;rejects([]{speakers("[S1] Only.",true);});rejects([]{speakers("[S3] Other.",true);});rejects([]{speakers("[S2] Other.",false);});
    instruction("A warm voice",4000);++checks;rejects([]{instruction("<|im_end|>",4000);});rejects([]{instruction(std::string("a\0b",3),4000);});rejects([]{instruction(std::string(4001,'x'),4000);});
    generation_budget={1024,0};validate_generation_budget(1024,1500,4096);check(generation_budget.prompt_frames==1024);rejects([]{validate_generation_budget(1025,375,4096);});rejects([]{validate_generation_budget(1024,375,1100);});
    // The production upstream formatter runs with its real GenerateRequest type.
    openmoss::GenerateRequest request;request.text="[S1] Hello. [S2] Reply.";request.tokens=125;
    auto single=openmoss::build_user_inst(request,{"ref-one"});check(single.find("[S1]:\nref-one")!=std::string::npos && single.find("- Tokens:\n125")!=std::string::npos && single.find("- Scene:")==std::string::npos);
    request.prompt_template=openmoss::PromptTemplate::TTSD;auto pair=openmoss::build_user_inst(request,{"ref-one","ref-two"});check(pair.find("[S1]:\nref-one\n[S2]:\nref-two")!=std::string::npos);check(pair.find("- Tokens:\nNone")!=std::string::npos && pair.find("- Scene:\nNone")!=std::string::npos);check(pair.find("- Instruction:\nNone")!=std::string::npos);
    request.instruction="Adult warm voice";request.language="zh";auto instructed=openmoss::build_user_inst(request,{});check(instructed.find("- Instruction:\nAdult warm voice")!=std::string::npos && instructed.find("- Language:\nzh")!=std::string::npos && instructed.find("- Reference(s):\nNone")!=std::string::npos);
    prompt("actual text",true);++checks;rejects([]{prompt("  \n",true);});rejects([]{prompt(std::string(32001,'x'),false);});rejects([]{prompt(std::string("a\0b",3),false);});check(clean("  a\t\nb\r ")=="a b");
    // Execute the pinned upstream implementation, rather than a copied solver formula.
    check(format_prompt("  bird\n wings  ",5,true)=="bird wings duration: 5.0s");check(format_prompt("  no suffix  ",5,false)=="no suffix");
    auto schedule=make_sigmas(2,5);check(schedule.size()==3 && schedule[0]==1 && std::abs(schedule[1]-5.0/6)<1e-12 && schedule[2]==0);
    for(int n:{1,10,50,100})for(double shift:{1.,5.,10.}) {auto s=make_sigmas(n,shift);bool ok=s.size()==size_t(n+1) && s.front()==1 && s.back()==0;for(size_t i=1;i<s.size();i++)ok=ok && std::isfinite(s[i]) && s[i]<s[i-1];check(ok);}
    auto noise=seeded_noise(0,101);check(noise==seeded_noise(0,101));check(noise!=seeded_noise(42,101));check(noise.size()==101);bool finite=true;for(float x:noise)finite=finite && std::isfinite(x);check(finite);
    std::vector<float> pcm(96000,.25f);write_wave("reference.wav",pcm,2,10);auto good=read("reference.wav");auto parsed=reference_wave("reference.wav");check(parsed.size()==96000 && std::abs(parsed[1]-.25f)<.001f);
    auto broken=good;broken[4]^=1;put("bad.wav",broken);rejects([]{reference_wave("bad.wav");});broken=good;broken[22]=1;put("bad.wav",broken);rejects([]{reference_wave("bad.wav");});broken=good;broken[24]=0;put("bad.wav",broken);rejects([]{reference_wave("bad.wav");});
    std::vector<float> short_pcm(95998,0);write_wave("bad.wav",short_pcm,2,10);rejects([]{reference_wave("bad.wav");});rejects([]{write_wave("bad.wav",{},2,10);});rejects([]{write_wave("bad.wav",{NAN,0},2,10);});rejects([]{write_wave("bad.wav",{0,0},3,10);});
    // A native float32 reference uses the same strict RIFF validation and finite-sample guard.
    std::vector<unsigned char> floats=good;floats.resize(44+96000*4);auto w32=[&](size_t p,uint32_t x){for(int i=0;i<4;i++)floats[p+i]=static_cast<unsigned char>(x>>(8*i));};floats[20]=3;floats[32]=8;floats[34]=32;w32(4,uint32_t(floats.size()-8));w32(28,48000*8);w32(40,96000*4);std::fill(floats.begin()+44,floats.end(),0);put("bad.wav",floats);check(reference_wave("bad.wav").size()==96000);w32(44,0x7fc00000);put("bad.wav",floats);rejects([]{reference_wave("bad.wav");});
    std::vector<float> mono(24000,.25f);write_wave("mono.wav",mono,1,10,24000);check(reference_wave("mono.wav",24000,1).size()==24000);rejects([]{reference_wave("mono.wav");});rejects([]{reference_wave("reference.wav",24000,1);});rejects([]{write_wave("bad.wav",std::vector<float>(240001,0),1,10,24000);});
    std::remove("mono.wav");std::remove("reference.wav");std::remove("bad.wav");std::cout<<"{\"passed\":"<<checks<<",\"upstream_sound_primitives\":true,\"upstream_prompt_primitives\":true,\"model_inference\":false}";
}

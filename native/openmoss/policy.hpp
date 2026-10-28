#pragma once
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace lma_openmoss {
inline void require(bool ok,const char* message) { if(!ok)throw std::runtime_error(message); }
inline bool local(const std::string& pipeline) {
    require(pipeline=="moss_local_v15_cpu_v1" || pipeline=="moss_soundeffect_v2_cpu_v1","Unknown openmoss pipeline");return pipeline=="moss_local_v15_cpu_v1";
}
inline void common(int threads,int64_t seed) { require(threads>=1 && threads<=32 && seed>=0 && seed<=INT32_MAX,"Invalid CPU thread/seed range"); }
inline void speech(int input,int steps,float text,float audio,float p,int k,float penalty) {
    require(input>=1 && input<=2048 && steps>=1 && steps<=750,"Invalid Local input/generation budget");
    require(std::isfinite(text) && text>=0 && text<=3 && std::isfinite(audio) && audio>=0 && audio<=3 && std::isfinite(p) && p>=.01f && p<=1 && k>=1 && k<=1024 && std::isfinite(penalty) && penalty>=1 && penalty<=2,"Invalid Local sampling parameters");
}
inline void sound(float seconds,int steps,float cfg,float shift) { require(std::isfinite(seconds) && seconds>=1 && seconds<=30 && steps>=1 && steps<=100 && std::isfinite(cfg) && cfg>=1 && cfg<=10 && std::isfinite(shift) && shift>=1 && shift<=10,"Invalid SoundEffect duration/sampler range"); }
inline void context(int prompt,int limit,int steps,int actual) { require(prompt>0 && prompt<=limit && actual<=4096 && prompt+steps+8<=actual,"Formatted prompt and generation exceed the selected context budget"); }
inline std::string clean(const std::string& s) { std::string out;bool pending=false;for(char c:s) { if(c==' ' || c=='\n' || c=='\r' || c=='\t' || c=='\f' || c=='\v')pending=!out.empty();else {if(pending)out+=' ';out+=c;pending=false;} }return out; }
inline void prompt(const std::string& s,bool required) { require((!required || !clean(s).empty()) && s.size()<=32000 && s.find('\0')==std::string::npos,"Invalid audio prompt length/content"); }
inline void waveform(const std::vector<float>& x,int channels,int max_seconds) {
    require((channels==1 || channels==2) && !x.empty() && x.size()%channels==0 && x.size()<=size_t(48000)*channels*max_seconds,"Empty or oversized audio output");for(float v:x)require(std::isfinite(v),"Nonfinite audio output");
}
}

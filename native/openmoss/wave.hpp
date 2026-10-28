#pragma once
#include "policy.hpp"
#include <algorithm>
#include <cstring>
#include <fstream>

namespace lma_openmoss {
inline uint32_t u32(const unsigned char* p) { return uint32_t(p[0]) | uint32_t(p[1])<<8 | uint32_t(p[2])<<16 | uint32_t(p[3])<<24; }
inline uint16_t u16(const unsigned char* p) { return uint16_t(p[0]) | uint16_t(p[1])<<8; }
inline std::vector<float> reference_wave(const std::string& path,int rate=48000,int channels=2) {
    require(rate==48000 && channels==2 || rate==24000 && channels==1,"Unsupported reference layout");
    std::ifstream in(path,std::ios::binary|std::ios::ate);require(bool(in) && in.tellg()>=44 && in.tellg()<=(rate==48000?4:1)*1024*1024,"Reference WAV exceeds the selected layout byte limit");
    std::vector<unsigned char> b(static_cast<size_t>(in.tellg()));in.seekg(0);in.read(reinterpret_cast<char*>(b.data()),b.size());
    require(bool(in) && !std::memcmp(b.data(),"RIFF",4) && !std::memcmp(b.data()+8,"WAVE",4) && u32(b.data()+4)==b.size()-8,"Invalid RIFF extent");
    unsigned format=0,bits=0;size_t start=0,length=0,chunks=0;
    for(size_t pos=12;pos<b.size();) {
        require(++chunks<=16384 && b.size()-pos>=8,"Invalid WAV chunks");const auto* h=b.data()+pos;uint32_t n=u32(h+4);size_t next=pos+8+size_t(n)+(n&1);require(next<=b.size(),"Truncated WAV chunk");
        if(!std::memcmp(h,"fmt ",4)) { require(!format && n>=16,"Duplicate or short WAV format");const auto* p=h+8;format=u16(p);bits=u16(p+14);unsigned align=bits/8*channels;
            require((format==1 && bits==16 || format==3 && bits==32) && u16(p+2)==channels && u32(p+4)==rate && u16(p+12)==align && u32(p+8)==rate*align,"Reference must match the selected sample rate/channels and PCM16/float32 format");
        } else if(!std::memcmp(h,"data",4)) {require(!start && n>0,"Duplicate or empty WAV data");start=pos+8;length=n;}pos=next;
    }
    require(format && start && length%(bits/8*channels)==0,"Missing or incomplete WAV data");size_t count=length/(bits/8);require(count>=size_t(rate)*channels && count<=size_t(rate)*channels*10,"Reference must be 1 to 10 seconds");
    std::vector<float> x(count);for(size_t i=0;i<count;++i) {const auto* p=b.data()+start+i*(bits/8);if(format==1)x[i]=int16_t(u16(p))/32768.f;else {uint32_t v=u32(p);std::memcpy(&x[i],&v,4);}require(std::isfinite(x[i]) && x[i]>=-1 && x[i]<=1,"Reference samples must be finite and normalized");}return x;
}
inline void write_wave(const std::string& path,const std::vector<float>& x,int channels,int max_seconds,int rate=48000) {
    waveform(x,channels,max_seconds,rate);std::ofstream out(path,std::ios::binary|std::ios::trunc);require(bool(out),"Cannot open WAV output");
    auto w16=[&](uint16_t v){out.put(char(v));out.put(char(v>>8));};auto w32=[&](uint32_t v){w16(uint16_t(v));w16(uint16_t(v>>16));};
    out.write("RIFF",4);w32(uint32_t(36+x.size()*2));out.write("WAVEfmt ",8);w32(16);w16(1);w16(uint16_t(channels));w32(rate);w32(rate*channels*2);w16(uint16_t(channels*2));w16(16);out.write("data",4);w32(uint32_t(x.size()*2));
    for(float v:x)w16(uint16_t(int16_t(std::round(std::max(-1.f,std::min(1.f,v))*32767.f))));out.flush();require(bool(out),"Cannot finish WAV output");
}
}

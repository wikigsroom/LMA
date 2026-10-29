#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <functional>
#include <stdexcept>
#include <string>
#include <vector>
#include <utility>

namespace lma_audio {
inline void require(bool value,const char* message) {if(!value)throw std::runtime_error(message);}
inline std::string base64(const std::vector<unsigned char>& bytes) {
    static const char* table="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string out;out.reserve((bytes.size()+2)/3*4);
    for(size_t i=0;i<bytes.size();i+=3) {uint32_t v=uint32_t(bytes[i])<<16;if(i+1<bytes.size())v|=uint32_t(bytes[i+1])<<8;if(i+2<bytes.size())v|=bytes[i+2];out+=table[v>>18];out+=table[v>>12&63];out+=i+1<bytes.size()?table[v>>6&63]:'=';out+=i+2<bytes.size()?table[v&63]:'=';}return out;
}
/** One owned worker, bounded PCM16 blocks. The final WAV uses the same quantization. */
class Stream {
public:
    using Emit=std::function<void(int,int,int,const std::string&)>;
    Stream(int rate,int channels,int max_frames,int max_chunk,Emit emit):rate_(rate),channels_(channels),limit_(max_frames),chunk_(max_chunk),emit_(std::move(emit)) {
        require(rate>=8000 && rate<=48000 && channels>=1 && channels<=2 && max_frames>=1 && max_frames<=rate*120 && int64_t(max_frames)*channels*2<=24*1024*1024 && max_chunk>=1 && max_chunk<=4800 && bool(emit_),"Invalid audio stream limits");
    }
    void write(const std::vector<float>& samples,int rate) {
        require(!ended_ && rate==rate_ && !samples.empty() && samples.size()%channels_==0,"Invalid audio stream block");
        int frames=int(samples.size()/channels_);require(frames<=chunk_ && frames<=limit_-frames_ && sequence_<4096,"Audio stream exceeds its frame boundary");
        std::vector<unsigned char> pcm;pcm.reserve(samples.size()*2);
        for(float value:samples) {require(std::isfinite(value),"Audio stream contains a nonfinite sample");uint16_t sample=uint16_t(int16_t(std::round(std::max(-1.f,std::min(1.f,value))*32767.f)));pcm.push_back(uint8_t(sample));pcm.push_back(uint8_t(sample>>8));}
        emit_(sequence_,frames_,frames,base64(pcm));sequence_++;frames_+=frames;
    }
    void finish() {require(!ended_ && sequence_>0,"Audio stream has no final boundary");ended_=true;}
    int frames() const{return frames_;}int next() const{return sequence_;}
private:
    int rate_,channels_,limit_,chunk_,frames_=0,sequence_=0;bool ended_=false;Emit emit_;
};
}

// SPDX-License-Identifier: MIT
#pragma once
#include "json.hpp"
#include "../../research/soulx_language/policy.hpp"
#include "../../research/soulx/dsp.hpp"
#include <cstring>
#include <filesystem>
#include <fstream>
#include <sstream>
#ifdef _WIN32
#include <codecvt>
#include <locale>
#endif

namespace lma_soulx_worker {
using json = nlohmann::json;
namespace fs = std::filesystem;
namespace lg = lma::soulx::language;
#ifdef _WIN32
template<class F> int wide_main(int argc, wchar_t** argv, F run) {
    std::wstring_convert<std::codecvt_utf8_utf16<wchar_t>> converter; std::vector<std::string> strings; std::vector<char*> pointers;
    for(int i=0;i<argc;++i) strings.push_back(converter.to_bytes(argv[i]));
    for(auto& value:strings) pointers.push_back(value.data()); pointers.push_back(nullptr); return run(argc,pointers.data());
}
#endif
inline void require(bool value, const char* message) { if (!value) throw std::invalid_argument(message); }
inline std::string read(const fs::path& path, size_t maximum) {
    auto bytes = fs::file_size(path); require(bytes && bytes <= maximum, "Missing or oversized SoulX input");
    std::string data(static_cast<size_t>(bytes), '\0'); std::ifstream file(path, std::ios::binary);
    require(bool(file.read(data.data(), static_cast<std::streamsize>(bytes))), "Cannot read SoulX input"); return data;
}
inline int integer(const json& p, const char* key, int low, int high) {
    const auto& x = p.at(key); require(x.is_number_integer() && x.get<double>() >= low && x.get<double>() <= high, "Invalid SoulX integer parameter"); return x.get<int>();
}
inline double number(const json& p, const char* key, double low, double high) {
    const auto& x = p.at(key); require(x.is_number(), "Invalid SoulX numeric parameter"); double v = x.get<double>(); require(std::isfinite(v) && v >= low && v <= high, "SoulX numeric parameter exceeds bounds"); return v;
}
struct Config {
    int context, threads, steps, seed, pause_ms, seconds; float cfg; lg::Sampling sampling; lg::Window window;
    explicit Config(const json& p) {
        require(p.is_object() && p.size() == 20, "Unknown or missing SoulX parameters");
        context = integer(p,"context",256,8192); threads = integer(p,"threads",1,32); steps = integer(p,"steps",1,100); seed = integer(p,"seed",0,2147483647);
        pause_ms = integer(p,"pauseMs",0,2000); seconds = integer(p,"maxOutputSeconds",1,960); cfg = static_cast<float>(number(p,"cfg",0,10));
        sampling.maximum = integer(p,"maxNewTokens",1,std::min(3000,context-64)); sampling.minimum = integer(p,"minNewTokens",0,sampling.maximum-1);
        sampling.temperature = number(p,"temperature",0,3); sampling.repetition = number(p,"repetitionPenalty",.01,10); sampling.top_k = integer(p,"topK",0,262144); sampling.top_p = number(p,"topP",.0001,1);
        require(p.at("useRas").is_boolean(), "SoulX useRas must be boolean"); sampling.ras = p.at("useRas").get<bool>(); sampling.window = integer(p,"rasWindow",1,256); sampling.tau = number(p,"rasTau",.0001,1);
        window.max_turns = integer(p,"maxHistoryTurns",5,64); window.history = integer(p,"historyTurns",1,std::min(8,window.max_turns-4)); window.text_history = integer(p,"textHistoryTurns",0,16); window.threshold = integer(p,"historyThreshold",128,context); lg::valid_sampling(sampling);
    }
};
inline std::string trim(const std::string& text) { size_t a = 0, b = text.size(); while(a < b && static_cast<unsigned char>(text[a]) <= 32) ++a; while(b > a && static_cast<unsigned char>(text[b-1]) <= 32) --b; return text.substr(a,b-a); }
inline void text(const std::string& value) {
    auto points = lg::unicode(value); size_t length = 0; for(auto c : points) length += c > 0xffff ? 2 : 1;
    require(!trim(value).empty() && length <= 4000, "SoulX text must contain 1-4000 UTF-16 units"); lg::plain_text(value);
}
struct Inputs { std::vector<std::string> transcripts; std::vector<lg::Turn> turns; };
inline Inputs inputs(const json& input) {
    require(input.is_object(), "Invalid SoulX input object");
    for(auto it = input.begin(); it != input.end(); ++it) require(it.key()=="prompt" || it.key()=="negativePrompt" || it.key()=="artifacts" || it.key()=="transcripts", "Unknown SoulX input field");
    require(input.value("negativePrompt",std::string()).empty(), "SoulX does not accept negative prompts");
    const auto& refs = input.at("artifacts"); const auto& transcripts = input.at("transcripts");
    require(refs.is_array() && refs.size() >= 1 && refs.size() <= 4 && transcripts.is_object() && transcripts.size() == refs.size(), "SoulX requires 1-4 paired references and transcripts");
    Inputs result; std::vector<bool> present(refs.size());
    for(const auto& ref : refs) {
        require(ref.is_object() && ref.size()==2 && ref.at("artifactId").is_string(), "Use bound local artifact IDs for SoulX references"); std::string role = ref.at("role");
        require(role.size()==12 && role.substr(0,11)=="reference_s" && role[11]>='1' && role[11]<='4', "Unknown SoulX reference role"); size_t index = static_cast<size_t>(role[11]-'1');
        require(index < present.size() && !present[index], "SoulX references must be unique and contiguous from S1"); present[index] = true;
    }
    for(size_t i=0; i<refs.size(); ++i) { require(present[i], "SoulX reference gap"); std::string value = transcripts.at("reference_s"+std::to_string(i+1)); text(value); result.transcripts.push_back(value); }
    std::string prompt = input.at("prompt"); text(prompt);
    if(prompt.find("[S") == std::string::npos) result.turns.push_back({prompt,0});
    else {
        std::istringstream lines(prompt); std::string raw;
        while(std::getline(lines,raw)) {
            auto line = trim(raw); if(line.empty()) continue;
            require(line.size()>=6 && line[0]=='[' && line[1]=='S' && line[2]>='1' && line[2]<='4' && line[3]==']', "Use one [S1] to [S4] utterance per line");
            int speaker = line[2]-'1'; require(static_cast<size_t>(speaker) < refs.size(), "SoulX speaker has no selected reference"); auto value = trim(line.substr(4)); text(value); require(value.find("[S")==std::string::npos, "Use one SoulX speaker marker per line"); result.turns.push_back({value,speaker});
        }
    }
    require(!result.turns.empty() && result.turns.size()<=64, "SoulX accepts 1-64 utterances"); return result;
}
inline uint16_t u16(const std::string& x, size_t n) { return uint16_t(static_cast<unsigned char>(x[n])) | uint16_t(static_cast<unsigned char>(x[n+1]))<<8; }
inline uint32_t u32(const std::string& x, size_t n) { return uint32_t(u16(x,n)) | uint32_t(u16(x,n+2))<<16; }
inline lma::soulx::Samples reference_wave(const fs::path& path) {
    auto x = read(path,1536000); require(x.size()>=44 && x.substr(0,4)=="RIFF" && x.substr(8,4)=="WAVE" && uint64_t(u32(x,4))+8==x.size(), "Reference must be a complete RIFF WAV");
    int format=0,bits=0; bool fmt=false; std::vector<std::pair<size_t,size_t>> chunks; size_t total=0,offset=12,count=0;
    while(offset<x.size()) {
        require(++count<=16384 && x.size()-offset>=8, "Invalid reference WAV chunks"); auto size=u32(x,offset+4); size_t start=offset+8; require(size<=x.size()-start, "Truncated reference WAV chunk");
        if(x.compare(offset,4,"fmt ")==0) {
            require(!fmt && size>=16 && size<=4096, "Duplicate or invalid WAV format"); fmt=true; format=u16(x,start); bits=u16(x,start+14);
            require(u16(x,start+2)==1 && u32(x,start+4)==24000 && (format==1 && bits==16 || format==3 && bits==32) && u16(x,start+12)==bits/8 && u32(x,start+8)==24000u*static_cast<unsigned>(bits/8), "Use mono 24kHz PCM16 or float32 reference WAV");
        } else if(x.compare(offset,4,"data")==0) { require(size>0, "Empty reference PCM chunk"); chunks.push_back({start,size}); total+=size; }
        offset=start+size+(size&1); require(offset<=x.size(), "Missing reference WAV padding");
    }
    require(fmt && !chunks.empty() && total%static_cast<size_t>(bits/8)==0, "Missing or misaligned reference PCM"); auto samples=total/static_cast<size_t>(bits/8); require(samples>=24000 && samples<=360000, "Reference must be 1-15 seconds");
    lma::soulx::Samples result; result.reserve(samples);
    for(auto chunk:chunks) { require(chunk.second%static_cast<size_t>(bits/8)==0, "Misaligned reference PCM chunk"); for(size_t n=chunk.first; n<chunk.first+chunk.second; n+=bits/8) {
        float value; if(format==1) { auto raw=u16(x,n); int signed_value=raw>=32768 ? int(raw)-65536 : int(raw); value=static_cast<float>(signed_value)/32768; }
        else { auto raw=u32(x,n); std::memcpy(&value,&raw,4); }
        require(std::isfinite(value) && std::abs(value)<=1, "Reference PCM must be finite and normalized"); result.push_back(value);
    }} return result;
}
class Wave {
    fs::path part_; std::ofstream stream_; size_t limit_,samples_=0; bool committed_=false;
    void le(uint32_t n,int bytes) { for(int i=0;i<bytes;++i) stream_.put(static_cast<char>((n>>(i*8))&255)); }
public:
    double peak=0; size_t clipped=0;
    Wave(const fs::path& part,int seconds):part_(part),limit_(static_cast<size_t>(seconds)*24000) { require(!fs::exists(part), "SoulX temporary output must be new"); stream_.open(part,std::ios::binary); require(bool(stream_), "Cannot create SoulX private WAV"); for(int i=0;i<44;++i) stream_.put(0); }
    ~Wave() { stream_.close(); if(!committed_) { std::error_code ignored; fs::remove(part_,ignored); } }
    size_t samples() const { return samples_; }
    void append(const lma::soulx::Samples& pcm) {
        require(pcm.size()<=limit_-samples_, "SoulX output exceeds requested duration");
        for(float sample:pcm) { require(std::isfinite(sample), "Non-finite SoulX waveform"); peak=std::max(peak,static_cast<double>(std::abs(sample))); if(std::abs(sample)>1) ++clipped; auto value=static_cast<int32_t>(std::lround(std::clamp(sample,-1.f,1.f)*32767)); le(static_cast<uint16_t>(value),2); }
        samples_+=pcm.size(); require(bool(stream_), "Cannot write SoulX waveform");
    }
    void silence(size_t count) { require(count<=limit_-samples_, "SoulX pause exceeds requested duration"); for(size_t i=0;i<count;++i) le(0,2); samples_+=count; require(bool(stream_), "Cannot write SoulX pause"); }
    void commit(const fs::path& destination) {
        require(samples_>0 && !fs::exists(destination), "SoulX output must be a new nonempty file"); stream_.seekp(0); stream_.write("RIFF",4); le(static_cast<uint32_t>(36+samples_*2),4); stream_.write("WAVEfmt ",8); le(16,4); le(1,2); le(1,2); le(24000,4); le(48000,4); le(2,2); le(16,2); stream_.write("data",4); le(static_cast<uint32_t>(samples_*2),4); stream_.flush(); require(bool(stream_), "Cannot finalize SoulX WAV"); stream_.close(); require(!stream_.fail(), "Cannot close SoulX WAV"); fs::rename(part_,destination); committed_=true;
    }
};
}

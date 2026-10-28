// SPDX-License-Identifier: MIT
#include "../../native/soulx/contract.hpp"
#include <iostream>
using namespace lma_soulx_worker;
static int passed=0;
static void check(bool yes) { if(!yes) throw std::runtime_error("SoulX contract assertion"); ++passed; }
template<class F> void rejects(F action) { try { action(); } catch(const std::exception&) { ++passed; return; } throw std::runtime_error("Expected SoulX contract rejection"); }
static json parameters() { return {{"context",4096},{"threads",4},{"maxNewTokens",512},{"minNewTokens",8},{"temperature",.6},{"repetitionPenalty",1.25},{"topK",100},{"topP",.9},{"useRas",true},{"rasWindow",25},{"rasTau",.2},{"maxHistoryTurns",10},{"historyTurns",2},{"textHistoryTurns",2},{"historyThreshold",4096},{"steps",15},{"cfg",.7},{"seed",42},{"pauseMs",200},{"maxOutputSeconds",120}}; }
static json request() { return {{"prompt","[S1] First local utterance.\n[S2] Second local utterance."},{"artifacts",json::array({{{"role","reference_s2"},{"artifactId","two"}},{{"role","reference_s1"},{"artifactId","one"}}})},{"transcripts",{{"reference_s1","First reference."},{"reference_s2","Second reference."}}}}; }
static void write(const fs::path& file,const std::string& data) { std::ofstream out(file,std::ios::binary); out.write(data.data(),static_cast<std::streamsize>(data.size())); check(bool(out)); }
static int execute(int argc,char** argv) {
    try {
        require(argc==2,"Pass owned test output directory"); auto dir=fs::u8path(argv[1]); fs::create_directories(dir);
        Config good(parameters()); check(good.context==4096 && good.sampling.maximum==512);
        for(const auto& pair:std::vector<std::pair<std::string,double>>{{"context",8193},{"threads",0},{"steps",101},{"seed",-1},{"pauseMs",2001},{"maxOutputSeconds",961},{"cfg",11},{"maxNewTokens",3001},{"minNewTokens",512},{"temperature",4},{"repetitionPenalty",0},{"topK",-1},{"topP",0},{"rasWindow",0},{"rasTau",2},{"maxHistoryTurns",4},{"historyTurns",7},{"textHistoryTurns",17},{"historyThreshold",4097}}) {
            auto p=parameters(); if(p[pair.first].is_number_integer()) p[pair.first]=static_cast<int>(pair.second); else p[pair.first]=pair.second; rejects([&]{Config invalid(p);});
        }
        for(const char* key:{"context","threads","steps","seed","maxNewTokens","pauseMs"}) { auto p=parameters(); p[key]=2.5; rejects([&]{Config invalid(p);}); }
        auto p=parameters();p["useRas"]="true";rejects([&]{Config invalid(p);});p=parameters();p["temperature"]=0;rejects([&]{Config invalid(p);});p["useRas"]=false;check(Config(p).sampling.temperature==0);
        p=parameters();p["unknown"]=1;rejects([&]{Config invalid(p);});p=parameters();p.erase("cfg");rejects([&]{Config invalid(p);});
        auto input=request();auto parsed=inputs(input);check(parsed.transcripts.size()==2 && parsed.turns.size()==2 && parsed.turns[1].speaker==1);
        for(const char* prompt:{"", " \n", "[S3] Missing speaker.", "[S0] Invalid speaker.", "[S1] First. [S2] Inline.", "[S1] First.\nMissing tag.", "<|task_podcast|>"}) { auto value=input;value["prompt"]=prompt;rejects([&]{inputs(value);}); }
        auto value=input;value["prompt"]="Plain\nmultiline text.";check(inputs(value).turns.size()==1);
        value=input;value["transcripts"].erase("reference_s2");rejects([&]{inputs(value);});value=input;value["transcripts"]["reference_s2"]=" ";rejects([&]{inputs(value);});value=input;value["artifacts"][0]["role"]="reference_s3";rejects([&]{inputs(value);});value=input;value["artifacts"][0]["role"]="reference_s1";rejects([&]{inputs(value);});value=input;value["artifacts"][0]["url"]="https://example.com";rejects([&]{inputs(value);});
        rejects([]{text(std::string(4001,'a'));});rejects([]{text(std::string("a\0b",3));});rejects([]{text("\xc0\x80");});
        auto part=dir/"wave.part",wave=dir/"wave.wav";
        { Wave writer(part,2); writer.append(lma::soulx::Samples(24000,.125f));writer.silence(24000);check(writer.samples()==48000);writer.commit(wave); }
        auto pcm=reference_wave(wave);check(pcm.size()==48000 && std::abs(pcm[0]-.125f)<.0001f && pcm.back()==0);
        rejects([&]{Wave invalid(wave,1);});
        auto original=read(wave,1536000);
        for(const auto& mutation:std::vector<std::pair<size_t,char>>{{0,'X'},{4,0},{20,2},{22,2},{24,0},{32,3},{34,24},{40,1}}) { auto bytes=original;bytes[mutation.first]=mutation.second;auto bad=dir/"bad.wav";write(bad,bytes);rejects([&]{reference_wave(bad);}); }
        auto truncated=original.substr(0,original.size()-1);write(dir/"truncated.wav",truncated);rejects([&]{reference_wave(dir/"truncated.wav");});
        { Wave writer(part,1);rejects([&]{writer.append(lma::soulx::Samples(24001,0));});rejects([&]{writer.append({std::numeric_limits<float>::quiet_NaN()});}); }
        check(!fs::exists(part));
        std::string float_wave=original.substr(0,44);float_wave[20]=3;float_wave[34]=32;float_wave[32]=4;
        auto set32=[&](size_t off,uint32_t n){for(int i=0;i<4;++i)float_wave[off+i]=static_cast<char>((n>>(8*i))&255);};set32(4,36+96000);set32(28,96000);set32(40,96000);float_wave.resize(44+96000,0);write(dir/"float.wav",float_wave);check(reference_wave(dir/"float.wav").size()==24000);
        float_wave[44]=0;float_wave[45]=0;float_wave[46]=char(0xc0);float_wave[47]=char(0x7f);write(dir/"nan.wav",float_wave);rejects([&]{reference_wave(dir/"nan.wav");});
        std::cout<<json({{"passed",passed},{"neural_inference",false},{"scope","production_contract_bounds_and_wav"}}).dump()<<'\n';return 0;
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
#ifdef _WIN32
int wmain(int argc,wchar_t** argv) { return wide_main(argc,argv,execute); }
#else
int main(int argc,char** argv) { return execute(argc,argv); }
#endif

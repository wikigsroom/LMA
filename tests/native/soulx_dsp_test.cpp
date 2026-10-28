// SPDX-License-Identifier: MIT
// File transport is host-test-only. The production library has no file/network IO.
#include "../../research/soulx/dsp.hpp"
#include <cmath>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
using namespace lma::soulx;
Samples read(const std::string& path) {
    std::ifstream f(path,std::ios::binary|std::ios::ate);
    auto bytes=f.tellg();
    if (!f || bytes<0 || bytes%4 || bytes>128*1024*1024) throw std::runtime_error("Bad fixture bytes");
    Samples x(static_cast<size_t>(bytes)/4); f.seekg(0); f.read(reinterpret_cast<char*>(x.data()),bytes);
    if (!f) throw std::runtime_error("Fixture read failed"); return x;
}
void write(const std::string& path,const Samples& x,size_t rows=1,size_t cols=0) {
    std::ofstream f(path,std::ios::binary); f.write(reinterpret_cast<const char*>(x.data()),x.size()*4);
    if (!f) throw std::runtime_error("Fixture write failed");
    std::cout<<"{\"rows\":"<<rows<<",\"cols\":"<<(cols?cols:x.size())<<"}\n";
}
int main(int argc,char** argv) {
    try {
        if (argc<4) throw std::runtime_error("Operation/input/output required");
        std::string op=argv[1]; Samples x=read(argv[2]); std::string out=argv[3];
        Matrix result;
        if (op=="normalize") write(out,normalize_volume(x));
        else if (op=="resample") write(out,resample_24k_to_16k(x));
        else if (op=="s3") { result=semantic_features(x); write(out,result.values,result.rows,result.cols); }
        else if (op=="flow") { result=flow_features(x); write(out,result.values,result.rows,result.cols); }
        else if (op=="speaker") { result=speaker_features(x); write(out,result.values,result.rows,result.cols); }
        else if (op=="stft") { result=source_stft(x); write(out,result.values,result.rows,result.cols); }
        else if (op=="filters") {
            if (x.size()!=1) throw std::runtime_error("Filter fixture selector");
            result=x[0]==128?slaney_filters(16000,400,128,8000):slaney_filters(24000,1920,80,8000);
            write(out,result.values,result.rows,result.cols);
        } else if (op=="istft") {
            if (argc!=5 || x.empty() || x.size()%9) throw std::runtime_error("ISTFT fixture layout");
            Matrix m{9,x.size()/9,x}; Samples p=read(argv[4]); Matrix phase{9,p.size()/9,p};
            write(out,hift_istft(m,phase));
        } else if (op=="nsf") {
            if (argc!=5) throw std::runtime_error("NSF noise fixture required");
            Samples noise=read(argv[4]), emitted; size_t cursor=0; emitted.reserve(noise.size());
            nsf_harmonics(x,[&](){return noise.at(cursor++);},[&](size_t,const std::array<float,9>& v){emitted.insert(emitted.end(),v.begin(),v.end());});
            if (cursor!=noise.size()) throw std::runtime_error("Unused NSF fixture noise");
            write(out,emitted,emitted.size()/9,9);
        } else if (op=="schedule") write(out,cosine_schedule(static_cast<int>(x.at(0))));
        else if (op=="euler") {
            if (x.size()<5 || (x.size()-2)%3) throw std::runtime_error("Euler fixture layout");
            size_t n=(x.size()-2)/3; Samples state(x.begin()+2,x.begin()+2+n),c(x.begin()+2+n,x.begin()+2+2*n),u(x.begin()+2+2*n,x.end());
            euler_step(state,c,u,x[0],x[1]);write(out,state);
        } else if (op=="reference") {
            auto features=reference_features(x);
            write(out+".s3",features.semantic.values,features.semantic.rows,features.semantic.cols);
            write(out+".flow",features.flow.values,features.flow.rows,features.flow.cols);
            write(out+".speaker",features.speaker.values,features.speaker.rows,features.speaker.cols);
        } else if (op=="cancel") {
            int calls=0; bool stopped=false;
            try { reference_features(x,[&](){ return ++calls>4; }); }
            catch (const std::runtime_error& e) { stopped=std::string(e.what())=="SoulX DSP cancelled"; }
            if (!stopped) throw std::runtime_error("Cancellation not observed");
            write(out,{static_cast<float>(calls)});
        } else if (op=="guards") {
            size_t passed=0;
            auto rejects=[&](auto f){bool rejected=false;try{f();}catch(const std::exception&){rejected=true;}if(!rejected)throw std::runtime_error("Guard did not reject");++passed;};
            rejects([&]{normalize_volume({});}); rejects([&]{normalize_volume({NAN});});
            rejects([&]{reference_features(Samples(23999));}); rejects([&]{reference_features(Samples(kMaxReference24k+1));});
            rejects([&]{semantic_features(Samples(200));}); rejects([&]{semantic_features(Samples(240001));});
            rejects([&]{flow_features(Samples(720));}); rejects([&]{speaker_features(Samples(399));});
            rejects([&]{semantic_features(Samples(1600,1e20f));}); rejects([&]{flow_features(Samples(4800,1e20f));});
            rejects([&]{Samples huge(1600,1e30f); huge[200]=-1e30f; speaker_features(huge);});
            rejects([&]{cosine_schedule(0);}); rejects([&]{cosine_schedule(101);});
            rejects([&]{align_prompt(0,10);}); rejects([&]{align_prompt(1,1);}); rejects([&]{align_prompt(376,750);});
            auto aligned=align_prompt(5,8); if(aligned.token_count!=4 || aligned.mel_frames!=8) throw std::runtime_error("Alignment");++passed;
            aligned=align_prompt(5,12);if(aligned.token_count!=5 || aligned.mel_frames!=10) throw std::runtime_error("Mel crop");++passed;
            Samples state{1,2};
            rejects([&]{euler_step(state,{1},{1},.1f);}); rejects([&]{euler_step(state,{1,1},{1,1},0);});
            rejects([&]{euler_step(state,{1,1},{1,1},.1f,-1);}); rejects([&]{euler_step(state,{1,NAN},{1,1},.1f);});
            if (state!=Samples({1,2})) throw std::runtime_error("Failed Euler mutated state"); ++passed;
            rejects([&]{source_stft(Samples(481));}); rejects([&]{hift_istft({8,121,Samples(8*121)},{9,121,Samples(9*121)});});
            rejects([&]{hift_istft({9,120,Samples(9*120)},{9,120,Samples(9*120)});});
            rejects([&]{hift_istft({9,121,Samples(9*121,-1)},{9,121,Samples(9*121)});});
            rejects([&]{nsf_harmonics({-1},[]{return 0.f;},[](size_t,const std::array<float,9>&){});});
            rejects([&]{nsf_harmonics({200},[]{return NAN;},[](size_t,const std::array<float,9>&){});});
            write(out,{static_cast<float>(passed)});
        } else throw std::runtime_error("Unknown DSP fixture operation");
        return 0;
    } catch(const std::exception& e) { std::cerr<<e.what()<<'\n';return 1; }
}

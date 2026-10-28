// Host tests of production validation, real LiteRT C API and Arm sampler equivalence.
#include "../../native/stable_audio/litert_model.hpp"
#include <iostream>
#include <limits>
using namespace lma_sao;
static int passed;
static void ok(bool value){if(!value)throw std::runtime_error("Stable Audio native assertion failed");++passed;}
template<class F>static void rejects(F f){try{f();}catch(const std::exception&){++passed;return;}throw std::runtime_error("Invalid input accepted");}
// Extracted verbatim at build time from pinned Apache-2.0 Arm source.
#include "arm_sampler_reference.hpp"
int main(int argc,char** argv){try{
    require(argc==2,"Pass private fixture directory");std::string dir=argv[1];
    for(int s:{1,5,11}){bounds(4,42,s,8,64);ok(true);}for(int s:{0,12})rejects([=]{bounds(4,42,s,8,64);});for(int n:{0,33})rejects([=]{bounds(4,42,5,n,64);});rejects([]{bounds(0,42,5,8,64);});rejects([]{bounds(4,-1,5,8,64);});rejects([]{bounds(4,42,5,8,65);});
    prompt("rain in the forest");ok(true);for(const std::string s:{std::string(),std::string(" \r\n\t"),std::string(16001,'a'),std::string("a\0b",3)})rejects([&]{prompt(s);});
    std::vector<int> ids{42,51};token_ids(ids,64,32000,0,1);ok(ids==std::vector<int>({42,51,1}));rejects([&]{token_ids(ids,2,32000,0,1);});rejects([&]{token_ids(ids,64,32100,0,1);});ids={32000};rejects([&]{token_ids(ids,64,32000,0,1);});ids.assign(64,42);rejects([&]{token_ids(ids,64,32000,0,1);});ids.assign(63,42);token_ids(ids,64,32000,0,1);ok(ids.size()==64 && ids.back()==1);
    for(int steps:{1,4,8,32}){
        auto actual=schedule(steps);std::vector<float> expected(size_t(steps)+1);arm_reference::fill_sigmas(expected,-6,2,1);ok(actual==expected);
        std::vector<float> x(64),v(64),ref_x(64),ref_v(64);random_normal(x,42);arm_reference::fill_random_norm_dist(ref_x.data(),ref_x.size(),42);ok(x==ref_x);random_normal(v,19);
        for(int step=0;step<steps;step++){ref_v=v;advance(x,v,actual[size_t(step)],actual[size_t(step)+1],42+step+4564);arm_reference::sampler_ping_pong(ref_v.data(),ref_x.data(),ref_x.size(),actual[size_t(step)],actual[size_t(step)+1],size_t(step),42+step+4564);ok(x==ref_x);}
    }
    std::vector<float> x{1,2},v{1,2};v[0]=std::numeric_limits<float>::quiet_NaN();rejects([&]{advance(x,v,1,0,1);});ok(cpu_options(3).find("num_threads = 3")!=std::string::npos);
    std::vector<float> planar(2*decoded_frames,0);planar[0]=2;planar[decoded_frames]=-1;auto audio=pcm(planar,1);ok(audio.size()==88200 && audio[0]==32767 && audio[1]==-16384 && audio[2]==0);write_wave(dir+"/native-fixture.wav",audio);ok(true);planar.back()=std::numeric_limits<float>::infinity();rejects([&]{pcm(planar,1);});rejects([&]{pcm({},1);});
    Environment env;check(LiteRtCreateEnvironment(0,nullptr,&env.value),"Cannot create host environment");
    // Three actual load/run/unload cycles per tiny graph; neither is a trained checkpoint.
    for(int load=0;load<3;load++){
        {Model model(env,dir+"/tiny-add.tflite",2,{f32({1,4})},{f32({1,4})});model.write(0,std::vector<float>{10,20,30,40});model.run();ok(model.read(0)==std::vector<float>({11,22,33,44}));rejects([&]{model.write(0,std::vector<float>{1});});}
        {Model model(env,dir+"/tiny-cast.tflite",2,{i64({1,4})},{f32({1,4})});model.write(0,std::vector<int64_t>{-10,0,7,128});model.run();ok(model.read(0)==std::vector<float>({-10,0,7,128}));}
    }
    rejects([&]{Model model(env,dir+"/tiny-add.tflite",2,{f32({1,3})},{f32({1,4})});});rejects([&]{Model model(env,dir+"/tiny-add.tflite",2,{i64({1,4})},{f32({1,4})});});rejects([&]{Model model(env,dir+"/tiny-add.tflite",2,{f32({1,4})},{});});rejects([&]{Model model(env,dir+"/missing.tflite",2,{f32({1,4})},{f32({1,4})});});
    std::cout<<"{\"passed\":"<<passed<<",\"actual_litert_graph_runs\":6,\"model_checkpoint\":false,\"arm_sampler_equivalence\":true}"<<std::endl;return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<std::endl;return 1;}}

#include "../../native/moss-rq/policy.hpp"
#include <iostream>
using namespace lma_moss_rq;
static int passed;
static void check(bool v){if(!v)throw std::runtime_error("RQ native assertion failed");++passed;}
template<class F>static void rejects(F f){try{f();}catch(const std::exception&){++passed;return;}throw std::runtime_error("Invalid RQ input accepted");}
int main(){
    check(realtime("moss_realtime_rq_cpu_v1"));check(!realtime("moss_local_v10_rq_cpu_v1"));rejects([]{realtime("moss_local_v15_cpu_v1");});
    for(int input:{1,1024,2048})for(int steps:{1,375,750}){budget(input,steps);++passed;}
    for(int input:{0,2049})rejects([=]{budget(input,1);});for(int steps:{0,751})rejects([=]{budget(1024,steps);});
    sampling(.8f,.6f,30,1.1f);++passed;for(float n:{-1.f,4.f,NAN})rejects([=]{sampling(n,.6f,30,1.1f);});rejects([]{sampling(.8f,0,30,1.1f);});rejects([]{sampling(.8f,.6f,0,1.1f);});rejects([]{sampling(.8f,.6f,30,.9f);});
    run=Run{};run.input_limit=1024;int events=0;run.notify=[&](const std::string&,int,int){++events;};before_prefill(200,24,13,375);check(run.prefill==200 && run.remaining_text==24 && run.reference_frames==13);step(1,375);step(8,375);before_codec(7,false);check(run.steps==8 && run.output_frames==7 && !run.stopped && events==4 && run.prefill_ms>=0 && run.generation_ms>=0);
    rejects([]{before_prefill(1024,1,0,375);});rejects([]{before_prefill(1,376,0,375);});rejects([]{before_prefill(0,0,0,375);});rejects([]{before_codec(9,true);});
    run=Run{};run.input_limit=2048;before_prefill(2048,0,0,750);step(1,750);before_codec(0,true);check(run.stopped && run.output_frames==0);
    std::cout<<"{\"passed\":"<<passed<<",\"model_inference\":false}"<<std::endl;
}

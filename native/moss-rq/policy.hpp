#pragma once
#include "../openmoss/policy.hpp"
#include <chrono>
#include <functional>

namespace lma_moss_rq {
using lma_openmoss::require;
using Clock=std::chrono::steady_clock;
inline bool realtime(const std::string& pipeline) {
    require(pipeline=="moss_local_v10_rq_cpu_v1" || pipeline=="moss_realtime_rq_cpu_v1","Unknown MOSS RQ pipeline");return pipeline=="moss_realtime_rq_cpu_v1";
}
inline void sampling(float temp,float p,int k,float penalty) {
    require(std::isfinite(temp) && temp>=0 && temp<=3 && std::isfinite(p) && p>=.01f && p<=1 && k>=1 && k<=1024 && std::isfinite(penalty) && penalty>=1 && penalty<=2,"Invalid RQ sampling bounds");
}
inline void budget(int input,int steps) {require(input>=1 && input<=2048 && steps>=1 && steps<=750,"Invalid RQ input/generation budget");}
struct Run {
    int input_limit=0,prefill=0,remaining_text=0,reference_frames=0,steps=0,output_frames=0;bool stopped=false;
    double prefill_ms=0,generation_ms=0;Clock::time_point prefill_start,generation_start,codec_start;
    std::function<void(const std::string&,int,int)> notify;
};
inline thread_local Run run;
inline void before_prefill(int prefill,int remaining,int references,int max_steps) {
    budget(run.input_limit,max_steps);
    require(prefill>0 && remaining>=0 && references>=0 && prefill+remaining<=run.input_limit && prefill+max_steps+8<=4096,"Formatted prompt/text stream and generation exceed the selected RQ budget");
    require(remaining<=max_steps,"Generation budget cannot consume the remaining Realtime text; shorten text or raise the frame limit");
    run.prefill=prefill;run.remaining_text=remaining;run.reference_frames=references;run.prefill_start=Clock::now();if(run.notify)run.notify("prefilling",0,0);
}
inline void step(int step,int total) {
    if(step==1) {run.generation_start=Clock::now();run.prefill_ms=std::chrono::duration<double,std::milli>(run.generation_start-run.prefill_start).count();}
    run.steps=step;if(run.notify && (step==1 || step%8==0 || step==total))run.notify("generating_audio",step,total);
}
inline void before_codec(int frames,bool stopped) {
    require(frames>=0 && frames<=run.steps,"Invalid RQ generated frame count");run.output_frames=frames;run.stopped=stopped;run.codec_start=Clock::now();run.generation_ms=std::chrono::duration<double,std::milli>(run.codec_start-run.generation_start).count();if(run.notify)run.notify("decoding_audio",0,0);
}
}

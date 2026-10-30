#pragma once
#include "policy.hpp"

// Called from the generated copy of the pinned pipeline, after its actual
// multi-reference/prefix grid is built and before any prefill or sampling.
namespace lma_openmoss {
struct GenerationBudget { int input_limit=0;int prompt_frames=0;std::string ambient_sound="None"; };
inline thread_local GenerationBudget generation_budget;
struct GenerationTrace {
    int steps=0;int limit=0;bool end_of_speech=false;
    void (*progress)(int,int)=nullptr;
    void (*decoding)()=nullptr;
};
inline thread_local GenerationTrace generation_trace;
inline void validate_generation_budget(int prompt,int steps,int actual_context) {
    context(prompt,generation_budget.input_limit,steps,actual_context);
    generation_budget.prompt_frames=prompt;
    generation_trace.steps=0;generation_trace.limit=steps;generation_trace.end_of_speech=false;
    if(generation_trace.progress)generation_trace.progress(0,steps);
}
// Invoked immediately after the actual pinned frame decoder samples each step,
// including the terminating step. No simulated timers or estimated token counts.
inline void generation_step(int step,int limit,bool end_of_speech) {
    require(limit==generation_trace.limit && step==generation_trace.steps+1 && step<=limit && !generation_trace.end_of_speech,"Invalid generation progress sequence");
    generation_trace.steps=step;generation_trace.end_of_speech=end_of_speech;
    if(generation_trace.progress)generation_trace.progress(step,limit);
}
inline void generation_decoding() {if(generation_trace.decoding)generation_trace.decoding();}
}

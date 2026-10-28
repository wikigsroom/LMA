#pragma once
#include "policy.hpp"

// Called from the generated copy of the pinned pipeline, after its actual
// multi-reference/prefix grid is built and before any prefill or sampling.
namespace lma_openmoss {
struct GenerationBudget { int input_limit=0;int prompt_frames=0;std::string ambient_sound="None"; };
inline thread_local GenerationBudget generation_budget;
inline void validate_generation_budget(int prompt,int steps,int actual_context) {
    context(prompt,generation_budget.input_limit,steps,actual_context);
    generation_budget.prompt_frames=prompt;
}
}

#pragma once
#include "../worker_common.hpp"
namespace lma_shape {
inline float sigma(int i,int steps,float shift){float t=1-float(i)/steps;return shift*t/(1+(shift-1)*t);}
inline void flow_step(std::vector<float>& state,const std::vector<float>& velocity,int i,int steps,float shift){
 lma_worker::require(state.size()==velocity.size()&&i>=0&&i<steps,"Invalid RF step");
 // The pinned TripoSG/PartCrafter RF predicts the opposite direction to SD3.
 float dt=sigma(i,steps,shift)-sigma(i+1,steps,shift);
 for(size_t j=0;j<state.size();j++){state[j]+=dt*velocity[j];lma_worker::require(std::isfinite(state[j]),"Nonfinite RF state");}
}
}

#pragma once
#include "../worker_common.hpp"
namespace lma_spatial {
// These publishers supply ascending linspace(0,1,steps), followed by 1.
// This is intentionally different from the RF Shape sampler.
inline float spatial_sigma(int i,int steps,float shift){
 lma_worker::require(steps>=1&&i>=0&&i<=steps&&std::isfinite(shift)&&shift>0,"Invalid spatial schedule");
 float x=i>=steps?1.f:steps==1?0.f:float(i)/(steps-1);return shift*x/(1+(shift-1)*x);
}
}

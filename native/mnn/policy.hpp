#pragma once
#include <cmath>
#include <stdexcept>
#include <string>
namespace lma_mnn {
inline void parameters(int width, int height, int steps, int threads, int maximum_tokens, bool cfg, float scale, const std::string& negative) {
    if (width < 256 || width > 2048 || height < 256 || height > 2048 || width % 32 || height % 32) throw std::runtime_error("Sana dimensions must be 256..2048 and multiples of 32");
    if (steps < 1 || steps > 50 || threads < 1 || threads > 32 || maximum_tokens < 1 || maximum_tokens > 1792) throw std::runtime_error("Sana application parameter guard exceeded");
    if (!std::isfinite(scale) || scale < 0 || scale > 30 || (!cfg && !negative.empty())) throw std::runtime_error("Negative conditioning requires enabled Sana CFG");
}
}

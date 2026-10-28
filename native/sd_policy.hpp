#pragma once
#include <cmath>
#include <stdexcept>
#include <string>

namespace lma_sd {
inline void route(const std::string& pipeline, const std::string& architecture, const std::string& detected) {
    std::string expected, version;
    if (pipeline == "sd15" || pipeline == "sd15_lcm") { expected = "sd15"; version = "SD 1.x"; }
    else if (pipeline == "sdxl" || pipeline == "sdxl_lcm") { expected = "sdxl"; version = "SDXL"; }
    else if (pipeline == "sd21_turbo") { expected = "sd21"; version = "SD 2.x"; }
    if (!expected.empty() && (architecture != expected || detected != version)) throw std::runtime_error("Loaded tensor architecture does not match the selected diffusion recipe");
}
inline void sampling(const std::string& profile, const std::string& pipeline, const std::string& method,
                     const std::string& schedule, int steps, float cfg, const std::string& negative) {
    if (profile != "standard" && profile != "lcm" && profile != "sd_turbo") throw std::runtime_error("Unknown signed diffusion sampling policy");
    bool lcm_checkpoint = pipeline == "sd15_lcm" || pipeline == "sdxl_lcm";
    if ((lcm_checkpoint && profile != "lcm") || (pipeline == "sd21_turbo" && profile != "sd_turbo")) throw std::runtime_error("Distilled checkpoint requires its sampling policy");
    if ((profile == "lcm" && pipeline != "sd15" && pipeline != "sdxl" && !lcm_checkpoint) || (profile == "sd_turbo" && pipeline != "sd21_turbo")) throw std::runtime_error("Sampling policy does not match this pipeline");
    if (profile != "standard") {
        bool lcm = profile == "lcm";
        if (steps < 1 || steps > (lcm ? 8 : 4) || !std::isfinite(cfg) || cfg != 1.0f || !negative.empty()
            || method != (lcm ? "lcm" : "euler_a") || schedule != (lcm ? "lcm" : "discrete")) throw std::runtime_error("Distilled sampling parameters do not match the frozen plan");
    } else if (method == "lcm" || schedule == "lcm") throw std::runtime_error("LCM sampling requires an explicitly selected consistency model or adapter");
}
}

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
    else if (pipeline == "z_image_turbo") { expected = "z_image"; version = "Z-Image"; }
    else if (pipeline == "flux2_klein_4b") { expected = "flux2_klein"; version = "Flux.2 klein"; }
    else if (pipeline == "qwen_image_21") { expected = "qwen_image_21"; version = "Qwen Image 2.1"; }
    else if (pipeline == "wan21_13b") { expected = "wan21"; version = "Wan 2.x"; }
    else throw std::runtime_error("Unknown signed diffusion pipeline");
    if (architecture != expected || detected != version) throw std::runtime_error("Loaded tensor architecture does not match the selected diffusion recipe");
}
inline void sampling(const std::string& profile, const std::string& pipeline, const std::string& method,
                     const std::string& schedule, int steps, float cfg, const std::string& negative) {
    if (profile != "standard" && profile != "lcm" && profile != "sd_turbo" && profile != "z_image_turbo" && profile != "flux2_klein") throw std::runtime_error("Unknown signed diffusion sampling policy");
    bool lcm_checkpoint = pipeline == "sd15_lcm" || pipeline == "sdxl_lcm";
    if ((lcm_checkpoint && profile != "lcm") || (pipeline == "sd21_turbo" && profile != "sd_turbo") || (pipeline == "z_image_turbo" && profile != "z_image_turbo") || (pipeline == "flux2_klein_4b" && profile != "flux2_klein")) throw std::runtime_error("Distilled checkpoint requires its sampling policy");
    if ((profile == "lcm" && pipeline != "sd15" && pipeline != "sdxl" && !lcm_checkpoint) || (profile == "sd_turbo" && pipeline != "sd21_turbo") || (profile == "z_image_turbo" && pipeline != "z_image_turbo") || (profile == "flux2_klein" && pipeline != "flux2_klein_4b")) throw std::runtime_error("Sampling policy does not match this pipeline");
    if (profile != "standard") {
        bool lcm = profile == "lcm";
        if (steps < 1 || steps > (lcm || profile == "z_image_turbo" ? 8 : 4) || !std::isfinite(cfg) || cfg != 1.0f || !negative.empty()
            || method != (lcm ? "lcm" : profile == "sd_turbo" ? "euler_a" : "euler") || schedule != (lcm ? "lcm" : profile == "flux2_klein" ? "flux2" : "discrete")) throw std::runtime_error("Distilled sampling parameters do not match the frozen plan");
    } else if (method == "lcm" || schedule == "lcm") throw std::runtime_error("LCM sampling requires an explicitly selected consistency model or adapter");
    if ((pipeline == "qwen_image_21" && (method != "euler" || schedule != "flux")) || (pipeline == "wan21_13b" && (method != "euler" || schedule != "discrete"))) throw std::runtime_error("Sampling does not match the selected pipeline");
}
inline float flow_shift(float value) {
    if (!std::isfinite(value) || value < 0 || value > 32) throw std::runtime_error("Flow shift out of bounds");
    return value == 0 ? INFINITY : value;
}
inline void geometry(const std::string& pipeline, int width, int height, int frames, int fps) {
    int alignment = pipeline == "qwen_image_21" ? 32 : 16;
    if (width < 64 || height < 64 || width > 2048 || height > 2048 || width % alignment || height % alignment) throw std::runtime_error("Image dimensions must align to the selected recipe");
    if (pipeline == "wan21_13b" && (frames < 5 || frames > 129 || (frames - 1) % 4 || fps < 1 || fps > 60)) throw std::runtime_error("Wan frames must be 4n+1 with a valid frame rate");
}
}

#include "../../native/sd_policy.hpp"
#include <iostream>
#include <limits>
static int passed;
template <class F> static void rejects(F action) { try { action(); } catch (const std::exception&) { passed++; return; } throw std::runtime_error("Expected native policy rejection"); }
int main() {
    using namespace lma_sd;
    route("sd15", "sd15", "SD 1.x"); passed++;
    route("sd15_lcm", "sd15", "SD 1.x"); passed++;
    route("sdxl", "sdxl", "SDXL"); passed++;
    route("sdxl_lcm", "sdxl", "SDXL"); passed++;
    route("sd21_turbo", "sd21", "SD 2.x"); passed++;
    rejects([] { route("sd15", "sd15", "SDXL"); });
    rejects([] { route("sd15", "sdxl", "SD 1.x"); });
    rejects([] { route("sdxl", "sdxl", "SDXL Inpaint"); });
    rejects([] { route("sd21_turbo", "sd21", "SD 1.x"); });
    sampling("lcm", "sd15", "lcm", "lcm", 4, 1, ""); passed++;
    sampling("lcm", "sdxl_lcm", "lcm", "lcm", 8, 1, ""); passed++;
    sampling("sd_turbo", "sd21_turbo", "euler_a", "discrete", 1, 1, ""); passed++;
    sampling("standard", "sdxl", "euler", "discrete", 20, 7, "blur"); passed++;
    rejects([] { sampling("lcm", "sd15", "euler", "lcm", 4, 1, ""); });
    rejects([] { sampling("lcm", "sd15", "lcm", "discrete", 4, 1, ""); });
    rejects([] { sampling("lcm", "sd15", "lcm", "lcm", 9, 1, ""); });
    rejects([] { sampling("lcm", "sd15", "lcm", "lcm", 0, 1, ""); });
    rejects([] { sampling("lcm", "sd15", "lcm", "lcm", 4, 7, ""); });
    rejects([] { sampling("lcm", "sd15", "lcm", "lcm", 4, std::numeric_limits<float>::quiet_NaN(), ""); });
    rejects([] { sampling("lcm", "sd15", "lcm", "lcm", 4, 1, "negative"); });
    rejects([] { sampling("standard", "sd15", "lcm", "lcm", 4, 1, ""); });
    rejects([] { sampling("standard", "sd15_lcm", "euler", "discrete", 20, 7, ""); });
    rejects([] { sampling("standard", "sd21_turbo", "euler", "discrete", 20, 7, ""); });
    rejects([] { sampling("lcm", "sd21_turbo", "lcm", "lcm", 4, 1, ""); });
    rejects([] { sampling("sd_turbo", "sdxl", "euler_a", "discrete", 1, 1, ""); });
    rejects([] { sampling("sd_turbo", "sd21_turbo", "euler_a", "discrete", 5, 1, ""); });
    rejects([] { sampling("unknown", "sd15", "euler", "discrete", 20, 7, ""); });
    route("z_image_turbo", "z_image", "Z-Image"); passed++;
    route("flux2_klein_4b", "flux2_klein", "Flux.2 klein"); passed++;
    route("qwen_image_21", "qwen_image_21", "Qwen Image 2.1"); passed++;
    route("wan21_13b", "wan21", "Wan 2.x"); passed++;
    rejects([] { route("qwen_image_21", "qwen_image_21", "Qwen Image"); });
    rejects([] { route("flux2_klein_4b", "flux2_klein", "Flux.2"); });
    rejects([] { route("wan21_13b", "wan21", "Wan 2.2 I2V"); });
    rejects([] { route("unknown", "unknown", "unknown"); });
    sampling("z_image_turbo", "z_image_turbo", "euler", "discrete", 8, 1, ""); passed++;
    sampling("flux2_klein", "flux2_klein_4b", "euler", "flux2", 4, 1, ""); passed++;
    sampling("standard", "qwen_image_21", "euler", "flux", 20, 6, "blur"); passed++;
    sampling("standard", "wan21_13b", "euler", "discrete", 20, 6, "blur"); passed++;
    rejects([] { sampling("z_image_turbo", "z_image_turbo", "euler", "discrete", 9, 1, ""); });
    rejects([] { sampling("flux2_klein", "flux2_klein_4b", "euler", "flux2", 4, 1, "blur"); });
    rejects([] { sampling("flux2_klein", "flux2_klein_4b", "euler", "discrete", 4, 1, ""); });
    rejects([] { sampling("standard", "z_image_turbo", "euler", "discrete", 8, 1, ""); });
    rejects([] { sampling("standard", "qwen_image_21", "euler", "discrete", 20, 6, ""); });
    rejects([] { sampling("standard", "wan21_13b", "euler_a", "discrete", 20, 6, ""); });
    rejects([] { sampling("z_image_turbo", "sd15", "euler", "discrete", 8, 1, ""); });
    if (!std::isinf(flow_shift(0)) || flow_shift(3) != 3) throw std::runtime_error("Automatic/explicit flow shift mismatch"); passed++;
    rejects([] { flow_shift(-1); });
    rejects([] { flow_shift(33); });
    rejects([] { flow_shift(std::numeric_limits<float>::infinity()); });
    rejects([] { flow_shift(std::numeric_limits<float>::quiet_NaN()); });
    geometry("qwen_image_21", 1024, 1024, 0, 0); passed++;
    geometry("wan21_13b", 512, 288, 17, 8); passed++;
    rejects([] { geometry("qwen_image_21", 1008, 1024, 0, 0); });
    rejects([] { geometry("wan21_13b", 512, 288, 18, 8); });
    rejects([] { geometry("wan21_13b", 512, 288, 17, 61); });
    rejects([] { geometry("wan21_13b", 512, 288, 1, 8); });
    std::cout << "{\"passed\":" << passed << ",\"production_cpp_policy\":true,\"model_inference\":false}" << std::endl;
}

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
    std::cout << "{\"passed\":" << passed << ",\"production_cpp_policy\":true,\"model_inference\":false}" << std::endl;
}

#pragma once
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace lma_qwen {
inline void require(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }
inline int language(const std::string& name) {
    const std::vector<std::string> names = {"auto", "en", "zh", "ja", "ko", "de", "fr", "ru", "pt", "es", "it"};
    const int ids[] = {-1, 2050, 2055, 2058, 2064, 2053, 2061, 2069, 2071, 2054, 2070};
    for (size_t i = 0; i < names.size(); ++i) if (name == names[i]) return ids[i];
    throw std::runtime_error("Unsupported Qwen speech language");
}
inline void parameters(int threads, int input_tokens, int audio_tokens, float temperature, float top_p, int top_k, float repetition, int64_t seed) {
    require(threads >= 1 && threads <= 32, "CPU thread count exceeds the application guard");
    require(input_tokens >= 1 && input_tokens <= 2048, "Input token budget exceeds the application guard");
    require(audio_tokens >= 1 && audio_tokens <= 1500, "Audio frame budget exceeds the application guard");
    require(std::isfinite(temperature) && temperature >= 0 && temperature <= 2, "Invalid temperature");
    require(std::isfinite(top_p) && top_p >= .01f && top_p <= 1, "Invalid top-p");
    require(top_k >= 1 && top_k <= 1024, "Invalid top-k");
    require(std::isfinite(repetition) && repetition >= 1 && repetition <= 2, "Invalid repetition penalty");
    require(seed >= 0 && seed <= 2147483647, "Record an actual seed before execution");
}
}

#pragma once
#include "stable-diffusion.h"
#include "ggml.h"
#include "ggml-backend.h"
#include "json.hpp"
#include <atomic>
#include <cctype>
#include <stdexcept>
#include <string>
#include <vector>

namespace lma_sd_backend {
#if defined(LMA_SD_VULKAN) && LMA_SD_VULKAN
inline constexpr bool vulkan = true;
#else
inline constexpr bool vulkan = false;
#endif
inline const char* name() { return vulkan ? "vulkan" : "cpu"; }
inline const char* engine() { return vulkan ? "wan_sd_cpp" : "sd_cpp"; }

inline std::string devices() {
    const size_t size = sd_list_devices(nullptr, 0);
    if (size > 65536) throw std::runtime_error("Local device list exceeds bounds");
    std::vector<char> result(size + 1, '\0');
    if (sd_list_devices(result.data(), result.size()) > size)
        throw std::runtime_error("Local GPU devices changed during inspection");
    return std::string(result.data());
}

inline bool has_vulkan(const std::string& devices) {
    size_t position = 0;
    while (position < devices.size()) {
        const size_t end = devices.find('\n', position);
        std::string line = devices.substr(position, end == std::string::npos ? end : end - position);
        for (char& ch : line) ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
        if (line.rfind("vulkan0\t", 0) == 0) return true;
        if (end == std::string::npos) break;
        position = end + 1;
    }
    return false;
}

inline void configure(const nlohmann::json& request, sd_ctx_params_t& params) {
    if (request.value("backend", std::string(name())) != name())
        throw std::runtime_error("Requested backend does not match the signed local worker");
    if (vulkan && !has_vulkan(devices()))
        throw std::runtime_error("Vulkan GPU is unavailable; this local recipe cannot run");
    params.backend = vulkan ? "all=cpu,diffusion=vulkan0" : "cpu";
    params.params_backend = params.backend;
    params.rpc_servers = nullptr;
}

// Observe one completed GPU matrix operation, rather than treating device
// enumeration or a requested backend name as evidence of GPU execution.
struct Observation {
    std::atomic_bool completed{false};
    static bool gpu_tensor(const ggml_tensor* tensor) {
        if (!tensor || !tensor->buffer || tensor->op != GGML_OP_MUL_MAT) return false;
        const auto type = ggml_backend_buffer_get_type(tensor->buffer);
        if (!type || ggml_backend_buft_is_host(type)) return false;
        const auto device = ggml_backend_buft_get_device(type);
        if (!device) return false;
        const auto kind = ggml_backend_dev_type(device);
        if (kind != GGML_BACKEND_DEVICE_TYPE_GPU && kind != GGML_BACKEND_DEVICE_TYPE_IGPU) return false;
        const auto registry = ggml_backend_dev_backend_reg(device);
        if (!registry) return false;
        const char* label = ggml_backend_reg_name(registry);
        return label && std::string(label).find("Vulkan") != std::string::npos;
    }
    static bool callback(ggml_tensor* tensor, bool ask, void* data) {
        auto& state = *static_cast<Observation*>(data);
        if (ask) return !state.completed.load(std::memory_order_relaxed) && gpu_tensor(tensor);
        if (gpu_tensor(tensor)) state.completed.store(true, std::memory_order_relaxed);
        return true;
    }
    void require() const {
        if (vulkan && !completed.load(std::memory_order_relaxed))
            throw std::runtime_error("No completed Vulkan diffusion operation was observed");
    }
    nlohmann::json details() const {
        return {{"runtimeBackend", name()}, {"textBackend", "cpu"}, {"vaeBackend", "cpu"},
                {"diffusionBackend", vulkan ? "vulkan0" : "cpu"},
                {"vulkanGraphObserved", completed.load(std::memory_order_relaxed)},
                {"remoteInference", false}};
    }
};
}

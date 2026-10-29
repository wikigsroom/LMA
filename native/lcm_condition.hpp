#pragma once
#include "json.hpp"
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace lma_lcm_condition {
using Json = nlohmann::json;
inline void require(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }
inline bool digest(const std::string& value) { return value.size() == 64 && value.find_first_not_of("0123456789abcdef") == std::string::npos; }
struct Reader {
    std::vector<uint8_t> data; size_t position = 0;
    explicit Reader(const std::string& path) {
        std::ifstream file(path, std::ios::binary | std::ios::ate);
        require(file && file.tellg() >= 5120 && file.tellg() <= 65536, "LCM condition file exceeds its bounded layout");
        data.resize(static_cast<size_t>(file.tellg())); file.seekg(0); file.read(reinterpret_cast<char*>(data.data()), data.size());
        require(file && file.gcount() == static_cast<std::streamsize>(data.size()) && file.peek() == EOF, "LCM condition file changed or was truncated");
    }
    uint64_t number(size_t count) {
        require(count <= 8 && position <= data.size() && count <= data.size() - position, "Truncated LCM condition header");
        uint64_t result = 0; for (size_t i = 0; i < count; ++i) result |= uint64_t(data[position++]) << (8 * i); return result;
    }
    std::string string() {
        auto count = number(8); require(count >= 1 && count <= 512 && count <= data.size() - position, "LCM condition string exceeds its budget");
        std::string result; result.reserve(static_cast<size_t>(count));
        for (uint64_t i = 0; i < count; ++i) { auto c = number(1); require(c >= 32 && c <= 126, "LCM condition metadata must be ASCII"); result.push_back(static_cast<char>(c)); } return result;
    }
};
inline std::string validate(const Json& request) {
    const auto& components = request.at("components"); bool component = components.contains("condition_bias"), descriptor = request.contains("conditionBias");
    if (!component && !descriptor) return "";
    require(component && descriptor, "LCM condition component requires its source binding");
    const auto& binding = request.at("conditionBias");
    std::set<std::string> keys; for (const auto& item : binding.items()) keys.insert(item.key());
    require(binding.is_object() && keys == std::set<std::string>{"schema","algorithm","sourceSha256","baseSha256","distilledGuidance"}, "Unknown LCM condition binding fields");
    require(binding.at("schema") == "lma.condition-bias-overlay/1" && binding.at("algorithm") == "lcm-fixed-guidance-f16-mlp-double-dot/1"
            && binding.at("distilledGuidance").is_number() && binding.at("distilledGuidance").get<double>() == 8.5
            && digest(binding.at("sourceSha256").get<std::string>()) && digest(binding.at("baseSha256").get<std::string>()), "Unknown LCM condition algorithm or source identity");
    keys.clear(); for (const auto& item : components.items()) keys.insert(item.key());
    require(request.at("pipeline") == "sd15_lcm" && request.at("architecture") == "sd15" && request.at("samplingProfile") == "lcm"
            && request.at("type") == "image.generate" && keys == std::set<std::string>{"model","clip_merges","condition_bias"}, "LCM condition requires its complete SD1.5 model and LCM policy");
    std::string path = components.at("condition_bias"); Reader reader(path);
    require(reader.number(4) == 0x46554747 && reader.number(4) == 3 && reader.number(8) == 1 && reader.number(8) == 6, "LCM condition must contain one GGUFv3 tensor");
    std::map<std::string,std::string> metadata;
    for (int i = 0; i < 6; ++i) { auto name = reader.string(); require(reader.number(4) == 8, "LCM condition metadata must be strings"); auto value = reader.string(); require(metadata.emplace(name,value).second, "Duplicate LCM condition metadata"); }
    const std::map<std::string,std::string> expected = {
        {"lma.overlay.schema","lma.condition-bias-overlay/1"},{"lma.overlay.algorithm",binding.at("algorithm")},
        {"lma.overlay.source_sha256",binding.at("sourceSha256")},{"lma.overlay.base_sha256",binding.at("baseSha256")},
        {"lma.overlay.distilled_guidance","8.5"},{"lma.overlay.sampler_cfg","1"}};
    require(metadata == expected && reader.string() == "model.diffusion_model.time_embed.0.bias" && reader.number(4) == 1
            && reader.number(8) == 1280 && reader.number(4) == 0 && reader.number(8) == 0, "LCM condition tensor or source binding does not match");
    while (reader.position % 32) require(reader.number(1) == 0, "Invalid LCM condition padding");
    require(reader.data.size() - reader.position == 5120, "LCM condition payload size mismatch");
    for (int i = 0; i < 1280; ++i) { auto bits = static_cast<uint32_t>(reader.number(4)); float value; std::memcpy(&value,&bits,4); require(std::isfinite(value), "Non-finite LCM condition parameter"); }
    return path;
}
}

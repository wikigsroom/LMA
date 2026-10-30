// SPDX-License-Identifier: MIT
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace lma_mnn::sprint {
inline constexpr int sequence = 506, selected = 300, hidden = 2304, vocabulary = 256000;
inline constexpr float sigma_data = 0.5f, vae_scale = 0.41407f;
inline void require(bool condition, const char* message) { if (!condition) throw std::runtime_error(message); }
inline void finite(const std::vector<float>& values) {
    for (float value : values) require(std::isfinite(value), "Non-finite Sana-Sprint tensor");
}
inline void parameters(int width, int height, int steps, int threads, float guidance, int seed,
                       const std::string& prompt, const std::string& negative) {
    require(width == 1024 && height == 1024, "This Sana-Sprint export fixes output to 1024x1024");
    require(steps >= 1 && steps <= 4 && threads >= 1 && threads <= 32, "Invalid Sana-Sprint step/thread bounds");
    require(std::isfinite(guidance) && guidance >= 1 && guidance <= 30 && seed >= 0, "Invalid Sana-Sprint guidance/seed");
    require(!prompt.empty() && prompt.size() <= 64000 && prompt.find('\0') == std::string::npos && negative.empty(),
            "Sana-Sprint requires a bounded prompt and no negative prompt");
}
inline std::vector<float> schedule(int steps) {
    require(steps >= 1 && steps <= 4, "Sana-Sprint supports 1..4 steps");
    if (steps == 2) return {1.57080f, 1.3f, 0.0f};
    std::vector<float> result;
    for (int i = 0; i <= steps; ++i) result.push_back(1.57080f * (1.0f - float(i) / steps));
    result.back() = 0; return result;
}
inline float model_time(float time) { return std::sin(time) / (std::cos(time) + std::sin(time)); }
inline std::vector<float> model_input(const std::vector<float>& sample, float time) {
    finite(sample); float t = model_time(time), scale = std::sqrt(t*t + (1-t)*(1-t));
    std::vector<float> result(sample.size());
    for (size_t i = 0; i < sample.size(); ++i) result[i] = sample[i] / sigma_data * scale;
    finite(result); return result;
}
struct Step { std::vector<float> sample, denoised; };
// Same trigflow/SCM equations as the publisher's diffusers pipeline/scheduler.
// Noise is supplied by the owner so bounded tests can use independent vectors.
inline Step step(const std::vector<float>& sample, const std::vector<float>& prediction,
                 const std::vector<float>& noise, float time, float next) {
    require(sample.size() == prediction.size() && sample.size() == noise.size() && !sample.empty(), "Sana-Sprint tensor sizes differ");
    finite(sample); finite(prediction); finite(noise);
    auto input = model_input(sample, time); float t = model_time(time), scale = std::sqrt(t*t + (1-t)*(1-t));
    Step result; result.sample.resize(sample.size()); result.denoised.resize(sample.size());
    for (size_t i = 0; i < sample.size(); ++i) {
        float velocity = ((1 - 2*t)*input[i] + (1 - 2*t + 2*t*t)*prediction[i]) / scale * sigma_data;
        result.denoised[i] = std::cos(time)*sample[i] - std::sin(time)*velocity;
        result.sample[i] = std::cos(next)*result.denoised[i] + std::sin(next)*noise[i]*sigma_data;
    }
    finite(result.sample); finite(result.denoised); return result;
}
inline std::vector<float> causal_mask(size_t active, size_t length = sequence) {
    require(active >= 1 && active <= length && length <= sequence, "Invalid Sana-Sprint token mask");
    std::vector<float> result(length*length, -10000.0f);
    for (size_t query = 0; query < length; ++query)
        for (size_t key = 0; key <= query && key < active; ++key) result[query*length+key] = 0;
    return result;
}
inline std::vector<float> select_features(const std::vector<float>& values, size_t width = hidden,
                                        size_t length = sequence, size_t keep = selected) {
    require(keep >= 2 && keep <= length && values.size() == length*width, "Wrong Sana-Sprint encoder shape");
    finite(values); std::vector<float> result(keep*width);
    std::copy_n(values.begin(), width, result.begin());
    std::copy(values.begin() + (length-keep+1)*width, values.end(), result.begin()+width); return result;
}
inline std::vector<float> selected_mask(size_t active, size_t length = sequence, size_t keep = selected) {
    require(active >= 1 && active <= length && keep >= 2 && keep <= length, "Invalid Sana-Sprint selected mask");
    std::vector<float> result(keep, 0); result[0] = 1;
    for (size_t i = 1; i < keep; ++i) result[i] = length-keep+i < active ? 1.0f : 0.0f;
    return result;
}
inline float half(uint16_t value) {
    const int sign = value & 0x8000 ? -1 : 1, exponent = (value >> 10) & 31, mantissa = value & 1023;
    require(exponent != 31, "Non-finite Sana-Sprint token embedding");
    return sign * std::ldexp(float(exponent ? 1024+mantissa : mantissa), exponent ? exponent-25 : -24);
}
inline std::vector<uint8_t> pixels(const std::vector<float>& chw, int width, int height) {
    require(width > 0 && height > 0 && size_t(width)*height <= 4194304 && chw.size() == size_t(width)*height*3,
            "Wrong Sana-Sprint decoded image shape");
    finite(chw); size_t plane = size_t(width)*height; std::vector<uint8_t> rgb(plane*3);
    for (size_t i = 0; i < plane; ++i) for (size_t c = 0; c < 3; ++c) {
        float value = std::clamp(chw[c*plane+i]*0.5f+0.5f, 0.0f, 1.0f) * 255.0f;
        rgb[3*i+c] = static_cast<uint8_t>(std::nearbyint(value));
    }
    return rgb;
}
}

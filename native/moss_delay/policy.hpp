#pragma once
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace lma_moss {
inline void require(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }
inline void parameters(int threads, int input, int frames, float text_temp, float text_p, int text_k, float audio_temp, float audio_p, int audio_k, float repetition, int64_t seed) {
    require(threads >= 1 && threads <= 32, "CPU threads exceed the application guard");
    require(input >= 1 && input <= 2048, "Formatted input budget exceeds the application guard");
    require(frames >= 64 && frames <= 1500, "Generation budget must include the 32-channel delay flush");
    for (float value : {text_temp, audio_temp}) require(std::isfinite(value) && value >= 0 && value <= 3, "Invalid temperature");
    for (float value : {text_p, audio_p}) require(std::isfinite(value) && value >= .01f && value <= 1, "Invalid top-p");
    for (int value : {text_k, audio_k}) require(value >= 1 && value <= 1024, "Invalid top-k");
    require(std::isfinite(repetition) && repetition >= 1 && repetition <= 2, "Invalid audio repetition penalty");
    require(seed >= 0 && seed <= 2147483647, "Record the actual seed before execution");
}
inline void context(size_t prompt, int input, int generated, int training) {
    require(prompt > 0 && prompt <= size_t(input), "Formatted text and reference exceed the selected input budget");
    require(prompt + size_t(generated) + 8 <= 4096 && prompt + size_t(generated) + 8 <= size_t(training), "Generation exceeds the model or application context limit");
}
inline void language(const std::string& value) {
    const std::vector<std::string> choices={"auto","zh","en","de","es","fr","ja","it","hu","ko","ru","fa","ar","pl","pt","cs","da","sv","el","tr"};
    for (const auto& item : choices) if (item == value) return;
    throw std::runtime_error("Unsupported language hint");
}
inline std::vector<int32_t> encoder_codes(const int32_t* values,size_t padded_frames,size_t valid_frames) {
    require(values && valid_frames>0 && valid_frames<=padded_frames && padded_frames<=126,"Invalid reference codec extent");
    std::vector<int32_t> result(valid_frames*32);
    // llama_get_output_i32 returns frame-major rows, each containing all quantizers.
    for(size_t i=0;i<result.size();++i) { require(values[i]>=0 && values[i]<1024,"Reference encoder produced an invalid code");result[i]=values[i]; }
    return result;
}
}

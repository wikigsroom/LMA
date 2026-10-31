#pragma once
#include "json.hpp"
#include "runtime_metrics.hpp"
#include <algorithm>
#include <cmath>
#include <csignal>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
#ifdef _WIN32
#include <io.h>
#define LMA_DUP _dup
#define LMA_FDOPEN _fdopen
#define LMA_FILENO _fileno
#define LMA_SYNC _commit
#else
#include <unistd.h>
#include <sys/prctl.h>
#define LMA_DUP dup
#define LMA_FDOPEN fdopen
#define LMA_FILENO fileno
#define LMA_SYNC fsync
#endif
namespace lma_worker {
using json = nlohmann::json;
inline FILE* events = nullptr;
inline void require(bool value, const char* message) { if (!value) throw std::runtime_error(message); }
inline void event(const json& value) {
    require(events != nullptr, "Event channel unavailable");
    const auto kind=value.value("event",std::string());
    if(kind=="stage")lma_metrics::stage(value.value("stage",std::string("generating")));
    if(kind=="complete"||kind=="error"){
        const auto measured=json{{"event","execution"},{"details",{{"runtimeMeasurements",lma_metrics::finish()}}}}.dump();
        std::fprintf(events,"%s\n",measured.c_str());
    }
    std::string line = value.dump(); std::fprintf(events, "%s\n", line.c_str()); std::fflush(events);
}
inline void initialize() {
#ifndef _WIN32
    prctl(PR_SET_PDEATHSIG, SIGKILL);
#endif
    events = LMA_FDOPEN(LMA_DUP(LMA_FILENO(stdout)), "w");
    require(events != nullptr, "Cannot create private worker event channel");
    std::freopen(
#ifdef _WIN32
        "NUL"
#else
        "/dev/null"
#endif
        , "w", stdout);
    std::freopen(
#ifdef _WIN32
        "NUL"
#else
        "/dev/null"
#endif
        , "w", stderr);
}
inline json request(const char* path) {
    auto length = std::filesystem::file_size(path); require(length > 0 && length <= 262144, "Invalid request size");
    std::ifstream stream(path, std::ios::binary); json value; stream >> value;
    require(value.at("schema") == "lma.engine-request/1", "Unsupported worker protocol"); return value;
}
inline int integer(const json& params, const char* key, int fallback, int low, int high) {
    if (!params.contains(key)) return fallback;
    require(params.at(key).is_number(), "Parameter must be numeric"); double v = params.at(key).get<double>();
    require(std::isfinite(v) && v == std::trunc(v), "Parameter must be an integer"); return int(std::clamp(v, double(low), double(high)));
}
inline float number(const json& params, const char* key, float fallback, float low, float high) {
    if (!params.contains(key)) return fallback;
    require(params.at(key).is_number(), "Parameter must be numeric"); double v = params.at(key).get<double>();
    require(std::isfinite(v), "Parameter must be finite"); return float(std::clamp(v, double(low), double(high)));
}
inline std::string regular(const json& value, const char* key) {
    std::string path = value.at(key).get<std::string>();
    require(path.find('\0') == std::string::npos && std::filesystem::path(path).is_absolute() &&
            std::filesystem::is_regular_file(path) && !std::filesystem::is_symlink(path), "Selected component must be a local regular file");
    return path;
}
inline std::string text(const json& value, const char* key, size_t maximum = 4000) {
    std::string result = value.at(key).get<std::string>();
    require(!result.empty() && result.size() <= maximum * 4 && result.find('\0') == std::string::npos, "Invalid synthesis text"); return result;
}
inline void u32(FILE* file, uint32_t value, int width = 4) { for (int i=0; i<width; ++i) std::fputc((value >> (8*i)) & 255, file); }
inline void wave(const std::string& path, const float* samples, size_t frames, int rate, int channels, int maximum) {
    require(samples && rate >= 8000 && rate <= 48000 && channels >= 1 && channels <= 2 && frames > 0 &&
            frames <= size_t(rate) * maximum, "Generated waveform exceeds the selected limit");
    double peak = 0; for (size_t i=0; i<frames*channels; ++i) { require(std::isfinite(samples[i]), "Nonfinite waveform"); peak=std::max(peak, double(std::abs(samples[i]))); }
    require(peak > 1e-6, "Generated waveform is silent");
    std::unique_ptr<FILE, decltype(&std::fclose)> file(std::fopen(path.c_str(), "wb"), std::fclose);
    require(bool(file), "Cannot create waveform"); uint32_t bytes = uint32_t(frames*channels*2);
    std::fwrite("RIFF",1,4,file.get()); u32(file.get(),36+bytes); std::fwrite("WAVEfmt ",1,8,file.get());
    u32(file.get(),16); u32(file.get(),1,2); u32(file.get(),channels,2); u32(file.get(),rate); u32(file.get(),rate*channels*2);
    u32(file.get(),channels*2,2); u32(file.get(),16,2); std::fwrite("data",1,4,file.get()); u32(file.get(),bytes);
    for(size_t i=0;i<frames*channels;++i) u32(file.get(),uint16_t(std::lround(std::clamp(samples[i],-1.f,1.f)*32767)),2);
    require(!std::ferror(file.get()) && !std::fflush(file.get()) && !LMA_SYNC(LMA_FILENO(file.get())), "Cannot persist waveform");
}
}

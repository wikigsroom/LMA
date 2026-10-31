#include "sherpa-onnx/c-api/c-api.h"
#include "json.hpp"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <signal.h>
#include <sys/prctl.h>
#include <unistd.h>
#include <cstdarg>
#include <cstring>
#include <atomic>

// These are the only liblog imports of the pinned runtime libraries. Interpose
// them inside this worker process so user text cannot bypass the private pipe.
static std::atomic<bool> frontendFailure{false};
static void inspectDiagnostic(const char* format) {
    if (format && (strstr(format, "OOV ") || strstr(format, "Skip unknown"))) frontendFailure = true;
}
extern "C" int __android_log_print(int, const char*, const char* format, ...) { inspectDiagnostic(format); return 0; }
extern "C" int __android_log_vprint(int, const char*, const char* format, va_list) { inspectDiagnostic(format); return 0; }
extern "C" int __android_log_write(int, const char*, const char*) { return 0; }

using json = nlohmann::json;
static FILE* events = nullptr;
static void event(const json& value) {
    std::string text = value.dump() + "\n";
    if (fwrite(text.data(), 1, text.size(), events) != text.size() || fflush(events)) throw std::runtime_error("Host event pipe closed");
}
static int integer(const json& p, const char* key, int fallback, int low, int high) {
    if (p.contains(key) && !p.at(key).is_number_integer()) throw std::runtime_error("Integer parameter required");
    int64_t value = p.value(key, int64_t(fallback));
    if (value < low || value > high) throw std::runtime_error("TTS parameter exceeds application bounds");
    return static_cast<int>(value);
}
static float number(const json& p, const char* key, float fallback, float low, float high) {
    float value = p.value(key, fallback);
    if (!std::isfinite(value) || value < low || value > high) throw std::runtime_error("TTS parameter exceeds application bounds");
    return value;
}
struct Progress { int64_t count = 0, maximum = 0; bool exceeded = false; };
static int32_t progress(const float*, int32_t n, float fraction, void* arg) {
    auto& p = *static_cast<Progress*>(arg);
    if (n < 0 || p.count + n > p.maximum) { p.exceeded = true; return 0; }
    p.count += n;
    try { event({{"event", "progress"}, {"stage", "synthesizing"}, {"fraction", std::isfinite(fraction) ? std::clamp(fraction, 0.0f, 1.0f) : 0.0f}}); }
    catch (...) { return 0; }
    return 1;
}
static void u32(FILE* out, uint32_t value, int bytes = 4) {
    for (int i = 0; i < bytes; ++i) if (fputc((value >> (i * 8)) & 255, out) == EOF) throw std::runtime_error("Cannot write WAVE output");
}
int main(int argc, char** argv) {
    try {
        pid_t parent = getppid();
        if (prctl(PR_SET_PDEATHSIG, SIGKILL) || parent == 1 || getppid() != parent) return 1;
        events = fdopen(dup(STDOUT_FILENO), "w");
        if (!events) return 1;
        // Third-party diagnostics can contain user text. Only our structured events leave the worker.
        if (!freopen("/dev/null", "w", stdout) || !freopen("/dev/null", "w", stderr)) return 1;
        if (argc == 2 && std::string(argv[1]) == "--info") {
            event({{"schema", "lma.engine/1"}, {"engine", "sherpa_tts"}, {"revision", LMA_SHERPA_REVISION},
                   {"sherpa", SherpaOnnxGetVersionStr()}, {"onnxruntime", SherpaOnnxGetOnnxruntimeVersionStr()},
                   {"backend", "cpu"}, {"bundled_model_data", false}, {"generation_tested", false}}); return 0;
        }
        if (argc != 2) throw std::runtime_error("Pass a private engine request JSON file");
        std::ifstream input(argv[1], std::ios::binary | std::ios::ate);
        if (!input || input.tellg() < 1 || input.tellg() > 256 * 1024) throw std::runtime_error("Invalid engine request file");
        input.seekg(0); json request; input >> request;
        if (request.at("schema") != "lma.engine-request/1" || request.at("type") != "speech.synthesize") throw std::runtime_error("Unsupported TTS task");
        auto params = request.at("parameters"); auto components = request.at("components");
        std::string pipeline = request.at("pipeline"), text = request.at("input").at("prompt"), output = request.at("output");
        if (text.empty() || text.size() > 16000 || text.find('\0') != std::string::npos || output.empty()) throw std::runtime_error("Invalid speech text or output");
        std::map<std::string, std::string> paths;
        for (auto it = components.begin(); it != components.end(); ++it) paths[it.key()] = it.value().get<std::string>();
        auto path = [&](const char* role) -> const char* {
            auto found = paths.find(role);
            if (found == paths.end() || found->second.empty() || found->second.find(',') != std::string::npos || access(found->second.c_str(), R_OK)) throw std::runtime_error("A required TTS component is missing");
            return found->second.c_str();
        };
        int threads = integer(params, "threads", 2, 1, 16), speaker = integer(params, "speaker", 0, 0, 65535);
        int maxSeconds = integer(params, "maxAudioSeconds", 180, 1, 600);
        float speed = number(params, "speed", 1, 0.25f, 3), silence = number(params, "silenceScale", 1, 0, 3);
        std::string lexicons = path("lexicon");
        for (int i = 2; i <= 8; ++i) { std::string role = "lexicon_" + std::to_string(i); if (paths.count(role)) lexicons += "," + std::string(path(role.c_str())); }
        SherpaOnnxOfflineTtsConfig cfg{}; cfg.model.num_threads = threads; cfg.model.provider = "cpu";
        cfg.max_num_sentences = 1; cfg.silence_scale = silence;
        if (pipeline == "kokoro") {
            cfg.model.kokoro.model = path("model"); cfg.model.kokoro.voices = path("voices");
            cfg.model.kokoro.tokens = path("tokens"); cfg.model.kokoro.lexicon = lexicons.c_str(); cfg.model.kokoro.length_scale = 1;
        } else if (pipeline == "piper_vits" || pipeline == "melo_zh") {
            cfg.model.vits.model = path("model"); cfg.model.vits.tokens = path("tokens"); cfg.model.vits.lexicon = lexicons.c_str();
            cfg.model.vits.length_scale = 1; cfg.model.vits.noise_scale = number(params, "noiseScale", 0.667f, 0, 2);
            cfg.model.vits.noise_scale_w = number(params, "noiseScaleW", 0.8f, 0, 2);
        } else if (pipeline == "matcha") {
            cfg.model.matcha.acoustic_model = path("model"); cfg.model.matcha.vocoder = path("vocoder");
            cfg.model.matcha.tokens = path("tokens"); cfg.model.matcha.lexicon = lexicons.c_str(); cfg.model.matcha.length_scale = 1;
            cfg.model.matcha.noise_scale = number(params, "noiseScale", 0.667f, 0, 2);
        } else throw std::runtime_error("Unsupported TTS pipeline");
        // Language normalization assets are optional, explicit user components, never bundled data.
        std::string ruleFsts;
        if (paths.count("rule_fst")) ruleFsts = path("rule_fst");
        for (int i = 2; i <= 4; ++i) {
            std::string role = "rule_fst_" + std::to_string(i);
            if (paths.count(role)) { if (!ruleFsts.empty()) ruleFsts += ","; ruleFsts += path(role.c_str()); }
        }
        if (!ruleFsts.empty()) cfg.rule_fsts = ruleFsts.c_str();
        if (paths.count("rule_far")) cfg.rule_fars = path("rule_far");
        event({{"event", "stage"}, {"stage", "loading"}});
        std::unique_ptr<const SherpaOnnxOfflineTts, decltype(&SherpaOnnxDestroyOfflineTts)> tts(SherpaOnnxCreateOfflineTts(&cfg), SherpaOnnxDestroyOfflineTts);
        if (!tts) throw std::runtime_error("TTS model configuration or ONNX loading failed");
        int rate = SherpaOnnxOfflineTtsSampleRate(tts.get()), speakers = SherpaOnnxOfflineTtsNumSpeakers(tts.get());
        if (rate < 8000 || rate > 192000 || speakers < 1) throw std::runtime_error("Invalid model sample rate or speaker metadata");
        speaker = std::min(speaker, speakers - 1);
        params["speaker"] = speaker; params["speed"] = speed; params["threads"] = threads; params["maxAudioSeconds"] = maxSeconds;
        event({{"event", "execution"}, {"details", {{"effectiveParameters", params}, {"sampleRate", rate}, {"speakerCount", speakers}, {"pipeline", pipeline}}}});
        event({{"event", "stage"}, {"stage", "synthesizing"}});
        SherpaOnnxGenerationConfig generation{}; generation.sid = speaker; generation.speed = speed; generation.silence_scale = silence;
        Progress state; state.maximum = static_cast<int64_t>(maxSeconds) * rate;
        std::unique_ptr<const SherpaOnnxGeneratedAudio, decltype(&SherpaOnnxDestroyOfflineTtsGeneratedAudio)> audio(
            SherpaOnnxOfflineTtsGenerateWithConfig(tts.get(), text.c_str(), &generation, progress, &state), SherpaOnnxDestroyOfflineTtsGeneratedAudio);
        if (state.exceeded) throw std::runtime_error("Audio exceeded the selected duration limit; no partial output was accepted");
        if (frontendFailure) throw std::runtime_error("The selected language lexicon does not cover this text; skipped words were not accepted");
        if (!audio || !audio->samples || audio->n < 1 || audio->n > state.maximum || audio->sample_rate != rate) throw std::runtime_error("TTS did not return a complete bounded waveform");
        double energy = 0, peak = 0;
        for (int i = 0; i < audio->n; ++i) {
            float v = audio->samples[i]; if (!std::isfinite(v)) throw std::runtime_error("TTS waveform contains nonfinite samples");
            peak = std::max(peak, double(std::abs(v))); energy += double(v) * v;
        }
        if (peak < 1e-6) throw std::runtime_error("TTS returned an empty or silent waveform");
        event({{"event", "stage"}, {"stage", "encoding"}});
        std::unique_ptr<FILE, decltype(&fclose)> wave(fopen(output.c_str(), "wb"), fclose);
        if (!wave) throw std::runtime_error("Cannot create WAVE output");
        uint32_t bytes = static_cast<uint32_t>(audio->n) * 2;
        fwrite("RIFF", 1, 4, wave.get()); u32(wave.get(), 36 + bytes); fwrite("WAVEfmt ", 1, 8, wave.get());
        u32(wave.get(), 16); u32(wave.get(), 1, 2); u32(wave.get(), 1, 2); u32(wave.get(), rate); u32(wave.get(), rate * 2);
        u32(wave.get(), 2, 2); u32(wave.get(), 16, 2); fwrite("data", 1, 4, wave.get()); u32(wave.get(), bytes);
        for (int i = 0; i < audio->n; ++i) u32(wave.get(), static_cast<uint16_t>(std::lround(std::clamp(audio->samples[i], -1.0f, 1.0f) * 32767)), 2);
        if (ferror(wave.get()) || fflush(wave.get()) || fsync(fileno(wave.get()))) throw std::runtime_error("Cannot persist WAVE output");
        wave.reset();
        event({{"event", "execution"}, {"details", {{"audio", {{"samples", audio->n}, {"sampleRate", rate}, {"seconds", double(audio->n) / rate}, {"peak", peak}, {"rms", std::sqrt(energy / audio->n)}}}}}});
        event({{"event", "complete"}, {"output", output}}); return 0;
    } catch (const json::exception&) {
        if (events) event({{"event", "error"}, {"message", "Invalid TTS request JSON"}});
    } catch (const std::exception& error) {
        if (events) event({{"event", "error"}, {"message", error.what()}});
    }
    return 1;
}

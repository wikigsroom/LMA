#include "json.hpp"
#include "qwen3_tts.h"
#include "model_contract.hpp"
#include "wave.hpp"
#include <cstdio>
#include <cstdlib>
#include <chrono>
#include <signal.h>
#include <sys/prctl.h>
#include <unistd.h>

using json = nlohmann::json;
static FILE* events;
static void event(const json& value) { if (events) { auto line = value.dump(); std::fprintf(events, "%s\n", line.c_str()); std::fflush(events); } }
int main(int argc, char** argv) {
    try {
        events = fdopen(dup(STDOUT_FILENO), "w");
        lma_qwen::require(events && freopen("/dev/null", "w", stdout) && freopen("/dev/null", "w", stderr), "Cannot isolate native diagnostics");
        pid_t parent = getppid(); lma_qwen::require(prctl(PR_SET_PDEATHSIG, SIGKILL) == 0 && parent != 1 && getppid() == parent, "Cannot bind worker lifetime to host");
        if (argc == 2 && std::string(argv[1]) == "--info") { event({{"schema","lma.engine/1"},{"engine","qwen_tts_native"},{"revision",LMA_QWEN_REVISION},{"backend","cpu"},{"bundled_model_data",false},{"generation_tested",false}}); return 0; }
        lma_qwen::require(argc == 2, "Pass a private engine request file");
        std::ifstream in(argv[1], std::ios::binary | std::ios::ate); lma_qwen::require(bool(in) && in.tellg() > 0 && in.tellg() <= 256*1024, "Invalid request size"); in.seekg(0); json request; in >> request;
        lma_qwen::require(request.at("schema") == "lma.engine-request/1" && request.at("type") == "speech.synthesize" && request.at("pipeline") == "qwen3_tts_06b_base", "Unsupported speech pipeline");
        const auto& p = request.at("parameters"); qwen3_tts::tts_params params;
        params.n_threads = p.at("threads"); params.max_audio_tokens = p.at("maxAudioTokens"); params.temperature = p.at("temperature"); params.top_p = p.at("topP"); params.top_k = p.at("topK"); params.repetition_penalty = p.at("repetitionPenalty"); params.seed = p.at("seed"); params.language_id = lma_qwen::language(p.at("language")); params.print_timing = false; params.print_progress = false;
        int tokens = p.at("maxInputTokens"); lma_qwen::parameters(params.n_threads,tokens,params.max_audio_tokens,params.temperature,params.top_p,params.top_k,params.repetition_penalty,params.seed);
        std::string text = request.at("input").at("prompt"), root = request.at("workspace"), output = request.at("output");
        lma_qwen::require(!text.empty() && text.size() <= 16000 && text.find('\0') == std::string::npos && !root.empty() && !output.empty(), "Invalid speech input or paths");
        lma_qwen::require(request.at("input").value("negativePrompt", "").empty(), "Speech synthesis does not accept negative prompts");
        for (const char* name : {"QWEN3_TTS_DEBUG_DUMP_DIR", "QWEN3_TTS_SPEECH_ENCODER_DUMP_DIR", "QWEN3_TTS_ICL_PREFILL_CACHE"}) unsetenv(name);
        lma_qwen::require(setenv("QWEN3_TTS_LOW_MEM", "1", 1) == 0 && qwen3_tts::set_backend_preference(qwen3_tts::backend_preference::cpu) && qwen3_tts::set_cpu_thread_count(params.n_threads), "Cannot configure bounded CPU runtime");
        std::string talker = root+"/models/qwen-talker-0.6b-base.gguf", codec = root+"/models/qwen-tokenizer-12hz.gguf";
        auto pipeline_start = std::chrono::steady_clock::now();
        event({{"event","execution"},{"details",{{"effectiveParameters",p},{"pipeline","qwen3_tts_06b_base"},{"backend","cpu"}}}});
        event({{"event","stage"},{"stage","validating_components"}}); size_t count = lma_qwen::talker_contract(talker,text,tokens); lma_qwen::codec_contract(codec);
        std::vector<float> reference; if (request.contains("referenceAudio")) reference = lma_qwen::reference_wave(request.at("referenceAudio"));
        event({{"event","stage"},{"stage","loading_speech_model"}});
        auto load_start = std::chrono::steady_clock::now();
        qwen3_tts::Qwen3TTS engine; lma_qwen::require(engine.load_models(root+"/models", "qwen-talker-0.6b-base.gguf", codec), "Cannot load the selected complete Qwen Base bundle");
        auto load_ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-load_start).count();
        auto caps = engine.get_model_capabilities(); lma_qwen::require(caps.loaded && caps.supports_voice_clone && !caps.supports_named_speakers && !caps.supports_instruction && caps.speaker_embedding_dim == 1024, "Loaded capabilities do not match Qwen3-TTS 0.6B Base");
        engine.set_progress_callback([](int step, int maximum) {
            if (step == 1 || step % 16 == 0) {
                // EOS determines actual duration: a frame budget is not a completion percentage.
                event({{"event","progress"},{"stage","generating_audio_codes"}});
                event({{"event","execution"},{"details",{{"generatedAudioFrames",step},{"audioFrameLimit",maximum}}}});
            }
        });
        event({{"event","stage"},{"stage", reference.empty() ? "generating_audio_codes" : "encoding_reference_audio"}});
        auto start = std::chrono::steady_clock::now();
        auto result = reference.empty() ? engine.synthesize(text,params) : engine.synthesize_with_voice(text,reference.data(),int32_t(reference.size()),params);
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-start).count();
        lma_qwen::require(result.success && result.sample_rate == 24000 && !result.audio.empty() && result.audio.size() <= size_t(params.max_audio_tokens)*1920+48000, "Qwen model did not produce bounded 24 kHz audio");
        for (float value : result.audio) lma_qwen::require(std::isfinite(value), "Model produced nonfinite audio");
        event({{"event","stage"},{"stage","saving_audio"}}); lma_qwen::require(qwen3_tts::save_audio_file(output,result.audio,result.sample_rate), "Cannot write audio output");
        double duration = double(result.audio.size())/24000;
        auto pipeline_ms = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-pipeline_start).count();
        event({{"event","execution"},{"details",{{"inputTokens",count},{"sampleRate",24000},{"audioSamples",result.audio.size()},{"audioDurationSeconds",duration},{"modelLoadMs",load_ms},{"synthesisMs",elapsed},{"synthesisRTF",double(elapsed)/1000/duration},{"pipelineMs",pipeline_ms},{"pipelineRTF",double(pipeline_ms)/1000/duration},{"referenceMode",reference.empty()?"none":"speaker_embedding"},{"backend","cpu"}}}});
        event({{"event","complete"},{"output",output}}); return 0;
    } catch (const std::exception& e) { event({{"event","error"},{"message",e.what()}}); return 1; }
}

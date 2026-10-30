#include "json.hpp"
#include "lma_sana_llm.hpp"
#include "diffusion/diffusion.hpp"
#include "policy.hpp"
#include "image.hpp"
#include "sprint.hpp"
#include <cstdio>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <memory>
#include <stdexcept>
#include <signal.h>
#ifdef _WIN32
#include <io.h>
#include "platform.hpp" // Native Windows test parent-lifetime guard; Android uses prctl below.
#else
#include <sys/prctl.h>
#include <unistd.h>
// SentencePiece's bundled protobuf has an Android logger. Resolve it locally
// so malformed user model/tokenizer diagnostics never enter system logcat.
extern "C" int __android_log_write(int, const char*, const char*) { return 0; }
#endif

using json = nlohmann::json;
using namespace MNN;
using namespace MNN::Express;
using namespace MNN::DIFFUSION;
static FILE* events;
static void event(const json& value) { if (events) { std::string line = value.dump(); std::fprintf(events, "%s\n", line.c_str()); std::fflush(events); } }
int main(int argc, char** argv) {
    try {
        // Upstream diagnostics include user prompts/paths. Keep only our protocol on stdout.

#ifdef _WIN32
        events = _fdopen(_dup(_fileno(stdout)), "w");
        const char* null_device = "NUL";
#else
        events = fdopen(dup(STDOUT_FILENO), "w");
        const char* null_device = "/dev/null";
#endif
        if (!events || !freopen(null_device, "w", stdout) || !freopen(null_device, "w", stderr)) throw std::runtime_error("Cannot isolate native diagnostics");
        pid_t parent = getppid();
        if (prctl(PR_SET_PDEATHSIG, SIGKILL) != 0 || parent == 1 || getppid() != parent) throw std::runtime_error("Cannot bind worker lifetime to Android host");
        if (argc == 2 && std::string(argv[1]) == "--info") {
            event({{"schema", "lma.engine/1"}, {"engine", "mnn_diffusion"}, {"revision", LMA_MNN_REVISION}, {"backend", "cpu"}, {"bundled_model_data", false}, {"generation_tested", false}}); return 0;
        }
        if (argc != 2) throw std::runtime_error("Pass a private engine request file");
        std::ifstream in(argv[1], std::ios::binary | std::ios::ate);
        if (!in || in.tellg() < 1 || in.tellg() > 256 * 1024) throw std::runtime_error("Invalid native request");
        in.seekg(0); json request; in >> request;
        if (request.at("schema") != "lma.engine-request/1" || request.at("type") != "image.generate") throw std::runtime_error("Unsupported MNN task");
        if (request.at("pipeline") == "sana_sprint_06b_mnn_v1") {
            const auto& p = request.at("parameters"); const auto& input = request.at("input");
            std::string prompt = input.at("prompt"), negative = input.value("negativePrompt", ""), root = request.at("workspace"), output = request.at("output");
            lma_mnn::sprint::parameters(p.at("width"), p.at("height"), p.at("steps"), p.at("threads"), p.at("guidance"), p.at("seed"), prompt, negative);
            lma_mnn::sprint::run(std::filesystem::u8path(root), std::filesystem::u8path(output), prompt, p.at("steps"), p.at("threads"), p.at("guidance"), p.at("seed"),
                [](const std::string& stage, int done, int total) {
                    event({{"event", "stage"}, {"stage", stage}});
                    if (stage == "sampling" && total > 0) event({{"event", "progress"}, {"stage", stage}, {"fraction", double(done)/total}});
                });
            event({{"event", "complete"}, {"output", output}, {"format", "png"}, {"width", 1024}, {"height", 1024}}); return 0;
        }
        if (request.at("pipeline") != "sana_edit_mnn_v1") throw std::runtime_error("Unsupported MNN pipeline");
        const auto& p = request.at("parameters"); const auto& input = request.at("input");
        std::string prompt = input.value("prompt", ""), negative = input.value("negativePrompt", "");
        std::string root = request.at("workspace"), output = request.at("output");
        if (prompt.empty() || prompt.size() > 64000 || negative.size() > 64000 || root.empty() || output.empty()) throw std::runtime_error("Invalid Sana input or private paths");
        int width = p.at("width"), height = p.at("height"), steps = p.at("steps"), threads = p.at("threads"), maximum_tokens = p.at("maxInputTokens");
        bool cfg = p.at("useCfg"); float scale = p.at("cfg"); int seed = p.at("seed");
        lma_mnn::parameters(width, height, steps, threads, maximum_tokens, cfg, scale, negative);
        lma_mnn::edit_parameters(width, height, cfg, prompt, negative);
        std::string image = input.at("imagePath");
        std::ifstream image_file(image, std::ios::binary | std::ios::ate);
        if (!image_file || image_file.tellg() < 8 || image_file.tellg() > 16 * 1024 * 1024) throw std::runtime_error("Sana edit requires the selected bounded local image");
        lma_mnn::image_dimensions(image);
        if (seed < 0) throw std::runtime_error("Record the actual nonnegative seed before execution");
        std::string thread_count = std::to_string(threads);

#ifdef _WIN32
        const int environment_status = _putenv_s("LMA_MNN_THREADS", thread_count.c_str());
#else
        const int environment_status = setenv("LMA_MNN_THREADS", thread_count.c_str(), 1);
#endif
        if (environment_status != 0) throw std::runtime_error("Cannot set bounded CPU thread count");
        event({{"event", "stage"}, {"stage", "encoding_text"}});
        // This matched Qwen export fixes its internal batch to one. Encode each
        // CFG condition in a fresh instance, then combine the independent features.
        auto encode = [&](const std::string& text) -> VARP {
            SanaLlm encoder(root + "/llm", maximum_tokens);
            auto raw = encoder.process(text, false, "");
            if (!raw.get() || !raw->getInfo()) throw std::runtime_error("Sana text encoding failed");
            auto info = raw->getInfo();
            if (info->dim != std::vector<int>({1, 256, 1024}) || info->type != halide_type_of<float>()) throw std::runtime_error("Encoder features do not match the selected mobile Sana recipe");
            const float* data = raw->readMap<float>();
            if (!data) throw std::runtime_error("Cannot materialize text features");
            for (size_t i = 0; i < 256 * 1024; ++i) if (!std::isfinite(data[i])) throw std::runtime_error("Sana text encoder returned nonfinite features");
            VARP result = _Const(data, info->dim, NCHW, halide_type_of<float>());
            result.fix(VARP::CONSTANT);
            return result;
        };
        VARP features = encode(prompt);
        if (cfg) features = _Concat({features, encode(negative)}, 0);
        features.fix(VARP::CONSTANT);
        // Both text encoder instances exit before any diffusion model is loaded.
        event({{"event", "stage"}, {"stage", "loading_diffusion"}});
        std::unique_ptr<Diffusion> diffusion(Diffusion::createDiffusion(root + "/models", SANA_DIFFUSION, MNN_FORWARD_CPU, 0));
        if (!diffusion || !diffusion->load()) throw std::runtime_error("Complete matched Sana diffusion components could not load");
        event({{"event", "stage"}, {"stage", "encoding_image"}});
        bool ok = diffusion->run(features, "img2img", image, output, width, height, steps, seed, cfg, scale,
            [](int percent) { if (percent >= 0 && percent <= 100) event({{"event", "progress"}, {"stage", "sampling"}, {"fraction", percent / 100.0}}); });
        std::ifstream result(output, std::ios::binary | std::ios::ate);
        if (!ok || !result || result.tellg() < 8) throw std::runtime_error("Sana did not return an image artifact");
        event({{"event", "complete"}, {"output", output}, {"format", "png"}, {"width", width}, {"height", height}});
        return 0;
    } catch (const std::exception& error) { event({{"event", "error"}, {"message", error.what()}}); return 1; }
}

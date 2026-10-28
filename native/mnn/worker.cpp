#include "json.hpp"
#include "lma_sana_llm.hpp"
#include "diffusion/diffusion.hpp"
#include "policy.hpp"
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <memory>
#include <stdexcept>
#include <signal.h>
#include <sys/prctl.h>
#include <unistd.h>

using json = nlohmann::json;
using namespace MNN;
using namespace MNN::Express;
using namespace MNN::DIFFUSION;
static FILE* events;
static void event(const json& value) { if (events) { std::string line = value.dump(); std::fprintf(events, "%s\n", line.c_str()); std::fflush(events); } }
int main(int argc, char** argv) {
    try {
        // Upstream diagnostics include user prompts/paths. Keep only our protocol on stdout.
        events = fdopen(dup(STDOUT_FILENO), "w");
        if (!events || !freopen("/dev/null", "w", stdout) || !freopen("/dev/null", "w", stderr)) throw std::runtime_error("Cannot isolate native diagnostics");
        pid_t parent = getppid();
        if (prctl(PR_SET_PDEATHSIG, SIGKILL) != 0 || parent == 1 || getppid() != parent) throw std::runtime_error("Cannot bind worker lifetime to Android host");
        if (argc == 2 && std::string(argv[1]) == "--info") {
            event({{"schema", "lma.engine/1"}, {"engine", "mnn_diffusion"}, {"revision", LMA_MNN_REVISION}, {"backend", "cpu"}, {"bundled_model_data", false}, {"generation_tested", false}}); return 0;
        }
        if (argc != 2) throw std::runtime_error("Pass a private engine request file");
        std::ifstream in(argv[1], std::ios::binary | std::ios::ate);
        if (!in || in.tellg() < 1 || in.tellg() > 256 * 1024) throw std::runtime_error("Invalid native request");
        in.seekg(0); json request; in >> request;
        if (request.at("schema") != "lma.engine-request/1" || request.at("type") != "image.generate" || request.at("pipeline") != "sana_mnn_v1") throw std::runtime_error("Unsupported MNN task/pipeline");
        const auto& p = request.at("parameters"); const auto& input = request.at("input");
        std::string prompt = input.value("prompt", ""), negative = input.value("negativePrompt", "");
        std::string root = request.at("workspace"), output = request.at("output");
        if (prompt.empty() || prompt.size() > 64000 || negative.size() > 64000 || root.empty() || output.empty()) throw std::runtime_error("Invalid Sana input or private paths");
        int width = p.at("width"), height = p.at("height"), steps = p.at("steps"), threads = p.at("threads"), maximum_tokens = p.at("maxInputTokens");
        bool cfg = p.at("useCfg"); float scale = p.at("cfg"); int seed = p.at("seed");
        lma_mnn::parameters(width, height, steps, threads, maximum_tokens, cfg, scale, negative);
        if (seed < 0) throw std::runtime_error("Record the actual nonnegative seed before execution");
        std::string thread_count = std::to_string(threads);
        if (setenv("LMA_MNN_THREADS", thread_count.c_str(), 1)) throw std::runtime_error("Cannot set bounded CPU thread count");
        event({{"event", "stage"}, {"stage", "encoding_text"}});
        VARP features;
        {
            SanaLlm encoder(root + "/llm", maximum_tokens);
            auto raw = encoder.process(prompt, cfg, negative);
            if (!raw.get() || !raw->getInfo()) throw std::runtime_error("Sana text encoding failed");
            auto info = raw->getInfo();
            if (info->dim != std::vector<int>({cfg ? 2 : 1, 256, 1024}) || info->type != halide_type_of<float>()) throw std::runtime_error("Encoder features do not match the selected mobile Sana recipe");
            const float* data = raw->readMap<float>();
            if (!data) throw std::runtime_error("Cannot materialize text features");
            features = _Const(data, info->dim, NCHW, halide_type_of<float>());
            features.fix(VARP::CONSTANT);
        } // Encoder weights are released before loading the diffusion stages.
        event({{"event", "stage"}, {"stage", "loading_diffusion"}});
        std::unique_ptr<Diffusion> diffusion(Diffusion::createDiffusion(root + "/models", SANA_DIFFUSION, MNN_FORWARD_CPU, 0));
        if (!diffusion || !diffusion->load()) throw std::runtime_error("Complete matched Sana diffusion components could not load");
        bool ok = diffusion->run(features, "text2img", "", output, width, height, steps, seed, cfg, scale,
            [](int percent) { if (percent >= 0 && percent <= 100) event({{"event", "progress"}, {"stage", "sampling"}, {"fraction", percent / 100.0}}); });
        std::ifstream result(output, std::ios::binary | std::ios::ate);
        if (!ok || !result || result.tellg() < 8) throw std::runtime_error("Sana did not return an image artifact");
        event({{"event", "complete"}, {"output", output}, {"format", "png"}, {"width", width}, {"height", height}});
        return 0;
    } catch (const std::exception& error) { event({{"event", "error"}, {"message", error.what()}}); return 1; }
}

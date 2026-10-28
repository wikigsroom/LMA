#include "stable-diffusion.h"
#include "json.hpp"
#include "sd_policy.hpp"
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"
#include <cstdio>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
#include <signal.h>
#include <sys/prctl.h>
#include <unistd.h>

using json = nlohmann::json;
static void event(const json& value) { std::cout << value.dump() << std::endl; }
static void progress(int step, int steps, float seconds, void*) {
    event({{"event", "progress"}, {"stage", "sampling"}, {"step", step}, {"steps", steps}, {"seconds", seconds}});
}
static int bounded(const json& params, const char* key, int fallback, int low, int high) {
    int value = params.value(key, fallback);
    if (value < low || value > high) throw std::runtime_error(std::string("Native parameter out of bounds: ") + key);
    return value;
}
static void u32(std::ostream& out, uint32_t value) { char bytes[4]; for (int i = 0; i < 4; i++) bytes[i] = (value >> (8 * i)) & 255; out.write(bytes, 4); }
int main(int argc, char** argv) {
    try {
        pid_t parent = getppid();
        if (prctl(PR_SET_PDEATHSIG, SIGKILL) != 0 || parent == 1 || getppid() != parent) throw std::runtime_error("Cannot bind worker lifetime to its Android host");
        if (argc == 2 && std::string(argv[1]) == "--info") {
            event({{"schema", "lma.engine/1"}, {"engine", "sd_cpp"}, {"revision", LMA_SD_REVISION}, {"backend", "cpu"}, {"bundled_model_data", false}, {"generation_tested", false}}); return 0;
        }
        if (argc != 2) throw std::runtime_error("Pass a private lma.engine-request/1 JSON file");
        std::ifstream input(argv[1], std::ios::binary | std::ios::ate);
        if (!input || input.tellg() < 1 || input.tellg() > 256 * 1024) throw std::runtime_error("Invalid engine request file");
        input.seekg(0); json request; input >> request;
        if (request.at("schema") != "lma.engine-request/1") throw std::runtime_error("Unsupported engine request version");
        const json& params = request.at("parameters"); const json& components = request.at("components");
        std::string pipeline = request.at("pipeline"), architecture = request.at("architecture"), profile = request.at("samplingProfile");
        std::string type = request.at("type"), output = request.at("output"), prompt = request.at("input").value("prompt", ""), negative = request.at("input").value("negativePrompt", "");
        if (prompt.empty() || prompt.size() > 64000 || negative.size() > 64000 || output.empty()) throw std::runtime_error("Invalid prompt or output");
        if (type != "image.generate" && type != "video.generate") throw std::runtime_error("Unsupported diffusion task");
        // Upstream logging may contain prompts, paths or generated text. Only structured progress leaves stdout.
        sd_set_log_callback([](sd_log_level_t, const char*, void*) {}, nullptr);
        sd_set_progress_callback(progress, nullptr);
        sd_ctx_params_t ctx_params; sd_ctx_params_init(&ctx_params);
        auto path = [&](const char* role) -> const char* { auto it = components.find(role); return it == components.end() ? nullptr : it->get_ref<const std::string&>().c_str(); };
        ctx_params.model_path = path("model"); ctx_params.diffusion_model_path = path("diffusion"); ctx_params.vae_path = path("vae");
        ctx_params.clip_l_path = path("clip_l"); ctx_params.clip_g_path = path("clip_g"); ctx_params.clip_vision_path = path("clip_vision");
        ctx_params.t5xxl_path = path("t5"); ctx_params.llm_path = path("llm"); ctx_params.tokenizer = path("tokenizer");
        if (!ctx_params.model_path && !ctx_params.diffusion_model_path) throw std::runtime_error("Missing diffusion/checkpoint component");
        ctx_params.n_threads = bounded(params, "threads", 4, 1, 64);
        ctx_params.enable_mmap = true; ctx_params.backend = "cpu"; ctx_params.params_backend = "cpu"; ctx_params.rpc_servers = nullptr;
        ctx_params.conditioning_cache_size = 0;
        event({{"event", "stage"}, {"stage", "loading"}});
        std::unique_ptr<sd_ctx_t, decltype(&free_sd_ctx)> context(new_sd_ctx(&ctx_params), free_sd_ctx);
        if (!context) throw std::runtime_error("Diffusion model loading failed; verify the complete recipe and device resources");
        lma_sd::route(pipeline, architecture, sd_get_model_version_name(context.get()));
        sd_sample_params_t sample; sd_sample_params_init(&sample);
        sample.sample_method = sd_get_default_sample_method(context.get());
        if (params.contains("sampler")) { sample.sample_method = str_to_sample_method(params.at("sampler").get_ref<const std::string&>().c_str()); if (sample.sample_method == SAMPLE_METHOD_COUNT) throw std::runtime_error("Unknown sampler"); }
        sample.scheduler = sd_get_default_scheduler(context.get(), sample.sample_method);
        if (params.contains("scheduler")) { sample.scheduler = str_to_scheduler(params.at("scheduler").get_ref<const std::string&>().c_str()); if (sample.scheduler == SCHEDULER_COUNT) throw std::runtime_error("Unknown scheduler"); }
        sample.sample_steps = bounded(params, "steps", 4, 1, 200);
        sample.guidance.txt_cfg = params.value("cfg", 1.0f);
        if (!std::isfinite(sample.guidance.txt_cfg) || sample.guidance.txt_cfg < 0 || sample.guidance.txt_cfg > 30) throw std::runtime_error("CFG out of bounds");
        lma_sd::sampling(profile, pipeline, sd_sample_method_name(sample.sample_method), sd_scheduler_name(sample.scheduler), sample.sample_steps, sample.guidance.txt_cfg, negative);
        sample.flow_shift = lma_sd::flow_shift(params.value("flowShift", 0.0f));
        int width = bounded(params, "width", 512, 64, 2048), height = bounded(params, "height", 512, 64, 2048);
        int frames_count = type == "video.generate" ? bounded(params, "frames", 17, 5, 129) : 0;
        int fps = type == "video.generate" ? bounded(params, "fps", 8, 1, 60) : 0;
        if ((type == "video.generate") != (pipeline == "wan21_13b")) throw std::runtime_error("Task does not match the selected pipeline");
        lma_sd::geometry(pipeline, width, height, frames_count, fps);
        int64_t seed = params.value("seed", int64_t(0));
        std::vector<sd_lora_t> loras; const json& adapters = request.value("loras", json::array());
        if (adapters.size() > 8) throw std::runtime_error("Too many simultaneous LoRAs");
        for (const auto& adapter : adapters) {
            float multiplier = adapter.value("scale", 1.0f);
            if (!std::isfinite(multiplier) || multiplier < -4 || multiplier > 4) throw std::runtime_error("LoRA scale out of bounds");
            loras.push_back({false, multiplier, adapter.at("path").get_ref<const std::string&>().c_str()});
        }
        event({{"event", "stage"}, {"stage", "generating"}});
        if (type == "image.generate") {
            if (!sd_ctx_supports_image_generation(context.get())) throw std::runtime_error("This checkpoint does not support image generation");
            sd_img_gen_params_t generate; sd_img_gen_params_init(&generate);
            generate.prompt = prompt.c_str(); generate.negative_prompt = negative.c_str(); generate.width = width; generate.height = height;
            generate.sample_params = sample; generate.seed = seed; generate.batch_count = 1; generate.loras = loras.data(); generate.lora_count = loras.size();
            generate.vae_tiling_params.enabled = params.value("vaeTiling", true); generate.vae_tiling_params.tile_size_w = 128; generate.vae_tiling_params.tile_size_h = 128;
            sd_image_generation_result_t* raw = nullptr;
            if (!generate_image(context.get(), &generate, &raw) || !raw) throw std::runtime_error("Image generation failed");
            std::unique_ptr<sd_image_generation_result_t, decltype(&free_sd_image_generation_result)> result(raw, free_sd_image_generation_result);
            if (result->count != 1 || !result->items[0].image.data) throw std::runtime_error("No generated image was returned");
            const sd_image_t& image = result->items[0].image;
            if (!stbi_write_png(output.c_str(), image.width, image.height, image.channel, image.data, image.width * image.channel)) throw std::runtime_error("Cannot write generated PNG");
            event({{"event", "complete"}, {"output", output}, {"format", "png"}, {"width", image.width}, {"height", image.height}});
        } else {
            if (!sd_ctx_supports_video_generation(context.get())) throw std::runtime_error("This checkpoint does not support video generation");
            sd_vid_gen_params_t generate; sd_vid_gen_params_init(&generate);
            generate.prompt = prompt.c_str(); generate.negative_prompt = negative.c_str(); generate.width = width; generate.height = height; generate.sample_params = sample; generate.seed = seed;
            generate.video_frames = frames_count; generate.fps = fps;
            generate.loras = loras.data(); generate.lora_count = loras.size(); generate.vae_tiling_params.enabled = params.value("vaeTiling", true);
            generate.vae_tiling_params.tile_size_w = 128; generate.vae_tiling_params.tile_size_h = 128;
            sd_video_generation_result_t* raw = nullptr;
            if (!generate_video(context.get(), &generate, &raw) || !raw) throw std::runtime_error("Video generation failed");
            std::unique_ptr<sd_video_generation_result_t, decltype(&free_sd_video_generation_result)> result(raw, free_sd_video_generation_result);
            if (result->frame_count != frames_count || result->fps != fps || !result->frames) throw std::runtime_error("No generated motion frames were returned");
            std::ofstream frames(output, std::ios::binary); frames.write("LMAFRM1\0", 8); u32(frames, width); u32(frames, height); u32(frames, result->frame_count); u32(frames, result->fps); u32(frames, 3);
            for (int i = 0; i < result->frame_count; i++) {
                const sd_image_t& frame = result->frames[i];
                if (!frame.data || frame.width != width || frame.height != height || frame.channel != 3) throw std::runtime_error("Inconsistent generated video frame layout");
                frames.write(reinterpret_cast<const char*>(frame.data), size_t(width) * height * 3);
            }
            frames.close(); if (!frames) throw std::runtime_error("Cannot write generated video frames");
            event({{"event", "complete"}, {"output", output}, {"format", "lma_rgb_frames"}, {"width", width}, {"height", height}, {"frames", result->frame_count}, {"fps", result->fps}});
        }
        return 0;
    } catch (const std::exception& error) { event({{"event", "error"}, {"message", error.what()}}); return 1; }
}

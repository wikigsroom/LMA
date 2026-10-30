// LMA diagnostic only: exercise the exact generated production prompt builder.
// Including its translation unit keeps the anonymous prompt functions intact.
// This executable never enters the APK and does not run language-model inference.
#include "json.hpp"
#include "pipeline.cpp"
#include <fstream>
#include <iostream>
#include <memory>

int main(int argc, char ** argv) {
    try {
        if (argc != 2) throw std::runtime_error("Pass the private probe request");
        nlohmann::json input;
        std::ifstream file(argv[1], std::ios::binary);
        file >> input;
        llama_backend_init();
        auto options = llama_model_default_params();
        options.vocab_only = true;
        options.n_gpu_layers = 0;
        std::unique_ptr<llama_model, decltype(&llama_model_free)> model(
            llama_model_load_from_file(input.at("model").get<std::string>().c_str(), options),
            &llama_model_free);
        if (!model) throw std::runtime_error("Cannot load actual GGUF vocabulary");
        openmoss::Tokenizer tokenizer(model.get());
        const auto & config = input.at("config");
        openmoss::ModelDims dims;
        dims.n_vq = config.at("n_vq");
        dims.audio_pad_code = config.at("audio_pad_code");
        dims.im_start_token_id = config.at("im_start_token_id");
        dims.im_end_token_id = config.at("im_end_token_id");
        dims.audio_start_token_id = config.at("audio_start_token_id");
        dims.audio_end_token_id = config.at("audio_end_token_id");
        dims.audio_user_slot_token_id = config.at("audio_user_slot_token_id");
        dims.audio_assistant_gen_slot_token_id = config.at("audio_assistant_gen_slot_token_id");
        dims.audio_assistant_delay_slot_token_id = config.at("audio_assistant_delay_slot_token_id");
        nlohmann::json results = nlohmann::json::array();
        for (const auto & test : input.at("cases")) {
            openmoss::GenerateRequest request;
            request.text = test.at("text");
            if (test.contains("language")) request.language = test.at("language");
            if (test.contains("instruction")) request.instruction = test.at("instruction");
            std::vector<std::vector<int32_t>> references;
            std::vector<int32_t> lengths;
            std::vector<std::string> blocks;
            for (const auto & ref : test.at("references")) {
                const int frames = ref.at("frames");
                auto codes = ref.at("codes").get<std::vector<int32_t>>();
                if (frames <= 0 || codes.size() != size_t(frames) * dims.n_vq)
                    throw std::runtime_error("Invalid diagnostic reference shape");
                lengths.push_back(frames);
                references.push_back(std::move(codes));
                blocks.push_back(openmoss::build_reference_audio_block(tokenizer, dims, frames));
            }
            int32_t positions = 0;
            auto grid = openmoss::build_prompt_grid(tokenizer, dims, request, blocks,
                &references, &lengths, nullptr, 0, positions);
            results.push_back({{"name", test.at("name")}, {"positions", positions},
                {"columns", 1 + dims.n_vq}, {"grid", grid},
                {"prompt", openmoss::build_prompt_text(tokenizer, dims, request, blocks, 0)}});
        }
        std::cout << results.dump() << '\n';
        model.reset();
        llama_backend_free();
        return 0;
    } catch (const std::exception & error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}

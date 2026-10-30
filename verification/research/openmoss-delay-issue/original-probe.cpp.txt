// SPDX-License-Identifier: Apache-2.0
// Developer diagnostic: real pinned DelayState with independently fixed logits.
#include "json.hpp"
#include "openmoss/delay.h"
#include <fstream>
#include <iostream>
#include <limits>

int main(int argc, char ** argv) {
    try {
        if (argc != 2) throw std::runtime_error("Pass the local probe request");
        nlohmann::json input; std::ifstream file(argv[1]); file >> input;
        const auto & config = input.at("config");
        openmoss::ModelDims dims;
        dims.n_vq = config.at("n_vq");
        dims.text_vocab_size = config.at("language_config").at("vocab_size");
        dims.audio_vocab_size = config.at("audio_vocab_size");
        dims.audio_pad_code = config.at("audio_pad_code");
        dims.pad_token_id = config.at("pad_token_id");
        dims.im_end_token_id = config.at("im_end_token_id");
        dims.audio_start_token_id = config.at("audio_start_token_id");
        dims.audio_end_token_id = config.at("audio_end_token_id");
        dims.audio_assistant_gen_slot_token_id = config.at("audio_assistant_gen_slot_token_id");
        dims.audio_assistant_delay_slot_token_id = config.at("audio_assistant_delay_slot_token_id");
        openmoss::SamplingConfig sampling;
        sampling.text_temperature = sampling.audio_temperature = 0;
        sampling.audio_repetition_penalty = 1;
        sampling.min_audio_frames = sampling.max_audio_frames = 0;
        nlohmann::json results = nlohmann::json::array();
        for (const auto & test : input.at("cases")) {
            auto prompt = test.at("prompt").get<std::vector<std::vector<int32_t>>>();
            openmoss::DelayState state(dims, prompt);
            const auto schedule = test.at("schedule").get<std::vector<int32_t>>();
            nlohmann::json rows = nlohmann::json::array();
            for (size_t step = 0; step < schedule.size(); ++step) {
                std::vector<float> text(dims.text_vocab_size, -1000000.f);
                text[42] = -10; text[dims.audio_start_token_id] = -20;
                text[dims.audio_assistant_gen_slot_token_id] = -30;
                text[dims.audio_assistant_delay_slot_token_id] = -40;
                text[dims.im_end_token_id] = -50;
                text.at(schedule[step]) = 100;
                const int width = dims.audio_vocab_size + 1;
                std::vector<float> audio(size_t(dims.n_vq) * width, -1000000.f);
                for (int cb = 0; cb < dims.n_vq; ++cb)
                    audio[size_t(cb) * width + ((step * 37 + cb * 11) % dims.audio_vocab_size)] = 100;
                auto result = state.step(text.data(), audio.data(), sampling);
                if (result.stop) break;
                rows.push_back(result.ids);
                if (result.ids[0] == dims.im_end_token_id) break;
            }
            int32_t codebooks = 0, frames = 0;
            auto codes = state.extract_audio_codes(codebooks, frames);
            results.push_back({{"name",test.at("name")},{"rows",rows},
                               {"codebooks",codebooks},{"frames",frames},{"codes",codes}});
        }
        std::cout << results.dump() << std::endl;
    } catch (const std::exception & error) {
        std::cerr << error.what() << std::endl; return 1;
    }
}

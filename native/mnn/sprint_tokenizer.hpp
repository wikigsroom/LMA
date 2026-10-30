// SPDX-License-Identifier: Apache-2.0
// The instruction is from diffusers 0.35.1 (Sana authors / Hugging Face).
// Token ownership and bounded native processing are LMA integration code.
#pragma once
#include "sprint_policy.hpp"
#include <sentencepiece_processor.h>
#include <filesystem>
#include <fstream>

namespace lma_mnn::sprint {
inline const std::string& instruction() {
    static const std::string value =
        "Given a user prompt, generate an 'Enhanced prompt' that provides detailed visual descriptions suitable for image generation. Evaluate the level of detail in the user prompt:\n"
        "- If the prompt is simple, focus on adding specifics about colors, shapes, sizes, textures, and spatial relationships to create vivid and concrete scenes.\n"
        "- If the prompt is already detailed, refine and enhance the existing details slightly without overcomplicating.\n"
        "Here are examples of how to transform or refine prompts:\n"
        "- User Prompt: A cat sleeping -> Enhanced: A small, fluffy white cat curled up in a round shape, sleeping peacefully on a warm sunny windowsill, surrounded by pots of blooming red flowers.\n"
        "- User Prompt: A busy city street -> Enhanced: A bustling city street scene at dusk, featuring glowing street lamps, a diverse crowd of people in colorful clothing, and a double-decker bus passing by towering glass skyscrapers.\n"
        "Please generate only the enhanced description for the prompt below and avoid including any additional commentary or evaluations:\n"
        "User Prompt: ";
    return value;
}
struct Tokens { std::vector<int> ids; size_t active = 0; bool truncated = false; };
class Tokenizer {
    sentencepiece::SentencePieceProcessor processor_;
public:
    explicit Tokenizer(const std::filesystem::path& file) {
        require(std::filesystem::is_regular_file(file) && std::filesystem::file_size(file) <= 16*1024*1024, "Missing/oversized Sana-Sprint tokenizer");
        // File streams use native paths; SentencePiece's narrow path overload does not on Windows.
        std::ifstream stream(file, std::ios::binary); std::string bytes((std::istreambuf_iterator<char>(stream)), {});
        require(stream.eof() || stream.good(), "Cannot read Sana-Sprint tokenizer");
        require(processor_.LoadFromSerializedProto(bytes).ok(), "Invalid Sana-Sprint SentencePiece model");
        require(processor_.GetPieceSize() == vocabulary && processor_.bos_id() == 2 && processor_.pad_id() == 0 && processor_.eos_id() == 1,
                "Sana-Sprint requires the matched Gemma2 vocabulary");
        require(encode(instruction()).size() == 208, "Sana-Sprint instruction token layout differs");
    }
    std::vector<int> encode(const std::string& text) const {
        std::vector<int> result{2};
        // HF's added-token matcher recognizes these literal control pieces.
        // SentencePiece otherwise treats control pieces as unavailable text.
        const std::vector<std::string> controls{"<pad>", "<eos>", "<bos>", "<unk>"};
        size_t position = 0;
        while (position < text.size()) {
            size_t next = text.size(); int control = -1;
            for (size_t i = 0; i < controls.size(); ++i) { size_t found = text.find(controls[i], position); if (found < next) { next = found; control = int(i); } }
            if (next > position) {
                std::vector<int> part;
                require(processor_.Encode(text.substr(position, next-position), &part).ok(), "Sana-Sprint tokenization failed");
                result.insert(result.end(), part.begin(), part.end());
            }
            if (control < 0) break;
            result.push_back(control); position = next+controls[control].size();
        }
        return result;
    }
    Tokens prompt(const std::string& normalized) const {
        require(!normalized.empty() && normalized.size() <= 64000 && normalized.find('\0') == std::string::npos, "Invalid Sana-Sprint prompt");
        Tokens tokens; tokens.ids = encode(instruction()+normalized);
        tokens.truncated = tokens.ids.size() > sequence; tokens.active = std::min(tokens.ids.size(), size_t(sequence)); tokens.ids.resize(sequence, 0);
        for (int id : tokens.ids) require(id >= 0 && id < vocabulary, "Sana-Sprint token ID out of range");
        return tokens;
    }
};
}

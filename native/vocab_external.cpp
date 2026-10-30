#include "vocab.h"
#include "tokenizer_data.hpp"
#include <cstdlib>
#include <fstream>
#include <iterator>
#include <stdexcept>

// No vocabulary bytes are compiled into the APK. The host supplies managed component paths.
static std::string vocabulary(const char* key) {
    const char* path = std::getenv(key);
    if (!path || !*path) throw std::runtime_error(std::string("Missing user-installed tokenizer component: ") + key);
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file || file.tellg() < 1 || file.tellg() > 32 * 1024 * 1024) throw std::runtime_error("Invalid tokenizer component");
    file.seekg(0);
    return std::string(std::istreambuf_iterator<char>(file), std::istreambuf_iterator<char>());
}
std::string load_clip_merges() { return vocabulary("LMA_VOCAB_CLIP_MERGES"); }
std::string load_qwen2_merges() { return lma_tokenizers::qwen_merges(vocabulary("LMA_VOCAB_QWEN_MERGES")); }
std::string load_mistral_merges() { return vocabulary("LMA_VOCAB_MISTRAL_MERGES"); }
std::string load_mistral_vocab_json() { return vocabulary("LMA_VOCAB_MISTRAL_JSON"); }
std::string load_t5_tokenizer_json() { return vocabulary("LMA_VOCAB_T5_JSON"); }
std::string load_umt5_tokenizer_json() { return vocabulary("LMA_VOCAB_UMT5_JSON"); }
std::string load_gemma_merges() { return vocabulary("LMA_VOCAB_GEMMA_MERGES"); }
std::string load_gemma_vocab_json() { return vocabulary("LMA_VOCAB_GEMMA_JSON"); }

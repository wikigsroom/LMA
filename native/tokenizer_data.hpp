#pragma once
#include <stdexcept>
#include <string>

namespace lma_tokenizers {
// Qwen2Tokenizer assigns IDs from merge order. A HF file header is not a merge.
// Preserve the installed asset; normalize only the private in-memory parser input.
inline std::string qwen_merges(const std::string& source) {
    std::string text; text.reserve(source.size());
    size_t begin = source.compare(0, 3, "\xef\xbb\xbf") == 0 ? 3 : 0;
    for (size_t i = begin; i < source.size(); ++i) {
        if (source[i] == '\r') {
            if (i + 1 == source.size() || source[i + 1] != '\n') throw std::runtime_error("Invalid Qwen merge line ending");
            continue;
        }
        text.push_back(source[i]);
    }
    const std::string header = "#version: 0.2\n";
    if (text.compare(0, header.size(), header) == 0) text.erase(0, header.size());
    if (text.empty() || text.compare(0, 9, "#version:") == 0) throw std::runtime_error("Unsupported Qwen merge file header");
    return text;
}
}

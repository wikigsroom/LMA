#include "qwen2_tokenizer.h"
#include "vocab.h"
#include "qwen_prompt.hpp"
#include "json.hpp"
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <codecvt>
#include <locale>

class ProbeTokenizer : public Qwen2Tokenizer {
public:
    nlohmann::json vocab() const {
        nlohmann::json result=nlohmann::json::object();
        std::wstring_convert<std::codecvt_utf8<char32_t>,char32_t> convert;
        for(const auto& entry:encoder) result[convert.to_bytes(entry.first)]=entry.second;
        return result;
    }
};

int main(int argc, char** argv) {
    try {
        if (argc != 3) throw std::runtime_error("Pass an owned tokenizer case JSON and canonical output path");
        std::ifstream stream(argv[1], std::ios::binary | std::ios::ate);
        if (!stream || stream.tellg() < 1 || stream.tellg() > 256*1024) throw std::runtime_error("Invalid tokenizer case file");
        stream.seekg(0); nlohmann::json input; stream >> input;
        auto canonical = load_qwen2_merges();
        std::ofstream output(argv[2], std::ios::binary); output.write(canonical.data(), canonical.size()); output.close();
        if (!output) throw std::runtime_error("Cannot save canonical tokenizer input");
        ProbeTokenizer tokenizer;
        nlohmann::json result = nlohmann::json::array();
        for (const auto& item : input.at("texts")) {
            std::string text = item.get<std::string>(), error; std::vector<int> tokens;
            if (!tokenizer.encode(lma_tokenizers::qwen_prompt(text),tokens,nullptr,&error)) throw std::runtime_error("Actual tokenizer failed: "+error);
            result.push_back(tokens);
        }
        nlohmann::json report{{"tokens",result},{"canonical_bytes",canonical.size()}};
        if(input.value("include_vocab",false)) report["vocab"]=tokenizer.vocab();
        std::cout << report.dump() << std::endl;
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << std::endl; return 1;
    }
}

#pragma once
#include "utf8proc.h"
#include <cstdlib>
#include <memory>
#include <stdexcept>
#include <string>

namespace lma_tokenizers {
// Match the Qwen HF tokenizer's NFC normalizer before its regex/BPE split.
inline std::string qwen_prompt(const std::string& input) {
    utf8proc_uint8_t* output=nullptr;
    auto length=utf8proc_map(reinterpret_cast<const utf8proc_uint8_t*>(input.data()),input.size(),&output,
                            static_cast<utf8proc_option_t>(UTF8PROC_STABLE | UTF8PROC_COMPOSE));
    std::unique_ptr<utf8proc_uint8_t,decltype(&std::free)> owned(output,&std::free);
    if(length<0)throw std::runtime_error("Invalid Qwen prompt Unicode");
    return length==0?std::string():std::string(reinterpret_cast<const char*>(output),length);
}
}

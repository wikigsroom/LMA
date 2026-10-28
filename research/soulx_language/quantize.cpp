// SPDX-License-Identifier: MIT
// Explicit developer-only Q4_K_M conversion; never packaged in the APK.
#include "llama.h"
#include <filesystem>
#include <iostream>
int main(int argc,char** argv){
    if(argc!=3 || std::filesystem::exists(argv[2])){std::cerr<<"Usage: quantize INPUT_F16 NEW_Q4_OUTPUT\n";return 2;}
    auto params=llama_model_quantize_default_params();params.ftype=LLAMA_FTYPE_MOSTLY_Q4_K_M;params.nthread=4;
    auto input=std::filesystem::path(argv[1]).u8string(),output=std::filesystem::path(argv[2]).u8string();
    return static_cast<int>(llama_model_quantize(input.c_str(),output.c_str(),&params));
}

// SPDX-License-Identifier: MIT
#pragma once
#include "../soulx/dsp.hpp"
#include <cstdint>
#include <filesystem>
#include <string>

namespace lma::soulx {
struct OrtStats {
    size_t graph_runs=0,session_loads=0,session_unloads=0,max_live_sessions=0,terminated_runs=0;
    std::string runtime_version;
};
using Progress = std::function<void(const std::string&,int,int)>;
using Trace = std::function<void(const std::string&,const Samples&,const std::vector<int64_t>&)>;
}

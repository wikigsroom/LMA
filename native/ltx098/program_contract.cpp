// SPDX-License-Identifier: Apache-2.0
// Host-only bounded check of the actual production RF update; never loads weights.
#include "sampling.hpp"
#include "json.hpp"
#include <iostream>
int main() {
    using namespace lma::ltx098;using Json=nlohmann::json;
    Json passes=Json::array();
    for(bool second:{false,true}) {
        auto schedule=multiscale_sigmas(second);std::vector<float> value{-.7f,.1f,.6f,1.2f},velocity{.3f,-.6f,.1f,.8f};Json steps=Json::array();
        for(size_t i=0;i<schedule.size();++i) {
            float next=i+1<schedule.size()?schedule[i+1]:0;
            value=multiscale_step(value,velocity,schedule[i],next);steps.push_back(value);
        }
        passes.push_back(Json{{"second",second},{"schedule",schedule},{"steps",steps}});
    }
    std::cout<<Json{{"ok",true},{"passes",passes},{"model_inference",false}}.dump()<<std::endl;
}

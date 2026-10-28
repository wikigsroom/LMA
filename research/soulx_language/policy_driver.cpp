// SPDX-License-Identifier: MIT
// Exposes actual production policy functions to independent host comparisons.
#include "policy.hpp"
#include "json.hpp"
#include <fstream>
#include <iostream>
using namespace lma::soulx::language;
using json=nlohmann::json;
int main(int argc,char** argv){
    try{
        require(argc==2,"Usage: policy-driver REQUEST_JSON");std::ifstream input(argv[1],std::ios::binary);json request;input>>request;json out;
        std::string mode=request.at("mode");
        if(mode=="text"){
            out["texts"]=json::array();for(const auto& item:request.at("texts")){std::string text=item;out["texts"].push_back(normalize(text));}
            out["formatted"]=json::array();for(const auto& item:request.at("turns"))out["formatted"].push_back(format_text(item.at("text"),item.at("speaker"),item.value("first_reference",false)));
        }else if(mode=="sample"){
            auto x=request.at("layout");Layout layout{x.at("vocabulary"),x.at("offset"),x.at("eos"),x.at("audio_start")};out["cases"]=json::array();
            for(const auto& item:request.at("cases")){
                try{
                    Sampling p;auto config=item.value("sampling",json::object());p.temperature=config.value("temperature",p.temperature);p.repetition=config.value("repetition_penalty",p.repetition);p.top_p=config.value("top_p",p.top_p);p.top_k=config.value("top_k",p.top_k);p.minimum=config.value("min_tokens",p.minimum);p.maximum=config.value("max_tokens",p.maximum);p.tau=config.value("ras_tau",p.tau);p.window=config.value("ras_window",p.window);p.ras=config.value("use_ras",p.ras);
                    auto raw=item.at("logits").get<std::vector<float>>();auto generated=item.at("generated").get<Tokens>();auto all=item.at("input").get<Tokens>();auto processed=scores(raw,generated,layout,p);auto probs=probabilities(processed);auto selected=sample(raw,generated,all,layout,p,item.at("candidate_uniform"),item.at("final_uniform"));
                    out["cases"].push_back({{"ok",true},{"probabilities",probs},{"token",selected.token},{"ras_reset",selected.ras_reset}});
                }catch(const std::exception& e){out["cases"].push_back({{"ok",false},{"error",e.what()}});}
            }
        }else if(mode=="history"){
            auto x=request.at("layout");Layout layout{x.at("vocabulary"),x.at("offset"),x.at("eos"),x.at("audio_start")};Window window;auto w=request.at("window");window.max_turns=w.at("max_turns");window.threshold=w.at("threshold");window.history=w.at("history");window.text_history=w.at("text_history");
            Tokenize tokenizer=[&](const std::string& text){return request.at("tokenized").at(text).get<Tokens>();};std::vector<Reference> refs;for(const auto& r:request.at("references"))refs.push_back({r.at("text"),r.at("codes").get<Tokens>()});
            History history(refs,layout,window,tokenizer);out["inputs"]=json::array();for(const auto& t:request.at("turns")){Turn turn{t.at("text"),t.at("speaker")};auto input=history.input(turn,request.at("context"),request.at("reserve"),tokenizer);out["inputs"].push_back(input);history.accept(turn,t.at("generated").get<Tokens>(),tokenizer);}out["resets"]=history.resets;
        }else throw std::invalid_argument("Unknown policy mode");
        out["ok"]=true;std::cout<<out.dump()<<'\n';return 0;
    }catch(const std::exception& e){std::cout<<json({{"ok",false},{"error",e.what()}}).dump()<<'\n';return 1;}
}

// SPDX-License-Identifier: MIT
// Developer-only protocol/generation CLI. Not an App worker or HTTP endpoint.
#include "language.hpp"
#include "json.hpp"
#include <atomic>
#include <chrono>
#include <fstream>
#include <iostream>
#include <thread>
using namespace lma::soulx::language;
using json=nlohmann::json;
namespace fs=std::filesystem;
std::string read(const fs::path& file,size_t maximum){auto n=fs::file_size(file);require(n && n<=maximum,"SoulX developer request exceeds bounds");std::string result(static_cast<size_t>(n),'\0');std::ifstream stream(file,std::ios::binary);require(static_cast<bool>(stream.read(result.data(),static_cast<std::streamsize>(n))),"Cannot read SoulX developer request");return result;}
Sampling sampling(const json& x){Sampling p;p.temperature=x.value("temperature",p.temperature);p.repetition=x.value("repetition_penalty",p.repetition);p.top_p=x.value("top_p",p.top_p);p.tau=x.value("ras_tau",p.tau);p.top_k=x.value("top_k",p.top_k);p.minimum=x.value("min_tokens",p.minimum);p.maximum=x.value("max_tokens",p.maximum);p.window=x.value("ras_window",p.window);p.ras=x.value("use_ras",p.ras);valid_sampling(p);return p;}
int main(int argc,char** argv){
    Stats stats;std::atomic<bool> cancel{false};std::thread delayed;
    struct Join{std::thread& t;~Join(){if(t.joinable())t.join();}}join{delayed};
    try{
        require(argc==4,"Usage: soulx-language-cli MODEL_GGUF REQUEST_JSON NEW_OUTPUT_JSON");fs::path output=argv[3];require(!fs::exists(output),"SoulX developer output must be new");
        auto request=json::parse(read(argv[2],4*1024*1024));require(request.at("format")=="lma.soulx-language-input/1","Unknown SoulX language request format");
        std::string mode=request.value("mode",std::string("generate"));Options options;options.context=request.value("context",2048);options.threads=request.value("threads",2);options.batch=request.value("batch",128);options.vocabulary_only=mode=="inspect";
        require(mode=="generate" || mode=="inspect" || mode=="evaluate" || mode=="cancel_before" || mode=="cancel_decode" || mode=="cancel_token","Unknown SoulX language developer mode");
        if(mode=="cancel_before")cancel=true;
        auto progress=[&](const std::string& stage,int done,int total){
            (void)done;(void)total;
            if(mode=="cancel_decode" && stage=="language_decode" && !delayed.joinable())delayed=std::thread([&]{std::this_thread::sleep_for(std::chrono::milliseconds(20));cancel=true;});
            if(mode=="cancel_token" && stage=="language_token")cancel=true;
        };
        json result;
        {
            Model model(argv[1],options,stats,[&]{return cancel.load();},progress);auto layout=model.layout();
            result={{"layout",{{"vocabulary",layout.vocabulary},{"speech_offset",layout.offset},{"speech_eos",layout.eos},{"audio_start",layout.audio_start}}},{"vocabulary_only",options.vocabulary_only},{"full_text_to_speech",false},{"apk_runtime",false}};
            if(options.vocabulary_only){
                result["texts"]=json::array();for(const auto& text:request.at("texts")){std::string source=text;result["texts"].push_back({{"source",source},{"normalized",normalize(source)},{"ids",model.tokenize(source)}});}
                result["formatted"]=json::array();for(const auto& turn:request.value("turns",json::array())){std::string text=turn.at("text");int speaker=turn.value("speaker",0);auto formatted=format_text(text,speaker,turn.value("first_reference",false));result["formatted"].push_back({{"text",formatted},{"ids",model.tokenize(formatted)}});}
            }else if(mode=="evaluate"){
                result["logits"]=model.evaluate(request.at("tokens").get<Tokens>());
            }else{
                std::vector<Reference> refs;for(const auto& r:request.at("references"))refs.push_back({r.at("text"),r.at("codes").get<Tokens>()});
                std::vector<Turn> turns;for(const auto& t:request.at("turns"))turns.push_back({t.at("text"),t.value("speaker",0)});
                Window window;auto w=request.value("window",json::object());window.max_turns=w.value("max_turns",10);window.threshold=w.value("threshold",6192);window.history=w.value("history",2);window.text_history=w.value("text_history",2);
                auto generated=model.generate(refs,turns,sampling(request.value("sampling",json::object())),window,request.value("seed",uint64_t(42)));
                result["turns"]=json::array();for(const auto& t:generated)result["turns"].push_back({{"speaker",t.speaker},{"codes",t.semantic},{"language_ids",t.language_ids},{"eos",t.eos},{"history_delimiter_inserted",t.history_delimiter_inserted},{"input_tokens",t.input_tokens}});
            }
        }
        require(mode=="inspect" || mode=="generate" || mode=="evaluate","Requested language cancellation was not observed");result["ok"]=true;result["model_loads"]=stats.model_loads;result["model_unloads"]=stats.model_unloads;result["decode_calls"]=stats.decode_calls;result["decoded_tokens"]=stats.decoded_tokens;result["aborted_decodes"]=stats.aborted_decodes;result["generated_tokens"]=stats.generated_tokens;result["ras_resets"]=stats.ras_resets;result["history_resets"]=stats.history_resets;
        std::ofstream file(output,std::ios::binary);file<<result.dump(2)<<'\n';require(static_cast<bool>(file),"Cannot write SoulX language result");std::cout<<result.dump()<<'\n';return 0;
    }catch(const std::exception& error){std::cout<<json({{"ok",false},{"error",error.what()},{"model_loads",stats.model_loads},{"model_unloads",stats.model_unloads},{"decode_calls",stats.decode_calls},{"decoded_tokens",stats.decoded_tokens},{"aborted_decodes",stats.aborted_decodes}}).dump()<<'\n';return 1;}
}

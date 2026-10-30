// SPDX-License-Identifier: MIT
// Bounded program graphs/arrays only; no complete or trained neural models.
#include "sprint.hpp"
#include "json.hpp"
#include <cstdio>
#include <fstream>
#include <iostream>
#include <limits>

using namespace lma_mnn::sprint;
using json = nlohmann::json;
static int passed = 0;
static void check(bool ok) { if (!ok) throw std::runtime_error("Sana-Sprint program assertion failed"); ++passed; }
template<class F> static void rejects(F action) { bool failed = false; try { action(); } catch (const std::exception&) { failed = true; } check(failed); }
static void equal(const Values& actual, const Values& expected, float tolerance = 0) {
    check(actual.size() == expected.size());
    for (size_t i = 0; i < actual.size(); ++i) check(std::abs(actual[i]-expected[i]) <= tolerance);
}
int main(int argc, char** argv) {
    try {
        require(argc == 4, "Pass bounded case JSON, tokenizer metadata and output directory");
        std::ifstream input(argv[1]); json cases; input >> cases; auto root = std::filesystem::path(argv[3]); std::filesystem::create_directories(root);
        parameters(1024,1024,2,4,4.5f,42,"cat",""); ++passed;
        rejects([]{parameters(512,1024,2,4,4.5f,42,"cat","");});
        rejects([]{parameters(1024,1024,5,4,4.5f,42,"cat","");});
        rejects([]{parameters(1024,1024,2,33,4.5f,42,"cat","");});
        rejects([]{parameters(1024,1024,2,4,NAN,42,"cat","");});
        rejects([]{parameters(1024,1024,2,4,4.5f,-1,"cat","");});
        rejects([]{parameters(1024,1024,2,4,4.5f,42,"cat","negative");});
        auto mask = causal_mask(2,4); equal(mask,{0,-10000,-10000,-10000,0,0,-10000,-10000,0,0,-10000,-10000,0,0,-10000,-10000});
        rejects([]{causal_mask(0);}); rejects([]{causal_mask(507);});
        Values features(6*2); for (int i = 0; i < 12; ++i) features[i] = float(i);
        equal(select_features(features,2,6,3),{0,1,8,9,10,11}); equal(selected_mask(5,6,3),{1,1,0});
        equal(selected_mask(1,6,3),{1,0,0}); rejects([&]{select_features(features,3,6,3);});
        for (const auto& item : cases.at("scm")) {
            auto times = schedule(item.at("steps")); equal(times,item.at("schedule").get<Values>(),2e-7f);
            for (const auto& sample : item.at("cases")) {
                auto x=sample.at("sample").get<Values>(), prediction=sample.at("prediction").get<Values>(), noise=sample.at("noise").get<Values>();
                auto out=step(x,prediction,noise,sample.at("time"),sample.at("next"));
                equal(model_input(x,sample.at("time")),sample.at("model_input").get<Values>(),3e-6f);
                equal(out.sample,sample.at("previous").get<Values>(),3e-6f); equal(out.denoised,sample.at("denoised").get<Values>(),3e-6f);
            }
        }
        rejects([]{schedule(0);}); rejects([]{step({1},{},{1},1,0);}); rejects([]{step({NAN},{1},{1},1,0);});
        check(half(0x3c00)==1 && half(0xc000)==-2 && half(0x0001)==std::ldexp(1.0f,-24)); rejects([]{half(0x7c00);});
        auto embedding=root/"embedding.bin";
        { std::ofstream stream(embedding,std::ios::binary); for (int i=0;i<8;++i) {uint16_t row[4]={0,0x3c00,0xc000,1};stream.write(reinterpret_cast<char*>(row),8);} }
        auto values=embeddings(embedding,{0,2,7},8,4,2);
        for (size_t i=0;i<values.size();i+=4) equal(Values(values.begin()+i,values.begin()+i+4),{0,2,-4,std::ldexp(1.0f,-23)});
        rejects([&]{embeddings(embedding,{8},8,4,2);}); rejects([&]{embeddings(embedding,{0},7,4,2);});
        auto rgb=pixels({-1,1,0,0,1,-1},2,1); check(rgb==std::vector<uint8_t>({0,128,255,255,128,0})); rejects([]{pixels({0,0,NAN},1,1);});
        Tokenizer tokenizer{std::filesystem::path(argv[2])};
        for (const auto& token : cases.at("tokens")) check(tokenizer.encode(token.at("text"))==token.at("ids").get<std::vector<int>>());
        for (const auto& token : cases.at("prompts")) {
            auto encoded=tokenizer.prompt(token.at("text")); check(encoded.ids==token.at("ids").get<std::vector<int>>());
            check(encoded.active==token.at("active") && encoded.truncated==token.at("truncated"));
        }
        // These two expressions use constants and twelve numbers, not model weights.
        using namespace MNN; using namespace MNN::Express;
        auto x=_Input({1,3,4},NCHW,halide_type_of<float>()), y=_Input({1,3,4},NCHW,halide_type_of<float>());
        x->setName("hidden_states"); y->setName("attention_mask"); auto sum=_Add(x,y); sum->setName("out");
        auto file=root/"small-add.mnn"; Variable::save({sum},file.u8string().c_str());
        Values a(12,1),b(12,2); auto actual=graph(file,{{"hidden_states",{1,3,4},&a},{"attention_mask",{1,3,4},&b}},{1,3,4},2);
        equal(actual,Values(12,3));
        rejects([&]{graph(file,{{"hidden_states",{1,3,4},&a},{"attention_mask",{1,3,4},&b}},{1,4,3},2);});
        rejects([&]{graph(file,{{"hidden_states",{1,4,3},&a},{"attention_mask",{1,3,4},&b}},{1,3,4},2);});
        auto image=_Input({1,3,2,2},NCHW,halide_type_of<float>()); image->setName("latent"); auto decoded=_Add(image,_Scalar(0.5f)); decoded->setName("image");
        file=root/"small-decode.mnn"; Variable::save({decoded},file.u8string().c_str()); Values zeros(12,0);
        equal(graph(file,{{"latent",{1,3,2,2},&zeros}},{1,3,2,2},1,"image"),Values(12,0.5f));
        std::cout << json{{"passed",passed},{"bounded_graphs",2},{"trained_model_execution",false},{"full_pipeline_execution",false},{"tokenizer_cases",cases.at("tokens").size()+cases.at("prompts").size()}}.dump() << std::endl;
        return 0;
    } catch(const std::exception& error) { std::cerr << error.what() << std::endl; return 1; }
}

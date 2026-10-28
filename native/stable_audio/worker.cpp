// SPDX-License-Identifier: MIT
// Export layout and ping-pong schedule adapted from Arm ML-examples (Apache-2.0).
#include "json.hpp"
#include "litert_model.hpp"
#include "litert/c/internal/litert_logging.h"
#include "sentencepiece_processor.h"
#include <chrono>
#include <cstdio>
#include <cstdarg>
#include <signal.h>
#include <sys/prctl.h>
#include <unistd.h>

// Prevent runtime diagnostics from writing prompts or model data into logcat.
extern "C" int __android_log_print(int,const char*,const char*,...){return 0;}
extern "C" int __android_log_vprint(int,const char*,const char*,va_list){return 0;}
extern "C" int __android_log_write(int,const char*,const char*){return 0;}
using json=nlohmann::json;using namespace lma_sao;
static FILE* events=nullptr;
static void event(const json& data){if(events){std::string line=data.dump();std::fprintf(events,"%s\n",line.c_str());std::fflush(events);}}
int main(int argc,char** argv) {
    try {
        events=fdopen(dup(STDOUT_FILENO),"w");require(events && freopen("/dev/null","w",stdout) && freopen("/dev/null","w",stderr),"Cannot isolate diagnostics");
        pid_t parent=getppid();require(prctl(PR_SET_PDEATHSIG,SIGKILL)==0 && parent!=1 && getppid()==parent,"Cannot bind worker to host lifetime");
        check(LiteRtSetMinLoggerSeverity(LiteRtGetDefaultLogger(),kLiteRtLogSeveritySilent),"Cannot silence runtime diagnostics");
        if(argc==2 && std::string(argv[1])=="--info"){event({{"schema","lma.engine/1"},{"engine","stable_audio_litert"},{"revision",LMA_SAO_REVISION},{"runtime","LiteRT 2.2.0"},{"backend","cpu"},{"bundled_model_data",false},{"generation_tested",false}});return 0;}
        require(argc==2,"Pass a private request file");std::ifstream in(argv[1],std::ios::binary|std::ios::ate);require(bool(in) && in.tellg()>0 && in.tellg()<=256*1024,"Invalid private request size");in.seekg(0);json r;in>>r;
        require(r.at("schema")=="lma.engine-request/1" && r.at("pipeline")=="stable_audio_small_litert_v1" && r.at("type")=="audio.generate","Unsupported Stable Audio request");
        const auto& p=r.at("parameters");int threads=p.at("threads"),seconds=p.at("seconds"),steps=p.at("steps"),limit=p.at("maxInputTokens");int64_t seed=p.at("seed");bounds(threads,seed,seconds,steps,limit);
        require(p.size()==5,"Unknown Stable Audio parameter");std::string text=r.at("input").at("prompt");prompt(text);require(r.at("input").value("negativePrompt",std::string()).empty() && (!r.at("input").contains("artifacts") || r.at("input").at("artifacts").empty()),"This export does not accept negative prompts or references");
        using Clock=std::chrono::steady_clock;auto start=Clock::now(),stage=start;auto elapsed=[](Clock::time_point from){return std::chrono::duration<double,std::milli>(Clock::now()-from).count();};
        std::string models=r.at("workspace").get<std::string>()+"/models/",output=r.at("output");std::vector<int> ids;
        event({{"event","stage"},{"stage","tokenizing_prompt"}});
        {sentencepiece::SentencePieceProcessor sp;require(sp.Load(models+"tokenizer.model").ok(),"Cannot load selected T5 SentencePiece tokenizer");require(sp.Encode(text,&ids).ok(),"Cannot tokenize audio description");token_ids(ids,limit,sp.GetPieceSize(),sp.pad_id(),sp.eos_id());}
        Environment env;check(LiteRtCreateEnvironment(0,nullptr,&env.value),"Cannot create local LiteRT environment");
        std::vector<float> cross,global,x(latent_size);double conditioner_ms,dit_ms,decoder_ms;
        event({{"event","stage"},{"stage","encoding_prompt"}});stage=Clock::now();
        {
            Model model(env,models+"conditioner.tflite",threads,{i64({1,128}),i64({1,128}),f32({1})},{f32({1,65,768}),f32({1,65}),f32({1,768})});
            std::vector<int64_t> tokens(128,0),mask(128,0);for(size_t i=0;i<ids.size();i++){tokens[i]=ids[i];mask[i]=1;}
            model.write(0,tokens);model.write(1,mask);model.write(2,std::vector<float>{float(seconds)});model.run();cross=model.read(0);model.read(1);global=model.read(2);
        }
        conditioner_ms=elapsed(stage);event({{"event","stage"},{"stage","diffusing_audio"}});stage=Clock::now();
        {
            Model model(env,models+"diffusion_model.tflite",threads,{f32({1,64,256}),f32({1}),f32({1,65,768}),f32({1,768})},{f32({1,64,256})});model.write(2,cross);model.write(3,global);
            cross.clear();cross.shrink_to_fit();global.clear();global.shrink_to_fit();random_normal(x,uint32_t(seed));auto sigmas=schedule(steps);
            for(int i=0;i<steps;i++) {model.write(0,x);model.write(1,std::vector<float>{sigmas[size_t(i)]});model.run();advance(x,model.read(0),sigmas[size_t(i)],sigmas[size_t(i)+1],uint32_t(seed)+uint32_t(i)+4564);event({{"event","progress"},{"stage","diffusing_audio"},{"step",i+1},{"steps",steps}});}
        }
        dit_ms=elapsed(stage);event({{"event","stage"},{"stage","decoding_audio"}});stage=Clock::now();std::vector<float> audio;
        {Model model(env,models+"audio_decoder.tflite",threads,{f32({1,64,256})},{f32({1,2,524288})});model.write(0,x);model.run();audio=model.read(0);}
        decoder_ms=elapsed(stage);event({{"event","stage"},{"stage","saving_audio"}});write_wave(output,pcm(audio,seconds));double total=elapsed(start);
        event({{"event","execution"},{"details",{{"backend","cpu"},{"sampleRate",44100},{"channels",2},{"promptTokensIncludingEos",ids.size()},{"conditioningLimit",64},{"fixedLatentFrames",256},{"decodedFrames",524288},{"outputFrames",seconds*44100},{"generationSteps",steps},{"conditionerMs",conditioner_ms},{"diffusionMs",dit_ms},{"decoderMs",decoder_ms},{"pipelineMs",total},{"audioDurationSeconds",seconds},{"pipelineRTF",total/1000/seconds},{"stageLoading","sequential"},{"sampler","arm_pingpong_logsnr_v1"},{"stopReason","requested_steps"}}}});
        event({{"event","complete"},{"output",output}});return 0;
    }catch(const std::exception& e){event({{"event","error"},{"message",e.what()}});return 1;}
}

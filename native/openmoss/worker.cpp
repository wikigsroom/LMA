#include "json.hpp"
#include "model_contract.hpp"
#include "wave.hpp"
#include "generation_guard.hpp"
#include "openmoss/model.h"
#include "openmoss/pipeline.h"
#include "openmoss/soundeffect.h"
#include "openmoss/tokenizer.h"
#include "aux_internal.h"
#include "ggml-cpu.h"
#include "llama.h"
#include <chrono>
#include <cstdio>
#include <fstream>
#include <signal.h>
#include <sys/prctl.h>
#include <unistd.h>

using json=nlohmann::json;using Clock=std::chrono::steady_clock;
static FILE* events;
static void event(const json& data) {if(events){auto s=data.dump();std::fprintf(events,"%s\n",s.c_str());std::fflush(events);}}
static int64_t elapsed(Clock::time_point t) {return std::chrono::duration_cast<std::chrono::milliseconds>(Clock::now()-t).count();}
int main(int argc,char** argv) {
    using namespace lma_openmoss;
    try {
        events=fdopen(dup(STDOUT_FILENO),"w");require(events && freopen("/dev/null","w",stdout) && freopen("/dev/null","w",stderr),"Cannot isolate native diagnostics");
        pid_t parent=getppid();require(prctl(PR_SET_PDEATHSIG,SIGKILL)==0 && parent!=1 && getppid()==parent,"Cannot bind worker lifetime to host");
        if(argc==2 && std::string(argv[1])=="--info") {event({{"schema","lma.engine/1"},{"engine","openmoss_native"},{"revision",LMA_OPENMOSS_REVISION},{"backend","cpu"},{"bundled_model_data",false},{"generation_tested",false}});return 0;}
        require(argc==2,"Pass a private request file");std::ifstream file(argv[1],std::ios::binary|std::ios::ate);require(bool(file) && file.tellg()>0 && file.tellg()<=256*1024,"Invalid request size");file.seekg(0);json request;file>>request;
        std::string pipeline=request.at("pipeline");bool is_local=local(pipeline),is_delay=delay(pipeline),is_sound=!is_local && !is_delay;int rate=is_delay?24000:48000,channels=is_local?2:1;
        require(request.at("schema")=="lma.engine-request/1" && request.at("type")== (is_sound?"audio.generate":"speech.synthesize"),"Unsupported openmoss task");
        const auto& p=request.at("parameters");int threads=p.at("threads");int64_t seed=p.at("seed");common(threads,seed);
        std::string text=request.at("input").at("prompt"),negative=request.at("input").value("negativePrompt",std::string());prompt(text,true);prompt(negative,false);
        require(is_sound?(!request.contains("referenceAudio") && !request.contains("referenceAudios")):negative.empty(),"Input does not match selected MOSS pipeline");
        require(is_delay?!request.contains("referenceAudio"):!request.contains("referenceAudios"),"Reference layout differs from selected pipeline");
        if(!is_sound)speech(p.at("maxInputTokens"),p.at("maxNewTokens"),p.at("textTemperature"),p.at("audioTemperature"),p.at("audioTopP"),p.at("audioTopK"),p.at("audioRepetitionPenalty"),is_delay);
        else {sound(p.at("seconds"),p.at("steps"),p.at("cfgScale"),p.at("sigmaShift"));require(p.at("cfgScale").get<double>()!=1 || clean(negative).empty(),"CFG=1 does not use negative conditioning; increase CFG or clear the negative prompt");}
        std::string workspace=request.at("workspace"),output=request.at("output"),backbone=workspace+"/models/model.gguf",extras=workspace+"/models/model.extras.gguf";
        if(is_delay) {instruction(text,32000);speakers(text,dialogue(pipeline));instruction(p.at("voiceInstruction"),4000);instruction(p.at("language"),256);if(pipeline=="moss_voicegen_openmoss_cpu_v1")require(!clean(p.at("voiceInstruction")).empty() && !request.contains("referenceAudios"),"VoiceGenerator requires an instruction and no reference audio");}
        auto start=Clock::now();event({{"event","stage"},{"stage","validating_model_layout"}});int budget=is_delay?delay_contract(backbone,extras,pipeline):model_contract(backbone,extras,is_local);
        llama_backend_init();openmoss::LoadOptions options;options.n_ctx=is_sound?512:budget;options.n_batch=512;options.n_threads=threads;options.n_gpu_layers=0;options.aux_cpu=true;options.flash_attn=false;
        event({{"event","stage"},{"stage","loading_models"}});auto model=openmoss::Model::load(backbone,options);int64_t load_ms=elapsed(start);require(model->aux() && model->aux()->backend,"CPU auxiliary backend missing");ggml_backend_cpu_set_n_threads(model->aux()->backend,threads);
        const auto& d=model->dims();require(d.arch==(is_delay?openmoss::Arch::TTSDelay:is_local?openmoss::Arch::TTSLocal:openmoss::Arch::SoundEffect),"Loaded architecture differs");
        json details={{"backend","cpu"},{"sampleRate",rate},{"channels",channels},{"modelLoadMs",load_ms}};std::vector<float> audio;
        if(!is_sound) {
            openmoss::GenerateRequest r;r.text=text;r.max_new_tokens=p.at("maxNewTokens");r.sampling=openmoss::default_sampling(d.arch);r.sampling.text_temperature=p.at("textTemperature");r.sampling.audio_temperature=p.at("audioTemperature");r.sampling.audio_top_p=p.at("audioTopP");r.sampling.audio_top_k=p.at("audioTopK");r.sampling.audio_repetition_penalty=p.at("audioRepetitionPenalty");r.sampling.seed=uint64_t(seed);
            if(is_delay) {r.prompt_template=dialogue(pipeline)?openmoss::PromptTemplate::TTSD:openmoss::PromptTemplate::VoiceGen;r.continuation_prefix=codebooks(pipeline)<32;std::string hint=p.at("voiceInstruction"),language=p.at("language");if(!clean(hint).empty())r.instruction=hint;if(!clean(language).empty())r.language=language;}
            int frames=0;int64_t reference_ms=0;json paths=json::array();if(request.contains("referenceAudio"))paths.push_back(request.at("referenceAudio"));if(request.contains("referenceAudios"))paths=request.at("referenceAudios");
            require(paths.is_array() && (paths.empty() || paths.size()==size_t(dialogue(pipeline)?2:1)),"References must follow the selected one/two speaker layout");
            if(!paths.empty()) {event({{"event","stage"},{"stage","encoding_reference"}});auto t=Clock::now();for(const auto& path:paths) {auto ref=openmoss::encode_reference(*model,reference_wave(path,rate,channels),true);require(ref.n_frames>=12 && ref.n_frames<=126 && ref.codes.size()==size_t(ref.n_frames)*codebooks(pipeline),"Reference encoder returned incompatible codes");for(int x:ref.codes)require(x>=0 && x<1024,"Reference codec values differ");frames+=ref.n_frames;r.reference_codes.push_back(std::move(ref));}reference_ms=elapsed(t);}
            generation_budget={p.at("maxInputTokens"),0};
            event({{"event","stage"},{"stage","generating_speech"}});auto result=openmoss::generate(*model,r);audio=std::move(result.waveform);
            int prefix=is_delay && codebooks(pipeline)<32?frames:0;require(result.n_channels==channels && result.n_codebooks==codebooks(pipeline) && result.n_audio_frames>prefix && result.n_audio_frames<=r.max_new_tokens+prefix,"Invalid speech codebook/frame count");
            details.update({{"formattedInputFrames",generation_budget.prompt_frames},{"referenceFrames",frames},{"referenceSpeakers",paths.size()},{"continuationPrefixFrames",prefix},{"referenceEncodeMs",reference_ms},{"audioFramesIncludingPrefix",result.n_audio_frames},{"prefillMs",result.prefill_seconds*1000},{"generationMs",result.generate_seconds*1000},{"codecDecodeMs",result.decode_seconds*1000},{"stopReason","model_or_application_limit"}});
        } else {
            openmoss::SoundEffectRequest r;r.prompt=text;r.negative_prompt=negative;r.seconds=p.at("seconds");r.num_inference_steps=p.at("steps");r.cfg_scale=p.at("cfgScale");r.sigma_shift=p.at("sigmaShift");r.seed=uint64_t(seed);
            char suffix[64];std::snprintf(suffix,sizeof(suffix)," duration: %.1fs",double(r.seconds));auto tokens=model->tokenizer()->encode(clean(text+suffix),false);auto neg=model->tokenizer()->encode(clean(negative),false);require(!tokens.empty() && tokens.size()<=512 && neg.size()<=512,"SoundEffect formatted prompt exceeds 512 tokens; shorten it");
            event({{"event","stage"},{"stage","generating_sound_effect"}});auto result=openmoss::generate_sound_effect(*model,r,[](int step,int total){event({{"event","progress"},{"step",step},{"steps",total},{"stage","denoising"}});if(step==total)event({{"event","stage"},{"stage","decoding_audio"}});});audio=std::move(result.waveform);
            require(result.sampling_rate==48000 && audio.size()==size_t(double(r.seconds)*48000),"SoundEffect output duration differs");
            details.update({{"promptTokens",result.n_prompt_tokens},{"latentFrames",result.n_latents},{"fullLatentSeconds",d.max_seconds},{"steps",r.num_inference_steps},{"textEncodeMs",result.text_seconds*1000},{"samplingMs",result.sample_seconds*1000},{"codecDecodeMs",result.decode_seconds*1000},{"stopReason","solver_complete"}});
        }
        model.reset();llama_backend_free();event({{"event","stage"},{"stage","saving_audio"}});write_wave(output,audio,channels,is_delay?120:is_local?60:30,rate);
        int64_t total=elapsed(start);double duration=double(audio.size())/rate/channels;details.update({{"pipelineMs",total},{"audioDurationSeconds",duration},{"pipelineRTF",double(total)/1000/duration}});event({{"event","execution"},{"details",details}});event({{"event","complete"},{"output",output}});return 0;
    } catch(const std::exception& error) {event({{"event","error"},{"message",error.what()}});return 1;}
}

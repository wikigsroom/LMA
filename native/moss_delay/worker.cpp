#include "json.hpp"
#include "llama.h"
#include "llama-cpp.h"
#include "model_contract.hpp"
#include "wave.hpp"
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <fstream>
#include <signal.h>
#include <sys/prctl.h>
#include <unistd.h>

// The upstream prompt builder needs only these two tokenizer utilities, not common/CLI/network code.
static std::vector<llama_token> common_tokenize(const llama_vocab* vocab,const std::string& text,bool special,bool parse) {
    int n=llama_tokenize(vocab,text.data(),int(text.size()),nullptr,0,special,parse);
    lma_moss::require(n<0 && n>=-65536,"Text tokenization exceeds the application guard");
    std::vector<llama_token> ids(size_t(-n)); n=llama_tokenize(vocab,text.data(),int(text.size()),ids.data(),int(ids.size()),special,parse);
    lma_moss::require(n>0 && size_t(n)==ids.size(),"Cannot tokenize selected MOSS text"); return ids;
}
static std::string common_token_to_piece(const llama_vocab* vocab,llama_token token,bool special) {
    char buffer[256];int n=llama_token_to_piece(vocab,token,buffer,sizeof(buffer),0,special);
    lma_moss::require(n>0 && n<int(sizeof(buffer)),"Required MOSS special token is missing");return std::string(buffer,n);
}
#define LOG(...) ((void)0)
#define LOG_ERR(...) ((void)0)
#include "moss-primitives.inc"
#undef LOG
#undef LOG_ERR

using json=nlohmann::json;
using clock_type=std::chrono::steady_clock;
static FILE* events;
static void event(const json& data) { if(events){auto line=data.dump();std::fprintf(events,"%s\n",line.c_str());std::fflush(events);} }
static long long elapsed(clock_type::time_point start) { return std::chrono::duration_cast<std::chrono::milliseconds>(clock_type::now()-start).count(); }
static llama_context_ptr cpu_context(llama_model* model,uint32_t length,int threads,bool audio,uint32_t batch) {
    llama_context_params p=llama_context_default_params();p.n_ctx=std::max(length,1u);p.n_batch=batch;p.n_ubatch=batch;p.n_seq_max=1;p.n_threads=threads;p.n_threads_batch=threads;p.embeddings=audio;p.pooling_type=LLAMA_POOLING_TYPE_NONE;
    llama_context_ptr ctx(llama_init_from_model(model,p));lma_moss::require(bool(ctx),"Cannot allocate the selected CPU context");
    llama_set_warmup(ctx.get(),false);llama_set_causal_attn(ctx.get(),!audio);llama_set_embeddings(ctx.get(),audio);return ctx;
}
static std::vector<llama_token> encode_reference(const std::string& model,const std::string& wav,int threads,size_t& frames) {
    auto samples=lma_moss::reference_wave(wav);
    frames=samples.size()/1920;size_t padded=(samples.size()+1919)/1920*1920;samples.resize(padded,0);
    auto encoder=moss_load_audio_model(model,"moss-tts-audio-encoder",0);
    auto ctx=cpu_context(encoder.get(),uint32_t(padded),threads,true,uint32_t(padded));
    auto batch=moss_batch_from_audio_waveform(samples);lma_moss::require(llama_encode(ctx.get(),batch.batch)==0,"Reference encoder failed");
    const int32_t* codes=llama_get_output_i32(ctx.get());lma_moss::require(codes && llama_model_n_out_i32(encoder.get())==32,"Reference encoder output does not match 32 audio channels");
    return lma_moss::encoder_codes(codes,padded/1920,frames);
}
static std::vector<float> decode_audio(const std::string& path,const moss_generation_audio& codes,int threads) {
    auto model=moss_load_audio_model(path,"moss-tts-audio-decoder",0);
    auto ctx=cpu_context(model.get(),uint32_t(codes.raw_frames),threads,true,uint32_t(codes.raw_frames));
    auto batch=moss_batch_from_audio_codes(codes.raw_codes,codes.raw_frames,32);
    lma_moss::require(llama_encode(ctx.get(),batch.batch)==0 && llama_model_n_embd_out(model.get())==1,"Native audio decoder failed");
    const float* audio=llama_get_embeddings(ctx.get());lma_moss::require(audio!=nullptr,"Native decoder produced no waveform");
    std::vector<float> result(audio,audio+codes.raw_frames*1920);for(float value:result)lma_moss::require(std::isfinite(value),"Native decoder produced nonfinite samples");return result;
}
int main(int argc,char** argv) {
    try {
        events=fdopen(dup(STDOUT_FILENO),"w");lma_moss::require(events && freopen("/dev/null","w",stdout) && freopen("/dev/null","w",stderr),"Cannot isolate native diagnostics");
        pid_t parent=getppid();lma_moss::require(prctl(PR_SET_PDEATHSIG,SIGKILL)==0 && parent!=1 && getppid()==parent,"Cannot bind worker lifetime to host");
        if(argc==2 && std::string(argv[1])=="--info") {event({{"schema","lma.engine/1"},{"engine","moss_delay_native"},{"revision",LMA_MOSS_REVISION},{"backend","cpu"},{"bundled_model_data",false},{"generation_tested",false}});return 0;}
        lma_moss::require(argc==2,"Pass a private request file");std::ifstream stream(argv[1],std::ios::binary|std::ios::ate);lma_moss::require(bool(stream) && stream.tellg()>0 && stream.tellg()<=256*1024,"Invalid request size");stream.seekg(0);json request;stream>>request;
        lma_moss::require(request.at("schema")=="lma.engine-request/1" && request.at("type")=="speech.synthesize" && request.at("pipeline")=="moss_delay_firstclass_v1","Unsupported MOSS pipeline");
        const auto& p=request.at("parameters");int threads=p.at("threads"),input=p.at("maxInputTokens"),steps=p.at("maxNewTokens");int64_t seed=p.at("seed");
        moss_sampling_config sampling;sampling.text_temperature=p.at("textTemperature");sampling.text_top_p=p.at("textTopP");sampling.text_top_k=p.at("textTopK");sampling.audio_temperature=p.at("audioTemperature");sampling.audio_top_p=p.at("audioTopP");sampling.audio_top_k=p.at("audioTopK");sampling.audio_repetition_penalty=p.at("audioRepetitionPenalty");
        lma_moss::parameters(threads,input,steps,sampling.text_temperature,sampling.text_top_p,sampling.text_top_k,sampling.audio_temperature,sampling.audio_top_p,sampling.audio_top_k,sampling.audio_repetition_penalty,seed);
        std::string text=request.at("input").at("prompt"),language=p.at("language"),root=request.at("workspace"),output=request.at("output");lma_moss::language(language);
        lma_moss::require(!text.empty() && text.size()<=16000 && text.find('\0')==std::string::npos && !root.empty() && !output.empty(),"Invalid text or paths");
        lma_moss::require(request.at("input").value("negativePrompt","").empty(),"Speech does not accept negative prompts");
        std::string model=root+"/models/moss-delay.gguf",decoder=root+"/models/moss-decoder.gguf",encoder=root+"/models/moss-encoder.gguf";auto start=clock_type::now();
        event({{"event","execution"},{"details",{{"effectiveParameters",p},{"pipeline","moss_delay_firstclass_v1"},{"backend","cpu"}}}});event({{"event","stage"},{"stage","validating_components"}});
        int training=lma_moss::backbone_contract(model);lma_moss::codec_contract(decoder,false);if(request.contains("referenceAudio"))lma_moss::codec_contract(encoder,true);
        llama_backend_scope backend;std::vector<llama_token> reference;size_t reference_frames=0;long long reference_ms=0;
        if(request.contains("referenceAudio")) {event({{"event","stage"},{"stage","encoding_reference_audio"}});auto mark=clock_type::now();reference=encode_reference(encoder,request.at("referenceAudio"),threads,reference_frames);reference_ms=elapsed(mark);}
        moss_generation_audio decoded;size_t prompt_frames=0,generated=0;long long load_ms=0,generation_ms=0;bool stopped=false;
        {
            event({{"event","stage"},{"stage","loading_speech_model"}});auto mark=clock_type::now();llama_model_params mp=llama_model_default_params();mp.n_gpu_layers=0;mp.use_mmap=true;
            llama_model_ptr backbone(llama_model_load_from_file(model.c_str(),mp));lma_moss::require(bool(backbone),"Cannot load selected first-class MOSS backbone");load_ms=elapsed(mark);
            auto vocab=llama_model_get_vocab(backbone.get());auto cfg=moss_delay_config_from_model(backbone.get());lma_moss::require(cfg.n_vq==32 && cfg.audio_vocab_size==1024 && cfg.audio_pad_code==1024,"Loaded backbone audio layout differs");
            auto prompt=moss_build_prompt_input(vocab,cfg,text,language=="auto"?"None":language,reference,reference_frames);prompt_frames=prompt.prompt_frames;lma_moss::context(prompt_frames,input,steps,training);
            auto ctx=cpu_context(backbone.get(),uint32_t(prompt_frames+steps+8),threads,false,128);mark=clock_type::now();event({{"event","stage"},{"stage","prefilling_speech_prompt"}});
            for(size_t offset=0;offset<prompt_frames;offset+=128) {size_t count=std::min(size_t(128),prompt_frames-offset);auto batch=moss_batch_from_packed_rows(prompt.packed_ids,offset,count,cfg,offset,offset+count==prompt_frames);lma_moss::require(llama_decode(ctx.get(),batch.batch)==0,"Speech prompt prefill failed");}
            auto state=moss_init_delay_state(prompt.packed_ids,cfg);moss_rng rng{uint32_t(seed)};std::vector<llama_token> next;int vocabulary=llama_vocab_n_tokens(vocab);
            event({{"event","stage"},{"stage","generating_audio_codes"}});
            for(int step=0;step<steps;++step) {
                const float* logits=llama_get_logits_ith(ctx.get(),-1);lma_moss::require(logits!=nullptr,"Speech model returned no logits");
                std::vector<float> text_logits(logits,logits+vocabulary),audio_logits(logits+vocabulary,logits+vocabulary+32*1025);next=moss_delay_step(state,text_logits,audio_logits,sampling,cfg,rng);
                auto batch=moss_batch_from_packed_rows(next,0,1,cfg,prompt_frames+size_t(step),true);lma_moss::require(llama_decode(ctx.get(),batch.batch)==0,"Speech generation failed");generated=size_t(step)+1;
                if(step==0 || generated%16==0) {event({{"event","progress"},{"stage","generating_audio_codes"}});event({{"event","execution"},{"details",{{"generatedSteps",generated},{"generationStepLimit",steps}}}});}
                if(state.is_stopping){stopped=true;break;}
            }
            decoded=moss_decode_generation_audio(state,prompt_frames,cfg);generation_ms=elapsed(mark);
        } // Release the backbone and KV cache before loading the waveform decoder.
        lma_moss::require(decoded.raw_frames>0 && decoded.raw_frames<=size_t(steps) && decoded.raw_codes.size()==decoded.raw_frames*32,"MOSS produced no bounded complete audio frames");
        for(auto code:decoded.raw_codes)lma_moss::require(code>=0 && code<1024,"MOSS produced an invalid codec value");
        event({{"event","stage"},{"stage","decoding_audio"}});auto mark=clock_type::now();auto audio=decode_audio(decoder,decoded,threads);auto decode_ms=elapsed(mark);
        event({{"event","stage"},{"stage","saving_audio"}});lma_moss::require(save_wav16(output,audio,24000),"Cannot save PCM16 output");double duration=double(audio.size())/24000;auto total=elapsed(start);
        event({{"event","execution"},{"details",{{"formattedInputFrames",prompt_frames},{"referenceFrames",reference_frames},{"referenceEncodeMs",reference_ms},{"modelLoadMs",load_ms},{"generationMs",generation_ms},{"codecDecodeMs",decode_ms},{"generatedSteps",generated},{"rawAudioFrames",decoded.raw_frames},{"sampleRate",24000},{"audioSamples",audio.size()},{"audioDurationSeconds",duration},{"stopReason",stopped?"model_stop":"application_step_limit"},{"pipelineMs",total},{"pipelineRTF",double(total)/1000/duration},{"backend","cpu"}}}});
        event({{"event","complete"},{"output",output}});return 0;
    }catch(const std::exception& error){event({{"event","error"},{"message",error.what()}});return 1;}
}

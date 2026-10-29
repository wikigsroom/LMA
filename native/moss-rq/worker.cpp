#include "json.hpp"
#include "model_contract.hpp"
#include "../openmoss/wave.hpp"
#include "../audio_pcm.hpp"
#include "moss_tts_local.hpp"
#include "moss_tts_rt.hpp"
#include "backend.hpp"
#include "common.hpp"
#include "ggml-cpu.h"
#include <cstdio>
#include <fstream>
#include <signal.h>
#include <sys/prctl.h>
#include <unistd.h>

using json=nlohmann::json;
static FILE* events;
static void event(const json& data) {if(events){std::string s=data.dump();std::fprintf(events,"%s\n",s.c_str());std::fflush(events);}}
int main(int argc,char** argv) {
    using namespace lma_moss_rq;
    try {
        events=fdopen(dup(STDOUT_FILENO),"w");require(events && freopen("/dev/null","w",stdout) && freopen("/dev/null","w",stderr),"Cannot isolate native diagnostics");
        pid_t parent=getppid();require(prctl(PR_SET_PDEATHSIG,SIGKILL)==0 && parent!=1 && getppid()==parent,"Cannot bind worker lifetime to host");
        if(argc==2 && std::string(argv[1])=="--info") {event({{"schema","lma.engine/1"},{"engine","moss_rq_native"},{"revision",LMA_MOSS_RQ_REVISION},{"backend","cpu"},{"bundled_model_data",false},{"generation_tested",false}});return 0;}
        require(argc==2,"Pass a private request file");std::ifstream input(argv[1],std::ios::binary|std::ios::ate);require(bool(input) && input.tellg()>0 && input.tellg()<=256*1024,"Invalid request size");input.seekg(0);json request;input>>request;
        bool rt=realtime(request.at("pipeline"));require(request.at("schema")=="lma.engine-request/1" && request.at("type")=="speech.synthesize","Unsupported MOSS RQ task");
        const auto& p=request.at("parameters");int threads=p.at("threads"),max_steps=p.at("maxNewTokens");int64_t seed=p.at("seed");lma_openmoss::common(threads,seed);budget(p.at("maxInputTokens"),max_steps);
        std::string text=request.at("input").at("prompt");lma_openmoss::prompt(text,true);lma_openmoss::instruction(text,16000);require(request.at("input").value("negativePrompt",std::string()).empty(),"RQ speech does not use negative prompts");
        sampling(p.at("audioTemperature"),p.at("audioTopP"),p.at("audioTopK"),p.at("audioRepetitionPenalty"));
        if(!rt) {sampling(p.at("textTemperature"),p.at("textTopP"),p.at("textTopK"),1);lma_openmoss::instruction(p.at("voiceInstruction"),4000);lma_openmoss::instruction(p.at("language"),256);}
        std::string workspace=request.at("workspace"),model=workspace+"/models/model.gguf",codec=workspace+"/models/codec.gguf",tokenizer=workspace+"/models/tokenizer.gguf",reference=request.value("referenceAudio",std::string()),output=request.at("output");
        if(!reference.empty())lma_openmoss::reference_wave(reference,24000,1);
        auto start=Clock::now();event({{"event","stage"},{"stage","validating_model_layout"}});contract(model,codec,tokenizer,rt);
        require(setenv("MOSS_TTS_BACKEND","cpu",1)==0 && setenv("MOSS_TTS_FLASH_ATTN","0",1)==0 && setenv("MOSS_HEAD_PARALLEL_MIN","2147483647",1)==0,"Cannot apply CPU execution policy");
        moss::set_log_callback([](moss::moss_log_level,const char*,void*){},nullptr);auto backend=moss::backend();require(backend && ggml_backend_is_cpu(backend),"CPU graph backend unavailable");ggml_backend_cpu_set_n_threads(backend,threads);
        run=Run{};run.input_limit=p.at("maxInputTokens");run.notify=[](const std::string& stage,int current,int total){if(current>0)event({{"event","progress"},{"stage",stage},{"step",current},{"steps",total}});else event({{"event","stage"},{"stage",stage}});};
        std::unique_ptr<lma_audio::Stream> stream;
        require(p.value("streamAudio",false)==request.contains("audioStream"),"Streaming parameter and owned consumer disagree");
        if(request.contains("audioStream")) {
            const auto& format=request.at("audioStream");
            require(rt && format.at("schema")=="lma.audio-stream/1" && format.at("format")=="pcm_s16le" && format.at("sampleRate")==24000 && format.at("channels")==1 && format.at("maxFrames")==max_steps*1920 && format.at("maxChunkFrames")==1920,"Invalid Realtime audio stream declaration");
            stream=std::make_unique<lma_audio::Stream>(24000,1,max_steps*1920,1920,[](int sequence,int start,int frames,const std::string& pcm){event({{"event","audio_chunk"},{"schema","lma.audio-stream/1"},{"sequence",sequence},{"startFrame",start},{"frames",frames},{"sampleRate",24000},{"channels",1},{"pcm",pcm}});});
            run.audio=[&](const std::vector<float>& pcm,int sample_rate){stream->write(pcm,sample_rate);};
        }
        event({{"event","stage"},{"stage","loading_models"}});std::vector<float> audio;int rate=0;double load_ms=0;
        auto elapsed=[&](Clock::time_point from){return std::chrono::duration<double,std::milli>(Clock::now()-from).count();};
        if(rt) {
            moss::RealtimeTTS engine;require(engine.load(model,codec,tokenizer,4096),"Cannot load the selected Realtime model and dependencies");load_ms=elapsed(start);moss::RtTtsOpts opts;opts.reference_wav=reference;opts.seed=int(seed);opts.max_new_tokens=max_steps;opts.sampling.audio_temperature=p.at("audioTemperature");opts.sampling.audio_top_p=p.at("audioTopP");opts.sampling.audio_top_k=p.at("audioTopK");opts.sampling.audio_repetition_penalty=p.at("audioRepetitionPenalty");
            event({{"event","stage"},{"stage",reference.empty()?"preparing_prompt":"encoding_reference"}});require(engine.tts(text,opts,&audio,&rate),"Realtime generation or codec execution failed");
        } else {
            moss::LocalTTS engine;require(engine.load(model,codec,tokenizer,4096),"Cannot load the selected old Local model and dependencies");load_ms=elapsed(start);moss::LocalTtsOpts opts;opts.reference_wav=reference;opts.seed=int(seed);opts.max_new_tokens=max_steps;std::string hint=p.at("voiceInstruction"),language=p.at("language");if(!lma_openmoss::clean(hint).empty())opts.instruction=hint;if(!lma_openmoss::clean(language).empty())opts.language=language;opts.sampling.text_temperature=p.at("textTemperature");opts.sampling.text_top_p=p.at("textTopP");opts.sampling.text_top_k=p.at("textTopK");opts.sampling.audio_temperature=p.at("audioTemperature");opts.sampling.audio_top_p=p.at("audioTopP");opts.sampling.audio_top_k=p.at("audioTopK");opts.sampling.audio_repetition_penalty=p.at("audioRepetitionPenalty");
            event({{"event","stage"},{"stage",reference.empty()?"preparing_prompt":"encoding_reference"}});require(engine.tts(text,opts,&audio,&rate),"Old Local generation or codec execution failed");
        }
        require(rate==24000 && run.steps>0 && run.output_frames>0 && run.output_frames<=max_steps,"RQ returned empty or incompatible audio frames");
        event({{"event","stage"},{"stage","saving_audio"}});lma_openmoss::write_wave(output,audio,1,60,24000);double duration=double(audio.size())/24000,total=elapsed(start);
        if(stream) {require(stream->frames()==int(audio.size()),"Streamed audio differs from the final frame count");stream->finish();event({{"event","audio_end"},{"schema","lma.audio-stream/1"},{"nextSequence",stream->next()},{"frames",stream->frames()}});}
        json details={{"backend","cpu"},{"sampleRate",24000},{"channels",1},{"modelLoadMs",load_ms},{"formattedPrefillFrames",run.prefill},{"remainingTextTokens",run.remaining_text},{"referenceFrames",run.reference_frames},{"generationSteps",run.steps},{"audioFrames",run.output_frames},{"prefillMs",run.prefill_ms},{"generationMs",run.generation_ms},{"pipelineMs",total},{"audioDurationSeconds",duration},{"pipelineRTF",total/1000/duration},{"stopReason",run.stopped?"audio_end":"application_step_limit"},{"interfaceMode","single_text_to_wav"}};
        details["interfaceMode"]=stream?"single_text_incremental_pcm_and_wav":"single_text_to_wav";details["outputGain"]=stream?"unity_for_stream_and_final":"whole_clip_rms_bounded_3db";
        event({{"event","execution"},{"details",details}});event({{"event","complete"},{"output",output}});return 0;
    }catch(const std::exception& error){event({{"event","error"},{"message",error.what()}});return 1;}
}

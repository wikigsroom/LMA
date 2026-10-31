#include "../worker_common.hpp"
#include "f5_frontend.hpp"
#include "audiocpp.h"
#include "engine/community_models/f5_tts/synthesize.h"
#include "engine/framework/audio/wav_reader.h"
using namespace lma_worker;
static void ok(audiocpp_status status) { require(status == AUDIOCPP_OK, "OmniVoice native operation failed; check selected model resources and memory"); }
struct Handles {
 audiocpp_registry* registry=nullptr; audiocpp_model* model=nullptr; audiocpp_session* session=nullptr;
 audiocpp_request* request=nullptr; audiocpp_result* result=nullptr; audiocpp_options* options=nullptr;
 ~Handles() { audiocpp_result_free(result); audiocpp_request_free(request); audiocpp_session_free(session);
              audiocpp_model_free(model); audiocpp_registry_free(registry); audiocpp_options_free(options); }
};
static engine::audio::WavData reference(const json& request, bool required, int maximum) {
 if(!request.contains("referenceAudio")) { require(!required,"Select reference audio and its transcript"); return {}; }
 auto path=regular(request,"referenceAudio"); require(std::filesystem::file_size(path)<=8*1024*1024,"Reference audio exceeds 8 MiB");
 auto wave=engine::audio::read_wav_f32(std::filesystem::path(path));
 require(wave.sample_rate==24000 && wave.channels==1 && wave.samples.size()>=24000 &&
         wave.samples.size()<=size_t(maximum)*24000, "Reference audio must be mono 24 kHz WAV within the declared duration");
 for(float value:wave.samples) require(std::isfinite(value),"Reference audio contains nonfinite samples"); return wave;
}
int main(int argc,char** argv) {
 if(argc==2 && !std::strcmp(argv[1],"--info")) {
  std::puts("{\"engine\":\"audio_cpp\",\"backend\":\"cpu\",\"pipelines\":[\"f5_v1\",\"omnivoice\"],\"modelInferenceTested\":false,\"modelDownloads\":false}"); return 0;
 }
 try {
  initialize(); require(argc==2,"Supply one private request");
  auto command=request(argv[1]); require(command.at("type")=="speech.synthesize","Unsupported speech task");
  auto pipeline=command.at("pipeline").get<std::string>(); require(pipeline=="f5_v1"||pipeline=="omnivoice","Unsupported speech pipeline");
  auto input=command.at("input"), params=command.at("parameters"); std::string prompt=text(input,"prompt"), output=command.at("output");
  require(std::filesystem::path(output).is_absolute() && !std::filesystem::exists(output),"Output must be a new private file");
  int threads=integer(params,"threads",2,1,16), maximum=integer(params,"maxAudioSeconds",30,1,120), steps=integer(params,"steps",32,1,64);
  float speed=number(params,"speed",1,0.5f,2), cfg=number(params,"cfg",2,0,10); int seed=integer(params,"seed",1234,0,2147483647);
  params["threads"]=threads;params["maxAudioSeconds"]=maximum;params["steps"]=steps;params["speed"]=speed;params["cfg"]=cfg;params["seed"]=seed;
  auto ref=reference(command,pipeline=="f5_v1",pipeline=="f5_v1"?12:30);
  event({{"event","execution"},{"details",{{"pipeline",pipeline},{"backend","cpu"},{"effectiveParameters",params},{"audioStreaming",false}}}});
  event({{"event","stage"},{"stage","loading"}});
  if(pipeline=="f5_v1") {
   auto components=command.at("components"); auto model=regular(components,"model"), vocoder=regular(components,"vocoder");
   regular(components,"vocab"); lma_f5::active=true; lma_f5::maximum_mel_frames=size_t(maximum)*24000/256;
   if(components.contains("pinyin_chars")) lma_f5::load(regular(components,"pinyin_chars"),false);
   if(components.contains("pinyin_phrases")) lma_f5::load(regular(components,"pinyin_phrases"),true);
   if(components.contains("frontend")) lma_f5_official::load(regular(components,"frontend"));
   engine::models::f5_tts::F5SynthesisRequest value; value.text=prompt; value.ref_audio=std::move(ref.samples); value.ref_sample_rate=24000;
   value.ref_text=text(input.at("transcripts"),"reference_audio"); value.dialect="LMA_F5_V1";
   value.strip_diacritics=false; value.threads=threads; value.speed=speed; value.steps=steps; value.cfg_strength=cfg;
   value.sway_sampling_coef=number(params,"sway",-1,-5,5); value.seed=uint32_t(seed); value.fixed_seed=true;
   value.frame_budget=integer(params,"frameBudget",2048,512,4096); value.use_cuda=false;
   auto parent=std::filesystem::path(model).parent_path(); require(parent / "vocab.txt" == std::filesystem::path(components.at("vocab").get<std::string>()),"F5 vocabulary execution layout mismatch");
   std::ifstream vocabulary(parent / "vocab.txt"); std::string token; std::unordered_map<std::string,int32_t> words; int32_t index=0;
   while(std::getline(vocabulary,token)) { if(!token.empty() && token.back()=='\r') token.pop_back(); words[token]=index++; require(index<=65536,"F5 vocabulary exceeds limits"); }
   require(index>0,"F5 vocabulary is empty"); lma_f5::tokenize(words,value.ref_text); lma_f5::tokenize(words,prompt);
   event({{"event","stage"},{"stage","synthesizing"}});
   auto audio=engine::models::f5_tts::f5_synthesize(model,vocoder,value);
   wave(output,audio.audio.data(),audio.audio.size(),int(audio.sample_rate),1,maximum);
  } else {
   std::string model=regular(command.at("components"),"model"); Handles h;
   ok(audiocpp_registry_create(nullptr,&h.registry)); audiocpp_model_config config{"omnivoice",nullptr,nullptr,nullptr};
   std::string loadPath=std::filesystem::path(model).extension()==".gguf"?model:std::filesystem::path(model).parent_path().string();
   ok(audiocpp_model_load(h.registry,loadPath.c_str(),&config,nullptr,&h.model));
   require(std::strcmp(audiocpp_model_family(h.model),"omnivoice")==0,"Wrong speech model family");
   h.options=audiocpp_options_create(); require(h.options,"Cannot allocate session options");
   ok(audiocpp_options_set(h.options,"mem_saver","true"));
   std::string mode=params.value("voiceMode","auto"), instruction=params.value("voiceInstruction","");
   require(mode=="auto"||mode=="clone"||mode=="design","Unknown voice mode");
   require(instruction.size()<=4000 && instruction.find('\0')==std::string::npos,"Invalid voice instruction");
   require(mode!="clone"||!ref.samples.empty(),"Voice cloning requires reference audio");
   require(mode!="design"||(!instruction.empty()&&ref.samples.empty()),"Voice design requires an instruction and no reference audio");
   const char* task=audiocpp_task_from_spec_name(!ref.samples.empty()?"clone":!instruction.empty()?"design":"tts");
   require(task,"Speech task is unavailable"); audiocpp_backend_config backend{"cpu",0,threads};
   ok(audiocpp_session_create(h.model,task,"offline",&backend,h.options,&h.session));
   h.request=audiocpp_request_create(); require(h.request,"Cannot allocate speech request");
   std::string language=params.value("language","auto"); require(language.size()<=80 && language.find('\0')==std::string::npos,"Invalid language");
   ok(audiocpp_request_set_text(h.request,prompt.c_str(),language=="auto"?nullptr:language.c_str()));
   auto option=[&](const char* key,const std::string& value){ok(audiocpp_request_set_option(h.request,key,value.c_str()));};
   option("num_inference_steps",std::to_string(steps)); option("guidance_scale",std::to_string(cfg));
   option("speed",std::to_string(speed)); option("seed",std::to_string(seed));
   option("duration_sec",std::to_string(number(params,"durationSeconds",4,1,float(std::min(maximum,30)))));
   if(!instruction.empty()) option("instruct",instruction);
   if(!ref.samples.empty()) { ok(audiocpp_request_set_voice_audio(h.request,ref.samples.data(),ref.samples.size(),24000,1));
     if(input.contains("transcripts") && input.at("transcripts").contains("reference_audio")) option("reference_text",text(input.at("transcripts"),"reference_audio")); }
   event({{"event","stage"},{"stage","synthesizing"}}); ok(audiocpp_session_run(h.session,h.request,&h.result));
   const float* samples=nullptr; size_t frames=0; int rate=0,channels=0; ok(audiocpp_result_audio(h.result,&samples,&frames,&rate,&channels));
   wave(output,samples,frames,rate,channels,maximum);
  }
  event({{"event","complete"},{"output",output}}); return 0;
 } catch(const std::exception&) {
  if(events) event({{"event","error"},{"message","Speech engine failed: check component versions, text pronunciation, reference audio and memory."}});
 }
 return 1;
}

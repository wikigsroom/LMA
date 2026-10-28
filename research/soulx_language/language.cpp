// SPDX-License-Identifier: MIT
#include "language.hpp"
#include "llama.h"
#include "ggml-backend.h"
#include <mutex>
#include <random>
#include <cstdio>
#include <cstring>
#ifdef __ANDROID__
#include <dlfcn.h>
#endif

namespace lma::soulx::language {
struct Model::State{
    llama_model* model=nullptr;llama_context* context=nullptr;const llama_vocab* vocabulary=nullptr;
    Options options;Stats& stats;Cancel cancelled;Progress progress;Layout layout;
    State(const Options& o,Stats& s,Cancel c,Progress p):options(o),stats(s),cancelled(std::move(c)),progress(std::move(p)){}
    ~State(){if(context)llama_free(context);if(model){llama_model_free(model);++stats.model_unloads;}}
    bool interrupted() noexcept {try{return cancelled && cancelled();}catch(...){return true;}}
    void stop(){if(interrupted())throw std::runtime_error("SoulX language execution cancelled");}
    void event(const char* stage,int done,int total){stop();if(progress)progress(stage,done,total);stop();}
    Tokens tokenize(const std::string& text) const{
        require(text.size()<=262144,"SoulX formatted text exceeds the byte limit");
        int count=llama_tokenize(vocabulary,text.data(),static_cast<int32_t>(text.size()),nullptr,0,false,true);
        require(count<=0 && count>=-65536,"Invalid SoulX tokenizer length");Tokens result(static_cast<size_t>(-count));
        int actual=llama_tokenize(vocabulary,text.data(),static_cast<int32_t>(text.size()),result.data(),static_cast<int32_t>(result.size()),false,true);
        require(actual==static_cast<int>(result.size()),"SoulX tokenizer size changed");return result;
    }
    int32_t special(const std::string& text) const {auto tokens=tokenize(text);require(tokens.size()==1,"SoulX model is missing a single-token protocol marker");return tokens[0];}
    void decode(Tokens& tokens,size_t offset,size_t count){
        stop();auto batch=llama_batch_get_one(tokens.data()+offset,static_cast<int32_t>(count));
        event("language_decode",stats.decode_calls,static_cast<int>(count));int result=llama_decode(context,batch);++stats.decode_calls;
        if(result!=0){if(interrupted()){++stats.aborted_decodes;throw std::runtime_error("SoulX language execution cancelled during neural evaluation");}throw std::runtime_error("SoulX llama_decode failed locally");}
        stats.decoded_tokens+=static_cast<int>(count);stop();
    }
};
Model::Model(const std::filesystem::path& file,const Options& options,Stats& stats,Cancel cancelled,Progress progress):state_(std::make_unique<State>(options,stats,std::move(cancelled),std::move(progress))){
    auto& s=*state_;stats={};require(options.context>=256 && options.context<=8192 && options.threads>=1 && options.threads<=32 && options.batch>=1 && options.batch<=512,"Invalid SoulX language runtime profile");
    s.stop();static std::once_flag initialized;std::call_once(initialized,[]{
        llama_log_set([](ggml_log_level level,const char* message,void*){if(level==GGML_LOG_LEVEL_ERROR)std::fputs(message,stderr);},nullptr);
#ifdef __ANDROID__
        // Load only the packaged baseline CPU module adjacent to this exact
        // pinned libllama, never GGML_BACKEND_PATH, CWD or model directories.
        Dl_info info{};require(dladdr(reinterpret_cast<void*>(&llama_backend_init),&info) && info.dli_fname,"Cannot locate packaged llama runtime");
        auto library=std::filesystem::canonical(info.dli_fname);require(library.filename()=="libllama.so","Unexpected llama runtime location");
        auto cpu=library.parent_path()/"libggml-cpu-android_armv8.0_1.so";require(ggml_backend_load(cpu.c_str())!=nullptr,"Packaged baseline CPU backend unavailable");
#endif
        llama_backend_init();
    });
    s.event("language_load",0,1);auto params=llama_model_default_params();params.n_gpu_layers=0;params.load_mode=LLAMA_LOAD_MODE_MMAP;params.vocab_only=options.vocabulary_only;
    ggml_backend_dev_t no_accelerators[]={nullptr};params.devices=no_accelerators;
    params.progress_callback=[](float,void* data){return !static_cast<State*>(data)->interrupted();};params.progress_callback_user_data=&s;
    s.model=llama_model_load_from_file(file.u8string().c_str(),params);if(s.model)++stats.model_loads;s.stop();require(s.model!=nullptr,"Cannot load the selected SoulX GGUF");
    char architecture[64]{};require(llama_model_meta_val_str(s.model,"general.architecture",architecture,sizeof(architecture))>0 && std::string(architecture)=="qwen3","SoulX requires a Qwen3 language backbone");
    auto metadata=[&](const char* key){char value[64]{};require(llama_model_meta_val_str(s.model,key,value,sizeof(value))>0,"Missing SoulX architecture metadata");size_t used=0;auto number=std::stoll(value,&used);require(used==std::strlen(value),"Invalid SoulX architecture metadata");return number;};
    require(metadata("qwen3.embedding_length")==2048 && metadata("qwen3.block_count")==28 && metadata("qwen3.attention.head_count")==16 && metadata("qwen3.attention.head_count_kv")==8,"Incompatible SoulX Qwen3 architecture");
    require(metadata("qwen3.context_length")>=options.context,"SoulX context exceeds the selected model");
    if(!options.vocabulary_only)require(llama_model_n_embd(s.model)==2048 && llama_model_n_layer(s.model)==28 && llama_model_n_head(s.model)==16 && llama_model_n_head_kv(s.model)==8,"Loaded SoulX architecture differs from its metadata");
    s.vocabulary=llama_model_get_vocab(s.model);s.layout={llama_vocab_n_tokens(s.vocabulary),s.special("<|0|>"),s.special("<|semantic_token_end|>"),s.special("<|semantic_token_start|>")};valid_layout(s.layout);
    for(int i=0;i<6561;++i){if(i%64==0)s.stop();require(s.special("<|"+std::to_string(i)+"|>")==s.layout.offset+i,"SoulX semantic token IDs are not contiguous");}
    std::vector<int32_t> controls{s.layout.eos,s.layout.audio_start,s.special("<|text_start|>"),s.special("<|text_end|>"),s.special("<|task_podcast|>")};
    for(int i=0;i<4;++i)controls.push_back(s.special("<|SPEAKER_"+std::to_string(i)+"|>"));
    std::sort(controls.begin(),controls.end());require(std::adjacent_find(controls.begin(),controls.end())==controls.end() && controls.front()>=0 && controls.back()<s.layout.offset,"SoulX control markers collide with semantic tokens");
    if(!options.vocabulary_only){
        auto context=llama_context_default_params();context.n_ctx=static_cast<uint32_t>(options.context);context.n_batch=static_cast<uint32_t>(std::min(options.batch,options.context));context.n_ubatch=context.n_batch;
        context.n_threads=options.threads;context.n_threads_batch=options.threads;context.n_seq_max=1;context.offload_kqv=false;context.op_offload=false;context.no_perf=true;
        context.abort_callback=[](void* data){return static_cast<State*>(data)->interrupted();};context.abort_callback_data=&s;
        s.context=llama_init_from_model(s.model,context);s.stop();require(s.context!=nullptr && llama_n_ctx(s.context)>=static_cast<uint32_t>(options.context),"Cannot allocate SoulX CPU context");
    }s.event("language_load",1,1);
}
Model::~Model()=default;
Layout Model::layout()const{return state_->layout;}
Tokens Model::tokenize(const std::string& text)const{return state_->tokenize(text);}
std::vector<float> Model::evaluate(Tokens input){
    auto& s=*state_;require(s.context && !input.empty() && input.size()<static_cast<size_t>(s.options.context),"Invalid SoulX evaluation input");
    for(auto token:input)require(token>=0 && token<s.layout.vocabulary,"Invalid SoulX input token ID");
    llama_memory_clear(llama_get_memory(s.context),true);
    for(size_t at=0;at<input.size();at+=static_cast<size_t>(s.options.batch))s.decode(input,at,std::min(static_cast<size_t>(s.options.batch),input.size()-at));
    auto values=llama_get_logits_ith(s.context,-1);require(values!=nullptr,"Missing SoulX decoder logits");return {values,values+s.layout.vocabulary};
}
std::vector<Generated> Model::generate(const std::vector<Reference>& references,const std::vector<Turn>& turns,const Sampling& sampling,const Window& window,uint64_t seed){
    auto& s=*state_;require(s.context!=nullptr,"Vocabulary-only inspection cannot run neural generation");valid_sampling(sampling);require(!turns.empty() && turns.size()<=64,"SoulX requires 1 to 64 target turns");
    Tokenize tokenizer=[&](const std::string& text){return s.tokenize(text);};History history(references,s.layout,window,tokenizer);std::mt19937_64 rng(seed);
    auto uniform=[&]{return static_cast<double>(rng()>>11)*0x1.0p-53;};std::vector<Generated> result;size_t total_codes=0;
    for(size_t turn=0;turn<turns.size();++turn){
        s.event("language_turn",static_cast<int>(turn),static_cast<int>(turns.size()));auto input=history.input(turns[turn],s.options.context,sampling.maximum,tokenizer);Tokens all=input,generated;
        llama_memory_clear(llama_get_memory(s.context),true); // Re-evaluate a bounded window; no hidden cross-request cache.
        for(size_t at=0;at<input.size();at+=static_cast<size_t>(s.options.batch))s.decode(input,at,std::min(static_cast<size_t>(s.options.batch),input.size()-at));
        Generated output;output.speaker=turns[turn].speaker;output.input_tokens=input.size();
        for(int step=0;step<sampling.maximum;++step){
            s.stop();auto values=llama_get_logits_ith(s.context,-1);require(values!=nullptr,"Missing SoulX decoder logits");std::vector<float> logits(values,values+s.layout.vocabulary);
            double candidate=uniform(),final=uniform();auto selected=sample(logits,generated,all,s.layout,sampling,candidate,final);if(selected.ras_reset)++s.stats.ras_resets;
            require(selected.token==s.layout.eos || selected.token>=s.layout.offset && selected.token<s.layout.offset+6561,"SoulX generated a non-semantic token; incompatible model or prompt");
            generated.push_back(selected.token);all.push_back(selected.token);++s.stats.generated_tokens;
            if(selected.token==s.layout.eos){output.eos=true;break;}
            output.semantic.push_back(selected.token-s.layout.offset);s.event("language_token",step+1,sampling.maximum);
            if(step+1<sampling.maximum){Tokens token{selected.token};s.decode(token,0,1);}
        }
        require(!output.semantic.empty(),"SoulX generated no semantic audio codes");total_codes+=output.semantic.size();require(total_codes<=24000,"SoulX task exceeds the explicit total audio-code budget");
        output.language_ids=generated;output.history_delimiter_inserted=!output.eos;history.accept(turns[turn],generated,tokenizer);result.push_back(std::move(output));
    }s.stats.history_resets=static_cast<int>(history.resets);s.event("language_complete",1,1);return result;
}
}

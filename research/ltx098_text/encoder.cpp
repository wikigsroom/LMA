// SPDX-License-Identifier: MIT
#include "encoder.hpp"
#include "graph.hpp"
#include "llama.h"
#include "ggml-backend.h"
#include <cmath>
#include <cstdio>
#include <cstring>
#include <mutex>
#ifdef __ANDROID__
#include <dlfcn.h>
#endif

namespace lma::ltx098::text {
namespace {
// LTX 0.9.8 uses Python str.strip(), without lowercasing or HTML cleanup.
bool whitespace(uint32_t c) {
    return (c>=9 && c<=13) || (c>=0x1c && c<=0x20) || c==0x85 || c==0xa0 ||
        c==0x1680 || (c>=0x2000 && c<=0x200a) || c==0x2028 || c==0x2029 ||
        c==0x202f || c==0x205f || c==0x3000;
}
std::string strip_utf8(const std::string& text) {
    require(text.size()<=65536, "Prompt exceeds 65536 UTF-8 bytes");
    size_t begin=text.size(), end=0;
    for (size_t i=0;i<text.size();) {
        const size_t start=i; auto b=static_cast<unsigned char>(text[i++]); uint32_t c=b; int count=0;
        if (b>=0xc2 && b<=0xdf) { c=b&31; count=1; }
        else if (b>=0xe0 && b<=0xef) { c=b&15; count=2; }
        else if (b>=0xf0 && b<=0xf4) { c=b&7; count=3; }
        else require(b<0x80, "Invalid UTF-8 prompt");
        require(i+count<=text.size(), "Incomplete UTF-8 prompt");
        for (int n=0;n<count;++n) {
            auto next=static_cast<unsigned char>(text[i++]); require((next&0xc0)==0x80, "Invalid UTF-8 continuation"); c=(c<<6)|(next&63);
        }
        require((count!=1 || c>=0x80) && (count!=2 || c>=0x800) && (count!=3 || c>=0x10000) &&
            c<=0x10ffff && !(c>=0xd800 && c<=0xdfff), "Invalid UTF-8 scalar");
        if (!whitespace(c)) { if (begin==text.size()) begin=start; end=i; }
    }
    return end ? text.substr(begin,end-begin) : std::string();
}
}
struct Model::State {
    llama_model* model=nullptr;
    const llama_vocab* vocab=nullptr;
    std::unique_ptr<Graph> graph;
    Options options; Stats& stats; Cancel cancelled; Progress progress; Layout layout;
    State(const Options& o,Stats& s,Cancel c,Progress p):options(o),stats(s),cancelled(std::move(c)),progress(std::move(p)) {}
    ~State() { if(graph) {graph.reset();++stats.model_unloads;} if(model) {llama_model_free(model);++stats.vocabulary_unloads;} }
    bool interrupted() noexcept { try { return cancelled && cancelled(); } catch (...) { return true; } }
    void stop() { if(interrupted()) throw std::runtime_error("T5 execution cancelled"); }
    void event(const char* name,int done,int total) { stop(); if(progress) progress(name,done,total); stop(); }
    long long integer(const char* key) const {
        char value[80]{}; require(llama_model_meta_val_str(model,key,value,sizeof(value))>0,"Missing T5 metadata");
        size_t used=0; auto n=std::stoll(value,&used); require(used==std::strlen(value),"Invalid T5 integer metadata"); return n;
    }
    void inspect() {
        char arch[64]{}; require(llama_model_meta_val_str(model,"general.architecture",arch,sizeof(arch))>0 &&
            std::string(arch)=="t5encoder", "Expected an encoder-only T5 GGUF");
        layout={static_cast<int>(integer("t5encoder.embedding_length")),static_cast<int>(integer("t5encoder.block_count")),
            static_cast<int>(integer("t5encoder.attention.head_count")),static_cast<int>(integer("t5encoder.feed_forward_length")),
            llama_vocab_n_tokens(llama_model_get_vocab(model)),static_cast<int>(integer("t5encoder.context_length"))};
        const bool small=options.fixture && layout.width==32 && layout.heads==4 && layout.feed_forward==64 && (layout.layers==2 || layout.layers==24);
        require(small || (layout.width==4096 && layout.layers==24 && layout.heads==64 && layout.feed_forward==10240), "Unexpected T5 architecture dimensions");
        require(layout.vocabulary==32128 && layout.context>=256 && layout.context<=512 &&
            integer("t5encoder.attention.key_length")==layout.width/layout.heads &&
            integer("t5encoder.attention.value_length")==layout.width/layout.heads &&
            integer("t5encoder.attention.relative_buckets_count")==32, "Unexpected T5 vocabulary/attention profile");
        char eps[80]{}; require(llama_model_meta_val_str(model,"t5encoder.attention.layer_norm_rms_epsilon",eps,sizeof(eps))>0 &&
            std::abs(std::stod(eps)-1e-6)<1e-10, "Unexpected T5 RMS normalization epsilon");
        vocab=llama_model_get_vocab(model);
        require(llama_vocab_eos(vocab)==1 && llama_vocab_pad(vocab)==0, "Unexpected T5 EOS/PAD IDs");
    }
};
Model::Model(const std::filesystem::path& file,const Options& options,Stats& stats,Cancel cancel,Progress progress)
    :state_(std::make_unique<State>(options,stats,std::move(cancel),std::move(progress))) {
    auto& s=*state_; stats={};
    require(options.threads>=1 && options.threads<=32 && options.max_tokens>=1 && options.max_tokens<=256,"Invalid T5 threads/token limit");
    require(options.additional_special_tokens.size()==100,"Original external T5 extra-token configuration is required");
    for(int i=0;i<100;++i) require(options.additional_special_tokens[i]=="<extra_id_"+std::to_string(i)+">","Unexpected T5 extra-token configuration");
    s.stop(); require(std::filesystem::is_regular_file(file),"Selected T5 GGUF is not a local regular file");
    static std::once_flag initialized;
    std::call_once(initialized,[]{
        llama_log_set([](ggml_log_level level,const char* message,void*){ if(level==GGML_LOG_LEVEL_ERROR) std::fputs(message,stderr); },nullptr);
#ifdef __ANDROID__
        Dl_info info{}; require(dladdr(reinterpret_cast<void*>(&llama_backend_init),&info) && info.dli_fname,"Cannot locate packaged llama runtime");
        auto library=std::filesystem::canonical(info.dli_fname); require(library.filename()=="libllama.so","Unexpected llama runtime location");
        auto cpu=library.parent_path()/"libggml-cpu-android_armv8.0_1.so";
        require(ggml_backend_load(cpu.c_str())!=nullptr,"Packaged baseline CPU backend unavailable");
#endif
        llama_backend_init();
    });
    s.event("t5_load",0,1);
    auto params=llama_model_default_params(); ggml_backend_dev_t cpu_only[]={nullptr};
    params.devices=cpu_only; params.n_gpu_layers=0; params.load_mode=LLAMA_LOAD_MODE_MMAP; params.vocab_only=true;
    params.progress_callback=[](float,void* data){return !static_cast<State*>(data)->interrupted();}; params.progress_callback_user_data=&s;
    s.model=llama_model_load_from_file(file.u8string().c_str(),params); s.stop(); require(s.model!=nullptr,"Cannot read selected T5 GGUF metadata");
    ++stats.vocabulary_loads; s.inspect();
    if(!options.vocabulary_only) {
        require(llama_model_has_encoder(s.model) && !llama_model_has_decoder(s.model),"Expected an encoder-only execution graph");
        s.graph=std::make_unique<Graph>(file,s.layout,options.threads,[&s]{return s.interrupted();},[&s](const char* stage,int done,int total){s.event(stage,done,total);});++stats.model_loads;s.stop();
    }
    s.event("t5_load",1,1);
}
Model::~Model()=default;
const Layout& Model::layout() const { return state_->layout; }
Buffers Model::buffers() const {return state_->graph?state_->graph->buffers():Buffers{};}
Tokenized Model::tokenize(const std::string& prompt) const {
    auto& s=*state_; s.stop(); auto text=strip_utf8(prompt);
    Tokens ids;
    auto segment=[&](const std::string& value) {
        if(value.empty()) return;
        int count=llama_tokenize(s.vocab,value.data(),static_cast<int32_t>(value.size()),nullptr,0,false,true);
        require(count<=0 && count>=-131072,"Invalid T5 tokenizer length"); Tokens part(static_cast<size_t>(-count));
        if(count) require(llama_tokenize(s.vocab,value.data(),static_cast<int32_t>(value.size()),part.data(),static_cast<int32_t>(part.size()),false,true)==-count,"T5 tokenizer length changed");
        ids.insert(ids.end(),part.begin(),part.end());
    };
    // This community GGUF labels positions 32000..32127 as unused padding.
    // The ORIGINAL EXTERNAL tokenizer config supplies the 100 sentinel names;
    // T5's published reversed-ID convention maps them onto 32099..32000.
    size_t offset=0;
    while(offset<text.size()) {
        size_t next=std::string::npos;int marker=-1;
        for(int i=0;i<100;++i) { auto found=text.find(s.options.additional_special_tokens[i],offset);if(found<next) {next=found;marker=i;} }
        if(marker<0) {segment(text.substr(offset));break;}
        segment(text.substr(offset,next-offset));ids.push_back(32099-marker);offset=next+s.options.additional_special_tokens[marker].size();
    }
    // The pinned Transformers 5.17 tokenizer postprocessor always appends EOS,
    // including after a literal EOS in user text. Preserve that exact contract.
    ids.push_back(1);
    bool truncated=ids.size()>static_cast<size_t>(s.options.max_tokens);
    if(truncated) { ids.resize(s.options.max_tokens); ids.back()=1; }
    s.stop(); return {std::move(ids),truncated};
}
std::vector<float> Model::encode(const Tokens& ids) {
    auto& s=*state_; s.stop(); require(s.graph!=nullptr,"Vocabulary-only T5 cannot encode");
    require(!ids.empty() && ids.size()<=static_cast<size_t>(s.options.max_tokens),"T5 token count exceeds selected limit");
    for(auto id:ids) require(id>=0 && id<s.layout.vocabulary,"T5 token ID outside vocabulary");
    s.event("t5_encode",s.stats.encode_calls,static_cast<int>(ids.size()));
    ++s.stats.encode_calls;std::vector<float> output;
    try {output=s.graph->encode(ids);} catch(...) {if(s.interrupted()) ++s.stats.aborted_encodes;throw;}
    s.event("t5_encode_done",s.stats.encode_calls,static_cast<int>(ids.size())); return output;
}
}

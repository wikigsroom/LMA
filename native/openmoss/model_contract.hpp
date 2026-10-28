#pragma once
#include "policy.hpp"
#include "gguf.h"
#include "ggml.h"

namespace lma_openmoss {
struct Header {
    ggml_context* tensors=nullptr;gguf_context* values=nullptr;
    explicit Header(const std::string& path) { gguf_init_params p={true,&tensors};values=gguf_init_from_file(path.c_str(),p);if(!values || !tensors) {if(values)gguf_free(values);if(tensors)ggml_free(tensors);throw std::runtime_error("Cannot read complete GGUF metadata");} }
    ~Header() { gguf_free(values);ggml_free(tensors); }
    Header(const Header&)=delete;Header& operator=(const Header&)=delete;
    uint32_t number(const std::string& key) const { auto i=gguf_find_key(values,key.c_str());require(i>=0 && gguf_get_kv_type(values,i)==GGUF_TYPE_UINT32,"Missing or mistyped GGUF dimension");return gguf_get_val_u32(values,i); }
    std::string string(const char* key) const { auto i=gguf_find_key(values,key);require(i>=0 && gguf_get_kv_type(values,i)==GGUF_TYPE_STRING,"Missing GGUF architecture");return gguf_get_val_str(values,i); }
    void tensor(const std::string& name) const {require(ggml_get_tensor(tensors,name.c_str())!=nullptr,"Required matching GGUF tensor is absent");}
    void eq(const char* key,uint32_t v) const {require(number(key)==v,"Selected GGUF geometry does not match this MOSS pipeline");}
};
inline int model_contract(const std::string& backbone,const std::string& extras,bool local) {
    Header b(backbone),e(extras);require(b.string("general.architecture")=="qwen3","Select a matching converted Qwen3 backbone");
    require(e.string("moss.architecture")== (local?"moss_tts_local":"moss_soundeffect"),"Extras architecture differs; first-class and Nano layouts are incompatible");
    e.eq("moss.sampling_rate",48000);e.eq("moss.codec.version",local?2:0);e.eq("moss.codec.number_channels",local?2:1);e.eq("moss.downsample_rate",local?3840:960);
    b.eq("qwen3.embedding_length",local?2560:2048);b.tensor("token_embd.weight");b.tensor("output_norm.weight");
    for(const char* key:{"tokenizer.ggml.tokens","tokenizer.ggml.merges"}) {auto i=gguf_find_key(b.values,key);require(i>=0 && gguf_get_kv_type(b.values,i)==GGUF_TYPE_ARRAY && gguf_get_arr_type(b.values,i)==GGUF_TYPE_STRING && gguf_get_arr_n(b.values,i)>0 && gguf_get_arr_n(b.values,i)<=2000000,"Matching BPE arrays are required");}
    uint32_t training=b.number("qwen3.context_length");require(training>=4096 && training<=1048576,"Unexpected Qwen3 context metadata");
    if(local) {
        e.eq("moss.n_vq",12);e.eq("moss.audio_vocab_size",1024);e.eq("moss.audio_pad_code",1024);e.eq("moss.local.n_layer",1);e.eq("moss.local.n_embd",2560);e.eq("moss.local.n_head",32);e.eq("moss.local.n_inner",9728);
        for(int i=0;i<12;i++)e.tensor("moss.audio_embed."+std::to_string(i)+".weight");e.tensor("moss.local_text_head.weight");
        e.tensor("moss.codec.quantizer.q.0.codebook.weight");
    } else {
        e.eq("moss.dit.dim",1536);e.eq("moss.dit.n_layers",30);e.eq("moss.dit.n_heads",12);e.eq("moss.dit.in_dim",128);e.eq("moss.dit.out_dim",128);e.eq("moss.dit.text_dim",2048);
        e.eq("moss.vae.latent_dim",128);e.eq("moss.vae.hop",960);e.eq("moss.text.max_len",512);e.eq("moss.max_seconds",30);
        auto ff=e.number("moss.dit.ffn_dim"),freq=e.number("moss.dit.freq_dim");require(ff>0 && ff<=16384 && freq>0 && freq<=4096,"Unbounded DiT dimensions");e.tensor("moss.dit.patch.weight");e.tensor("moss.vae.dec.in.weight");
    }
    return int(std::min(training,4096u));
}
inline int delay_contract(const std::string& backbone,const std::string& extras,const std::string& pipeline) {
    require(delay(pipeline),"Select a reviewed delay profile");Header b(backbone),e(extras);
    require(b.string("general.architecture")=="qwen3" && e.string("moss.architecture")=="moss_tts_delay","Delay profile needs matching openmoss Qwen3/extras, not first-class or Nano files");
    bool voice=pipeline=="moss_voicegen_openmoss_cpu_v1";int hidden=voice?2048:4096,nvq=codebooks(pipeline);
    e.eq("moss.n_vq",nvq);e.eq("moss.sampling_rate",24000);e.eq("moss.downsample_rate",1920);e.eq("moss.codec.version",1);e.eq("moss.codec.number_channels",1);e.eq("moss.audio_vocab_size",1024);e.eq("moss.audio_pad_code",1024);
    b.eq("qwen3.embedding_length",hidden);b.eq("qwen3.block_count",voice?28:36);b.eq("qwen3.attention.head_count",voice?16:32);b.eq("qwen3.attention.head_count_kv",8);b.tensor("token_embd.weight");b.tensor("output_norm.weight");
    for(const char* key:{"tokenizer.ggml.tokens","tokenizer.ggml.merges"}) {auto i=gguf_find_key(b.values,key);require(i>=0 && gguf_get_kv_type(b.values,i)==GGUF_TYPE_ARRAY && gguf_get_arr_type(b.values,i)==GGUF_TYPE_STRING && gguf_get_arr_n(b.values,i)>0 && gguf_get_arr_n(b.values,i)<=2000000,"Matching BPE arrays are required");}
    for(int i=0;i<nvq;i++) {
        for(const char* kind:{"moss.audio_embed.","moss.audio_head."}) {std::string name=std::string(kind)+std::to_string(i)+".weight";e.tensor(name);auto* t=ggml_get_tensor(e.tensors,name.c_str());require(t->ne[0]==hidden && t->ne[1]==1025,"Delay audio embedding/head geometry differs from backbone");}
    }
    e.tensor("moss.codec.quantizer.q.0.codebook.weight");uint32_t training=b.number("qwen3.context_length");require(training>=4096 && training<=1048576,"Unexpected Qwen3 context metadata");return 4096;
}
}

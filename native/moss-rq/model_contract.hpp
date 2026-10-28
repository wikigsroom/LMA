#pragma once
#include "policy.hpp"
#include "../openmoss/model_contract.hpp"

namespace lma_moss_rq {
inline void tensor_shape(const lma_openmoss::Header& h,const std::string& name,int64_t a,int64_t b) {
    h.tensor(name);auto* t=ggml_get_tensor(h.tensors,name.c_str());require(t->ne[0]==a && t->ne[1]==b,"MOSS RQ tensor geometry differs from the selected profile");
}
inline void contract(const std::string& model,const std::string& codec,const std::string& tokenizer,bool rt) {
    lma_openmoss::Header m(model),c(codec),t(tokenizer);
    require(m.string("general.architecture")== (rt?"moss-tts-rt":"moss-tts-local") && c.string("general.architecture")=="moss-audio-tokenizer" && t.string("general.architecture")=="moss-tokenizer","Select matching moss-tts.cpp model/codec/tokenizer GGUFs, not openmoss or first-class layouts");
    m.eq("qwen3.hidden",2048);m.eq("qwen3.n_layers",28);m.eq("qwen3.n_heads",16);m.eq("qwen3.n_kv_heads",8);m.eq("qwen3.head_dim",128);m.eq("qwen3.intermediate",6144);m.eq("qwen3.text_vocab",rt?151936:155648);m.tensor("qwen3.output_norm.weight");
    for(int i=0;i<28;i++)m.tensor("qwen3.blk."+std::to_string(i)+".attn_q.weight");
    const std::string depth=rt?"rtl.":"local.";m.eq((depth+"hidden").c_str(),rt?2048:1536);m.eq((depth+"n_layers").c_str(),4);m.eq((depth+"n_heads").c_str(),16);m.eq((depth+"n_kv_heads").c_str(),8);m.eq((depth+"head_dim").c_str(),128);m.eq((depth+"intermediate").c_str(),rt?6144:8960);
    if(rt) {
        m.eq("rt.rvq",16);m.eq("rt.audio_vocab",1027);m.eq("rt.audio_pad",1024);m.eq("rt.bos_audio",1025);m.eq("rt.eos_audio",1026);m.eq("rt.ref_audio_pad",151654);m.eq("rt.text_pad",151655);m.eq("rt.delay_tokens",12);m.eq("rt.sample_rate",24000);
        tensor_shape(m,"rt.embed.0.weight",2048,151936);
        for(int i=0;i<16;i++) {tensor_shape(m,"rt.embed."+std::to_string(i+1)+".weight",2048,1027);if(i<15)tensor_shape(m,"rtl.embed."+std::to_string(i)+".weight",2048,1027);tensor_shape(m,"rtl.head."+std::to_string(i)+".weight",2048,1027);}
    } else {
        require(m.string("local.arch")=="qwen3","Old Local requires the Qwen3 depth transformer, not v1.5 GPT-J");m.eq("lc.n_vq",32);m.eq("lc.audio_vocab",1025);m.eq("lc.additional_mlp_ffn",2048);m.eq("lc.sample_rate",24000);m.eq("lc.local_text_head_mode",0);m.eq("lc.stereo",0);m.eq("lc.audio_pad_code",1024);
        for(int i=0;i<33;i++) {tensor_shape(m,"lc.embed."+std::to_string(i)+".weight",2048,i==0?155648:1025);tensor_shape(m,"lc.lm_head."+std::to_string(i)+".weight",2048,i==0?155648:1025);m.tensor("lc.out_mlp."+std::to_string(i)+".gate.weight");m.tensor("lc.head_norm."+std::to_string(i)+".weight");}m.tensor("lc.in_mlp.gate.weight");
    }
    c.eq("moss.at.sample_rate",24000);c.eq("moss.at.downsample",1920);c.eq("moss.at.num_quantizers",32);c.eq("moss.at.codebook_size",1024);c.eq("moss.at.codebook_dim",8);c.eq("moss.at.rvq_dim",512);
    require(t.string("tokenizer.model")=="qwen2-bbpe","RQ requires a matching Qwen BPE tokenizer");
    for(const char* key:{"tokenizer.tokens","tokenizer.merges"}) {auto n=gguf_find_key(t.values,key);require(n>=0 && gguf_get_kv_type(t.values,n)==GGUF_TYPE_ARRAY && gguf_get_arr_type(t.values,n)==GGUF_TYPE_STRING && gguf_get_arr_n(t.values,n)>0 && gguf_get_arr_n(t.values,n)<=2000000,"RQ tokenizer BPE arrays are missing or invalid");}
    auto tokens=gguf_find_key(t.values,"tokenizer.tokens");size_t count=gguf_get_arr_n(t.values,tokens);require(count>=151669 && count<=size_t(rt?151936:155648),"Tokenizer vocabulary exceeds the selected RQ model or lacks required IDs");
    for(auto entry:std::initializer_list<std::pair<size_t,const char*>>{{151644,"<|im_start|>"},{151645,"<|im_end|>"},{151652,"<|audio_start|>"},{151653,"<|audio_end|>"}})require(std::string(gguf_get_arr_str(t.values,tokens,entry.first))==entry.second,"RQ tokenizer special-token IDs do not match this model");
    require(std::string(gguf_get_arr_str(t.values,tokens,151654))==(rt?"<|audio_pad|>":"<|audio_user_slot|>") && std::string(gguf_get_arr_str(t.values,tokens,151655))==(rt?"<|text_pad|>":"<|image_pad|>"),"Do not exchange old Local and Realtime tokenizers");
}
}

#pragma once
#include "gguf.h"
#include "ggml.h"
#include "policy.hpp"
#include <memory>

namespace lma_moss {
struct Header {
    ggml_context* tensors=nullptr;
    gguf_context* values=nullptr;
    explicit Header(const std::string& path) {
        gguf_init_params p={true,&tensors}; values=gguf_init_from_file(path.c_str(),p);
        if (!values || !tensors) { if(values)gguf_free(values); if(tensors)ggml_free(tensors); throw std::runtime_error("Cannot read complete GGUF metadata"); }
    }
    ~Header() { gguf_free(values); ggml_free(tensors); }
    Header(const Header&)=delete; Header& operator=(const Header&)=delete;
    uint32_t number(const std::string& key) const {
        int64_t i=gguf_find_key(values,key.c_str()); require(i>=0 && gguf_get_kv_type(values,i)==GGUF_TYPE_UINT32,"Required integer model metadata is absent or mistyped");
        return gguf_get_val_u32(values,i);
    }
    void identity(const char* arch) const {
        int64_t i=gguf_find_key(values,"general.architecture"); require(i>=0 && gguf_get_kv_type(values,i)==GGUF_TYPE_STRING && std::string(gguf_get_val_str(values,i))==arch,"Select a matching first-class MOSS GGUF, not a generic backbone");
    }
    void tensor(const std::string& name, std::initializer_list<int64_t> dims) const {
        auto t=ggml_get_tensor(tensors,name.c_str()); require(t!=nullptr,"Required first-class MOSS tensor is missing");
        int i=0; for(auto d:dims) require(t->ne[i++]==d,"First-class MOSS tensor dimensions differ");
        while(i<GGML_MAX_DIMS) require(t->ne[i++]==1,"Unexpected extra tensor dimensions");
    }
};
inline int backbone_contract(const std::string& path) {
    Header h(path); h.identity("moss-tts-delay");
    for (auto item : {std::pair<const char*,uint32_t>{"embedding_length",4096},{"block_count",36},{"attention.head_count",32},{"attention.head_count_kv",8},{"n_vq",32},{"audio_vocab_size",1024},{"audio_pad_code",1024},{"sampling_rate",24000}})
        require(h.number(std::string("moss-tts-delay.")+item.first)==item.second,"Selected MOSS backbone does not match the 8B/32-channel/24k layout");
    auto training=h.number("moss-tts-delay.context_length"); require(training>=4096 && training<=1048576,"Unexpected backbone context metadata");
    h.tensor("token_embd.weight",{4096,155648}); h.tensor("output.weight",{4096,155648}); h.tensor("output_norm.weight",{4096});
    for(int i=0;i<32;++i) { h.tensor("token_embd_audio."+std::to_string(i)+".weight",{4096,1025}); h.tensor("output_audio."+std::to_string(i)+".weight",{4096,1025}); }
    for(int i=0;i<36;++i) h.tensor("blk."+std::to_string(i)+".attn_norm.weight",{4096});
    for(const char* key:{"tokenizer.ggml.tokens","tokenizer.ggml.merges"}) {
        auto i=gguf_find_key(h.values,key); require(i>=0 && gguf_get_kv_type(h.values,i)==GGUF_TYPE_ARRAY && gguf_get_arr_type(h.values,i)==GGUF_TYPE_STRING,"Matching embedded BPE arrays are required");
        auto n=gguf_get_arr_n(h.values,i); require(n>0 && n<=2000000,"Unexpected BPE array length");
    }
    return int(training);
}
inline void codec_contract(const std::string& path,bool encoder) {
    Header h(path); const std::string arch=encoder?"moss-tts-audio-encoder":"moss-tts-audio-decoder"; h.identity(arch.c_str());
    for(auto item:{std::pair<const char*,uint32_t>{"sampling_rate",24000},{"downsample_rate",1920},{"quantizer.num_quantizers",32},{"quantizer.codebook_size",1024}})
        require(h.number(arch+"."+item.first)==item.second,"Selected codec does not match 24k/32-channel MOSS v1");
    require(gguf_get_n_tensors(h.values)>0,"Codec tensors are absent");
}
}

#pragma once
#include "gguf_loader.h"
#include "text_tokenizer.h"
#include "policy.hpp"
#include <initializer_list>

namespace lma_qwen {
inline int64_t integer(gguf_context* ctx, const char* key) {
    int64_t i = gguf_find_key(ctx, key); require(i >= 0 && gguf_get_kv_type(ctx, i) == GGUF_TYPE_UINT32, "Required Qwen model metadata is absent or mistyped");
    return gguf_get_val_u32(ctx, i);
}
inline std::string string_value(gguf_context* ctx, const char* key) {
    int64_t i = gguf_find_key(ctx, key); require(i >= 0 && gguf_get_kv_type(ctx, i) == GGUF_TYPE_STRING, "Required Qwen model identity is absent");
    return gguf_get_val_str(ctx, i);
}
inline void integer_any(gguf_context* ctx, std::initializer_list<const char*> keys, int expected) {
    bool found = false;
    for (const char* key : keys) if (gguf_find_key(ctx,key) >= 0) { require(integer(ctx,key) == expected, "Qwen component metadata conflicts with the selected recipe"); found = true; }
    require(found, "A required Qwen component dimension is not declared");
}
inline void tensor(qwen3_tts::GGUFLoader& loader, const std::string& name, std::initializer_list<int64_t> dims) {
    ggml_tensor* t = ggml_get_tensor(loader.get_meta_ctx(), name.c_str()); require(t != nullptr, "A required Qwen tensor is missing");
    int i = 0; for (int64_t d : dims) require(t->ne[i++] == d, "Qwen tensor dimensions do not match 0.6B Base");
    while (i < GGML_MAX_DIMS) require(t->ne[i++] == 1, "Unexpected extra Qwen tensor dimensions");
}
inline size_t talker_contract(const std::string& path, const std::string& text, int max_tokens) {
    qwen3_tts::GGUFLoader loader; require(loader.open(path), "Cannot read Talker GGUF"); auto ctx = loader.get_ctx();
    require(string_value(ctx, "general.architecture") == "qwen3-tts" && string_value(ctx, "qwen3-tts.model_type") == "base", "Select the exact Qwen3-TTS 0.6B Base conversion");
    for (auto kv : {std::pair<const char*, int>{"qwen3-tts.talker.embedding_length",1024}, {"qwen3-tts.talker.block_count",28}, {"qwen3-tts.talker.text_hidden_size",2048}, {"qwen3-tts.talker.text_vocab_size",151936}, {"qwen3-tts.code_pred.block_count",5}, {"qwen3-tts.code_pred.embedding_length",1024}}) require(integer(ctx, kv.first) == kv.second, "Qwen model architecture does not match the selected recipe");
    integer_any(ctx,{"qwen3-tts.num_code_groups","qwen3-tts.talker.num_codebooks"},16);
    tensor(loader, "talker.text_embd.weight", {2048,151936}); tensor(loader, "talker.codec_embd.weight", {1024,3072}); tensor(loader, "talker.codec_head.weight", {1024,3072});
    tensor(loader, "talker.output_norm.weight", {1024}); tensor(loader, "code_pred.output_norm.weight", {1024});
    for (int i = 0; i < 28; ++i) tensor(loader, "talker.blk."+std::to_string(i)+".attn_norm.weight", {1024});
    for (int i = 0; i < 5; ++i) tensor(loader, "code_pred.blk."+std::to_string(i)+".attn_norm.weight", {1024});
    for (int i = 0; i < 15; ++i) tensor(loader, "code_pred.lm_head."+std::to_string(i)+".weight", {1024,2048});
    tensor(loader, "spk_enc.fc.weight", {1,3072,1024});
    for (const char* key : {"tokenizer.ggml.tokens", "tokenizer.ggml.merges"}) {
        int64_t i = gguf_find_key(ctx,key);
        require(i >= 0 && gguf_get_kv_type(ctx,i) == GGUF_TYPE_ARRAY && gguf_get_arr_type(ctx,i) == GGUF_TYPE_STRING, "Talker BPE vocabulary/merges must be string arrays");
        size_t n = gguf_get_arr_n(ctx,i);
        require(std::string(key) == "tokenizer.ggml.tokens" ? n >= 151646 && n <= 151936 : n > 0 && n <= 2000000, "Talker BPE vocabulary/merges do not fit the expected embeddings");
    }
    qwen3_tts::TextTokenizer tokenizer; require(tokenizer.load_from_gguf(ctx), "Talker must contain its matching text BPE vocabulary and merges");
    auto ids = tokenizer.encode_for_tts(text); require(!ids.empty() && ids.size() <= size_t(max_tokens), "Formatted speech text exceeds this model's selected input token budget");
    return ids.size();
}
inline void codec_contract(const std::string& path) {
    qwen3_tts::GGUFLoader loader; require(loader.open(path), "Cannot read audio codec GGUF"); auto ctx = loader.get_ctx();
    require(string_value(ctx, "general.architecture") == "qwen3-tts-tokenizer", "Select the matching Qwen3 12Hz audio codec");
    integer_any(ctx,{"qwen3-tts-tokenizer.output_sample_rate","qwen3-tts-tokenizer.sample_rate"},24000);
    integer_any(ctx,{"qwen3-tts-tokenizer.decoder.num_quantizers","qwen3-tts-tokenizer.num_codebooks","qwen3-tts-tokenizer.num_code_groups"},16);
    require(integer(ctx,"qwen3-tts-tokenizer.decode_upsample_rate") == 1920, "Audio codec must match the 12Hz frame contract");
    bool decoder = false; for (int64_t i = 0; i < loader.get_n_tensors(); ++i) if (std::string(loader.get_tensor_name(i)).find("tok_dec.") == 0) decoder = true;
    require(decoder, "Selected codec GGUF lacks decoder weights");
}
}

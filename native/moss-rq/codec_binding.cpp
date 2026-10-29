#include "moss_tts.h"
#include "audio_tokenizer.hpp"

// Only the codec surface is needed by the two reviewed orchestrators.
namespace moss {
Codec::Codec():impl_(std::make_unique<AudioTokenizer>()) {}
Codec::~Codec()=default;
bool Codec::load(const std::string& path) {return impl_->load(path);}
int Codec::sample_rate() const {return impl_->sample_rate();}
int Codec::num_quantizers() const {return impl_->num_quantizers();}
bool Codec::encode(const std::vector<float>& wav,std::vector<int32_t>* codes,int* frames) {return impl_->encode(wav,codes,frames);}
bool Codec::decode(const std::vector<int32_t>& codes,int frames,std::vector<float>* wav,int quantizers) {return impl_->decode(codes,frames,wav,quantizers);}
bool Codec::reconstruct(const std::vector<float>& wav,std::vector<float>* out) {return impl_->reconstruct(wav,out);}
std::unique_ptr<NanoCodecStream> Codec::stream_begin() {return impl_->decode_stream_begin();}
bool Codec::stream_step(NanoCodecStream& state,const std::vector<int32_t>& codes,std::vector<float>* pcm) {return impl_->decode_stream_step(state,codes,pcm);}
}

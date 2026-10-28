// SPDX-License-Identifier: MIT
// SoulX-Podcast audio primitives. No weights, asset loading or execution provider.
#pragma once
#include <array>
#include <cstddef>
#include <functional>
#include <vector>

namespace lma::soulx {
using Samples = std::vector<float>;
using Cancel = std::function<bool()>;
struct Matrix {
    size_t rows = 0, cols = 0;
    Samples values; // Row-major; channels x frames unless specified otherwise.
    float& at(size_t row, size_t col) { return values.at(row * cols + col); }
    float at(size_t row, size_t col) const { return values.at(row * cols + col); }
};
// The caller decodes a mono PCM reference before calling these functions.
// Limits are defensive library bounds, not a claim of phone capacity/quality.
constexpr size_t kMaxReference24k = 15 * 24000;
constexpr size_t kMaxMelFrames = 6000;
constexpr size_t kMaxFlowFrames = kMaxMelFrames + 750; // include 15s reference
Samples normalize_volume(const Samples& pcm);
Samples resample_24k_to_16k(const Samples& pcm, Cancel cancelled = {});
Matrix slaney_filters(int sample_rate, int fft_size, int mel_bins, float max_hz);
Matrix semantic_features(const Samples& pcm16k, Cancel cancelled = {}); // [128,T]
Matrix flow_features(const Samples& pcm24k, Cancel cancelled = {}); // [80,T], even T
Matrix speaker_features(const Samples& pcm16k, Cancel cancelled = {}); // [T,80], CMN

struct ReferenceFeatures {
    Matrix semantic, flow, speaker;
};
// Exact upstream normalization order: normalize after resampling for S3/CAMP;
// normalize at 24 kHz for Flow. Never feed one model's mel layout to another.
ReferenceFeatures reference_features(const Samples& mono24k, Cancel cancelled = {});

struct AlignedPrompt { size_t token_count, mel_frames; };
AlignedPrompt align_prompt(size_t speech_tokens, size_t mel_frames);
Samples cosine_schedule(int steps);
void euler_step(Samples& state, const Samples& conditional, const Samples& unconditional,
                float dt, float cfg = 0.7f);

// HiFT's source STFT: n_fft=16, hop=4, periodic Hann, reflected center padding.
// Layout [18,frames]: all 9 real channels followed by all 9 imaginary channels.
Matrix source_stft(const Samples& source, Cancel cancelled = {});
// Neural HiFT spectral outputs are [9,frames], magnitude and phase radians.
// This operation performs ISTFT and the upstream final [-.99,.99] clamp.
Samples hift_istft(const Matrix& magnitude, const Matrix& phase, Cancel cancelled = {});

// F0 comes from the user's trained HiFT F0 graph (one value per mel frame).
// Inject noise explicitly: an eventual worker owns its seed and RNG state.
// Emit one 9-harmonic vector at a time so the caller can merge learned source
// weights without allocating a samples x 9 tensor for a long utterance.
void nsf_harmonics(const Samples& f0, const std::function<float()>& normal_noise,
                   const std::function<void(size_t, const std::array<float,9>&)>& emit,
                   Cancel cancelled = {});
}

// SPDX-License-Identifier: Apache-2.0
// Audio/CFM/NSF ports: Soul-AILab contributors, Alibaba Inc., OpenAI and
// Tsinghua S3Tokenizer contributors. LMA adaptations Copyright 2026 LMA contributors.
// Equations/layouts reviewed against the pinned Soul-AILab and S3Tokenizer
// sources in third_party/soulx-dsp-source-lock.json; FFT is pinned KISS FFT.
#include "dsp.hpp"
#include "kiss_fftr.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>

namespace lma::soulx {
namespace {
constexpr double pi = 3.14159265358979323846;
void require(bool ok, const char* message) { if (!ok) throw std::invalid_argument(message); }
void check_cancel(const Cancel& cancelled) {
    if (cancelled && cancelled()) throw std::runtime_error("SoulX DSP cancelled");
}
void finite(const Samples& x) {
    for (float v : x) require(std::isfinite(v), "Non-finite SoulX audio/tensor");
}
void pcm_bound(const Samples& x, size_t min, size_t max) {
    require(x.size() >= min && x.size() <= max, "SoulX PCM length outside bounds"); finite(x);
}
Matrix matrix(size_t rows, size_t cols) {
    require(rows && cols && rows <= 4096 && cols <= 3000000 && rows <= 32000000 / cols,
            "SoulX tensor allocation outside bounds");
    return {rows, cols, Samples(rows * cols)};
}
void shape(const Matrix& m, size_t rows) {
    require(m.rows == rows && m.cols && m.cols <= kMaxMelFrames * 120 + 1 &&
            m.rows * m.cols == m.values.size(), "Invalid SoulX spectral tensor shape"); finite(m.values);
}
int reflect(int i, int length) {
    // PyTorch reflect padding excludes the boundary sample itself.
    while (i < 0 || i >= length) i = i < 0 ? -i : 2 * length - 2 - i;
    return i;
}
Samples hann(int size, bool periodic = true, double exponent = 1) {
    Samples w(size);
    for (int i = 0; i < size; ++i)
        w[i] = static_cast<float>(std::pow(0.5 - 0.5 * std::cos(2 * pi * i / (periodic ? size : size - 1)), exponent));
    return w;
}
class Fft {
    std::unique_ptr<kiss_fftr_state, decltype(&std::free)> cfg_;
public:
    explicit Fft(int n, bool inverse = false) : cfg_(kiss_fftr_alloc(n, inverse, nullptr, nullptr), std::free) {
        if (!cfg_) throw std::bad_alloc();
    }
    void forward(const float* in, kiss_fft_cpx* out) { kiss_fftr(cfg_.get(), in, out); }
    void inverse(const kiss_fft_cpx* in, float* out) { kiss_fftri(cfg_.get(), in, out); }
};
Matrix stft(const Samples& pcm, int nfft, int hop, int padding, bool drop_last, Cancel cancelled) {
    require(pcm.size() > static_cast<size_t>(padding), "PCM too short for reflected STFT");
    int frames = 1 + (static_cast<int>(pcm.size()) + 2 * padding - nfft) / hop;
    if (drop_last) --frames;
    require(frames > 0, "STFT has no complete frames");
    Matrix result = matrix(2 * (nfft / 2 + 1), frames);
    Samples window = hann(nfft), frame(nfft); std::vector<kiss_fft_cpx> spectrum(nfft / 2 + 1); Fft fft(nfft);
    for (int t = 0; t < frames; ++t) {
        check_cancel(cancelled);
        for (int k = 0; k < nfft; ++k)
            frame[k] = pcm[reflect(t * hop - padding + k, static_cast<int>(pcm.size()))] * window[k];
        fft.forward(frame.data(), spectrum.data());
        for (int k = 0; k <= nfft / 2; ++k) {
            result.at(k,t) = spectrum[k].r; result.at(k+nfft/2+1,t) = spectrum[k].i;
        }
    }
    finite(result.values); return result;
}
double hz_to_slaney(double hz) { return hz < 1000 ? hz / (200.0/3) : 15 + std::log(hz / 1000) / (std::log(6.4)/27); }
double slaney_to_hz(double mel) { return mel < 15 ? mel * (200.0/3) : 1000 * std::exp((mel - 15) * (std::log(6.4)/27)); }
}

Samples normalize_volume(const Samples& pcm) {
    pcm_bound(pcm, 1, kMaxReference24k);
    Samples result(pcm), sorted; sorted.reserve(pcm.size());
    float peak = 0;
    for (float v : pcm) { peak = std::max(peak, std::abs(v)); if (std::abs(v) > .01f) sorted.push_back(std::abs(v)); }
    // Upstream computes its percentile on ORIGINAL amplitudes even if it has
    // already amplified quiet PCM. Retaining that order matters for voices.
    if (peak < .1f) for (float& v : result) v = v / std::max(peak,.001f) * .1f;
    if (sorted.size() <= 10) return result;
    std::sort(sorted.begin(), sorted.end());
    size_t low = static_cast<size_t>(.9 * sorted.size()), high = static_cast<size_t>(.99 * sorted.size());
    double sum = 0; for (size_t i=low; i<high; ++i) sum += sorted[i];
    float scale = std::clamp(.1f / static_cast<float>(sum / (high-low)), .1f, 10.f);
    peak = 0; for (float& v : result) { v *= scale; peak = std::max(peak,std::abs(v)); }
    if (peak > 1) for (float& v : result) v /= peak;
    return result;
}

Samples resample_24k_to_16k(const Samples& pcm, Cancel cancelled) {
    pcm_bound(pcm, 1, kMaxReference24k);
    // torchaudio's default sinc_interp_hann, reduced ratio 3:2, width=6,
    // rolloff=.99, zero boundary extension. Output length is ceil(N*2/3).
    constexpr double base = 2 * .99;
    constexpr int width = 10; // ceil(6 * 3 / (2*.99))
    double kernels[2][2*width+3] = {};
    for (int phase=0; phase<2; ++phase) for (int j=0; j<2*width+3; ++j) {
        double t = std::clamp(((-phase/2.0) + (j-width)/3.0) * base, -6., 6.);
        double angle = t * pi;
        kernels[phase][j] = (angle == 0 ? 1 : std::sin(angle)/angle) *
            std::pow(std::cos(t * pi / 12), 2) * base / 3;
    }
    Samples out((pcm.size()*2+2)/3);
    for (size_t i=0; i<out.size(); ++i) {
        if (i%1024 == 0) check_cancel(cancelled);
        double sum = 0; int start = static_cast<int>(i/2)*3-width;
        for (int j=0; j<2*width+3; ++j) {
            int pos = start+j;
            if (pos >= 0 && pos < static_cast<int>(pcm.size())) sum += pcm[pos] * kernels[i%2][j];
        }
        out[i] = static_cast<float>(sum);
    }
    finite(out); return out;
}

Matrix slaney_filters(int sample_rate, int fft_size, int mel_bins, float max_hz) {
    require((sample_rate==16000 && fft_size==400 && mel_bins==128 && max_hz==8000) ||
            (sample_rate==24000 && fft_size==1920 && mel_bins==80 && max_hz==8000), "Unsupported SoulX Slaney layout");
    Matrix filters = matrix(mel_bins, fft_size/2+1); std::vector<double> frequencies(mel_bins+2);
    for (int i=0; i<mel_bins+2; ++i) frequencies[i] = slaney_to_hz(hz_to_slaney(max_hz)*i/(mel_bins+1));
    for (int m=0; m<mel_bins; ++m) for (int k=0; k<=fft_size/2; ++k) {
        double hz = static_cast<double>(sample_rate)*k/fft_size;
        double triangle = std::max(0.,std::min((hz-frequencies[m])/(frequencies[m+1]-frequencies[m]),
                                               (frequencies[m+2]-hz)/(frequencies[m+2]-frequencies[m+1])));
        // librosa stores the triangle in float32 before in-place Slaney norm.
        filters.at(m,k) = static_cast<float>(triangle) * static_cast<float>(2/(frequencies[m+2]-frequencies[m]));
    }
    return filters;
}

Matrix semantic_features(const Samples& pcm, Cancel cancelled) {
    pcm_bound(pcm, 201, 15*16000);
    Matrix spectrum = stft(pcm,400,160,200,true,cancelled), filters = slaney_filters(16000,400,128,8000);
    Matrix result = matrix(128,spectrum.cols); Samples energy(201);
    float maximum = -std::numeric_limits<float>::infinity();
    for (size_t t=0; t<spectrum.cols; ++t) {
        check_cancel(cancelled);
        for (size_t k=0; k<201; ++k) {
            float r=spectrum.at(k,t), i=spectrum.at(k+201,t); energy[k]=r*r+i*i;
            require(std::isfinite(energy[k]),"SoulX semantic FFT power overflow");
        }
        for (size_t m=0; m<128; ++m) {
            double sum=0;
            for (size_t k=0; k<201; ++k) sum += filters.at(m,k)*energy[k];
            float v=std::log10(std::max(1e-10f,static_cast<float>(sum))); result.at(m,t)=v; maximum=std::max(maximum,v);
        }
    }
    for (float& v : result.values) v=(std::max(v,maximum-8)+4)/4;
    finite(result.values); return result;
}

Matrix flow_features(const Samples& pcm, Cancel cancelled) {
    pcm_bound(pcm, 721, kMaxReference24k);
    Matrix spectrum=stft(pcm,1920,480,720,false,cancelled), filters=slaney_filters(24000,1920,80,8000);
    size_t frames=spectrum.cols & ~size_t(1); require(frames>0,"No even SoulX Flow frames");
    Matrix result=matrix(80,frames); Samples magnitudes(961);
    for (size_t t=0; t<frames; ++t) {
        check_cancel(cancelled);
        for (size_t k=0; k<961; ++k) {
            float r=spectrum.at(k,t), i=spectrum.at(k+961,t); float power=r*r+i*i+1e-9f;
            require(std::isfinite(power),"SoulX Flow FFT power overflow"); magnitudes[k]=std::sqrt(power);
        }
        for (size_t m=0; m<80; ++m) {
            double sum=0;
            for (size_t k=0; k<961; ++k) sum += filters.at(m,k)*magnitudes[k];
            result.at(m,t)=std::log(std::max(1e-5f,static_cast<float>(sum)));
        }
    }
    finite(result.values); return result;
}

Matrix speaker_features(const Samples& pcm, Cancel cancelled) {
    pcm_bound(pcm,400,15*16000);
    // torchaudio.compliance.kaldi.fbank defaults: snip_edges, 25ms/10ms,
    // DC removal, .97 preemphasis, nonperiodic Povey window, 512 FFT,
    // power, 20Hz low cut, Nyquist high cut, dither=0, no energy append.
    const size_t frames=1+(pcm.size()-400)/160;
    Matrix result=matrix(frames,80); Samples window=hann(400,false,.85),frame(512),energy(256);
    Fft fft(512); std::vector<kiss_fft_cpx> spectrum(257);
    double mel_low=1127*std::log1p(20./700), mel_high=1127*std::log1p(8000./700);
    float low_mel=static_cast<float>(mel_low), delta=static_cast<float>((mel_high-mel_low)/81);
    Matrix filters=matrix(80,256);
    for (size_t m=0; m<80; ++m) {
        float left=low_mel+static_cast<float>(m)*delta, center=low_mel+static_cast<float>(m+1)*delta;
        float right=low_mel+static_cast<float>(m+2)*delta;
        for (size_t k=0; k<256; ++k) {
            float mel=1127.f*std::log(1.f+(16000.f*static_cast<float>(k)/512)/700.f);
            filters.at(m,k)=std::max(0.f,std::min((mel-left)/(center-left),(right-mel)/(right-center)));
        }
    }
    for (size_t t=0; t<frames; ++t) {
        check_cancel(cancelled); double mean=0;
        for (size_t i=0; i<400; ++i) mean+=pcm[t*160+i];
        float dc=static_cast<float>(mean/400);
        for (int i=399; i>=0; --i) {
            float current=pcm[t*160+i]-dc, previous=pcm[t*160+std::max(i-1,0)]-dc;
            frame[i]=(current-.97f*previous)*window[i];
        }
        std::fill(frame.begin()+400,frame.end(),0); fft.forward(frame.data(),spectrum.data());
        for (size_t k=0; k<256; ++k) {
            energy[k]=spectrum[k].r*spectrum[k].r+spectrum[k].i*spectrum[k].i;
            require(std::isfinite(energy[k]),"SoulX speaker FFT power overflow");
        }
        for (size_t m=0; m<80; ++m) {
            double sum=0;
            for (size_t k=0; k<256; ++k) sum+=filters.at(m,k)*energy[k];
            result.at(t,m)=std::log(std::max(std::numeric_limits<float>::epsilon(),static_cast<float>(sum)));
        }
    }
    for (size_t m=0; m<80; ++m) {
        double sum=0; for (size_t t=0; t<frames; ++t) sum+=result.at(t,m);
        float mean=static_cast<float>(sum/frames);
        for (size_t t=0; t<frames; ++t) result.at(t,m)-=mean;
    }
    finite(result.values); return result;
}

ReferenceFeatures reference_features(const Samples& mono24k, Cancel cancelled) {
    pcm_bound(mono24k,24000,kMaxReference24k); check_cancel(cancelled);
    Samples pcm16=normalize_volume(resample_24k_to_16k(mono24k,cancelled));
    ReferenceFeatures result;
    result.semantic=semantic_features(pcm16,cancelled); result.speaker=speaker_features(pcm16,cancelled);
    result.flow=flow_features(normalize_volume(mono24k),cancelled); return result;
}

AlignedPrompt align_prompt(size_t tokens, size_t frames) {
    require(tokens>0 && tokens<=375 && frames>0 && frames<=750,"Invalid SoulX reference token/mel count");
    if (2*tokens>frames) tokens=frames/2; else frames=2*tokens;
    require(tokens>0,"SoulX reference has no aligned semantic token"); return {tokens,frames};
}
Samples cosine_schedule(int steps) {
    require(steps>=1 && steps<=100,"Invalid SoulX Flow step count"); Samples schedule(steps+1);
    for (int i=0; i<=steps; ++i) schedule[i]=1-std::cos(static_cast<float>(i)/steps * .5f * static_cast<float>(pi));
    return schedule;
}
void euler_step(Samples& state, const Samples& conditional, const Samples& unconditional, float dt, float cfg) {
    require(!state.empty() && state.size()<=80*kMaxFlowFrames && conditional.size()==state.size() && unconditional.size()==state.size(), "Invalid SoulX Flow velocity layout");
    require(std::isfinite(dt) && dt>0 && dt<=1 && std::isfinite(cfg) && cfg>=0 && cfg<=10,"Invalid SoulX Flow time/CFG");
    finite(state); finite(conditional); finite(unconditional);
    Samples next(state.size());
    for (size_t i=0; i<state.size(); ++i) {
        next[i]=state[i]+dt*((1+cfg)*conditional[i]-cfg*unconditional[i]);
        require(std::isfinite(next[i]),"SoulX Flow update overflow");
    }
    state.swap(next);
}

Matrix source_stft(const Samples& source, Cancel cancelled) {
    pcm_bound(source, 480, kMaxMelFrames*480); require(source.size()%480==0,"HiFT source must contain complete mel frames");
    return stft(source,16,4,8,false,cancelled);
}
Samples hift_istft(const Matrix& magnitude, const Matrix& phase, Cancel cancelled) {
    shape(magnitude,9); shape(phase,9);
    require(magnitude.cols==phase.cols && magnitude.cols>1 && (magnitude.cols-1)%120==0,"HiFT spectral frames do not match 480 samples/mel");
    const size_t length=(magnitude.cols-1)*4+16;
    Samples output(length,0),norm(length,0),frame(16),window=hann(16);
    std::vector<kiss_fft_cpx> spectrum(9); Fft fft(16,true);
    for (size_t t=0; t<magnitude.cols; ++t) {
        check_cancel(cancelled);
        for (size_t k=0; k<9; ++k) {
            require(magnitude.at(k,t)>=0,"Negative HiFT magnitude");
            float mag=std::min(magnitude.at(k,t),100.f), p=phase.at(k,t);
            spectrum[k].r=mag*std::cos(p); spectrum[k].i=mag*std::sin(p);
        }
        fft.inverse(spectrum.data(),frame.data());
        for (size_t k=0; k<16; ++k) {
            output[t*4+k]+=frame[k]/16*window[k]; norm[t*4+k]+=window[k]*window[k];
        }
    }
    Samples result(length-16);
    for (size_t i=8; i<length-8; ++i) {
        require(norm[i]>1e-11f,"HiFT ISTFT overlap has a zero denominator");
        result[i-8]=std::clamp(output[i]/norm[i],-.99f,.99f);
    }
    finite(result); return result;
}

void nsf_harmonics(const Samples& f0, const std::function<float()>& normal_noise,
        const std::function<void(size_t,const std::array<float,9>&)>& emit, Cancel cancelled) {
    pcm_bound(f0,1,kMaxMelFrames); require(bool(normal_noise) && bool(emit),"Missing SoulX NSF noise/output callback");
    Matrix phase=matrix(9,f0.size());
    for (size_t h=0; h<9; ++h) {
        double cumulative=0;
        for (size_t t=0; t<f0.size(); ++t) {
            require(f0[t]>=0 && f0[t]<=12000,"Invalid SoulX F0");
            float r=f0[t]*static_cast<float>(h+1)/24000;
            cumulative+=r-std::floor(r);
            phase.at(h,t)=static_cast<float>(cumulative)*2*static_cast<float>(pi)*480;
        }
    }
    // Upstream first repeats each F0 480 times then linearly downsamples at
    // half-pixel centers; its random first-sample phase is not sampled. Linear
    // upsampling below preserves the GLOBAL sample offset across output chunks.
    for (size_t i=0; i<f0.size()*480; ++i) {
        if (i%1024==0) check_cancel(cancelled);
        // PyTorch linear interpolation uses a float32 reciprocal scale and
        // clamps its half-pixel coordinate BEFORE calculating the weights.
        // Computing an exact double coordinate drifts from its phase at long
        // sample offsets; weighting duplicate left-edge samples also rounds.
        float pos=std::max(0.f,(1.f/480)*(static_cast<float>(i)+.5f)-.5f);
        int low=static_cast<int>(std::floor(pos)); float fraction=pos-low;
        size_t a=static_cast<size_t>(std::max(0,low)), b=std::min(f0.size()-1,static_cast<size_t>(std::max(0,low+1)));
        a=std::min(a,f0.size()-1); std::array<float,9> harmonics;
        bool voiced=f0[i/480]>10;
        for (size_t h=0; h<9; ++h) {
            float p=(1-fraction)*phase.at(h,a)+fraction*phase.at(h,b), noise=normal_noise();
            require(std::isfinite(noise),"Non-finite SoulX NSF noise");
            harmonics[h]=std::sin(p)*.1f*(voiced?1.f:0.f)+(voiced?.003f:.1f/3)*noise;
        }
        emit(i,harmonics);
    }
}
}

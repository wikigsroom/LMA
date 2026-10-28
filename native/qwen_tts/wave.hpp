#pragma once
#include "policy.hpp"
#include <cstdint>
#include <cstring>
#include <fstream>

namespace lma_qwen {
inline uint32_t le32(const unsigned char* p) { return uint32_t(p[0]) | uint32_t(p[1]) << 8 | uint32_t(p[2]) << 16 | uint32_t(p[3]) << 24; }
inline uint16_t le16(const unsigned char* p) { return uint16_t(p[0]) | uint16_t(p[1]) << 8; }
// Strict input validation before passing normalized samples to the upstream API.
inline std::vector<float> reference_wave(const std::string& path) {
    std::ifstream in(path, std::ios::binary | std::ios::ate);
    require(bool(in) && in.tellg() >= 44 && in.tellg() <= 4 * 1024 * 1024, "Reference WAV size must be 44 bytes to 4 MiB");
    std::vector<unsigned char> bytes(static_cast<size_t>(in.tellg())); in.seekg(0); in.read(reinterpret_cast<char*>(bytes.data()), bytes.size());
    require(bool(in) && !std::memcmp(bytes.data(), "RIFF", 4) && !std::memcmp(bytes.data()+8, "WAVE", 4) && le32(bytes.data()+4) == bytes.size()-8, "Invalid WAV RIFF extent");
    unsigned format = 0, bits = 0; size_t start = 0, length = 0, chunks = 0;
    for (size_t pos = 12; pos < bytes.size();) {
        require(++chunks <= 16384 && bytes.size()-pos >= 8, "Invalid WAV chunks");
        const unsigned char* h = bytes.data()+pos; uint32_t n = le32(h+4); size_t next = pos+8+size_t(n)+(n&1);
        require(next <= bytes.size(), "Truncated WAV chunk");
        if (!std::memcmp(h, "fmt ", 4)) {
            require(!format && n >= 16, "Duplicate or truncated WAV format"); const unsigned char* p = h+8;
            format = le16(p); bits = le16(p+14); unsigned align = bits/8;
            require((format == 1 && bits == 16 || format == 3 && bits == 32) && le16(p+2) == 1 && le32(p+4) == 24000 && le16(p+12) == align && le32(p+8) == 24000*align, "Reference must be 24 kHz mono PCM16 or float32 WAV");
        } else if (!std::memcmp(h, "data", 4)) {
            require(!start && n > 0, "Duplicate or empty WAV data"); start = pos+8; length = n;
        }
        pos = next;
    }
    require(format && start && length % (bits/8) == 0, "WAV format/data missing or incomplete");
    size_t count = length/(bits/8); require(count >= 24000 && count <= 720000, "Reference duration must be 1 to 30 seconds");
    std::vector<float> samples(count);
    for (size_t i = 0; i < count; ++i) {
        const unsigned char* p = bytes.data()+start+i*(bits/8);
        if (format == 1) samples[i] = int16_t(le16(p))/32768.f;
        else { uint32_t value = le32(p); std::memcpy(&samples[i], &value, 4); }
        require(std::isfinite(samples[i]) && samples[i] >= -1 && samples[i] <= 1, "Reference samples must be finite and normalized");
    }
    return samples;
}
}

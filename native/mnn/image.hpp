#pragma once
#include <cstdint>
#include <fstream>
#include <stdexcept>
#include <string>
#include <utility>

namespace lma_mnn {
// Inspect the actual selected file before allocating a decoded image.
inline std::pair<int, int> image_dimensions(const std::string& path) {
    std::ifstream in(path, std::ios::binary | std::ios::ate);
    const auto length = in.tellg();
    if (!in || length < 24 || length > 16 * 1024 * 1024) throw std::runtime_error("Select a local PNG/JPEG of at most 16 MiB");
    in.seekg(0); unsigned char header[24];
    in.read(reinterpret_cast<char*>(header), sizeof(header));
    auto bounded = [](uint32_t w, uint32_t h) {
        if (!w || !h || uint64_t(w) * h > 4194304) throw std::runtime_error("Sana source image exceeds the four-megapixel limit");
        return std::make_pair(static_cast<int>(w), static_cast<int>(h));
    };
    const unsigned char png[] = {137,80,78,71,13,10,26,10};
    bool is_png = true;
    for (int i=0;i<8;++i) is_png = is_png && header[i] == png[i];
    if (is_png) {
        if (header[8] || header[9] || header[10] || header[11] != 13 || header[12] != 'I' || header[13] != 'H' || header[14] != 'D' || header[15] != 'R') throw std::runtime_error("Invalid PNG dimensions header");
        auto be32 = [&](int offset) { return uint32_t(header[offset]) << 24 | uint32_t(header[offset+1]) << 16 | uint32_t(header[offset+2]) << 8 | header[offset+3]; };
        return bounded(be32(16), be32(20));
    }
    if (header[0] != 255 || header[1] != 216) throw std::runtime_error("Sana source image must be PNG or JPEG");
    in.seekg(2);
    auto byte = [&]() -> unsigned int { int b=in.get(); if (b == EOF) throw std::runtime_error("Truncated JPEG header"); return static_cast<unsigned int>(b); };
    while (in.tellg() < length) {
        if (byte() != 255) throw std::runtime_error("Invalid JPEG marker");
        unsigned int marker; do { marker=byte(); } while (marker == 255);
        if (marker == 217 || marker == 218 || marker == 0) break;
        if (marker == 1 || (marker >= 208 && marker <= 215)) continue;
        unsigned int a=byte(), b=byte(), segment=a*256+b;
        if (segment < 2 || in.tellg() > length - static_cast<std::streamoff>(segment-2)) throw std::runtime_error("Invalid JPEG segment size");
        if ((marker >= 192 && marker <= 195) || (marker >= 197 && marker <= 199) || (marker >= 201 && marker <= 203) || (marker >= 205 && marker <= 207)) {
            if (segment < 8) throw std::runtime_error("Invalid JPEG frame header");
            byte(); unsigned int h1=byte(), h2=byte(), w1=byte(), w2=byte();
            return bounded(w1*256+w2, h1*256+h2);
        }
        in.seekg(segment-2, std::ios::cur);
    }
    throw std::runtime_error("JPEG dimensions are missing");
}
}

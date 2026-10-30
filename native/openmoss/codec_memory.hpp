#pragma once
#include "ggml-alloc.h"
#include "ggml-backend.h"
#include <algorithm>
#include <cstdint>
#include <stdexcept>

namespace lma_openmoss {
struct CodecMemoryStats {
    uint64_t released_bytes = 0;
    uint64_t largest_released_buffer = 0;
    int releases = 0;
};
inline thread_local CodecMemoryStats codec_memory_stats;

// Host copies own every output code before this call. Persistent model weights
// and the separate streaming allocator do not belong to this batch allocator.
inline void release_encoder_scratch(ggml_gallocr_t & allocator, ggml_backend_t backend) {
    if (!allocator || !backend) throw std::runtime_error("Missing reference encoder allocator");
    if (ggml_backend_dev_type(ggml_backend_get_device(backend)) != GGML_BACKEND_DEVICE_TYPE_CPU) return;
    const size_t bytes = ggml_gallocr_get_buffer_size(allocator, 0);
    ggml_gallocr_free(allocator);
    allocator = nullptr;
    allocator = ggml_gallocr_new(ggml_backend_get_default_buffer_type(backend));
    if (!allocator) throw std::runtime_error("Cannot recreate reference encoder allocator");
    codec_memory_stats.released_bytes += bytes;
    codec_memory_stats.largest_released_buffer = std::max(codec_memory_stats.largest_released_buffer, uint64_t(bytes));
    ++codec_memory_stats.releases;
}
}

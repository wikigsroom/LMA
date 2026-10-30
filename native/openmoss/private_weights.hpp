#pragma once

// CPU GGUF tensors retain their original bytes and types. Clean weight pages
// stay file backed; a private write never changes the user's immutable object.
#include "ggml.h"
#include "ggml-backend.h"
#include "ggml-backend-impl.h"
#include "ggml-cpu.h"
#include <algorithm>
#include <cstdint>
#include <limits>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <vector>
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#else
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#endif

namespace lma_openmoss {
struct WeightBinding { ggml_tensor * tensor; uint64_t offset; };
struct WeightSource { std::string path; std::vector<WeightBinding> tensors; };
struct WeightMappingStats {
    uint64_t files = 0, file_bytes = 0, mapped_bytes = 0, tensors = 0, tensor_bytes = 0;
};
inline std::mutex & mapping_mutex() { static std::mutex m; return m; }
inline WeightMappingStats & mapping_totals() { static WeightMappingStats s; return s; }
inline WeightMappingStats weight_mapping_stats() {
    std::lock_guard<std::mutex> guard(mapping_mutex()); return mapping_totals();
}

class PrivateWeightFile {
    void * address_ = nullptr;
    size_t size_ = 0;
    size_t view_size_ = 0;
    uint64_t view_offset_ = 0;
#ifdef _WIN32
    HANDLE file_ = INVALID_HANDLE_VALUE, mapping_ = nullptr;
#else
    int file_ = -1;
#endif
    void release() noexcept {
#ifdef _WIN32
        if (address_) UnmapViewOfFile(address_);
        if (mapping_) CloseHandle(mapping_);
        if (file_ != INVALID_HANDLE_VALUE) CloseHandle(file_);
#else
        if (address_) munmap(address_, view_size_);
        if (file_ != -1) close(file_);
#endif
    }
public:
    PrivateWeightFile(const std::string & path, uint64_t first, uint64_t last) {
        try {
#ifdef _WIN32
            const int n = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path.c_str(), -1, nullptr, 0);
            if (n <= 0) throw std::runtime_error("Invalid UTF-8 weight path");
            std::wstring wide(size_t(n), L'\0');
            if (!MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, path.c_str(), -1, wide.data(), n))
                throw std::runtime_error("Cannot convert weight path");
            file_ = CreateFileW(wide.c_str(), GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_DELETE,
                                nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
            LARGE_INTEGER length{};
            if (file_ == INVALID_HANDLE_VALUE || GetFileType(file_) != FILE_TYPE_DISK ||
                !GetFileSizeEx(file_, &length) || length.QuadPart <= 0 ||
                uint64_t(length.QuadPart) > uint64_t(std::numeric_limits<size_t>::max()))
                throw std::runtime_error("Cannot open nonempty regular weight file");
            size_ = size_t(length.QuadPart);
            if (first >= last || last > size_) throw std::runtime_error("CPU weight tensor extends beyond its GGUF");
            SYSTEM_INFO system{}; GetSystemInfo(&system);
            view_offset_ = first - first % system.dwAllocationGranularity;
            view_size_ = size_t(last - view_offset_);
            mapping_ = CreateFileMappingW(file_, nullptr, PAGE_WRITECOPY, 0, 0, nullptr);
            if (mapping_) address_ = MapViewOfFile(mapping_, FILE_MAP_COPY, DWORD(view_offset_ >> 32), DWORD(view_offset_), view_size_);
#else
            file_ = open(path.c_str(), O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
            struct stat st{};
            if (file_ == -1 || fstat(file_, &st) || !S_ISREG(st.st_mode) || st.st_size <= 0 ||
                uint64_t(st.st_size) > uint64_t(std::numeric_limits<size_t>::max()))
                throw std::runtime_error("Cannot open nonempty regular weight file");
            size_ = size_t(st.st_size);
            if (first >= last || last > size_) throw std::runtime_error("CPU weight tensor extends beyond its GGUF");
            const long page_size = sysconf(_SC_PAGESIZE);
            if (page_size <= 0) throw std::runtime_error("Cannot determine weight mapping page size");
            view_offset_ = first - first % uint64_t(page_size);
            view_size_ = size_t(last - view_offset_);
            address_ = mmap(nullptr, view_size_, PROT_READ | PROT_WRITE, MAP_PRIVATE, file_, off_t(view_offset_));
            if (address_ == MAP_FAILED) address_ = nullptr;
#endif
            if (!address_) throw std::runtime_error("Cannot privately map CPU weight file");
        } catch (...) { release(); throw; }
    }
    ~PrivateWeightFile() { release(); }
    PrivateWeightFile(const PrivateWeightFile &) = delete;
    PrivateWeightFile & operator=(const PrivateWeightFile &) = delete;
    void * data() const { return address_; }
    size_t size() const { return size_; }
    size_t view_size() const { return view_size_; }
    uint64_t view_offset() const { return view_offset_; }
};

struct WeightMappingOwner {
    std::vector<std::unique_ptr<PrivateWeightFile>> files;
    WeightMappingStats stats;
    bool registered = false;
    void register_stats() {
        std::lock_guard<std::mutex> guard(mapping_mutex()); auto & s = mapping_totals();
        s.files += stats.files; s.file_bytes += stats.file_bytes;
        s.mapped_bytes += stats.mapped_bytes;
        s.tensors += stats.tensors; s.tensor_bytes += stats.tensor_bytes; registered = true;
    }
    ~WeightMappingOwner() {
        if (!registered) return;
        std::lock_guard<std::mutex> guard(mapping_mutex()); auto & s = mapping_totals();
        s.files -= stats.files; s.file_bytes -= stats.file_bytes;
        s.mapped_bytes -= stats.mapped_bytes;
        s.tensors -= stats.tensors; s.tensor_bytes -= stats.tensor_bytes;
    }
};
inline void free_weight_mapping_owner(ggml_backend_buffer_t buffer) {
    delete static_cast<WeightMappingOwner *>(buffer->context);
}
inline void clear_weight_mapping_owner(ggml_backend_buffer_t, uint8_t) {}
struct WeightBufferDeleter {
    void operator()(ggml_backend_buffer_t p) const { if (p) ggml_backend_buffer_free(p); }
};
using OwnedWeightBuffer = std::unique_ptr<ggml_backend_buffer, WeightBufferDeleter>;

inline ggml_backend_buffer_t map_cpu_weights(const std::vector<WeightSource> & sources) {
    auto owner = std::make_unique<WeightMappingOwner>();
    std::vector<OwnedWeightBuffer> buffers;
    std::vector<ggml_backend_buffer_t> raw;
    std::vector<ggml_tensor *> bound;
    // Validate all bounds before binding any tensor. Offsets remain 64 bit even
    // when one tensor is beyond 4 GiB; no staging allocation reads whole files.
    for (const auto & source : sources) {
        if (source.tensors.empty()) continue;
        uint64_t first = UINT64_MAX, last = 0;
        for (const auto & binding : source.tensors) {
            if (!binding.tensor) throw std::runtime_error("Missing CPU weight tensor");
            const uint64_t n = ggml_nbytes(binding.tensor);
            if (!n || binding.offset > UINT64_MAX - n) throw std::runtime_error("CPU weight tensor offset overflows");
            first = std::min(first, binding.offset); last = std::max(last, binding.offset + n);
        }
        auto file = std::make_unique<PrivateWeightFile>(source.path, first, last);
        for (const auto & binding : source.tensors) {
            if (!binding.tensor || binding.tensor->buffer || binding.tensor->data || binding.tensor->view_src)
                throw std::runtime_error("CPU weight tensor is already bound or is a view");
            const size_t n = ggml_nbytes(binding.tensor);
            if (!n || binding.offset > file->size() || n > file->size() - size_t(binding.offset))
                throw std::runtime_error("CPU weight tensor extends beyond its GGUF");
            for (const auto & previous : sources) {
                if (&previous == &source) break;
                for (const auto & other : previous.tensors)
                    if (other.tensor == binding.tensor) throw std::runtime_error("Duplicate CPU weight binding");
            }
            owner->stats.tensors++; owner->stats.tensor_bytes += n;
        }
        for (size_t a = 0; a < source.tensors.size(); ++a)
            for (size_t b = 0; b < a; ++b)
                if (source.tensors[a].tensor == source.tensors[b].tensor)
                    throw std::runtime_error("Duplicate CPU weight binding");
        owner->stats.files++; owner->stats.file_bytes += file->size();
        owner->stats.mapped_bytes += file->view_size();
        buffers.emplace_back(ggml_backend_cpu_buffer_from_ptr(file->data(), file->view_size()));
        owner->files.emplace_back(std::move(file));
    }
    if (buffers.empty()) throw std::runtime_error("CPU weight mapping has no tensors");
    try {
        size_t index = 0;
        for (const auto & source : sources) {
            if (source.tensors.empty()) continue;
            auto buffer = buffers[index].get(); auto & file = *owner->files[index++];
            ggml_backend_buffer_set_usage(buffer, GGML_BACKEND_BUFFER_USAGE_WEIGHTS);
            for (const auto & binding : source.tensors) {
                // CPU_Mapped alloc_size is the exact tensor byte size. Tensor
                // offsets follow GGUF alignment; only the mapping base needs
                // the CPU buffer alignment, as in llama's GGUF mmap loader.
                const size_t relative = size_t(binding.offset - file.view_offset());
                if (ggml_backend_buffer_get_alloc_size(buffer, binding.tensor) > file.view_size() - relative)
                    throw std::runtime_error("CPU tensor allocation exceeds mapped file");
                bound.push_back(binding.tensor);
                if (ggml_backend_tensor_alloc(buffer, binding.tensor,
                    static_cast<char *>(file.data()) + relative) != GGML_STATUS_SUCCESS)
                    throw std::runtime_error("Cannot bind mapped CPU weight tensor");
            }
        }
        // Keep GGML's original multi-buffer implementation and identity intact.
        // A zero-byte final child owns the mappings and frees them only after
        // every real CPU_Mapped child has been freed by that implementation.
        ggml_backend_buffer_i lifetime{};
        lifetime.free_buffer = free_weight_mapping_owner;
        lifetime.clear = clear_weight_mapping_owner;
        buffers.emplace_back(ggml_backend_buffer_init(ggml_backend_cpu_buffer_type(), lifetime, owner.get(), 0));
        owner->register_stats(); owner.release();
        for (auto & buffer : buffers) raw.push_back(buffer.get());
        auto multi = ggml_backend_multi_buffer_alloc_buffer(raw.data(), raw.size());
        for (auto & buffer : buffers) buffer.release();
        ggml_backend_buffer_set_usage(multi, GGML_BACKEND_BUFFER_USAGE_WEIGHTS);
        return multi;
    } catch (...) {
        for (auto tensor : bound) { tensor->buffer = nullptr; tensor->data = nullptr; }
        throw;
    }
}
} // namespace lma_openmoss

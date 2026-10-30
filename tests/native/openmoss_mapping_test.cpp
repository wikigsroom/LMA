#include "private_weights.hpp"
#include "ggml-alloc.h"
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <winioctl.h>

static int checks = 0;
static void check(bool yes) { if (!yes) throw std::runtime_error("Weight mapping contract failed at " + std::to_string(checks + 1)); ++checks; }
template<class F> static void rejected(F action) {
    bool failed = false; try { action(); } catch (const std::exception &) { failed = true; } check(failed);
}
static void write(const std::string & path, size_t offset, const std::vector<float> & values) {
    std::ofstream out(std::filesystem::u8path(path), std::ios::binary); std::vector<char> pad(offset);
    out.write(pad.data(), pad.size()); out.write(reinterpret_cast<const char *>(values.data()), values.size() * sizeof(float));
    if (!out) throw std::runtime_error("Cannot write owned test file");
}
static std::vector<float> multiply(ggml_context * weights, ggml_tensor * w, ggml_tensor * x, ggml_backend_t backend) {
    auto ctx = ggml_init({ggml_tensor_overhead() * 16 + ggml_graph_overhead(), nullptr, true});
    auto result = ggml_mul_mat(ctx, w, x); auto graph = ggml_new_graph(ctx); ggml_build_forward_expand(graph, result);
    auto alloc = ggml_gallocr_new(ggml_backend_get_default_buffer_type(backend));
    check(ggml_gallocr_alloc_graph(alloc, graph)); check(ggml_backend_graph_compute(backend, graph) == GGML_STATUS_SUCCESS);
    std::vector<float> output(2); ggml_backend_tensor_get(result, output.data(), 0, sizeof(float) * output.size());
    ggml_gallocr_free(alloc); ggml_free(ctx); return output;
}
int wmain(int argc, wchar_t ** argv) {
    try {
        if (argc != 2) throw std::runtime_error("Owned test directory required");
        const auto folder = std::filesystem::absolute(argv[1]);
        if (!std::filesystem::is_directory(folder)) throw std::runtime_error("Test directory must already exist");
        const auto a = (folder / std::filesystem::u8path(u8"权重.bin")).u8string(), b = (folder / "b.bin").u8string();
        const std::vector<float> av{1,2,3,4,5,6,7,8}, bv{2,3,4,5};
        write(a, 32, av); write(b, 64, bv);
        auto backend = ggml_backend_cpu_init(); ggml_backend_cpu_set_n_threads(backend, 1);
        auto ctx = ggml_init({ggml_tensor_overhead() * 8, nullptr, true});
        auto w = ggml_new_tensor_2d(ctx, GGML_TYPE_F32, 4, 2), x = ggml_new_tensor_2d(ctx, GGML_TYPE_F32, 4, 1);
        auto mapped = lma_openmoss::map_cpu_weights({{a,{{w,32}}},{b,{{x,64}}}});
        check(ggml_backend_buffer_is_multi_buffer(mapped));
        check(ggml_backend_buffer_get_usage(w->buffer) == GGML_BACKEND_BUFFER_USAGE_WEIGHTS);
        auto stats = lma_openmoss::weight_mapping_stats(); check(stats.files == 2 && stats.tensors == 2);
        check(stats.tensor_bytes == 48 && stats.file_bytes == 144);
        auto result = multiply(ctx, w, x, backend); check(result == std::vector<float>({40,96}));
        auto heap = ggml_init({ggml_tensor_overhead() * 8, nullptr, true});
        auto hw = ggml_new_tensor_2d(heap, GGML_TYPE_F32, 4, 2), hx = ggml_new_tensor_2d(heap, GGML_TYPE_F32, 4, 1);
        auto uploaded = ggml_backend_alloc_ctx_tensors(heap, backend);
        ggml_backend_tensor_set(hw, av.data(), 0, 32); ggml_backend_tensor_set(hx, bv.data(), 0, 16);
        auto expected = multiply(heap, hw, hx, backend); check(std::memcmp(expected.data(), result.data(), 8) == 0);
        const float private_value = 99; ggml_backend_tensor_set(w, &private_value, 0, 4);
        float read_back = 0; ggml_backend_tensor_get(w, &read_back, 0, 4); check(read_back == 99);
        std::ifstream original(std::filesystem::u8path(a), std::ios::binary); original.seekg(32); original.read(reinterpret_cast<char *>(&read_back), 4); check(read_back == 1); original.close();
        ggml_backend_buffer_free(mapped); ggml_backend_buffer_free(uploaded); ggml_free(heap); ggml_free(ctx);
        stats = lma_openmoss::weight_mapping_stats(); check(stats.files == 0 && stats.tensor_bytes == 0);
        // A tensor can end exactly at EOF, including a GGUF-aligned offset that
        // is not CPU-buffer aligned. Invalid extents must never bind it.
        ctx = ggml_init({ggml_tensor_overhead() * 8, nullptr, true});
        auto tail = ggml_new_tensor_1d(ctx, GGML_TYPE_F32, 1);
        rejected([&]{ lma_openmoss::map_cpu_weights({{a,{{tail,61}}}}); });
        rejected([&]{ lma_openmoss::map_cpu_weights({{a,{{tail,UINT64_MAX}}}}); });
        rejected([&]{ lma_openmoss::map_cpu_weights({{a,{{tail,32},{tail,36}}}}); });
        rejected([&]{ lma_openmoss::map_cpu_weights({{a,{{tail,32}}},{b,{{tail,64}}}}); });
        rejected([&]{ lma_openmoss::map_cpu_weights({{(folder / "missing.bin").u8string(),{{tail,0}}}}); });
        write((folder / "empty.bin").u8string(), 0, {});
        rejected([&]{ lma_openmoss::map_cpu_weights({{(folder / "empty.bin").u8string(),{{tail,0}}}}); });
        check(!tail->data && !tail->buffer && lma_openmoss::weight_mapping_stats().files == 0);
        mapped = lma_openmoss::map_cpu_weights({{a,{{tail,60}}}}); ggml_backend_tensor_get(tail,&read_back,0,4); check(read_back == 8);
        ggml_backend_buffer_free(mapped); tail->buffer=nullptr; tail->data=nullptr;
        // A real sparse >4 GiB file catches offset truncation without allocating
        // four gigabytes of fixture data or storing model weights.
        const auto sparse = folder / "sparse.bin";
        HANDLE file = CreateFileW(sparse.c_str(), GENERIC_READ | GENERIC_WRITE, 0, nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (file == INVALID_HANDLE_VALUE) throw std::runtime_error("Cannot create sparse fixture");
        DWORD transferred = 0; bool sparse_ok = DeviceIoControl(file, FSCTL_SET_SPARSE, nullptr, 0, nullptr, 0, &transferred, nullptr) != 0;
        LARGE_INTEGER offset{}; offset.QuadPart = (1LL << 32) + 32;
        bool wrote = sparse_ok && SetFilePointerEx(file, offset, nullptr, FILE_BEGIN) && WriteFile(file, &private_value, 4, &transferred, nullptr) && transferred == 4;
        CloseHandle(file); check(wrote);
        mapped = lma_openmoss::map_cpu_weights({{sparse.u8string(),{{tail,uint64_t(offset.QuadPart)}}}});
        ggml_backend_tensor_get(tail,&read_back,0,4); check(read_back == 99);
        check(lma_openmoss::weight_mapping_stats().file_bytes == (1ULL << 32) + 36);
        ggml_backend_buffer_free(mapped); ggml_free(ctx); ggml_backend_free(backend);
        check(lma_openmoss::weight_mapping_stats().files == 0);
        std::cout << "{\"passed\":" << checks << ",\"mapped_cpu_graph_bitwise_equal\":true,\"copy_on_write_preserves_file\":true,\"sparse_offset_above_4gib\":true,\"all_mappings_released\":true}\n";
        return 0;
    } catch (const std::exception & error) { std::cerr << error.what() << '\n'; return 1; }
}

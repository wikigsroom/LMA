// SPDX-License-Identifier: Apache-2.0
#include "codec_memory.hpp"
#include "ggml-cpu.h"
#include <cstring>
#include <iostream>
#include <memory>
#include <vector>

namespace {
int checks = 0;
void check(bool value, const char * message) {
    if (!value) throw std::runtime_error(message);
    ++checks;
}
struct Graph {
    ggml_context * context = nullptr;
    ggml_cgraph * graph = nullptr;
    ggml_tensor * input = nullptr;
    ggml_tensor * output = nullptr;
    std::vector<float> values;
    Graph(ggml_tensor * weight, ggml_tensor * bias, int length, ggml_gallocr_t allocator) {
        ggml_init_params params{};
        params.mem_size = 64 * ggml_tensor_overhead() + ggml_graph_overhead();
        params.no_alloc = true;
        context = ggml_init(params);
        if (!context) throw std::runtime_error("Graph metadata allocation failed");
        input = ggml_new_tensor_2d(context, GGML_TYPE_F32, 64, length);
        ggml_set_input(input);
        output = ggml_add(context, ggml_mul_mat(context, weight, input), bias);
        ggml_set_output(output);
        graph = ggml_new_graph(context);
        ggml_build_forward_expand(graph, output);
        if (!ggml_gallocr_alloc_graph(allocator, graph)) throw std::runtime_error("Graph allocation failed");
        values.resize(size_t(64) * length);
        for (size_t i = 0; i < values.size(); ++i) values[i] = (int(i % 17) - 8) * .0625f;
        ggml_backend_tensor_set(input, values.data(), 0, values.size() * sizeof(float));
    }
    ~Graph() { if (context) ggml_free(context); }
    std::vector<float> compute(ggml_backend_t backend, const std::vector<float> & weight, const std::vector<float> & bias) {
        if (ggml_backend_graph_compute(backend, graph) != GGML_STATUS_SUCCESS) throw std::runtime_error("Real CPU graph failed");
        std::vector<float> result(ggml_nelements(output));
        ggml_backend_tensor_get(output, result.data(), 0, result.size() * sizeof(float));
        for (int t = 0; t < output->ne[1]; ++t) for (int out = 0; out < 32; ++out) {
            float expected = bias[out];
            for (int k = 0; k < 64; ++k) expected += weight[out * 64 + k] * values[t * 64 + k];
            if (result[t * 32 + out] != expected) throw std::runtime_error("Matrix output differs from independent exact arithmetic");
        }
        return result;
    }
};
}

int main() {
    try {
        auto backend = ggml_backend_cpu_init();
        if (!backend) throw std::runtime_error("CPU backend missing");
        ggml_backend_cpu_set_n_threads(backend, 2);
        ggml_init_params params{}; params.mem_size = 16 * ggml_tensor_overhead(); params.no_alloc = true;
        auto context = ggml_init(params);
        auto weight = ggml_new_tensor_2d(context, GGML_TYPE_F32, 64, 32);
        auto bias = ggml_new_tensor_1d(context, GGML_TYPE_F32, 32);
        auto buffer = ggml_backend_alloc_ctx_tensors(context, backend);
        if (!buffer) throw std::runtime_error("Persistent parameter allocation failed");
        std::vector<float> weights(64 * 32), biases(32);
        for (size_t i = 0; i < weights.size(); ++i) weights[i] = (int(i % 11) - 5) * .125f;
        for (size_t i = 0; i < biases.size(); ++i) biases[i] = (int(i % 7) - 3) * .25f;
        ggml_backend_tensor_set(weight, weights.data(), 0, weights.size() * sizeof(float));
        ggml_backend_tensor_set(bias, biases.data(), 0, biases.size() * sizeof(float));
        auto batch = ggml_gallocr_new(ggml_backend_get_default_buffer_type(backend));
        auto stream = ggml_gallocr_new(ggml_backend_get_default_buffer_type(backend));
        lma_openmoss::codec_memory_stats = {};
        check(lma_openmoss::codec_memory_stats.releases == 0, "Fresh request stats");
        std::vector<std::vector<float>> outputs;
        {
            Graph streaming(weight, bias, 13, stream);
            auto original_stream = streaming.compute(backend, weights, biases);
            const size_t stream_bytes = ggml_gallocr_get_buffer_size(stream, 0);
            check(stream_bytes > 0, "Real independent stream graph allocation");
            for (int length : {17, 9, 17}) {
                {
                    Graph graph(weight, bias, length, batch);
                    outputs.push_back(graph.compute(backend, weights, biases));
                    check(outputs.back().size() == size_t(length) * 32, "Real graph output with independent arithmetic");
                    check(ggml_gallocr_get_buffer_size(batch, 0) > 0, "Actual batch buffer exists");
                }
                lma_openmoss::release_encoder_scratch(batch, backend);
                check(batch && ggml_gallocr_get_buffer_size(batch, 0) == 0, "Completed batch scratch actually freed");
                check(ggml_gallocr_get_buffer_size(stream, 0) == stream_bytes, "Separate stream buffer preserved");
                check(streaming.compute(backend, weights, biases) == original_stream, "Live stream graph survives batch release");
            }
            check(outputs[0] == outputs[2], "Recreated encoder graph is bitwise identical");
        }
        std::vector<float> after(weights.size());
        ggml_backend_tensor_get(weight, after.data(), 0, after.size() * sizeof(float));
        check(after == weights, "Persistent parameter tensor remains exact");
        auto stats = lma_openmoss::codec_memory_stats;
        check(stats.releases == 3 && stats.released_bytes >= stats.largest_released_buffer && stats.largest_released_buffer > 0,
              "Recorded allocator bytes and release count");
        bool rejected = false;
        ggml_gallocr_t absent = nullptr;
        try { lma_openmoss::release_encoder_scratch(absent, backend); } catch (const std::exception &) { rejected = true; }
        check(rejected && absent == nullptr, "Missing allocator fails locally");
        ggml_gallocr_free(batch); ggml_gallocr_free(stream);
        ggml_backend_buffer_free(buffer); ggml_free(context); ggml_backend_free(backend);
        std::cout << "{\"passed\":" << checks << ",\"actual_cpu_graphs\":7,\"release_count\":" << stats.releases
                  << ",\"released_buffer_bytes\":" << stats.released_bytes
                  << ",\"largest_released_buffer_bytes\":" << stats.largest_released_buffer
                  << ",\"persistent_parameters_unchanged\":true,\"streaming_allocator_preserved\":true,\"model_inference\":false}" << std::endl;
        return 0;
    } catch (const std::exception & error) { std::cerr << error.what() << std::endl; return 1; }
}

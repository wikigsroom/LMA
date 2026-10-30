// SPDX-License-Identifier: MIT
#pragma once
#include "sprint_policy.hpp"
#include "sprint_tokenizer.hpp"
#include <MNN/expr/ExprCreator.hpp>
#include <MNN/expr/Module.hpp>
#include <cv/imgcodecs.hpp>
#include <filesystem>
#include <fstream>
#include <functional>
#include <memory>
#include <random>

namespace lma_mnn::sprint {
using Values = std::vector<float>;
using Event = std::function<void(const std::string&, int, int)>;
struct Feed { const char* name; std::vector<int> shape; const Values* values; };
// Every stage returns owned CPU data before its graph/runtime is destroyed.
inline Values graph(const std::filesystem::path& file, const std::vector<Feed>& inputs,
                    const std::vector<int>& output_shape, int threads, const char* output_name = "out") {
    using namespace MNN; using namespace MNN::Express;
    require(std::filesystem::is_regular_file(file), "Missing Sana-Sprint graph");
    BackendConfig backend; backend.precision = BackendConfig::Precision_Normal; backend.memory = BackendConfig::Memory_Low;
    ScheduleConfig schedule; schedule.type = MNN_FORWARD_CPU; schedule.numThread = threads; schedule.backendConfig = &backend;
    std::shared_ptr<Executor::RuntimeManager> runtime(Executor::RuntimeManager::createRuntimeManager(schedule));
    require(bool(runtime), "Cannot create local Sana-Sprint CPU runtime");
    std::string path = file.u8string();
    if (std::filesystem::is_regular_file(file.u8string()+".weight")) runtime->setExternalFile(path+".weight");
    Module::Config config; config.shapeMutable = false;
    std::vector<std::string> names; for (const auto& feed : inputs) names.push_back(feed.name);
    std::unique_ptr<Module> module(Module::load(names, {output_name}, path.c_str(), runtime, &config));
    require(bool(module), "Cannot load the matched Sana-Sprint graph");
    const auto* info = module->getInfo();
    require(info && info->inputNames == names && info->inputs.size() == inputs.size() && info->outputNames == std::vector<std::string>{output_name}, "Sana-Sprint graph IO names differ");
    std::vector<VARP> feed_values;
    for (size_t i = 0; i < inputs.size(); ++i) {
        const auto& feed = inputs[i]; size_t size = 1;
        for (int dimension : feed.shape) { require(dimension > 0 && size <= 16000000/size_t(dimension), "Sana-Sprint feed exceeds bounds"); size *= dimension; }
        require(info->inputs[i].dim == feed.shape && info->inputs[i].type == halide_type_of<float>() && feed.values && feed.values->size() == size,
                "Sana-Sprint graph input shape/type differs");
        finite(*feed.values); feed_values.push_back(_Const(feed.values->data(), feed.shape, NCHW, halide_type_of<float>()));
    }
    auto output = module->onForward(feed_values);
    require(output.size() == 1 && output[0].get() && output[0]->getInfo(), "Sana-Sprint graph returned no tensor");
    auto converted = _Convert(output[0], NCHW); const auto* shape = converted->getInfo();
    require(shape && shape->dim == output_shape && shape->type == halide_type_of<float>() && shape->size > 0 && shape->size <= 16000000,
            "Sana-Sprint runtime output shape/type differs");
    const float* pointer = converted->readMap<float>(); require(pointer, "Cannot materialize Sana-Sprint output");
    Values result(pointer, pointer+shape->size); finite(result); return result;
}
inline Values embeddings(const std::filesystem::path& file, const std::vector<int>& ids,
                         size_t vocab = vocabulary, size_t width = hidden, float normalization = 48) {
    require(vocab > 0 && vocab <= vocabulary && width > 0 && width <= hidden && !ids.empty() && ids.size() <= sequence && std::isfinite(normalization), "Invalid Sana-Sprint embedding dimensions");
    require(std::filesystem::is_regular_file(file) && std::filesystem::file_size(file) == vocab*width*2, "Sana-Sprint embedding file size differs");
    std::ifstream stream(file, std::ios::binary); require(bool(stream), "Cannot open Sana-Sprint embedding table");
    Values result(ids.size()*width); std::vector<uint16_t> row(width);
    for (size_t i = 0; i < ids.size(); ++i) {
        require(ids[i] >= 0 && size_t(ids[i]) < vocab, "Sana-Sprint embedding ID is out of range");
        stream.seekg(std::streamoff(ids[i])*std::streamoff(width)*2);
        require(bool(stream.read(reinterpret_cast<char*>(row.data()), std::streamsize(width)*2)), "Cannot read selected Sana-Sprint token embedding");
        for (size_t j = 0; j < width; ++j) result[i*width+j] = half(row[j])*normalization;
    }
    finite(result); return result;
}
inline void run(const std::filesystem::path& root, const std::filesystem::path& output,
                const std::string& normalized, int steps, int threads, float guidance, int seed, const Event& event) {
    parameters(1024, 1024, steps, threads, guidance, seed, normalized, "");
    event("tokenizing", 0, 0); Tokenizer tokenizer(root/"tokenizer.model"); Tokens tokens = tokenizer.prompt(normalized);
    event(tokens.truncated ? "input_truncated" : "input_encoded", int(tokens.active), sequence);
    auto features = embeddings(root/"token_emb.bin", tokens.ids), attention = causal_mask(tokens.active);
    for (int i = 0; i < 4; ++i) {
        event("encoding_text", i, 4);
        features = graph(root/("gemma_chunk"+std::to_string(i)+".mnn"),
            {{"hidden_states", {1, sequence, hidden}, &features}, {"attention_mask", {1, 1, sequence, sequence}, &attention}}, {1, sequence, hidden}, threads);
        MNN::Express::Executor::getGlobalExecutor()->gc(MNN::Express::Executor::FULL);
    }
    features = select_features(features); auto text_mask = selected_mask(tokens.active); attention.clear(); attention.shrink_to_fit();
    std::mt19937 random{uint32_t(seed)}; std::normal_distribution<float> normal(0, 1);
    Values latents(32*32*32); for (float& value : latents) value = normal(random)*sigma_data;
    auto times = schedule(steps); Values denoised;
    // Materialize and release each session before moving to another stage.
    for (int i = 0; i < steps; ++i) {
        event("sampling", i, steps); auto input = model_input(latents, times[i]);
        Values time{model_time(times[i])}, condition{guidance*0.1f};
        auto prediction = graph(root/"dit.mnn", {{"hidden_states", {1,32,32,32}, &input}, {"encoder_hidden_states", {1,selected,hidden}, &features},
            {"encoder_attention_mask", {1,selected}, &text_mask}, {"timestep", {1}, &time}, {"guidance", {1}, &condition}}, {1,32,32,32}, threads);
        Values noise(latents.size()); for (float& value : noise) value = normal(random);
        auto next = step(latents, prediction, noise, times[i], times[i+1]); latents = std::move(next.sample); denoised = std::move(next.denoised);
        event("sampling", i+1, steps); MNN::Express::Executor::getGlobalExecutor()->gc(MNN::Express::Executor::FULL);
    }
    features.clear(); features.shrink_to_fit(); event("decoding_image", 0, 0);
    for (float& value : denoised) value /= sigma_data*vae_scale;
    auto decoded = graph(root/"vae_decoder.mnn", {{"latent", {1,32,32,32}, &denoised}}, {1,3,1024,1024}, threads, "image");
    auto rgb = pixels(decoded, 1024, 1024);
    // MNN CV's image writer takes BGR HWC, independently from tensor NCHW.
    for (size_t i = 0; i < rgb.size(); i += 3) std::swap(rgb[i], rgb[i+2]);
    auto image = MNN::Express::_Const(rgb.data(), {1024,1024,3}, MNN::Express::NHWC, halide_type_of<uint8_t>());
    require(MNN::CV::imwrite(output.u8string(), image), "Cannot write Sana-Sprint PNG");
}
}

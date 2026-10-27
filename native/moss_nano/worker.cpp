// MOSS Nano host loop adapted from OpenMOSS/MOSS-TTS-Nano 8b7bcc9341b3,
// Apache-2.0. Model-specific metadata, SentencePiece data and voice codes are
// supplied exclusively through the user-selected verified component workspace.
#include "onnxruntime_cxx_api.h"
#include "sentencepiece_processor.h"
#include "json.hpp"
#include "onnx_external.hpp"
#include <algorithm>
#include <atomic>
#include <cstdarg>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <filesystem>
#include <map>
#include <random>
#include <set>
#include <signal.h>
#include <sys/prctl.h>
#include <unistd.h>

extern "C" int __android_log_print(int, const char*, const char*, ...) { return 0; }
extern "C" int __android_log_vprint(int, const char*, const char*, va_list) { return 0; }
extern "C" int __android_log_write(int, const char*, const char*) { return 0; }
using json = nlohmann::json;
namespace fs = std::filesystem;
static FILE* events = nullptr;
struct Failure : std::runtime_error { using std::runtime_error::runtime_error; };
static void require(bool condition, const char* message) { if (!condition) throw Failure(message); }
static void event(const json& value) {
    std::string bytes = value.dump() + "\n";
    require(bytes.size() <= 16384 && fwrite(bytes.data(), 1, bytes.size(), events) == bytes.size() && !fflush(events), "Host event pipe closed");
}
static std::string read(const fs::path& path, size_t maximum) {
    uintmax_t size = fs::file_size(path); require(size > 0 && size <= maximum, "Model metadata or graph exceeds application size bounds");
    std::string data(size_t(size), '\0'); std::ifstream stream(path, std::ios::binary); stream.read(data.data(), std::streamsize(size));
    require(stream && stream.gcount() == std::streamsize(size), "Cannot read selected model component"); return data;
}
static json metadata(const fs::path& path) { return json::parse(read(path, 2 * 1024 * 1024)); }
static int integer(const json& p, const char* key, int fallback, int low, int high) {
    if (!p.contains(key)) return fallback;
    require(p.at(key).is_number_integer(), "MOSS Nano parameters require integer values");
    int64_t v = p.at(key).get<int64_t>(); require(v >= low && v <= high, "MOSS Nano parameter exceeds application bounds"); return int(v);
}
static std::vector<int32_t> ids(const json& list, size_t maximum, int limit) {
    require(list.is_array() && list.size() <= maximum, "Model token sequence exceeds application bounds"); std::vector<int32_t> values;
    for (const auto& item : list) { require(item.is_number_integer(), "Model token IDs must be integers"); int64_t id = item.get<int64_t>(); require(id >= 0 && id < limit, "Model token ID is outside its vocabulary"); values.push_back(int32_t(id)); }
    return values;
}
static std::vector<std::string> names(const json& value) {
    require(value.is_array() && !value.empty() && value.size() <= 129, "Invalid ONNX metadata names"); std::vector<std::string> result; std::set<std::string> seen;
    for (const auto& item : value) { std::string name = item.get<std::string>(); require(!name.empty() && name.size() <= 100 && seen.insert(name).second, "Invalid or duplicate ONNX metadata name"); result.push_back(name); }
    return result;
}
static Ort::MemoryInfo memory = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
template<class T> static Ort::Value tensor(std::vector<T>& values, std::initializer_list<int64_t> shape) {
    size_t count = 1; for (int64_t d : shape) { require(d > 0 && uint64_t(d) <= 16000000 / count, "Tensor exceeds application bounds"); count *= size_t(d); }
    require(count == values.size(), "Tensor shape and data length disagree");
    return Ort::Value::CreateTensor<T>(memory, values.data(), values.size(), shape.begin(), shape.size());
}
static std::vector<int32_t> intValues(const Ort::Value& value, size_t expected) {
    auto info = value.GetTensorTypeAndShapeInfo(); require(info.GetElementCount() == expected, "Unexpected ONNX integer output length"); std::vector<int32_t> result(expected);
    auto type = info.GetElementType();
    if (type == ONNX_TENSOR_ELEMENT_DATA_TYPE_INT32) { const int32_t* data = value.GetTensorData<int32_t>(); std::copy(data, data + expected, result.begin()); }
    else if (type == ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64) { const int64_t* data = value.GetTensorData<int64_t>(); for (size_t i = 0; i < expected; i++) { require(data[i] >= INT32_MIN && data[i] <= INT32_MAX, "ONNX integer output overflow"); result[i] = int32_t(data[i]); } }
    else if (type == ONNX_TENSOR_ELEMENT_DATA_TYPE_BOOL) { const bool* data = value.GetTensorData<bool>(); for (size_t i = 0; i < expected; i++) result[i] = data[i] ? 1 : 0; }
    else throw Failure("Unexpected ONNX integer output type"); return result;
}
static std::vector<float> hidden(const Ort::Value& value, int width) {
    auto info = value.GetTensorTypeAndShapeInfo(); auto shape = info.GetShape();
    require(info.GetElementType() == ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT && (shape.size() == 2 || shape.size() == 3) && shape[0] == 1 && shape.back() == width, "Unexpected MOSS global hidden tensor");
    require(info.GetElementCount() >= size_t(width) && info.GetElementCount() <= 4096 * size_t(width), "MOSS global hidden tensor exceeds application bounds");
    const float* p = value.GetTensorData<float>() + info.GetElementCount() - width; return {p, p + width};
}
class Session {
    Ort::Session session_{nullptr}; std::vector<std::string> inputs_, outputs_; std::vector<const char*> in_, out_;
public:
    Session(Ort::Env& env, const fs::path& file, Ort::SessionOptions& options, std::vector<std::string> inputs, std::vector<std::string> outputs, const std::map<std::string,uint64_t>& data)
        : inputs_(std::move(inputs)), outputs_(std::move(outputs)) {
        auto model = read(file, 128 * 1024 * 1024); lma_onnx::References references(data); references.validate(model); model.clear(); model.shrink_to_fit();
        session_ = Ort::Session(env, file.c_str(), options); Ort::AllocatorWithDefaultOptions allocator;
        require(session_.GetInputCount() == inputs_.size() && session_.GetOutputCount() == outputs_.size(), "ONNX export does not match this MOSS Nano pipeline");
        std::set<std::string> actualIn, actualOut;
        for (size_t i = 0; i < inputs_.size(); i++) actualIn.insert(session_.GetInputNameAllocated(i, allocator).get());
        for (size_t i = 0; i < outputs_.size(); i++) actualOut.insert(session_.GetOutputNameAllocated(i, allocator).get());
        require(actualIn == std::set<std::string>(inputs_.begin(), inputs_.end()) && actualOut == std::set<std::string>(outputs_.begin(), outputs_.end()), "ONNX input/output names do not match the selected metadata");
        for (auto& s : inputs_) in_.push_back(s.c_str()); for (auto& s : outputs_) out_.push_back(s.c_str());
    }
    std::vector<Ort::Value> run(std::vector<Ort::Value>& inputs) { require(inputs.size() == in_.size(), "Incomplete ONNX input set"); return session_.Run(Ort::RunOptions{nullptr}, in_.data(), inputs.data(), inputs.size(), out_.data(), out_.size()); }
};
static void le(FILE* file, uint32_t value, int n = 4) { for (int i = 0; i < n; i++) require(fputc((value >> (i * 8)) & 255, file) != EOF, "Cannot write WAVE output"); }
static void wave(const fs::path& path, const std::vector<float>& pcm, int sampleRate) {
    FILE* f = fopen(path.c_str(), "wb"); require(f != nullptr, "Cannot create WAVE output");
    try {
        fwrite("RIFF", 1, 4, f); le(f, uint32_t(36 + pcm.size() * 2)); fwrite("WAVEfmt ", 1, 8, f); le(f, 16); le(f, 1, 2); le(f, 1, 2); le(f, sampleRate); le(f, sampleRate * 2); le(f, 2, 2); le(f, 16, 2); fwrite("data", 1, 4, f); le(f, uint32_t(pcm.size() * 2));
        for (float value : pcm) { require(std::isfinite(value), "Codec generated non-finite audio"); int16_t s = int16_t(std::lrint(std::clamp(value, -1.f, 1.f) * 32767.f)); le(f, uint16_t(s), 2); }
        require(!fflush(f) && !fsync(fileno(f)), "Cannot persist WAVE output"); fclose(f);
    } catch (...) { fclose(f); throw; }
}
static void generate(const json& command) {
    require(command.at("schema") == "lma.engine-request/1" && command.at("type") == "speech.synthesize" && command.at("pipeline") == "moss_nano", "Unsupported MOSS Nano worker request");
    const json& p = command.at("parameters");
    for (auto it = p.begin(); it != p.end(); ++it) require(std::set<std::string>{"threads", "speaker", "maxFrames", "maxInputTokens", "seed"}.count(it.key()), "Unsupported MOSS Nano parameter");
    int threads = integer(p, "threads", 2, 1, 16), speaker = integer(p, "speaker", 0, 0, 127), maxFrames = integer(p, "maxFrames", 375, 1, 1500), maxInput = integer(p, "maxInputTokens", 1024, 1, 2048);
    int seed = integer(p, "seed", 1234, 0, INT32_MAX);
    const json& input = command.at("input");
    for (auto it = input.begin(); it != input.end(); ++it) require(it.key() == "prompt" || it.key() == "negativePrompt" && it.value() == "", "MOSS Nano accepts narration text only");
    std::string text = input.at("prompt").get<std::string>(); require(!text.empty() && text.size() <= 16000, "Use nonempty bounded narration text");
    fs::path workspace = fs::canonical(command.at("workspace").get<std::string>()); std::map<std::string,fs::path> components; std::map<std::string,std::map<std::string,uint64_t>> data;
    const std::set<std::string> core = {"manifest", "tts_meta", "codec_meta", "text_tokenizer", "tts_prefill", "tts_decode", "tts_local", "codec_decode"};
    for (auto it = command.at("components").begin(); it != command.at("components").end(); ++it) {
        std::string role = it.key(), group = role.rfind("codec_", 0) == 0 ? "codec" : "tts"; fs::path file = fs::canonical(it.value().get<std::string>());
        require(file.parent_path() == workspace / group && lma_onnx::filename(file.filename().string()), "Component is outside its private execution workspace");
        bool external = role.rfind("tts_data_", 0) == 0 || role.rfind("codec_data_", 0) == 0;
        require(core.count(role) || external, "Unknown MOSS Nano component role"); components.emplace(role, file);
        if (external) { require(file.extension() == ".data" && data[group].emplace(file.filename().string(), fs::file_size(file)).second, "Invalid or duplicate external data component"); }
    }
    for (const auto& role : core) require(components.count(role), "MOSS Nano bundle is incomplete");
    json manifest = metadata(components.at("manifest")), tts = metadata(components.at("tts_meta")), codec = metadata(components.at("codec_meta"));
    const json& cfg = manifest.at("tts_config"); int nvq = integer(cfg, "n_vq", 0, 1, 32); require(nvq > 0, "Missing MOSS quantizer configuration");
    int vocab = integer(tts.at("model_config"), "vocab_size", 0, 1, 10000000), width = integer(tts.at("model_config"), "hidden_size", 0, 1, 8192); require(vocab > 0 && width > 0, "Missing MOSS model dimensions");
    auto books = ids(cfg.at("audio_codebook_sizes"), 32, 65537); require(books.size() == size_t(nvq) && books[0] > 0 && books[0] <= 8192 && std::all_of(books.begin(), books.end(), [&](int x) { return x == books[0]; }), "Unsupported MOSS audio codebook configuration");
    int sampleRate = integer(codec.at("codec_config"), "sample_rate", 0, 8000, 48000); require(sampleRate >= 8000, "Missing codec sample rate");
    auto selected = [&](const json& files, const char* key, const char* role) { std::string value = files.at(key).get<std::string>(); require(lma_onnx::filename(value) && components.at(role).filename() == value, "Selected ONNX graph does not match its metadata"); };
    selected(tts.at("files"), "prefill", "tts_prefill"); selected(tts.at("files"), "decode_step", "tts_decode"); selected(tts.at("files"), "local_fixed_sampled_frame", "tts_local"); selected(codec.at("files"), "decode_full", "codec_decode");
    require(manifest.at("builtin_voices").is_array() && !manifest.at("builtin_voices").empty() && manifest.at("builtin_voices").size() <= 128, "No bounded builtin voice asset was selected");
    require(size_t(speaker) < manifest.at("builtin_voices").size(), "Selected voice exceeds this model's actual voice count");
    event({{"event","stage"},{"stage","text_encoding"}});
    sentencepiece::SentencePieceProcessor tokenizer; require(tokenizer.Load(components.at("text_tokenizer").string()).ok(), "Cannot load the selected SentencePiece model");
    std::vector<int> textIds; require(tokenizer.Encode(text, &textIds).ok() && !textIds.empty() && textIds.size() <= size_t(maxInput), "Narration exceeds the selected token budget or cannot be tokenized");
    for (int token : textIds) require(token >= 0 && token < vocab, "SentencePiece IDs do not match this TTS vocabulary");
    int pad = integer(cfg, "audio_pad_token_id", -1, 0, 65536), userSlot = integer(cfg, "audio_user_slot_token_id", 8, 0, vocab - 1), assistantSlot = integer(cfg, "audio_assistant_slot_token_id", -1, 0, vocab - 1);
    int start = integer(cfg, "audio_start_token_id", -1, 0, vocab - 1), end = integer(cfg, "audio_end_token_id", -1, 0, vocab - 1); require(pad >= 0 && assistantSlot >= 0 && start >= 0 && end >= 0, "Missing audio token configuration");
    std::vector<int32_t> rows; auto row = [&](int id) { rows.push_back(id); for (int q = 0; q < nvq; q++) rows.push_back(pad); };
    auto textRows = [&](const json& list) { for (int id : ids(list, 128, vocab)) row(id); };
    const auto& prompt = manifest.at("prompt_templates"); textRows(prompt.at("user_prompt_prefix_token_ids")); row(start);
    const auto& reference = manifest.at("builtin_voices").at(speaker).at("prompt_audio_codes"); require(reference.is_array() && !reference.empty() && reference.size() <= 1500, "Voice reference exceeds application bounds");
    for (const auto& frame : reference) { auto codes = ids(frame, nvq, books[0]); require(codes.size() == size_t(nvq), "Voice reference and audio codec quantizers disagree"); rows.push_back(userSlot); rows.insert(rows.end(), codes.begin(), codes.end()); }
    row(end); textRows(prompt.at("user_prompt_after_reference_token_ids")); for (int id : textIds) row(id); textRows(prompt.at("assistant_prompt_prefix_token_ids")); row(start);
    int sequence = int(rows.size() / (nvq + 1)); require(sequence > 0 && sequence < 4096, "Combined voice and text prompt exceeds the execution context guard"); maxFrames = std::min(maxFrames, 4096 - sequence);
    std::vector<int32_t> mask(sequence, 1); auto outNames = names(tts.at("onnx").at("decode_output_names")), inNames = names(tts.at("onnx").at("decode_input_names"));
    require(outNames[0] == "global_hidden" && inNames.size() == outNames.size() + 1 && inNames[0] == "input_ids" && inNames[1] == "past_valid_lengths", "Unexpected MOSS KV cache interface");
    std::vector<size_t> cacheIndices;
    for (size_t i = 2; i < inNames.size(); i++) { require(inNames[i].rfind("past_", 0) == 0, "Unexpected MOSS KV cache name"); std::string name = "present_" + inNames[i].substr(5); auto found = std::find(outNames.begin() + 1, outNames.end(), name); require(found != outNames.end(), "Missing corresponding MOSS KV output"); cacheIndices.push_back(size_t(found - outNames.begin())); }
    event({{"event","stage"},{"stage","loading"}});
    Ort::Env env(ORT_LOGGING_LEVEL_FATAL, "lma_moss_nano", [](void*, OrtLoggingLevel, const char*, const char*, const char*, const char*) {}, nullptr);
    Ort::SessionOptions options; options.SetIntraOpNumThreads(threads); options.SetInterOpNumThreads(1); options.SetExecutionMode(ExecutionMode::ORT_SEQUENTIAL); options.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL); options.AddConfigEntry("session.intra_op.allow_spinning", "0");
    require(names(tts.at("onnx").at("prefill_output_names")) == outNames, "MOSS prefill and decode cache interfaces disagree");
    std::vector<int32_t> audioCodes; bool eos = false;
    {
    std::vector<Ort::Value> feeds, state;
    {
        Session prefill(env, components.at("tts_prefill"), options, {"input_ids", "attention_mask"}, outNames, data["tts"]);
        feeds.push_back(tensor(rows, {1, sequence, nvq + 1})); feeds.push_back(tensor(mask, {1, sequence}));
        state = prefill.run(feeds); feeds.clear();
    } // Release prefill graph weights before loading the autoregressive decoder.
    Session decode(env, components.at("tts_decode"), options, inNames, outNames, data["tts"]);
    Session local(env, components.at("tts_local"), options, {"global_hidden", "repetition_seen_mask", "assistant_random_u", "audio_random_u"}, {"should_continue", "frame_token_ids"}, data["tts"]);
    auto global = hidden(state[0], width); std::vector<int32_t> seen(nvq * books[0], 0);
    std::mt19937 random{uint32_t(seed)}; auto uniform = [&]() { return std::clamp(std::generate_canonical<float,24>(random), 0.000001f, 0.999999f); };
    event({{"event","stage"},{"stage","synthesizing"}});
    for (int step = 0; step < maxFrames; step++) {
        std::vector<float> assistantRandom{uniform()}, audioRandom(nvq); for (auto& x : audioRandom) x = uniform();
        feeds.push_back(tensor(global, {1, width})); feeds.push_back(tensor(seen, {1, nvq, books[0]})); feeds.push_back(tensor(assistantRandom, {1})); feeds.push_back(tensor(audioRandom, {1, nvq}));
        auto frameOutput = local.run(feeds); feeds.clear(); if (!intValues(frameOutput[0], 1)[0]) { eos = true; break; }
        auto frame = intValues(frameOutput[1], nvq); std::vector<int32_t> nextRow{int32_t(assistantSlot)}, pastLength{int32_t(sequence + step)};
        for (int q = 0; q < nvq; q++) { require(frame[q] >= 0 && frame[q] < books[q], "Generated audio token is outside the codec vocabulary"); seen[q * books[0] + frame[q]] = 1; nextRow.push_back(frame[q]); audioCodes.push_back(frame[q]); }
        feeds.push_back(tensor(nextRow, {1, 1, nvq + 1})); feeds.push_back(tensor(pastLength, {1})); for (size_t index : cacheIndices) feeds.push_back(std::move(state[index]));
        state = decode.run(feeds); feeds.clear(); global = hidden(state[0], width);
        if (step % 4 == 0) event({{"event","progress"},{"stage","synthesizing"},{"step",step + 1},{"steps",maxFrames}});
    }
    } // Drop TTS sessions and KV caches before loading the waveform codec.
    require(!audioCodes.empty(), "MOSS Nano generated no audio frames"); int frames = int(audioCodes.size() / nvq); std::vector<int32_t> lengths{frames};
    Session codecDecode(env, components.at("codec_decode"), options, {"audio_codes", "audio_code_lengths"}, {"audio", "audio_lengths"}, data["codec"]);
    std::vector<Ort::Value> feeds;
    event({{"event","stage"},{"stage","decoding"}}); feeds.push_back(tensor(audioCodes, {1, frames, nvq})); feeds.push_back(tensor(lengths, {1})); auto decoded = codecDecode.run(feeds);
    auto info = decoded[0].GetTensorTypeAndShapeInfo(); auto shape = info.GetShape(); int length = intValues(decoded[1], 1)[0];
    require(info.GetElementType() == ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT && shape.size() == 3 && shape[0] == 1 && shape[1] >= 1 && shape[1] <= 8 && shape[2] > 0 && length > 0 && length <= sampleRate * 60 && shape[2] >= length && info.GetElementCount() <= size_t(sampleRate) * 60 * 8, "Codec output exceeds supported audio bounds");
    const float* audio = decoded[0].GetTensorData<float>(); std::vector<float> pcm(length, 0);
    for (int64_t channel = 0; channel < shape[1]; channel++) for (int i = 0; i < length; i++) pcm[i] += audio[channel * shape[2] + i] / float(shape[1]);
    wave(command.at("output").get<std::string>(), pcm, sampleRate);
    event({{"event","execution"},{"details",{{"engine","moss_nano_ort"},{"effectiveParameters",p},{"effectiveMaxFrames",maxFrames},{"inputTokens",textIds.size()},{"prefillRows",sequence},{"generatedFrames",frames},{"finishReason",eos ? "stop" : "length"},{"sampleRate",sampleRate},{"channels",1},{"sourceChannels",shape[1]},{"samples",length},{"nativeSource",LMA_MOSS_REVISION}}}});
    event({{"event","complete"},{"output",command.at("output")}});
}
int main(int argc, char** argv) {
    try {
        pid_t parent = getppid(); if (prctl(PR_SET_PDEATHSIG, SIGKILL) || parent == 1 || getppid() != parent) return 1;
        events = fdopen(dup(STDOUT_FILENO), "w"); if (!events) return 1;
        if (!freopen("/dev/null", "w", stdout) || !freopen("/dev/null", "w", stderr)) return 1;
        if (argc == 2 && std::string(argv[1]) == "--info") { event({{"schema","lma.native-worker/1"},{"engine","moss_nano_ort"},{"pipeline","moss_nano"},{"backend","cpu"},{"modelData","user_selected_components"},{"sourceRevision",LMA_MOSS_REVISION},{"onnxruntime",OrtGetApiBase()->GetVersionString()}}); return 0; }
        require(argc == 2, "Supply one private JSON request file"); generate(metadata(argv[1])); return 0;
    } catch (const Failure& failure) { if (events) try { event({{"event","error"},{"message",failure.what()}}); } catch (...) {} }
      catch (...) { if (events) try { event({{"event","error"},{"message","MOSS Nano could not execute the selected components; check matching exports, metadata and local resources"}}); } catch (...) {} }
    return 1;
}

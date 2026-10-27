#pragma once
#include <cstdint>
#include <functional>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>
#include <string_view>

// ONNX protobuf wire traversal, following onnx/onnx v1.19.0 onnx.proto.
// Check every tensor container before ORT can resolve an external data location.
// This validates asset references; ONNX Runtime still validates the model itself.
namespace lma_onnx {
struct Field { uint32_t number; uint8_t wire; uint64_t integer; std::string_view bytes; };
class Reader {
    std::string_view bytes_; size_t offset_ = 0;
    uint64_t varint() {
        uint64_t result = 0;
        for (int shift = 0; shift < 64; shift += 7) {
            if (offset_ == bytes_.size()) throw std::runtime_error("Truncated ONNX protobuf");
            uint8_t byte = static_cast<uint8_t>(bytes_[offset_++]);
            if (shift == 63 && (byte & 254)) throw std::runtime_error("ONNX varint overflow");
            result |= uint64_t(byte & 127) << shift; if (!(byte & 128)) return result;
        }
        throw std::runtime_error("ONNX varint overflow");
    }
public:
    explicit Reader(std::string_view bytes) : bytes_(bytes) {}
    bool next(Field& field) {
        if (offset_ == bytes_.size()) return false;
        uint64_t tag = varint(); if (tag >> 3 == 0 || tag >> 3 > 536870911) throw std::runtime_error("Invalid ONNX protobuf tag");
        field = {uint32_t(tag >> 3), uint8_t(tag & 7), 0, {}};
        if (field.wire == 0) { field.integer = varint(); return true; }
        uint64_t count = field.wire == 2 ? varint() : field.wire == 1 ? 8 : field.wire == 5 ? 4 : std::numeric_limits<uint64_t>::max();
        if (count > bytes_.size() - offset_) throw std::runtime_error("Invalid ONNX protobuf field length");
        field.bytes = bytes_.substr(offset_, size_t(count)); offset_ += size_t(count); return true;
    }
};
inline bool filename(const std::string& value) {
    if (value.empty() || value.size() > 240 || value == "." || value == "..") return false;
    for (unsigned char c : value) if (c < 32 || c == 127 || c == '/' || c == '\\' || c == ':' || c == '\0') return false;
    return true;
}
inline uint64_t decimal(const std::string& text) {
    if (text.empty() || text.size() > 20) throw std::runtime_error("Invalid external tensor range");
    uint64_t result = 0;
    for (char c : text) {
        if (c < '0' || c > '9' || result > (std::numeric_limits<uint64_t>::max() - uint64_t(c - '0')) / 10) throw std::runtime_error("Invalid external tensor range");
        result = result * 10 + uint64_t(c - '0');
    }
    return result;
}
class References {
    const std::map<std::string, uint64_t>& files_;
    size_t fields_ = 0, references_ = 0;
    enum Kind { Model, Graph, Node, Attribute, Tensor, Sparse, Function, Training };
    std::pair<std::string,std::string> entry(std::string_view data) {
        Reader reader(data); Field f; std::string key, value; bool gotKey = false, gotValue = false;
        while (reader.next(f)) {
            if ((f.number == 1 || f.number == 2) && f.wire != 2) throw std::runtime_error("Invalid external tensor metadata");
            if (f.bytes.size() > 4096) throw std::runtime_error("Oversized external tensor metadata");
            if (f.number == 1) { if (gotKey) throw std::runtime_error("Duplicate external tensor key"); key = std::string(f.bytes); gotKey = true; }
            if (f.number == 2) { if (gotValue) throw std::runtime_error("Duplicate external tensor value"); value = std::string(f.bytes); gotValue = true; }
        }
        if (!gotKey || !gotValue) throw std::runtime_error("Incomplete external tensor metadata");
        if (key != "location" && key != "offset" && key != "length" && key != "checksum") throw std::runtime_error("Unsupported external tensor metadata key");
        return {key, value};
    }
    void walk(std::string_view data, Kind kind, unsigned depth) {
        if (depth > 32) throw std::runtime_error("ONNX tensor nesting exceeds application bounds");
        Reader reader(data); Field f; std::map<std::string, std::string> external; bool externalLocation = false;
        while (reader.next(f)) {
            if (++fields_ > 8000000) throw std::runtime_error("ONNX protobuf complexity exceeds application bounds");
            if (kind == Node && f.number == 4 && (f.wire != 2 || f.bytes == "EPContext")) throw std::runtime_error("External execution contexts are not model assets");
            if (kind == Tensor && f.number == 14) { if (f.wire != 0 || f.integer > 1) throw std::runtime_error("Invalid ONNX tensor location"); externalLocation = f.integer == 1; }
            if (kind == Tensor && f.number == 13) {
                if (f.wire != 2 || external.size() >= 8 || !external.insert(entry(f.bytes)).second) throw std::runtime_error("Invalid external tensor metadata");
            }
            Kind nested = Model; bool visit = true;
            if (kind == Model && f.number == 7) nested = Graph;
            else if (kind == Model && f.number == 25) nested = Function;
            else if (kind == Model && f.number == 20) nested = Training;
            else if (kind == Training && (f.number == 1 || f.number == 2)) nested = Graph;
            else if ((kind == Graph && f.number == 1) || (kind == Function && f.number == 7)) nested = Node;
            else if ((kind == Graph && f.number == 5) || (kind == Attribute && (f.number == 5 || f.number == 10)) || (kind == Sparse && (f.number == 1 || f.number == 2))) nested = Tensor;
            else if ((kind == Graph && f.number == 15) || (kind == Attribute && (f.number == 22 || f.number == 23))) nested = Sparse;
            else if ((kind == Node && f.number == 5) || (kind == Function && f.number == 11)) nested = Attribute;
            else if (kind == Attribute && (f.number == 6 || f.number == 11)) nested = Graph;
            else visit = false;
            if (visit) { if (f.wire != 2) throw std::runtime_error("Invalid ONNX tensor container"); walk(f.bytes, nested, depth + 1); }
        }
        if (kind != Tensor || (external.empty() && !externalLocation)) return;
        auto location = external.find("location");
        if (!externalLocation || location == external.end() || !filename(location->second)) throw std::runtime_error("External tensor must use a selected local data file");
        auto file = files_.find(location->second);
        if (file == files_.end()) throw std::runtime_error("External tensor data was not selected in this bundle");
        uint64_t start = external.count("offset") ? decimal(external.at("offset")) : 0;
        if (start > file->second) throw std::runtime_error("External tensor exceeds its verified data file");
        uint64_t length = external.count("length") ? decimal(external.at("length")) : file->second - start;
        if (length > file->second - start) throw std::runtime_error("External tensor exceeds its verified data file");
        ++references_;
    }
public:
    explicit References(const std::map<std::string,uint64_t>& files) : files_(files) {}
    size_t validate(std::string_view model) { walk(model, Model, 0); return references_; }
};
}

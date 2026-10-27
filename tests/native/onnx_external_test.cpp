#include "../../native/moss_nano/onnx_external.hpp"
#include <iostream>
#include <vector>
using namespace lma_onnx;
static int passed = 0;
static std::string var(uint64_t n) { std::string s; do { s.push_back(char((n & 127) | (n > 127 ? 128 : 0))); n >>= 7; } while (n); return s; }
static std::string bytes(int f, const std::string& s) { return var(uint64_t(f) * 8 + 2) + var(s.size()) + s; }
static std::string number(int f, uint64_t n) { return var(uint64_t(f) * 8) + var(n); }
static std::string entry(const std::string& k, const std::string& v) { return bytes(13, bytes(1,k) + bytes(2,v)); }
static std::string tensor(const std::string& location) { return entry("location",location) + number(14,1); }
static std::string graph(const std::string& t) { return bytes(7,bytes(5,t)); }
static void check(bool v) { if (!v) throw std::runtime_error("Native external-data contract failed"); ++passed; }
static size_t validate(const std::string& m) { const std::map<std::string,uint64_t> files{{"weights.data",64}}; References refs(files); return refs.validate(m); }
static void reject(const std::string& s) { try { validate(s); } catch (const std::exception&) { ++passed; return; } throw std::runtime_error("An invalid model reference was accepted"); }
int main() {
    try {
        std::string t = tensor("weights.data");
        check(validate(graph(t)) == 1);
        check(validate(graph(t + entry("offset","32"))) == 1); // missing length means remaining bytes
        check(validate(graph(t + entry("offset","32") + entry("length","32"))) == 1);
        check(validate(graph(t + entry("offset","64") + entry("length","0"))) == 1);
        check(validate(graph(t + entry("checksum","documented-checksum"))) == 1);
        for (int attr : {5,10}) check(validate(bytes(7,bytes(1,bytes(5,bytes(attr,t))))) == 1);
        for (int attr : {6,11}) check(validate(bytes(7,bytes(1,bytes(5,bytes(attr,bytes(5,t)))))) == 1);
        for (int attr : {22,23}) for (int field : {1,2}) check(validate(bytes(7,bytes(1,bytes(5,bytes(attr,bytes(field,t)))))) == 1);
        for (int field : {1,2}) check(validate(bytes(7,bytes(15,bytes(field,t)))) == 1);
        check(validate(bytes(25,bytes(7,bytes(5,bytes(5,t))))) == 1);
        check(validate(bytes(25,bytes(11,bytes(5,t)))) == 1);
        for (int field : {1,2}) check(validate(bytes(20,bytes(field,bytes(5,t)))) == 1);
        check(validate(graph(bytes(9,tensor("not-selected.data")))) == 0); // raw tensor bytes are not a protobuf container
        reject(graph(tensor("other.data")));
        for (const auto& name : {"../weights.data","/weights.data","a/weights.data","a\\weights.data","C:weights.data",".","..",""}) reject(graph(tensor(name)));
        reject(graph(t + entry("basepath","elsewhere")));
        reject(graph(t + entry("offset","65")));
        reject(graph(t + entry("offset","32") + entry("length","33")));
        for (const auto& n : {"-1","1x","18446744073709551616",""}) reject(graph(t + entry("offset",n)));
        reject(graph(t + entry("location","weights.data")));
        reject(graph(entry("location","weights.data")));
        reject(graph(number(14,1)));
        reject(graph(t + number(14,2)));
        reject(bytes(7,bytes(1,bytes(4,"EPContext"))));
        reject(bytes(7,number(5,1)));
        reject(graph(t).substr(0,graph(t).size()-1));
        reject(std::string(11,char(255)));
        reject(std::string(1,char(7)));
        std::string nested = bytes(5,t);
        for (int i = 0; i < 12; ++i) nested = bytes(1,bytes(5,bytes(6,nested)));
        reject(bytes(7,nested));
        const std::map<std::string,uint64_t> none; References empty(none);
        bool unavailable = false; try { empty.validate(graph(t)); } catch (...) { unavailable = true; } check(unavailable);
        std::cout << "{\"passed\":" << passed << ",\"native_host_execution\":true,\"model_inference\":false}" << std::endl;
    } catch (const std::exception& e) { std::cerr << e.what() << std::endl; return 1; }
}

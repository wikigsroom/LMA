// SPDX-License-Identifier: MIT
#include "encoder.hpp"
#include "json.hpp"
#include <cmath>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <limits>
#include <set>
#ifdef _WIN32
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#else
#include <fcntl.h>
#include <unistd.h>
#endif
using namespace lma::ltx098::text;
using Json=nlohmann::json;
namespace {
void keys(const Json& j,const std::set<std::string>& allowed) {
    require(j.is_object(),"Expected a JSON object");
    for(auto it=j.begin();it!=j.end();++it) require(allowed.count(it.key())!=0,"Unknown request key");
}
int integer(const Json& j,int low,int high) { require(j.is_number_integer(),"Expected an integer"); auto n=j.get<int64_t>(); require(n>=low && n<=high,"Integer outside supported range"); return static_cast<int>(n); }
Json parse_unique(std::istream& stream) {
    std::vector<std::set<std::string>> object_keys;
    auto callback=[&](int,Json::parse_event_t event,Json& value) {
        if(event==Json::parse_event_t::object_start) object_keys.emplace_back();
        else if(event==Json::parse_event_t::key) require(!object_keys.empty() && object_keys.back().insert(value.get<std::string>()).second,"Duplicate JSON object key");
        else if(event==Json::parse_event_t::object_end) {require(!object_keys.empty(),"Invalid JSON object nesting");object_keys.pop_back();}
        return true;
    };
    return Json::parse(stream,callback);
}
void exclusive_write(const std::filesystem::path& path,const std::vector<unsigned char>& data,Cancel cancel) {
    require(!cancel(),"T5 execution cancelled before writing");
#ifdef _WIN32
    auto handle=CreateFileW(path.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
    require(handle!=INVALID_HANDLE_VALUE,"Output already exists or cannot be created");
    DWORD written=0; bool ok=WriteFile(handle,data.data(),static_cast<DWORD>(data.size()),&written,nullptr)!=0 && written==data.size();
    ok=FlushFileBuffers(handle)!=0 && ok; CloseHandle(handle);
#else
    int handle=::open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL,0600); require(handle>=0,"Output already exists or cannot be created");
    size_t done=0; bool ok=true;
    while(done<data.size()) { auto n=::write(handle,data.data()+done,data.size()-done); if(n<=0) {ok=false;break;} done+=static_cast<size_t>(n); }
    ok=::fsync(handle)==0 && ok; ::close(handle);
#endif
    if(!ok || cancel()) { std::filesystem::remove(path); throw std::runtime_error("T5 output write failed or was cancelled"); }
}
template<class T> void append(std::vector<unsigned char>& output,const std::vector<T>& values) {
    const auto* bytes=reinterpret_cast<const unsigned char*>(values.data()); output.insert(output.end(),bytes,bytes+values.size()*sizeof(T));
}
int run(const std::vector<std::string>& args) {
    try {
        const bool pixart=args.size()>=7 && args[6]=="--pixart";
        const bool fixture=(args.size()==7 && args[6]=="--fixture") || (args.size()==9 && pixart && args[8]=="--fixture");
        require(args.size()==6 || (args.size()==7 && fixture) || (pixart && (args.size()==8 || (args.size()==9 && fixture))),"Usage: lma_ltx098_text MODEL TOKENIZER_CONFIG REQUEST OUTPUT THREADS [--pixart SPIECE] [--fixture]");
        size_t used=0; auto threads=std::stoi(args[5],&used); require(used==args[5].size() && threads>=1 && threads<=32,"Invalid thread count");
        auto tokenizer_file=std::filesystem::u8path(args[2]);require(std::filesystem::is_regular_file(tokenizer_file) && std::filesystem::file_size(tokenizer_file)<=32768,"Missing/oversized external tokenizer config");
        std::ifstream tokenizer_stream(tokenizer_file,std::ios::binary);auto tokenizer=parse_unique(tokenizer_stream);
        require(tokenizer.is_object() && tokenizer.contains("extra_ids") && tokenizer["extra_ids"].is_number_integer() && tokenizer["extra_ids"]==100 && tokenizer.value("eos_token",std::string())=="</s>" && tokenizer.value("pad_token",std::string())=="<pad>" && tokenizer.value("unk_token",std::string())=="<unk>","Unexpected external T5 tokenizer configuration");
        require(tokenizer.contains("additional_special_tokens") && tokenizer["additional_special_tokens"].is_array(),"Missing T5 sentinel definitions");
        auto file=std::filesystem::u8path(args[3]); require(std::filesystem::is_regular_file(file) && std::filesystem::file_size(file)<=300000,"Invalid request file");
        std::ifstream stream(file,std::ios::binary);Json request=parse_unique(stream);keys(request,{"operation","inputs","max_tokens","cancel_file"});
        require(request.contains("operation") && request["operation"].is_string(),"Missing T5 operation"); auto operation=request["operation"].get<std::string>();
        require(operation=="tokenize" || operation=="encode","Unknown T5 operation");
        Options options; options.threads=threads; options.fixture=fixture; options.vocabulary_only=operation=="tokenize";options.pixart=pixart;
        if(pixart) options.tokenizer_model=std::filesystem::u8path(args[7]);
        options.additional_special_tokens=tokenizer["additional_special_tokens"].get<std::vector<std::string>>();
        if(request.contains("max_tokens")) options.max_tokens=integer(request["max_tokens"],1,256);
        require(request.contains("inputs") && request["inputs"].is_array() && !request["inputs"].empty() && request["inputs"].size()<=4,"Expected one to four T5 inputs");
        // Validate every input before any neural allocation or output creation.
        for(const auto& input:request["inputs"]) {
            keys(input,{"prompt","tokens"}); require(input.size()==1,"Each input needs exactly one prompt or token list");
            if(input.contains("prompt")) require(input["prompt"].is_string() && input["prompt"].get_ref<const std::string&>().size()<=65536,"Invalid prompt");
            else {
                require(input["tokens"].is_array() && !input["tokens"].empty() && input["tokens"].size()<=static_cast<size_t>(options.max_tokens),"Invalid input token list");
                for(const auto& id:input["tokens"]) integer(id,0,32127);
            }
        }
        std::filesystem::path cancel_file;
        if(request.contains("cancel_file")) { require(request["cancel_file"].is_string(),"Invalid cancel file"); cancel_file=std::filesystem::u8path(request["cancel_file"].get<std::string>()); require(!cancel_file.empty(),"Empty cancel file"); }
        Cancel cancel=[&]{ return !cancel_file.empty() && std::filesystem::exists(cancel_file); };
        auto output=std::filesystem::u8path(args[4]); require(!std::filesystem::exists(output),"Output already exists");
        std::vector<unsigned char> data; Json items=Json::array(); Stats stats; Layout layout; Buffers buffers;
        {
            Model model(std::filesystem::u8path(args[1]),options,stats,cancel,[](const char* stage,int done,int total){std::cerr<<Json{{"stage",stage},{"done",done},{"total",total}}.dump()<<std::endl;});
            layout=model.layout();
            for(const auto& input:request["inputs"]) {
                Tokenized tokens;
                if(input.contains("prompt")) tokens=model.tokenize(input["prompt"].get<std::string>());
                else tokens.ids=input["tokens"].get<Tokens>();
                Json item={{"tokens",tokens.ids},{"mask",std::vector<int>(tokens.ids.size(),1)},{"truncated",tokens.truncated},{"offset_bytes",data.size()}};
                if(operation=="encode") { auto values=model.encode(tokens.ids); append(data,values); item["shape"]={1,tokens.ids.size(),layout.width}; }
                else append(data,tokens.ids);
                item["bytes"]=data.size()-item["offset_bytes"].get<size_t>(); items.push_back(item);
            }
            buffers=model.buffers();
        }
        exclusive_write(output,data,cancel);
        std::cout<<Json{{"schema","lma.ltx098-text/1"},{"operation",operation},{"backend","cpu"},{"encoder_implementation","independent_ggml_f32_compute"},{"weight_execution",pixart?"mapped_original_f32":"streamed_f32_matrix_casts"},{"pooling","none"},{"normalization","raw_final_rms_norm"},
            {"buffers",{{"mapped_file_bytes",buffers.mapped_file_bytes},{"tensor_bytes",buffers.tensor_bytes},{"peak_compute_bytes",buffers.peak_compute_bytes}}},
            {"width",layout.width},{"layers",layout.layers},{"items",items},{"bytes",data.size()},{"vocabulary_loads",stats.vocabulary_loads},{"vocabulary_unloads",stats.vocabulary_unloads},
            {"model_loads",stats.model_loads},{"model_unloads",stats.model_unloads},{"encode_calls",stats.encode_calls},{"aborted_encodes",stats.aborted_encodes},
            {"model_inference",operation=="encode"},{"text_variant",pixart?"pixart_original_f32":"google_community_t5_q5"},{"fixture",options.fixture},{"engine_registered",false},{"complete_video",false},{"physical_android",false}}.dump()<<std::endl;
        return 0;
    } catch(const std::exception& e) { std::cerr<<Json{{"error",e.what()}}.dump(-1,' ',false,Json::error_handler_t::replace)<<std::endl; return 2; }
}
}
#ifdef _WIN32
int wmain(int argc,wchar_t** argv) {
    std::vector<std::string> args;
    for(int i=0;i<argc;++i) { int n=WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,argv[i],-1,nullptr,0,nullptr,nullptr); if(n<=0) return 2; std::string value(static_cast<size_t>(n),0); WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,argv[i],-1,value.data(),n,nullptr,nullptr); value.pop_back(); args.push_back(std::move(value)); }
    return run(args);
}
#else
int main(int argc,char** argv) { return run(std::vector<std::string>(argv,argv+argc)); }
#endif

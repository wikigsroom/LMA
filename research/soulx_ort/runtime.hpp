// SPDX-License-Identifier: MIT
// Shared CPU-only ORT session policy for the unregistered SoulX research modules.
#pragma once
#ifndef ORT_API_MANUAL_INIT
#define ORT_API_MANUAL_INIT
#endif
#include "onnxruntime_cxx_api.h"
#include "types.hpp"
#include "../../native/moss_nano/onnx_external.hpp"
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <condition_variable>
#include <cstring>
#include <fstream>
#include <map>
#include <mutex>
#include <stdexcept>
#include <thread>

namespace lma::soulx::ort {
inline void require(bool ok,const char* message) { if(!ok) throw std::invalid_argument(message); }
inline void stop(const Cancel& cancelled) { if(cancelled && cancelled()) throw std::runtime_error("SoulX graph execution cancelled"); }
inline void finite(const Samples& x) { for(float v:x) require(std::isfinite(v),"Non-finite SoulX acoustic tensor"); }
inline void initialize() {
    static const bool initialized=[] {
        // Only API<=17 methods are used. This is also exercised on host ORT1.24;
        // Android links the existing pinned ORT1.28.2 runtime, never host DLLs.
        const OrtApi* api=OrtGetApiBase()->GetApi(17);
        if(!api) throw std::runtime_error("ONNX Runtime C API17 is unavailable");
        Ort::InitApi(api); return true;
    }(); (void)initialized;
}
inline std::string bytes(const std::filesystem::path& path,size_t maximum) {
    auto n=std::filesystem::file_size(path);require(n && n<=maximum,"Missing/oversized SoulX model asset");
    std::string result(static_cast<size_t>(n),'\0');std::ifstream stream(path,std::ios::binary);
    if(!stream.read(result.data(),static_cast<std::streamsize>(n)))throw std::runtime_error("Cannot read SoulX model asset");return result;
}
struct Field { const char* name; ONNXTensorElementDataType type; std::vector<int64_t> shape; };
const auto f32=ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT;
const auto i64=ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64;
const auto i32=ONNX_TENSOR_ELEMENT_DATA_TYPE_INT32;
class Graph {
    Ort::Session session_{nullptr}; OrtStats& stats_;
    std::vector<Field> inputs_,outputs_;
    std::vector<const char*> input_names_,output_names_;
    void signature(bool output,const std::vector<Field>& expected) {
        require((output?session_.GetOutputCount():session_.GetInputCount())==expected.size(),"Wrong SoulX graph IO count");
        Ort::AllocatorWithDefaultOptions allocator;
        for(size_t i=0;i<expected.size();++i) {
            auto name=output?session_.GetOutputNameAllocated(i,allocator):session_.GetInputNameAllocated(i,allocator);
            require(name && std::string(name.get())==expected[i].name,"Wrong SoulX graph IO name/order");
            auto info=output?session_.GetOutputTypeInfo(i):session_.GetInputTypeInfo(i);
            require(info.GetONNXType()==ONNX_TYPE_TENSOR,"SoulX graph IO must be a tensor");
            auto tensor=info.GetTensorTypeAndShapeInfo();auto shape=tensor.GetShape();
            require(tensor.GetElementType()==expected[i].type && shape.size()==expected[i].shape.size(),"Wrong SoulX graph IO dtype/rank");
            for(size_t j=0;j<shape.size();++j) {
                int64_t wanted=expected[i].shape[j];
                if(wanted<0) require(shape[j]<0,"SoulX time axis must be dynamic");
                else require(shape[j]<0 || shape[j]==wanted,"Wrong SoulX graph static dimension");
            }
        }
    }
public:
    Graph(Ort::Env& env,const std::filesystem::path& directory,const char* filename,int threads,OrtStats& stats,
          std::vector<Field> inputs,std::vector<Field> outputs) : stats_(stats),inputs_(std::move(inputs)),outputs_(std::move(outputs)) {
        require(stats_.session_loads==stats_.session_unloads,"SoulX graphs must load sequentially");
        auto path=directory/filename;auto data=bytes(path,128*1024*1024);
        std::map<std::string,uint64_t> allowed; std::string sidecar=std::string(filename)+".data";
        if(std::filesystem::is_regular_file(directory/sidecar)) allowed[sidecar]=std::filesystem::file_size(directory/sidecar);
        lma_onnx::References(allowed).validate(data);
        Ort::SessionOptions options;options.SetIntraOpNumThreads(threads);options.SetInterOpNumThreads(1);
        options.SetExecutionMode(ExecutionMode::ORT_SEQUENTIAL);options.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_BASIC);
        options.DisableCpuMemArena();options.DisableMemPattern();options.SetLogSeverityLevel(ORT_LOGGING_LEVEL_FATAL);
        session_=Ort::Session(env,path.c_str(),options);signature(false,inputs_);signature(true,outputs_);
        ++stats_.session_loads;stats_.max_live_sessions=std::max(stats_.max_live_sessions,stats_.session_loads-stats_.session_unloads);
        for(const auto& field:inputs_)input_names_.push_back(field.name);
        for(const auto& field:outputs_)output_names_.push_back(field.name);
    }
    ~Graph() { session_=Ort::Session(nullptr);++stats_.session_unloads; }
    Graph(const Graph&)=delete;Graph& operator=(const Graph&)=delete;
    std::vector<Ort::Value> run(const std::vector<Ort::Value>& input,const Cancel& cancelled) {
        stop(cancelled);require(input.size()==inputs_.size(),"Invalid SoulX graph feed count");
        Ort::RunOptions options;std::mutex mutex;std::condition_variable changed;bool finished=false;
        std::atomic<bool> terminated{false};std::thread monitor;
        if(cancelled) monitor=std::thread([&] {
            std::unique_lock<std::mutex> lock(mutex);
            while(!changed.wait_for(lock,std::chrono::milliseconds(10),[&]{return finished;})) {
                bool cancel=false;try{cancel=cancelled();}catch(...){cancel=true;}
                if(cancel){terminated=true;try{options.SetTerminate();}catch(...){}break;}
            }
        });
        auto join=[&]{ {std::lock_guard<std::mutex> lock(mutex);finished=true;}changed.notify_one();if(monitor.joinable())monitor.join(); };
        try {
            auto result=session_.Run(options,input_names_.data(),input.data(),input.size(),output_names_.data(),output_names_.size());
            join();if(terminated)throw std::runtime_error("SoulX graph execution cancelled");stop(cancelled);++stats_.graph_runs;return result;
        } catch(const Ort::Exception& error) {
            join();
            if(terminated) {
                if(std::string(error.what()).find("terminate")!=std::string::npos)++stats_.terminated_runs;
                throw std::runtime_error("SoulX graph execution cancelled");
            }
            throw;
        } catch(...) { join();if(terminated)throw std::runtime_error("SoulX graph execution cancelled");throw; }
    }
};
inline Ort::Value floats(Samples& data,std::vector<int64_t> shape) {
    auto memory=Ort::MemoryInfo::CreateCpu(OrtArenaAllocator,OrtMemTypeDefault);
    return Ort::Value::CreateTensor<float>(memory,data.data(),data.size(),shape.data(),shape.size());
}
inline Ort::Value integers(std::vector<int64_t>& data,std::vector<int64_t> shape) {
    auto memory=Ort::MemoryInfo::CreateCpu(OrtArenaAllocator,OrtMemTypeDefault);
    return Ort::Value::CreateTensor<int64_t>(memory,data.data(),data.size(),shape.data(),shape.size());
}
inline Ort::Value int32s(std::vector<int32_t>& data,std::vector<int64_t> shape) {
    auto memory=Ort::MemoryInfo::CreateCpu(OrtArenaAllocator,OrtMemTypeDefault);
    return Ort::Value::CreateTensor<int32_t>(memory,data.data(),data.size(),shape.data(),shape.size());
}
inline Samples output(Ort::Value& value,std::vector<int64_t> shape) {
    require(value.IsTensor(),"SoulX graph output is not a tensor");auto info=value.GetTensorTypeAndShapeInfo();
    require(info.GetElementType()==f32 && info.GetShape()==shape,"Wrong SoulX runtime output shape/type");
    size_t count=1;for(auto dim:shape){require(dim>0 && static_cast<size_t>(dim)<=32000000/count,"SoulX output size exceeds bounds");count*=static_cast<size_t>(dim);}
    require(info.GetElementCount()==count,"Invalid SoulX tensor size");
    // GetTensorData was added after API17; the original mutable-data accessor
    // is ABI-compatible with the deliberately selected older API table.
    const float* data=value.GetTensorMutableData<float>();Samples result(data,data+count);finite(result);return result;
}
}

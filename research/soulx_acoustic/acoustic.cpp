// SPDX-License-Identifier: MIT
// Native ORT orchestration of the complete exported SoulX acoustic networks.
#define ORT_API_MANUAL_INIT
#include "onnxruntime_cxx_api.h"
#include "acoustic.hpp"
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
#include <random>
#include <stdexcept>
#include <thread>

namespace lma::soulx {
namespace {
void require(bool ok,const char* message) { if(!ok) throw std::invalid_argument(message); }
void stop(const Cancel& cancelled) { if(cancelled && cancelled()) throw std::runtime_error("SoulX acoustic cancelled"); }
void finite(const Samples& x) { for(float v:x) require(std::isfinite(v),"Non-finite SoulX acoustic tensor"); }
void initialize() {
    static const bool initialized=[] {
        // Only API<=17 methods are used. This is also exercised on host ORT1.24;
        // Android links the existing pinned ORT1.28.2 runtime, never host DLLs.
        const OrtApi* api=OrtGetApiBase()->GetApi(17);
        if(!api) throw std::runtime_error("ONNX Runtime C API17 is unavailable");
        Ort::InitApi(api); return true;
    }(); (void)initialized;
}
std::string bytes(const std::filesystem::path& path,size_t maximum) {
    auto n=std::filesystem::file_size(path);require(n && n<=maximum,"Missing/oversized SoulX acoustic asset");
    std::string result(static_cast<size_t>(n),'\0');std::ifstream stream(path,std::ios::binary);
    if(!stream.read(result.data(),static_cast<std::streamsize>(n)))throw std::runtime_error("Cannot read SoulX acoustic asset");return result;
}
struct Field { const char* name; ONNXTensorElementDataType type; std::vector<int64_t> shape; };
const auto f32=ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT;
const auto i64=ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64;
class Graph {
    Ort::Session session_{nullptr}; AcousticStats& stats_;
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
    Graph(Ort::Env& env,const AcousticModels& models,const char* filename,int threads,AcousticStats& stats,
          std::vector<Field> inputs,std::vector<Field> outputs) : stats_(stats),inputs_(std::move(inputs)),outputs_(std::move(outputs)) {
        auto path=models.directory/filename;auto data=bytes(path,128*1024*1024);
        std::map<std::string,uint64_t> allowed; std::string sidecar=std::string(filename)+".data";
        if(std::filesystem::is_regular_file(models.directory/sidecar)) allowed[sidecar]=std::filesystem::file_size(models.directory/sidecar);
        lma_onnx::References(allowed).validate(data);
        Ort::SessionOptions options;options.SetIntraOpNumThreads(threads);options.SetInterOpNumThreads(1);
        options.SetExecutionMode(ExecutionMode::ORT_SEQUENTIAL);options.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_BASIC);
        options.DisableCpuMemArena();options.DisableMemPattern();options.SetLogSeverityLevel(ORT_LOGGING_LEVEL_FATAL);
        session_=Ort::Session(env,path.c_str(),options);signature(false,inputs_);signature(true,outputs_);
        require(stats_.session_loads==stats_.session_unloads,"SoulX acoustic graphs must load sequentially");
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
            join();if(terminated)throw std::runtime_error("SoulX acoustic cancelled");stop(cancelled);++stats_.graph_runs;return result;
        } catch(const Ort::Exception& error) {
            join();
            if(terminated) {
                if(std::string(error.what()).find("terminate")!=std::string::npos)++stats_.terminated_runs;
                throw std::runtime_error("SoulX acoustic cancelled");
            }
            throw;
        } catch(...) { join();if(terminated)throw std::runtime_error("SoulX acoustic cancelled");throw; }
    }
};
Ort::Value floats(Samples& data,std::vector<int64_t> shape) {
    auto memory=Ort::MemoryInfo::CreateCpu(OrtArenaAllocator,OrtMemTypeDefault);
    return Ort::Value::CreateTensor<float>(memory,data.data(),data.size(),shape.data(),shape.size());
}
Ort::Value integers(std::vector<int64_t>& data,std::vector<int64_t> shape) {
    auto memory=Ort::MemoryInfo::CreateCpu(OrtArenaAllocator,OrtMemTypeDefault);
    return Ort::Value::CreateTensor<int64_t>(memory,data.data(),data.size(),shape.data(),shape.size());
}
Samples output(Ort::Value& value,std::vector<int64_t> shape) {
    require(value.IsTensor(),"SoulX graph output is not a tensor");auto info=value.GetTensorTypeAndShapeInfo();
    require(info.GetElementType()==f32 && info.GetShape()==shape,"Wrong SoulX runtime output shape/type");
    size_t count=1;for(auto dim:shape){require(dim>0 && static_cast<size_t>(dim)<=32000000/count,"SoulX output size exceeds bounds");count*=static_cast<size_t>(dim);}
    require(info.GetElementCount()==count,"Invalid SoulX tensor size");
    // GetTensorData was added after API17; the original mutable-data accessor
    // is ABI-compatible with the deliberately selected older API table.
    const float* data=value.GetTensorMutableData<float>();Samples result(data,data+count);finite(result);return result;
}
}

Samples synthesize_acoustic(const AcousticModels& models,const AcousticInput& input,const AcousticParams& params,
        AcousticStats& stats,Cancel cancelled,Progress progress,Noise noise,Trace trace) {
    stats={};
    require(params.steps>=1 && params.steps<=100 && params.threads>=1 && params.threads<=32 &&
            std::isfinite(params.cfg) && params.cfg>=0 && params.cfg<=10 && params.seed>=-1 && params.seed<=2147483647,"Invalid SoulX acoustic parameters");
    require(input.prompt_tokens>=1 && input.prompt_tokens<=375 && input.tokens.size()>input.prompt_tokens &&
            input.tokens.size()<=input.prompt_tokens+3000,"Invalid SoulX reference/generated token count");
    for(auto token:input.tokens)require(token>=0 && token<6561,"Invalid SoulX semantic code");
    require(input.speaker.size()==192 && input.prompt_mel.rows==80 && input.prompt_mel.cols==input.prompt_tokens*2 &&
            input.prompt_mel.values.size()==80*input.prompt_mel.cols,"Invalid SoulX speaker/reference mel layout");
    finite(input.speaker);finite(input.prompt_mel.values);stop(cancelled);
    size_t frames=input.tokens.size()*2;require(frames<=kMaxFlowFrames,"SoulX Flow frame count exceeds bounds");
    int64_t F=static_cast<int64_t>(frames),N=static_cast<int64_t>(input.tokens.size());
    initialize();stats.runtime_version=OrtGetApiBase()->GetVersionString();Ort::Env env(ORT_LOGGING_LEVEL_FATAL,"lma-soulx-acoustic");
    std::mt19937 rng(params.seed<0?std::random_device{}():static_cast<uint32_t>(params.seed));std::normal_distribution<float> gaussian;
    if(!noise)noise=[&]{return gaussian(rng);};
    auto normal=[&]{float value=noise();require(std::isfinite(value),"Non-finite SoulX acoustic noise");return value;};
    auto event=[&](const char* stage,int done,int total){stop(cancelled);if(progress)progress(stage,done,total);stop(cancelled);};
    Samples mu,spks;
    {
        event("flow_encoder",0,1);
        Graph graph(env,models,"flow-encoder.onnx",params.threads,stats,{{"tokens",i64,{1,-1}},{"speaker",f32,{1,192}}},{{"mu",f32,{1,80,-1}},{"spks",f32,{1,80}}});
        auto tokens=input.tokens;auto speaker=input.speaker;std::vector<Ort::Value> feed;
        feed.push_back(integers(tokens,{1,N}));feed.push_back(floats(speaker,{1,192}));auto result=graph.run(feed,cancelled);
        mu=output(result[0],{1,80,F});spks=output(result[1],{1,80});event("flow_encoder",1,1);
        if(trace){trace("flow_mu",mu,{1,80,F});trace("flow_spks",spks,{1,80});}
    }
    Samples state(80*frames);for(float& value:state)value=normal();
    {
        event("flow_estimator",0,params.steps);
        Graph graph(env,models,"flow-estimator.onnx",params.threads,stats,
            {{"x",f32,{2,80,-1}},{"mask",f32,{2,1,-1}},{"mu",f32,{2,80,-1}},{"time",f32,{2}},{"spks",f32,{2,80}},{"cond",f32,{2,80,-1}}},{{"velocity",f32,{2,80,-1}}});
        Samples x(2*state.size()),mask(2*frames,1),mu2(2*mu.size(),0),spks2(160,0),cond(2*mu.size(),0),time(2);
        std::copy(mu.begin(),mu.end(),mu2.begin());std::copy(spks.begin(),spks.end(),spks2.begin());
        for(size_t c=0;c<80;++c)std::copy_n(input.prompt_mel.values.begin()+c*input.prompt_mel.cols,input.prompt_mel.cols,cond.begin()+c*frames);
        auto schedule=cosine_schedule(params.steps);float t=schedule[0],dt=schedule[1]-schedule[0];
        for(int step=0;step<params.steps;++step) {
            std::copy(state.begin(),state.end(),x.begin());std::copy(state.begin(),state.end(),x.begin()+state.size());std::fill(time.begin(),time.end(),t);
            std::vector<Ort::Value> feed;feed.push_back(floats(x,{2,80,F}));feed.push_back(floats(mask,{2,1,F}));feed.push_back(floats(mu2,{2,80,F}));
            feed.push_back(floats(time,{2}));feed.push_back(floats(spks2,{2,80}));feed.push_back(floats(cond,{2,80,F}));
            event("flow_estimator_step",step,params.steps);
            auto result=graph.run(feed,cancelled);auto velocity=output(result[0],{2,80,F});
            if(trace)trace("flow_velocity_"+std::to_string(step),velocity,{2,80,F});
            Samples conditional(velocity.begin(),velocity.begin()+state.size()),unconditional(velocity.begin()+state.size(),velocity.end());
            euler_step(state,conditional,unconditional,dt,params.cfg);t+=dt;
            if(step+1<params.steps)dt=schedule[step+2]-t;
            event("flow_estimator",step+1,params.steps);
        }
    }
    // Remove the EXACT reference prefix only after full Flow generation.
    size_t generated=frames-input.prompt_mel.cols;int64_t T=static_cast<int64_t>(generated);
    Samples mel(80*generated);for(size_t c=0;c<80;++c)std::copy_n(state.begin()+c*frames+input.prompt_mel.cols,generated,mel.begin()+c*generated);
    if(trace)trace("mel",mel,{1,80,T});
    mu.clear();spks.clear();state.clear();Samples f0;
    {
        event("hift_f0",0,1);Graph graph(env,models,"hift-f0.onnx",params.threads,stats,{{"mel",f32,{1,80,-1}}},{{"f0",f32,{1,-1}}});
        std::vector<Ort::Value> feed;feed.push_back(floats(mel,{1,80,T}));auto result=graph.run(feed,cancelled);f0=output(result[0],{1,T});event("hift_f0",1,1);
        if(trace)trace("f0",f0,{1,T});
    }
    auto merge_bytes=bytes(models.directory/"hift-source.f32",40);require(merge_bytes.size()==40,"Wrong HiFT source weights length");
    std::array<float,10> merge{};
    for(size_t i=0;i<10;++i){uint32_t bits=0;for(int j=0;j<4;++j)bits|=uint32_t(static_cast<unsigned char>(merge_bytes[i*4+j]))<<(8*j);std::memcpy(&merge[i],&bits,4);require(std::isfinite(merge[i]),"Non-finite learned HiFT source weight");}
    Samples source(generated*480);
    nsf_harmonics(f0,normal,[&](size_t offset,const std::array<float,9>& harmonics){
        float value=merge[9];for(size_t h=0;h<9;++h)value+=harmonics[h]*merge[h];require(std::isfinite(value),"HiFT source merge overflow");source[offset]=std::tanh(value);
    },cancelled);
    if(trace)trace("source",source,{1,1,static_cast<int64_t>(source.size())});
    Matrix spectrum=source_stft(source,cancelled);source.clear();f0.clear();Matrix magnitude,phase;
    {
        event("hift_spectrum",0,1);Graph graph(env,models,"hift-spectrum.onnx",params.threads,stats,
            {{"mel",f32,{1,80,-1}},{"source_stft",f32,{1,18,-1}}},{{"magnitude",f32,{1,9,-1}},{"phase",f32,{1,9,-1}}});
        int64_t columns=static_cast<int64_t>(spectrum.cols);std::vector<Ort::Value> feed;
        feed.push_back(floats(mel,{1,80,T}));feed.push_back(floats(spectrum.values,{1,18,columns}));auto result=graph.run(feed,cancelled);
        magnitude={9,spectrum.cols,output(result[0],{1,9,columns})};phase={9,spectrum.cols,output(result[1],{1,9,columns})};event("hift_spectrum",1,1);
        if(trace){trace("magnitude",magnitude.values,{1,9,columns});trace("phase",phase.values,{1,9,columns});}
    }
    auto wave=hift_istft(magnitude,phase,cancelled);require(wave.size()==generated*480,"Wrong SoulX acoustic sample count");
    event("complete",1,1);require(stats.session_loads==4 && stats.session_unloads==4 && stats.max_live_sessions==1,"SoulX acoustic session lifetime mismatch");return wave;
}
}

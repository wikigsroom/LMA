#pragma once
#define ORT_API_MANUAL_INIT
#include "onnxruntime_cxx_api.h"
#include "../moss_nano/onnx_external.hpp"
#include "../worker_common.hpp"
#include <map>
namespace lma_shape {
using namespace lma_worker;
using Floats=std::vector<float>;
namespace fs=std::filesystem;
inline std::string bytes(const fs::path& file,size_t maximum) {
 auto n=fs::file_size(file);require(n>0&&n<=maximum,"Missing/oversized shape metadata or graph");std::string data(size_t(n),'\0');
 std::ifstream in(file,std::ios::binary);in.read(data.data(),std::streamsize(n));require(bool(in),"Cannot read shape asset");return data;
}
inline void ort_init(){const OrtApi* api=OrtGetApiBase()->GetApi(17);require(api!=nullptr,"ONNX Runtime API17 unavailable");Ort::InitApi(api);}
inline Ort::Value tensor(Floats& data,const std::vector<int64_t>& shape) {
 size_t n=1;for(auto d:shape){require(d>0&&uint64_t(d)<=32000000/n,"Shape tensor exceeds application bounds");n*=size_t(d);}require(n==data.size(),"Shape tensor length mismatch");
 auto memory=Ort::MemoryInfo::CreateCpu(OrtArenaAllocator,OrtMemTypeDefault);return Ort::Value::CreateTensor<float>(memory,data.data(),data.size(),shape.data(),shape.size());
}
inline Floats values(Ort::Value& value,const std::vector<int64_t>& shape) {
 require(value.IsTensor(),"Shape output is not a tensor");auto info=value.GetTensorTypeAndShapeInfo();
 require(info.GetElementType()==ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT&&info.GetShape()==shape,"Shape output dtype/dimensions disagree with export");
 auto n=info.GetElementCount();require(n>0&&n<=32000000,"Shape output exceeds application bounds");
 const float* p=value.GetTensorMutableData<float>();Floats r(p,p+n);for(float f:r)require(std::isfinite(f),"Nonfinite shape output");return r;
}
struct Field {const char* name;std::vector<int64_t> shape;};
class Graph {
 Ort::Session session_{nullptr};std::vector<const char*> inputs_;const char* output_;
 void signature(bool output,const std::vector<Field>& expected) {
  require((output?session_.GetOutputCount():session_.GetInputCount())==expected.size(),"Shape graph IO count mismatch");Ort::AllocatorWithDefaultOptions a;
  for(size_t i=0;i<expected.size();i++){
   auto name=output?session_.GetOutputNameAllocated(i,a):session_.GetInputNameAllocated(i,a);
   require(std::string(name.get())==expected[i].name,"Shape graph IO name/order mismatch");
   auto ti=output?session_.GetOutputTypeInfo(i):session_.GetInputTypeInfo(i);require(ti.GetONNXType()==ONNX_TYPE_TENSOR,"Shape graph IO must be tensors");
   auto t=ti.GetTensorTypeAndShapeInfo();auto s=t.GetShape();require(t.GetElementType()==ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT&&s.size()==expected[i].shape.size(),"Shape graph IO dtype/rank mismatch");
   for(size_t j=0;j<s.size();j++)require(expected[i].shape[j]<0?s[j]<0:(s[j]<0||s[j]==expected[i].shape[j]),"Shape graph IO static/dynamic dimension mismatch");
  }
 }
public:
 Graph(Ort::Env& env,const fs::path& directory,const char* name,int threads,std::vector<Field> inputs,Field output):output_(output.name){
  std::string filename=std::string(name)+".onnx";fs::path path=directory/filename;
  auto model=bytes(path,128*1024*1024);std::map<std::string,uint64_t> external;
  fs::path side=directory/(filename+".data");if(fs::is_regular_file(side))external[side.filename().string()]=fs::file_size(side);
  lma_onnx::References(external).validate(model);model.clear();model.shrink_to_fit();
  Ort::SessionOptions options;options.SetIntraOpNumThreads(threads);options.SetInterOpNumThreads(1);options.SetExecutionMode(ExecutionMode::ORT_SEQUENTIAL);
  options.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_BASIC);options.DisableCpuMemArena();options.DisableMemPattern();options.SetLogSeverityLevel(ORT_LOGGING_LEVEL_FATAL);options.AddConfigEntry("session.intra_op.allow_spinning","0");
  session_=Ort::Session(env,path.c_str(),options);signature(false,inputs);signature(true,{output});for(auto& f:inputs)inputs_.push_back(f.name);
 }
 Ort::Value run(std::vector<Ort::Value>& data){require(data.size()==inputs_.size(),"Shape graph feed count mismatch");auto r=session_.Run(Ort::RunOptions{nullptr},inputs_.data(),data.data(),data.size(),&output_,1);return std::move(r[0]);}
};
}

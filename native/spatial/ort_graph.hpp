#pragma once
#include "sparse_ort.hpp"
namespace lma_spatial {
using namespace lma_shape;
// Dedicated Spatial graph loader: the signed-in CPU custom operators are built
// into the worker. No runtime libraries, scripts or user plugins are loaded.
class SpatialGraph {
 lma_sparse::Domain domain_;Ort::Session session_{nullptr};std::vector<const char*> inputs_;const char* output_;
 void signature(bool output,const std::vector<Field>& expected){
  require((output?session_.GetOutputCount():session_.GetInputCount())==expected.size(),"Spatial graph IO count mismatch");Ort::AllocatorWithDefaultOptions a;
  for(size_t i=0;i<expected.size();i++){auto name=output?session_.GetOutputNameAllocated(i,a):session_.GetInputNameAllocated(i,a);require(std::string(name.get())==expected[i].name,"Spatial graph IO name/order mismatch");
   auto ti=output?session_.GetOutputTypeInfo(i):session_.GetInputTypeInfo(i);require(ti.GetONNXType()==ONNX_TYPE_TENSOR,"Spatial graph IO must be tensors");auto t=ti.GetTensorTypeAndShapeInfo();auto s=t.GetShape();
   require(t.GetElementType()==ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT&&s.size()==expected[i].shape.size(),"Spatial graph IO dtype/rank mismatch");for(size_t j=0;j<s.size();j++)require(expected[i].shape[j]<0?s[j]<0:(s[j]<0||s[j]==expected[i].shape[j]),"Spatial graph dimension mismatch");}
 }
public:
 SpatialGraph(Ort::Env& env,const fs::path& directory,const char* name,int threads,std::vector<Field> inputs,Field output):output_(output.name){
  std::string filename=std::string(name)+".onnx";fs::path path=directory/filename;auto model=bytes(path,128*1024*1024);std::map<std::string,uint64_t> external;fs::path side=directory/(filename+".data");if(fs::is_regular_file(side))external[side.filename().string()]=fs::file_size(side);
  lma_onnx::References(external).validate(model);model.clear();model.shrink_to_fit();Ort::SessionOptions options;options.SetIntraOpNumThreads(threads);options.SetInterOpNumThreads(1);options.SetExecutionMode(ExecutionMode::ORT_SEQUENTIAL);
  options.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_BASIC);options.DisableCpuMemArena();options.DisableMemPattern();options.SetLogSeverityLevel(ORT_LOGGING_LEVEL_FATAL);options.AddConfigEntry("session.intra_op.allow_spinning","0");domain_.add(options);
  session_=Ort::Session(env,path.c_str(),options);signature(false,inputs);signature(true,{output});for(auto& f:inputs)inputs_.push_back(f.name);
 }
 Ort::Value run(std::vector<Ort::Value>& data){require(data.size()==inputs_.size(),"Spatial graph feed count mismatch");auto out=session_.Run(Ort::RunOptions{nullptr},inputs_.data(),data.data(),data.size(),&output_,1);return std::move(out[0]);}
};
}

#pragma once
#include "ort_graph.hpp"
namespace lma_spatial {
struct TypedField {
 std::string name; std::vector<int64_t> shape;
 ONNXTensorElementDataType type=ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT;
};
using Integers=std::vector<int64_t>;
inline Ort::Value integer_tensor(Integers& data,const std::vector<int64_t>& shape){
 size_t n=1;for(auto d:shape){require(d>0&&uint64_t(d)<=32000000/n,"Integer tensor exceeds bounds");n*=size_t(d);}require(n==data.size(),"Integer tensor length mismatch");
 auto memory=Ort::MemoryInfo::CreateCpu(OrtArenaAllocator,OrtMemTypeDefault);return Ort::Value::CreateTensor<int64_t>(memory,data.data(),data.size(),shape.data(),shape.size());
}
// A closed adapter supplies these signatures in code, never a user script or
// model-defined list of stages. Names own their storage throughout Run().
class TypedGraph {
 lma_sparse::Domain domain_;Ort::Session session_{nullptr};
 std::vector<TypedField> inputs_,outputs_;std::vector<const char*> in_names_,out_names_;
 static void dimensions(const std::vector<int64_t>& actual,const TypedField& expected,bool dynamic){
  require(actual.size()==expected.shape.size(),"Graph tensor rank mismatch");uint64_t count=1;
  for(size_t i=0;i<actual.size();i++){
   require(expected.shape[i]<0||actual[i]<0||actual[i]==expected.shape[i],"Graph tensor dimension mismatch");
   if(!dynamic){require(actual[i]>0&&uint64_t(actual[i])<=32000000/count,"Graph tensor budget exceeded");count*=uint64_t(actual[i]);}
  }
 }
 void signature(bool output,const std::vector<TypedField>& fields){
  require((output?session_.GetOutputCount():session_.GetInputCount())==fields.size(),"Graph signature count mismatch");Ort::AllocatorWithDefaultOptions allocator;
  for(size_t i=0;i<fields.size();i++){
   auto name=output?session_.GetOutputNameAllocated(i,allocator):session_.GetInputNameAllocated(i,allocator);
   require(std::string(name.get())==fields[i].name,"Graph signature name/order mismatch");
   auto info=output?session_.GetOutputTypeInfo(i):session_.GetInputTypeInfo(i);require(info.GetONNXType()==ONNX_TYPE_TENSOR,"Graph requires tensor IO");auto tensor=info.GetTensorTypeAndShapeInfo();
   require(tensor.GetElementType()==fields[i].type,"Graph signature dtype mismatch");dimensions(tensor.GetShape(),fields[i],true);
  }
 }
 static void validate(Ort::Value& value,const TypedField& field){
  require(value.IsTensor(),"Graph value is not a tensor");auto info=value.GetTensorTypeAndShapeInfo();require(info.GetElementType()==field.type,"Graph value dtype mismatch");dimensions(info.GetShape(),field,false);
  if(field.type==ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT){const float* p=value.GetTensorData<float>();for(size_t i=0;i<info.GetElementCount();i++)require(std::isfinite(p[i]),"Nonfinite graph tensor");}
 }
public:
 TypedGraph(Ort::Env& env,const fs::path& directory,const std::string& name,int threads,std::vector<TypedField> inputs,std::vector<TypedField> outputs):inputs_(std::move(inputs)),outputs_(std::move(outputs)){
  require(threads>=1&&threads<=16&&!inputs_.empty()&&!outputs_.empty()&&inputs_.size()<=32&&outputs_.size()<=16,"Graph signature bounds exceeded");
  require(name.find_first_not_of("abcdefghijklmnopqrstuvwxyz_0123456789")==std::string::npos,"Invalid internal graph name");
  std::string filename=name+".onnx";auto path=directory/filename;auto model=bytes(path,128*1024*1024);std::map<std::string,uint64_t> external;auto side=directory/(filename+".data");if(fs::is_regular_file(side))external[side.filename().string()]=fs::file_size(side);
  lma_onnx::References(external).validate(model);model.clear();model.shrink_to_fit();Ort::SessionOptions options;
  options.SetIntraOpNumThreads(threads);options.SetInterOpNumThreads(1);options.SetExecutionMode(ExecutionMode::ORT_SEQUENTIAL);options.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_BASIC);options.DisableCpuMemArena();options.DisableMemPattern();options.SetLogSeverityLevel(ORT_LOGGING_LEVEL_FATAL);options.AddConfigEntry("session.intra_op.allow_spinning","0");domain_.add(options);
  session_=Ort::Session(env,path.c_str(),options);signature(false,inputs_);signature(true,outputs_);for(auto& f:inputs_)in_names_.push_back(f.name.c_str());for(auto& f:outputs_)out_names_.push_back(f.name.c_str());
 }
 TypedGraph(const TypedGraph&)=delete;TypedGraph& operator=(const TypedGraph&)=delete;
 std::vector<Ort::Value> run(std::vector<Ort::Value>& args){
  require(args.size()==inputs_.size(),"Graph feed count mismatch");for(size_t i=0;i<args.size();i++)validate(args[i],inputs_[i]);
  auto result=session_.Run(Ort::RunOptions{nullptr},in_names_.data(),args.data(),args.size(),out_names_.data(),out_names_.size());for(size_t i=0;i<result.size();i++)validate(result[i],outputs_[i]);return result;
 }
};
}

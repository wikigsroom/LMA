#include "../../native/spatial/sparse_ort.hpp"
#include "../../native/spatial/fdg.hpp"
#include "../../native/spatial/view_router.hpp"
#include "../../native/spatial/fdg_mesh.hpp"
#include "../../native/spatial/flexicubes.hpp"
#include "../../native/spatial/depth.hpp"
#include "../../native/spatial/sam_math.hpp"
#include <iostream>
int main(int argc,char** argv){
 using namespace lma_shape;try{
  require(argc==2,"Need a local sparse graph fixture");std::ifstream in(argv[1]);json request;in>>request;
  if(request.value("operation","")=="sam_entropy"){
   std::vector<Floats> entropy;for(const auto& view:request.at("views"))entropy.push_back(lma_spatial::sam_patch_entropy(view.at("q").get<Floats>(),view.at("k").get<Floats>(),request.at("queries"),request.at("keys"),request.at("heads"),request.at("width"),request.at("begin"),request.at("end")));
   auto weights=lma_spatial::sam_fusion_weights(entropy,request.at("alpha"),request.at("temperature"),request.at("minimum"));json result={{"entropy",entropy},{"weights",weights}};
   if(request.contains("original"))result["expanded"]=lma_spatial::sam_expand_weights(weights,request.at("coarse").get<std::vector<lma_sparse::Coord>>(),request.at("original").get<std::vector<lma_sparse::Coord>>(),request.at("factor"));
   std::cout<<result.dump()<<std::endl;return 0;
  }
  if(request.value("operation","")=="sam_schedule"){
   auto p=request.at("schedule");lma_spatial::SamSchedule s;s.steps=p.at("steps");s.rescale=p.at("rescale");s.time_scale=p.at("timeScale");s.reversed=p.at("reversed");s.shortcut=p.at("shortcut");s.no_shortcut=p.at("noShortcut");s.solver=p.at("solver");
   std::vector<std::array<float,2>> calls;auto result=lma_spatial::sam_integrate(request.at("state").get<Floats>(),s,[&](const Floats& x,float t,float d){calls.push_back({t,d});Floats y(x.size());for(size_t i=0;i<x.size();i++)y[i]=std::sin(t*.001f+.17f)+x[i]*.035f+d*.0002f;return y;});
   std::cout<<json({{"state",result},{"calls",calls}}).dump()<<std::endl;return 0;
  }
  if(request.value("operation","")=="sam_cfg"){
   std::cout<<json(lma_spatial::sam_cfg(request.at("conditional").get<Floats>(),request.at("unconditional").get<Floats>(),request.at("withoutPoints").get<Floats>(),request.at("strength"),request.at("pointStrength"),request.at("pointmapCfg"))).dump()<<std::endl;return 0;
  }
  if(request.value("operation","")=="depth_postprocess"){
   int h=request.at("height"),w=request.at("width");std::vector<lma_spatial::DepthCamera> cameras;
   for(auto& pose:request.at("poses"))cameras.push_back(lma_spatial::da3_camera(pose.get<std::array<float,9>>(),h,w));
   auto depth=request.at("depth").get<Floats>(),confidence=request.at("confidence").get<Floats>();float scale=1;
   if(request.contains("metric")){std::mt19937 random(3924);scale=lma_spatial::da3_nested_align(depth,confidence,request.at("metric").get<Floats>(),request.at("sky").get<Floats>(),cameras,h,w,random);}
   json cs=json::array();for(auto& c:cameras)cs.push_back({{"intrinsics",c.intrinsics},{"extrinsics",c.world_to_camera}});
   std::cout<<json({{"depth",depth},{"confidence",confidence},{"scale",scale},{"cameras",cs}}).dump()<<std::endl;return 0;
  }
  if(request.value("operation","")=="moge_recover"){
   auto result=lma_spatial::moge_recover(request.at("points").get<Floats>(),request.at("mask").get<Floats>(),request.at("height"),request.at("width"),request.value("threshold",.5f));
   std::cout<<json({{"focal",result.focal},{"shift",result.shift},{"intrinsics",result.intrinsics}}).dump()<<std::endl;return 0;
  }
  if(request.value("operation","")=="flexicubes"){
   auto result=lma_spatial::flexicubes(request.at("coords").get<std::vector<lma_sparse::Coord>>(),request.at("fields").get<Floats>(),request.at("channels"),request.at("grid"),request.value("maxTriangles",size_t(1000000)));
   std::cout<<json({{"vertices",result.mesh.vertices},{"faces",result.mesh.indices},{"colors",result.colors}}).dump()<<std::endl;return 0;
  }
  if(request.value("operation","")=="mesh_to_dual_grid"){
   Mesh mesh;mesh.vertices=request.at("vertices").get<std::vector<Point>>();mesh.indices=request.at("indices").get<std::vector<uint32_t>>();auto fields=lma_spatial::voxelize_dual_grid(mesh,request.at("grid"));
   std::cout<<json({{"coords",fields.coords},{"vertices",fields.vertices},{"flags",fields.flags}}).dump()<<std::endl;return 0;
  }
  if(request.value("operation","")=="view_router"){
   int views=request.at("views"),grid=request.at("grid");require(views>=1&&views<=8,"Fixture view limit");size_t rows=size_t(views)*448*448;
   std::vector<float> points(rows*3),conf(rows);std::vector<uint8_t> mask(rows);
   for(const auto& sample:request.at("samples")){size_t row=sample.at("row");require(row<rows,"Fixture pixel outside selected views");auto p=sample.at("point").get<std::array<float,3>>();std::copy(p.begin(),p.end(),points.begin()+row*3);conf[row]=sample.at("confidence");mask[row]=sample.value("mask",true)?1:0;}
   auto result=lma_spatial::route_views(points,conf,mask,views,grid,request.at("targets").get<std::vector<lma_sparse::Coord>>());std::cout<<json(result).dump()<<std::endl;return 0;
  }
  if(request.value("operation","")=="dual_grid"){
   auto coords=request.at("coords").get<std::vector<lma_sparse::Coord>>();
   auto mesh=lma_spatial::dual_grid(coords,request.at("vertices").get<Floats>(),request.at("flags").get<std::vector<int64_t>>(),request.at("weights").get<Floats>(),request.at("grid"),request.value("maxTriangles",size_t(1000000)));
   std::cout<<json({{"vertices",mesh.vertices},{"faces",mesh.indices}}).dump()<<std::endl;return 0;
  }
  ort_init();Ort::Env env(ORT_LOGGING_LEVEL_FATAL,"sparse_fixture");lma_sparse::Domain domain;Ort::SessionOptions options;options.SetIntraOpNumThreads(1);options.SetLogSeverityLevel(ORT_LOGGING_LEVEL_FATAL);options.DisableCpuMemArena();domain.add(options);
  fs::path path=request.at("graph").get<std::string>();auto model=bytes(path,128*1024*1024);lma_onnx::References({}).validate(model);Ort::Session session(env,path.c_str(),options);auto memory=Ort::MemoryInfo::CreateCpu(OrtArenaAllocator,OrtMemTypeDefault);
  std::vector<std::vector<float>> floats;std::vector<std::vector<int64_t>> ints;std::vector<std::string> names;std::vector<Ort::Value> values;const auto& inputs=request.at("inputs");floats.reserve(inputs.size());ints.reserve(inputs.size());names.reserve(inputs.size());values.reserve(inputs.size());
  for(const auto& p:inputs){auto shape=p.at("shape").get<std::vector<int64_t>>();size_t n=1;for(int64_t d:shape){require(d>=0&&d<=32000000&&(!n||size_t(d)<=32000000/n),"Fixture tensor too large");n*=size_t(d);}names.push_back(p.at("name"));
   if(p.at("dtype")=="float32"){floats.push_back(p.at("values").get<std::vector<float>>());require(floats.back().size()==n,"Fixture float shape");values.push_back(Ort::Value::CreateTensor<float>(memory,floats.back().data(),n,shape.data(),shape.size()));}
   else{require(p.at("dtype")=="int64","Fixture dtype");ints.push_back(p.at("values").get<std::vector<int64_t>>());require(ints.back().size()==n,"Fixture int shape");values.push_back(Ort::Value::CreateTensor<int64_t>(memory,ints.back().data(),n,shape.data(),shape.size()));}}
  std::vector<const char*> input_names;for(const auto& n:names)input_names.push_back(n.c_str());Ort::AllocatorWithDefaultOptions allocator;std::vector<std::string> outputs;for(size_t i=0;i<session.GetOutputCount();i++){auto n=session.GetOutputNameAllocated(i,allocator);outputs.emplace_back(n.get());}std::vector<const char*> output_names;for(auto& n:outputs)output_names.push_back(n.c_str());
  auto results=session.Run(Ort::RunOptions{nullptr},input_names.data(),values.data(),values.size(),output_names.data(),output_names.size());json out=json::array();for(auto& r:results){auto info=r.GetTensorTypeAndShapeInfo();auto shape=info.GetShape();auto n=info.GetElementCount();require(n<=32000000,"Fixture output too large");json item={{"shape",shape}};if(info.GetElementType()==ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT){const float* d=r.GetTensorData<float>();item["values"]=n?std::vector<float>(d,d+n):std::vector<float>{};}else{require(info.GetElementType()==ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64,"Fixture output dtype");const int64_t* d=r.GetTensorData<int64_t>();item["values"]=n?std::vector<int64_t>(d,d+n):std::vector<int64_t>{};}out.push_back(item);}std::cout<<out.dump()<<std::endl;return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<std::endl;return 1;}
}

#pragma once
#include "ort.hpp"
#include "geometry.hpp"
#include "surface.hpp"
#include <random>
#include <numeric>
#include <set>

namespace lma_shape {
inline Floats pointcloud(const fs::path& file,int maximum){
 auto root=json::parse(bytes(file,8*1024*1024));require(root.size()==3&&root.at("schema")=="lma.pointcloud/1"&&root.at("coordinates")=="publisher_normalized","Unsupported point-cloud format");
 const auto& rows=root.at("points");require(rows.is_array()&&rows.size()>=16&&rows.size()<=size_t(maximum),"Point-cloud point budget exceeded");Floats data;data.reserve(rows.size()*6);
 for(const auto& row:rows){require(row.is_array()&&row.size()==6,"XYZ and normals are required for every point");float norm=0;
  for(int i=0;i<6;i++){require(row[i].is_number(),"Point features must be numeric");float v=row[i];require(std::isfinite(v)&&std::abs(v)<=1.005f,"Point features exceed normalized coordinates");data.push_back(v);if(i>=3)norm+=v*v;}
  require(norm>.8f&&norm<1.2f,"Point-cloud normals must have unit length");
 }return data;
}
// Publisher: draw 4*tokens, then FPS with eval random_start=False. The draw
// uses a disclosed MT19937 stream instead of NumPy's PCG64; the FPS recurrence
// uses the same first point and first argmax tie policy as torch_cluster CPU.
inline Floats point_fps(const Floats& points,const std::vector<size_t>& candidates,int tokens){
 require(points.size()%6==0&&tokens>0&&tokens<=4096&&candidates.size()==size_t(tokens)*4,"Invalid point-query shape");size_t total=candidates.size();for(auto id:candidates)require(id<points.size()/6,"Invalid FPS point index");
 Floats distance(total,std::numeric_limits<float>::infinity()),result;result.reserve(size_t(tokens)*6);size_t selected=0;
 for(int i=0;i<tokens;i++){
  auto begin=points.begin()+candidates[selected]*6;result.insert(result.end(),begin,begin+6);
  size_t next=0;float furthest=-1;
  for(size_t j=0;j<total;j++){float d=0;for(int k=0;k<3;k++){float delta=points[candidates[j]*6+k]-begin[k];d+=delta*delta;}distance[j]=std::min(distance[j],d);if(distance[j]>furthest){furthest=distance[j];next=j;}}
  selected=next;
 }return result;
}
inline Floats point_queries(const Floats& points,int tokens,std::mt19937& random){
 require(points.size()%6==0&&points.size()>=6&&tokens>0&&tokens<=4096,"Invalid point-query shape");size_t count=points.size()/6,total=size_t(tokens)*4;std::vector<size_t> candidates(total);
 if(total>count){std::uniform_int_distribution<size_t> draw(0,count-1);for(auto& id:candidates)id=draw(random);}
 else{std::vector<size_t> order(count);std::iota(order.begin(),order.end(),0);for(size_t i=0;i<total;i++){std::uniform_int_distribution<size_t> draw(i,count-1);std::swap(order[i],order[draw(random)]);candidates[i]=order[i];}}
 return point_fps(points,candidates,tokens);
}
inline void point_generate(const json& command){
 std::string pipeline=command.at("pipeline");bool part=pipeline=="partcrafter_points";require(part||pipeline=="triposg_points","Unknown point-VAE architecture");require(command.at("type")=="mesh.generate","Point VAE only exports meshes");
 auto p=command.at("parameters");std::set<std::string> keys={"threads","seed","tokens","posterior","grid","queryChunk","maxTriangles","extraction","octreeDepth","denseDepth"};for(auto it=p.begin();it!=p.end();it++)require(keys.count(it.key()),"Unknown point-VAE parameter");
 int threads=integer(p,"threads",2,1,16),seed=integer(p,"seed",1234,0,INT32_MAX),tokens=integer(p,"tokens",2048,512,4096),grid=integer(p,"grid",64,32,256),chunk=integer(p,"queryChunk",512,128,4096),limit=integer(p,"maxTriangles",300000,1000,1000000);
 std::string extraction=p.value("extraction",std::string("uniform"));require(extraction=="uniform"||extraction=="publisher_octree"||extraction=="publisher_flash","Unsupported extraction profile");int depth=integer(p,"octreeDepth",6,5,8),dense=integer(p,"denseDepth",5,3,8);require(dense<=depth,"Dense depth exceeds target depth");
 std::string posterior=p.value("posterior",std::string("mean"));require((posterior=="mean"||posterior=="sample")&&tokens%512==0&&grid%16==0,"Invalid point-VAE settings");
 fs::path workspace=command.at("workspace").get<std::string>(),output=command.at("output").get<std::string>();require(workspace.is_absolute()&&fs::is_directory(workspace)&&output.is_absolute()&&!fs::exists(output),"Invalid point-VAE workspace");workspace=fs::canonical(workspace);
 const std::map<std::string,std::string> names={{"config","shape-config.json"},{"encoder","encoder.onnx"},{"encoder_data","encoder.onnx.data"},{"cache","cache.onnx"},{"cache_data","cache.onnx.data"},{"query","query.onnx"},{"query_data","query.onnx.data"}};std::set<std::string> found;
 for(auto it=command.at("components").begin();it!=command.at("components").end();it++){require(names.count(it.key()),"Unknown point-VAE component");fs::path path=component(command,it.key().c_str());require(fs::canonical(path.parent_path())==workspace&&path.filename()==names.at(it.key()),"Point-VAE component escaped workspace");found.insert(it.key());}
 for(const char* role:{"config","encoder","cache","query"})require(found.count(role),"Missing point-VAE component");
 json cfg=json::parse(bytes(workspace/"shape-config.json",65536));require(cfg.at("schema")=="lma.rf-pointcloud-export/1"&&cfg.at("pipeline")==pipeline&&cfg.at("dtype")=="float32"&&cfg.at("opset")==17,"Unmatched point-VAE export");
 require(cfg.at("source").at("repository")== (part?"wgsxm/PartCrafter":"VAST-AI-Research/TripoSG")&&cfg.at("source").at("revision")== (part?LMA_PART_REVISION:LMA_TRIPO_REVISION),"Unsupported point-VAE source");
 auto dim=[&](const char* key,int low,int high){require(cfg.at(key).is_number_integer(),"Point metadata must use integers");int64_t v=cfg.at(key);require(v>=low&&v<=high,"Point-VAE export dimensions exceed bounds");return int(v);};
 int channels=dim("latentChannels",1,512),width=dim("decoderWidth",8,4096),max_points=dim("maxPoints",16,16384),max_tokens=dim("maxTokens",512,4096);require(tokens<=max_tokens&&cfg.at("features")=="xyz_normals"&&cfg.at("coordinates")=="publisher_normalized"&&cfg.at("sampling")=="seeded_mt19937_four_times_then_cpu_fps_first_argmax"&&cfg.at("posterior")=="mean_or_sample","Unsupported point-VAE profile");
 auto input=pointcloud(regular(command,"pointCloud"),max_points);size_t count=input.size()/6;require(uint64_t(count)*tokens<=16777216,"Point-VAE attention budget exceeded; reduce points or tokens");std::mt19937 random{uint32_t(seed)};auto queries=point_queries(input,tokens,random);ort_init();Ort::Env env(ORT_LOGGING_LEVEL_FATAL,"lma_points");Floats latents;
 event({{"event","execution"},{"details",{{"pipeline",pipeline},{"backend","cpu"},{"pointCount",count},{"posterior",posterior},{"pointSampling",cfg.at("sampling")},{"surfaceExtractor",extraction},{"effectiveParameters",p}}}});event({{"event","stage"},{"stage","encoding_pointcloud"}});
 {
  Graph graph(env,workspace,"encoder",threads,{{"points",{1,-1,6}},{"sampled_points",{1,-1,6}}},{"moments",{1,-1,channels*2}});std::vector<Ort::Value> args;args.push_back(tensor(input,{1,int64_t(count),6}));args.push_back(tensor(queries,{1,tokens,6}));auto r=graph.run(args);auto moments=values(r,{1,tokens,channels*2});latents.resize(size_t(tokens)*channels);std::normal_distribution<float> gaussian;
  for(int i=0;i<tokens;i++)for(int c=0;c<channels;c++){size_t at=size_t(i)*channels*2+c;float v=moments[at];if(posterior=="sample")v+=std::exp(.5f*std::clamp(moments[at+channels],-30.f,20.f))*gaussian(random);latents[size_t(i)*channels+c]=v;require(std::isfinite(v),"Nonfinite point posterior");}
 }
 input.clear();queries.clear();Floats cache;event({{"event","stage"},{"stage","preparing_sdf"}});
 {Graph graph(env,workspace,"cache",threads,{{"latents",{1,-1,channels}}},{"cache",{1,-1,width}});std::vector<Ort::Value> args;args.push_back(tensor(latents,{1,tokens,channels}));auto r=graph.run(args);cache=values(r,{1,tokens,width});}
 latents.clear();size_t n=size_t(grid+1),total=n*n*n;Floats field(total);event({{"event","stage"},{"stage","decoding_sdf"}});
 {Graph graph(env,workspace,"query",threads,{{"cache",{1,-1,width}},{"points",{1,-1,3}}},{"sdf",{1,-1,1}});
  if(extraction!="uniform"){
   auto query=[&](const Floats& q){auto input=q;size_t count=q.size()/3;std::vector<Ort::Value> args;args.push_back(tensor(cache,{1,tokens,width}));args.push_back(tensor(input,{1,int64_t(count),3}));auto r=graph.run(args);return values(r,{1,int64_t(count),1});};
   auto mesh=adaptive_surface(query,extraction,depth,dense,chunk,1.005f,size_t(limit));glb(output,{mesh});event({{"event","complete"},{"output",output.string()}});return;
  }
  for(size_t start=0;start<total;start+=chunk){size_t size=std::min(size_t(chunk),total-start);Floats points(size*3);for(size_t j=0;j<size;j++){size_t id=start+j;points[j*3]=float(id/(n*n))*2.01f/grid-1.005f;points[j*3+1]=float((id/n)%n)*2.01f/grid-1.005f;points[j*3+2]=float(id%n)*2.01f/grid-1.005f;}std::vector<Ort::Value> args;args.push_back(tensor(cache,{1,tokens,width}));args.push_back(tensor(points,{1,int64_t(size),3}));auto r=graph.run(args);auto sdf=values(r,{1,int64_t(size),1});std::copy(sdf.begin(),sdf.end(),field.begin()+start);}
 }event({{"event","stage"},{"stage","exporting_mesh"}});glb(output,{surface(field,grid,size_t(limit))});event({{"event","complete"},{"output",output.string()}});
}
}

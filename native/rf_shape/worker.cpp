#include "ort.hpp"
#include "image.hpp"
#include "geometry.hpp"
#include "math.hpp"
#include <random>
#include <set>
using namespace lma_shape;
static const std::map<std::string,std::string> layout={{"config","shape-config.json"},{"image_encoder","image_encoder.onnx"},{"flow","flow.onnx"},{"cache","cache.onnx"},{"query","query.onnx"},
 {"image_encoder_data","image_encoder.onnx.data"},{"flow_data","flow.onnx.data"},{"cache_data","cache.onnx.data"},{"query_data","query.onnx.data"}};
static int bounded(const json& cfg,const char* key,int low,int high){require(cfg.at(key).is_number_integer(),"Export metadata must contain integer dimensions");auto v=cfg.at(key).get<int64_t>();require(v>=low&&v<=high,"Export dimension exceeds application bounds");return int(v);}
static void generate(const json& command) {
 require(command.at("type")=="mesh.generate","Shape runtime accepts mesh tasks only");std::string pipeline=command.at("pipeline");bool part=pipeline=="partcrafter"||pipeline=="partcrafter_scene";require(pipeline=="triposg"||part,"Unsupported shape architecture");
 auto p=command.at("parameters");std::set<std::string> keys={"threads","steps","seed","tokens","parts","grid","queryChunk","guidance","maxTriangles"};for(auto it=p.begin();it!=p.end();it++)require(keys.count(it.key())!=0,"Unknown shape parameter");
 int threads=integer(p,"threads",2,1,16),steps=integer(p,"steps",30,1,100),seed=integer(p,"seed",1234,0,INT32_MAX),tokens=integer(p,"tokens",part?1024:2048,512,4096),parts=integer(p,"parts",part?3:1,1,part?16:1),grid=integer(p,"grid",64,32,256),chunk=integer(p,"queryChunk",512,128,4096),triangles=integer(p,"maxTriangles",300000,1000,1000000);
 float guidance=number(p,"guidance",7,0,15);require(tokens%512==0&&grid%16==0&&uint64_t(tokens)*chunk<=16777216,"Shape token/grid/query alignment or memory budget exceeded");
 fs::path workspace=command.at("workspace").get<std::string>(),output=command.at("output").get<std::string>();require(workspace.is_absolute()&&fs::is_directory(workspace)&&output.is_absolute()&&!fs::exists(output),"Invalid private shape workspace/output");
 workspace=fs::canonical(workspace);std::set<std::string> found;
 for(auto it=command.at("components").begin();it!=command.at("components").end();it++){
  auto role=layout.find(it.key());require(role!=layout.end(),"Unknown shape component role");fs::path file=regular(command.at("components"),it.key().c_str());require(fs::canonical(file).parent_path()==workspace&&file.filename()==role->second,"Shape component outside its selected workspace");found.insert(it.key());
 }
 for(const char* role:{"config","image_encoder","flow","cache","query"})require(found.count(role)!=0,"Missing shape component");
 json cfg=json::parse(bytes(workspace/"shape-config.json",65536));require(cfg.at("schema")=="lma.rf-shape-export/1"&&cfg.at("pipeline")==pipeline&&cfg.at("dtype")=="float32"&&cfg.at("opset")==17,"Unmatched shape export contract");
 const auto& source=cfg.at("source");require(source.at("repository")== (part?"wgsxm/PartCrafter":"VAST-AI-Research/TripoSG")&&source.at("revision")== (part?LMA_PART_REVISION:LMA_TRIPO_REVISION),"Shape export reference revision is not supported");
 int channels=bounded(cfg,"latentChannels",1,512),width=bounded(cfg,"decoderWidth",8,4096),image_size=bounded(cfg,"imageSize",28,518),edge=bounded(cfg,"resizeShortest",28,1024),encoder_tokens=bounded(cfg,"encoderTokens",2,2048),encoder_width=bounded(cfg,"encoderWidth",8,4096),max_tokens=bounded(cfg,"maxTokens",512,4096),max_parts=bounded(cfg,"maxParts",1,16);
 require(tokens<=max_tokens&&parts<=max_parts&&image_size<=edge&&cfg.at("imageMean").size()==3&&cfg.at("imageStd").size()==3,"Selected export limits do not allow these parameters");
 float shift=cfg.at("scheduleShift");int training=bounded(cfg,"trainingTimesteps",1,100000);require(std::isfinite(shift)&&shift>0&&shift<=16,"Invalid RF schedule shift");
 std::string image=regular(command,"referenceImage");ort_init();Ort::Env env(ORT_LOGGING_LEVEL_FATAL,"lma_shape");Floats embeddings;
 event({{"event","execution"},{"details",{{"pipeline",pipeline},{"backend","cpu"},{"partCount",parts},{"effectiveParameters",p},{"graphResidency","one_session_at_a_time"},{"surfaceExtractor","uniform_grid_marching_tetrahedra"},{"imageMatte","explicit_alpha_over_white_no_segmentation"},{"sourceRevision",source.at("revision")}}}});
 event({{"event","stage"},{"stage","encoding_image"}});
 {
  auto input=pixels(image,image_size,edge,cfg.at("imageMean"),cfg.at("imageStd"));Graph model(env,workspace,"image_encoder",threads,{{"pixel_values",{1,3,image_size,image_size}}},{"image_embeddings",{1,encoder_tokens,encoder_width}});
  std::vector<Ort::Value> args;args.push_back(tensor(input,{1,3,image_size,image_size}));auto result=model.run(args);embeddings=values(result,{1,encoder_tokens,encoder_width});
 }
 Floats condition;condition.reserve(embeddings.size()*parts);for(int i=0;i<parts;i++)condition.insert(condition.end(),embeddings.begin(),embeddings.end());Floats negative(condition.size(),0),latents(size_t(parts)*tokens*channels);
 std::mt19937 random{uint32_t(seed)};std::normal_distribution<float> gaussian;for(float& v:latents)v=gaussian(random);
 event({{"event","stage"},{"stage","sampling_shape"}});
 {
  Graph model(env,workspace,"flow",threads,{{"latents",{-1,-1,channels}},{"timestep",{-1}},{"image_embeddings",{-1,encoder_tokens,encoder_width}}},{"velocity",{-1,-1,channels}});
  auto predict=[&](Floats& context,float time){Floats times(size_t(parts),time);std::vector<Ort::Value> args;args.push_back(tensor(latents,{parts,tokens,channels}));args.push_back(tensor(times,{parts}));args.push_back(tensor(context,{parts,encoder_tokens,encoder_width}));auto r=model.run(args);return values(r,{parts,tokens,channels});};
  for(int i=0;i<steps;i++){float now=sigma(i,steps,shift);Floats velocity=predict(condition,now*training);
   if(guidance>1){Floats uncond=predict(negative,now*training);for(size_t j=0;j<velocity.size();j++)velocity[j]=uncond[j]+guidance*(velocity[j]-uncond[j]);}
   flow_step(latents,velocity,i,steps,shift);
   event({{"event","progress"},{"step",i+1},{"steps",steps},{"stage","sampling_shape"}});
  }
 }
 std::vector<Floats> caches;event({{"event","stage"},{"stage","preparing_sdf"}});
 {
  Graph model(env,workspace,"cache",threads,{{"latents",{1,-1,channels}}},{"cache",{1,-1,width}});
  for(int i=0;i<parts;i++){auto begin=latents.begin()+size_t(i)*tokens*channels;Floats one(begin,begin+size_t(tokens)*channels);std::vector<Ort::Value> args;args.push_back(tensor(one,{1,tokens,channels}));auto r=model.run(args);caches.push_back(values(r,{1,tokens,width}));}
 }
 latents.clear();latents.shrink_to_fit();std::vector<Mesh> meshes;size_t remaining=size_t(triangles),n=size_t(grid+1),points=n*n*n;
 event({{"event","stage"},{"stage","decoding_sdf"}});
 {
  Graph model(env,workspace,"query",threads,{{"cache",{1,-1,width}},{"points",{1,-1,3}}},{"sdf",{1,-1,1}});
  for(int part_id=0;part_id<parts;part_id++){
   Floats field(points);
   for(size_t start=0;start<points;start+=chunk){size_t count=std::min(size_t(chunk),points-start);Floats query(count*3);
    for(size_t j=0;j<count;j++){size_t id=start+j;query[j*3]=float(id/(n*n))*2.01f/grid-1.005f;query[j*3+1]=float((id/n)%n)*2.01f/grid-1.005f;query[j*3+2]=float(id%n)*2.01f/grid-1.005f;}
    std::vector<Ort::Value> args;args.push_back(tensor(caches[size_t(part_id)],{1,tokens,width}));args.push_back(tensor(query,{1,int64_t(count),3}));auto r=model.run(args);auto v=values(r,{1,int64_t(count),1});std::copy(v.begin(),v.end(),field.begin()+start);
   }
   meshes.push_back(surface(field,grid,remaining));remaining-=meshes.back().indices.size()/3;
   event({{"event","progress"},{"step",part_id+1},{"steps",parts},{"stage","decoding_sdf"}});
  }
 }
 event({{"event","stage"},{"stage","exporting_mesh"}});glb(output,meshes);event({{"event","complete"},{"output",output.string()}});
}
int main(int argc,char** argv){
 if(argc==2&&!std::strcmp(argv[1],"--info")){std::puts("{\"engine\":\"rf_shape_ort\",\"backend\":\"cpu\",\"pipelines\":[\"triposg\",\"partcrafter\",\"partcrafter_scene\"],\"modelInferenceTested\":false,\"modelDownloads\":false}");return 0;}
 try{initialize();require(argc==2,"Supply one private shape request");generate(request(argv[1]));return 0;}
 catch(const std::exception&){if(events)event({{"event","error"},{"message","Shape generation failed: check the matched FP32 ONNX export, selected image, model limits and available memory. No fallback was used."}});return 1;}
}

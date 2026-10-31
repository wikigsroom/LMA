#pragma once
#include "material.hpp"
#include "text_tokens.hpp"
namespace lma_spatial {
inline constexpr int ultra_order[6]={0,1,3,2,4,5};
inline Floats ultra_atlas(const std::vector<Floats>& tiles,int side,int channels){
 require(tiles.size()==6&&side>0&&channels>0&&uint64_t(side)*side*channels*6<=32000000,"UltraTex atlas budget exceeded");Floats result(size_t(side)*side*6*channels);
 for(int tile=0;tile<6;tile++){auto& v=tiles[ultra_order[tile]];require(v.size()==size_t(side)*side*channels,"UltraTex tile shape mismatch");for(int c=0;c<channels;c++)for(int y=0;y<side;y++)for(int x=0;x<side;x++)result[(size_t(c)*2*side+y+(tile/3)*side)*3*side+x+(tile%3)*side]=v[(size_t(c)*side+y)*side+x];}return result;
}
inline Floats ultra_tokens(const Floats& atlas,int height,int width,int channels){
 require(atlas.size()==size_t(height)*width*channels,"UltraTex pack shape mismatch");Floats result(atlas.size());for(int y=0;y<height;y++)for(int x=0;x<width;x++)for(int c=0;c<channels;c++)result[(size_t(y)*width+x)*channels+c]=atlas[(size_t(c)*height+y)*width+x];return result;
}
inline Floats ultra_tile(const Floats& tokens,int tile,int side,int channels){
 require(tile>=0&&tile<6&&tokens.size()==size_t(side)*side*channels*6,"UltraTex unpack shape mismatch");int cell=0;while(ultra_order[cell]!=tile)cell++;Floats result(size_t(side)*side*channels);
 for(int c=0;c<channels;c++)for(int y=0;y<side;y++)for(int x=0;x<side;x++)result[(size_t(c)*side+y)*side+x]=tokens[((size_t(y+cell/3*side)*3*side)+x+cell%3*side)*channels+c];return result;
}
inline Integers ultra_ids(int height,int width,int axes,int t=0,int offset=0,int width_offset=0){
 require(height>0&&width>0&&(axes==3||axes==4)&&height+offset<8192&&width+width_offset<8192,"UltraTex position budget exceeded");Integers result(size_t(height)*width*axes,0);
 for(int y=0;y<height;y++)for(int x=0;x<width;x++){size_t at=(size_t(y)*width+x)*axes;result[at]=t;result[at+1]=y+offset;result[at+2]=x+width_offset;}return result;
}
inline Integers ultra_mask(const Floats& alpha,int size,int side,bool require_any=true){
 require(alpha.size()==size_t(size)*size,"UltraTex alpha shape mismatch");Floats bytes_alpha=alpha;for(float& x:bytes_alpha)x=std::round(std::clamp(x,0.f,1.f)*255);
 auto small=resize(bytes_alpha,size,size,side,side,1,"bilinear_aa",true);Integers result(size_t(side)*side);
 // OpenCV's default 2x2 anchor is (1,1): current and previous row/column.
 for(int y=0;y<side;y++)for(int x=0;x<side;x++)for(int dy=-1;dy<=0;dy++)for(int dx=-1;dx<=0;dx++)if(y+dy>=0&&x+dx>=0&&small[size_t(y+dy)*side+x+dx]>0)result[size_t(y)*side+x]=1;
 require(!require_any||std::find(result.begin(),result.end(),1)!=result.end(),"UltraTex input has no foreground");return result;
}
inline float ultra_sigma(int step,int steps,int image_size){
 require(steps>=1&&steps<=100&&step>=0&&step<=steps&&image_size>=32&&image_size<=512,"Invalid UltraTex schedule");if(step==steps)return 0;if(!step)return 1;
 // Preserve the pinned UNO/UltraTex schedule's seq_len calculation, which is
 // distinct from the actual packed token count for the 2x3 atlas.
 double seq=(image_size*3/8)*(image_size*2/8)/256,mu=.5+(seq-256)*(1.15-.5)/(4096-256),t=1-double(step)/steps;
 return float(std::exp(mu)/(std::exp(mu)+(1/t-1)));
}
inline Camera ultra_camera(int view){
 // Explicit portable six-view rig. Upstream training consumes pre-rendered
 // TexVerse images and does not publish a reproducible canonical rig. This
 // bounded CPU rig is reported in execution metadata, never called identical.
 const Point eyes[6]={{0,0,1},{1,0,0},{0,0,-1},{-1,0,0},{0,1,0},{0,-1,0}};require(view>=0&&view<6,"Invalid UltraTex view");Point back=eyes[view],up=std::abs(back[1])>.9f?Point{0,0,-1}:Point{0,1,0};Point right=direction(cross(up,back));return {scale(back,1.45f),right,cross(back,right),back,1.2f};
}
inline Mesh ultra_geometry(const Mesh& input){
 require(input.vertices.size()>=3&&!input.indices.empty()&&input.indices.size()/3<=300000,"UltraTex mesh budget exceeded");Mesh mesh=input;Point lo=input.vertices[0],hi=lo;
 for(auto p:input.vertices)for(int c=0;c<3;c++){require(std::isfinite(p[c]),"Nonfinite UltraTex vertex");lo[c]=std::min(lo[c],p[c]);hi[c]=std::max(hi[c],p[c]);}Point center=scale(add(lo,hi),.5f);float radius=0;
 for(auto& p:mesh.vertices){p=subtract(p,center);radius=std::max(radius,std::sqrt(dot(p,p)));}require(radius>1e-12,"Degenerate UltraTex mesh");for(auto& p:mesh.vertices)p=scale(p,.55f/radius);return mesh;
}
inline void ultratex_generate(const json& command){
 require(command.at("type")=="mesh.generate","UltraTex accepts material mesh tasks");std::string pipeline=command.at("pipeline");bool flux1=pipeline=="ultratex_flux1";require(flux1||pipeline=="ultratex_flux2","Unsupported UltraTex family");
 auto p=command.at("parameters");std::set<std::string> allowed={"threads","steps","seed","guidance","atlas"};if(!flux1)allowed.insert("dropBackground");for(auto it=p.begin();it!=p.end();it++)require(allowed.count(it.key()),"Unknown UltraTex parameter");
 int threads=integer(p,"threads",2,1,16),steps=integer(p,"steps",25,1,100),seed=integer(p,"seed",0,0,INT32_MAX),atlas_size=integer(p,"atlas",1024,256,4096);float guidance=number(p,"guidance",flux1?4.f:3.5f,0,15);require(atlas_size%256==0&&(!p.contains("dropBackground")||p.at("dropBackground").is_boolean()),"Invalid UltraTex option");bool prune=flux1||p.value("dropBackground",false);p={{"threads",threads},{"steps",steps},{"seed",seed},{"atlas",atlas_size},{"guidance",guidance}};if(!flux1)p["dropBackground"]=prune;
 fs::path workspace=command.at("workspace").get<std::string>(),output=command.at("output").get<std::string>();require(workspace.is_absolute()&&fs::is_directory(workspace)&&output.is_absolute()&&!fs::exists(output),"Select a new UltraTex workspace/output");workspace=fs::canonical(workspace);
 std::map<std::string,std::string> layout={{"config","ultratex-config.json"},{"tokenizer",flux1?"t5.model":"qwen-tokenizer.json"}};if(flux1)layout["clip_tokenizer"]="clip-tokenizer.json";
 for(auto name:{"text","vae_encoder","albedo_flow","mr_flow","albedo_decoder","mr_decoder"}){layout[name]=std::string(name)+".onnx";layout[std::string(name)+"_data"]=std::string(name)+".onnx.data";}if(flux1){layout["clip"]="clip.onnx";layout["clip_data"]="clip.onnx.data";}
 std::set<std::string> found;for(auto it=command.at("components").begin();it!=command.at("components").end();it++){auto role=layout.find(it.key());require(role!=layout.end(),"Unknown UltraTex role");auto path=fs::path(regular(command.at("components"),it.key().c_str()));require(fs::canonical(path).parent_path()==workspace&&path.filename()==role->second,"UltraTex asset outside selected workspace");found.insert(it.key());}
 for(auto& role:layout)if(role.first.size()<5||role.first.substr(role.first.size()-5)!="_data")require(found.count(role.first),"Missing matched UltraTex asset");
 auto c=json::parse(bytes(workspace/"ultratex-config.json",65536));require(c.at("schema")=="lma.ultratex-export/1"&&c.at("pipeline")==pipeline&&c.at("dtype")=="float32"&&c.at("opset")==17&&c.at("source").at("repository")=="yiboz2001/UltraTex"&&c.at("source").at("revision")=="a726678f3f3631fe2c5e3d1fb4597114784c7a8b","Unmatched UltraTex export");
 int size=material_dimension(c,"imageSize",32,512),channels=material_dimension(c,"latentChannels",4,128),width=material_dimension(c,"textWidth",8,12288),vocab=material_dimension(c,"textVocab",32,300000),pad=material_dimension(c,"textPad",0,vocab-1),side=size/16,axes=flux1?3:4,targets=6*side*side;
 require(size%16==0&&channels%4==0&&c.at("textLength")==512&&c.at("cameraRig")=="lma_orthographic_y_up_six_v1","Invalid UltraTex graph/camera contract");bool embedded_guidance=c.at("guidanceEmbedding");require(!flux1||embedded_guidance,"UltraTex FLUX1 requires dev guidance");
 int cw=flux1?material_dimension(c,"clipWidth",8,4096):0,cv=flux1?material_dimension(c,"clipVocab",32,300000):0,cp=flux1?material_dimension(c,"clipPad",0,cv-1):0;
 std::string prompt=command.at("prompt");require(prompt.size()<=65536,"UltraTex prompt too long");event({{"event","stage"},{"stage","rendering_conditions"}});auto mesh=read_glb(regular(command,"sourceMesh")),geometry=ultra_geometry(mesh);std::vector<Floats> normal_images,alpha_tiles;
 for(int i=0;i<6;i++){auto g=render_material(geometry,ultra_camera(i),size);normal_images.push_back(condition_rgb(g,true));Floats alpha(g.face.size());for(size_t j=0;j<alpha.size();j++)alpha[j]=g.face[j]>=0;alpha_tiles.push_back(std::move(alpha));}
 // Atlas token order interleaves rows across its three cells.
 std::vector<Floats> mask_tiles;for(auto& alpha:alpha_tiles){auto m=ultra_mask(alpha,size,side,false);mask_tiles.emplace_back(m.begin(),m.end());}auto mask_atlas=ultra_atlas(mask_tiles,side,1);Integers target_mask(mask_atlas.begin(),mask_atlas.end()),normal_mask=target_mask;require(std::count(target_mask.begin(),target_mask.end(),int64_t(1))>0,"No mesh foreground");
 if(!prune){std::fill(target_mask.begin(),target_mask.end(),1);std::fill(normal_mask.begin(),normal_mask.end(),1);}
 int iw,ih,ic;auto image=regular(command,"referenceImage");require(fs::file_size(image)<=16*1024*1024&&stbi_info(image.c_str(),&iw,&ih,&ic)&&iw>0&&ih>0&&uint64_t(iw)*ih<=4194304,"Invalid UltraTex reference PNG");std::unique_ptr<stbi_uc,decltype(&stbi_image_free)> rgba(stbi_load(image.c_str(),&iw,&ih,&ic,4),stbi_image_free);require(bool(rgba),"Cannot decode UltraTex reference");Floats rgb(size_t(iw)*ih*3),alpha(size_t(iw)*ih);
 for(size_t i=0;i<alpha.size();i++){alpha[i]=rgba.get()[i*4+3]/255.f;for(int k=0;k<3;k++)rgb[i*3+k]=float((int(rgba.get()[i*4+k])*rgba.get()[i*4+3]+255*(255-rgba.get()[i*4+3])+127)/255);}
 auto ref_rgb=resize(rgb,iw,ih,size,size,3,"bilinear_aa",true);for(float& f:ref_rgb)f/=255;auto ref_alpha=resize(alpha,iw,ih,size,size,1,"bilinear_aa",false);Integers reference_mask=ultra_mask(ref_alpha,size,side);if(!prune)std::fill(reference_mask.begin(),reference_mask.end(),1);
 event({{"event","execution"},{"details",{{"pipeline",pipeline},{"backend","cpu"},{"graphResidency","one_session_at_a_time"},{"cameraRig","lma_orthographic_y_up_six_v1"},{"publisherCameraParity",false},{"samplingPrecision","float32"},{"rng","mt19937_normal_distribution"},{"effectiveParameters",p},{"completeModelInferenceTested",false}}}});
 ort_init();Ort::Env env(ORT_LOGGING_LEVEL_FATAL,"ultratex");Floats text,negative_text,pooled;event({{"event","stage"},{"stage","encoding_text"}});
 {std::vector<TypedField> in={{"input_ids",{1,512},ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64}};if(!flux1)in.push_back({"attention_mask",{1,512},ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64});TypedGraph graph(env,workspace,"text",threads,in,{{"text",{1,512,width}}});
  auto encode=[&](const std::string& value){auto t=flux1?t5_tokens(workspace/"t5.model",value,512,vocab):bpe_tokens(workspace/"qwen-tokenizer.json",value,512,vocab,pad,true);std::vector<Ort::Value> args;args.push_back(integer_tensor(t.ids,{1,512}));if(!flux1)args.push_back(integer_tensor(t.mask,{1,512}));auto r=graph.run(args);return values(r[0],{1,512,width});};text=encode(prompt);if(!flux1)negative_text=encode("");}
 if(flux1){auto t=bpe_tokens(workspace/"clip-tokenizer.json",prompt,77,cv,cp,false);TypedGraph graph(env,workspace,"clip",threads,{{"input_ids",{1,77},ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64}},{{"pooled_text",{1,cw}}});std::vector<Ort::Value> args;args.push_back(integer_tensor(t.ids,{1,77}));auto r=graph.run(args);pooled=values(r[0],{1,cw});}
 event({{"event","stage"},{"stage","encoding_material_conditions"}});std::mt19937 random{uint32_t(seed)};std::normal_distribution<float> gaussian;Floats normal_tokens,ref_tokens,black_tokens;
 {std::vector<int64_t> noise_shape=flux1?std::vector<int64_t>{1,channels/4,side*2,side*2}:std::vector<int64_t>{1,channels,side,side};TypedGraph graph(env,workspace,"vae_encoder",threads,{{"image",{1,3,size,size}},{"noise",noise_shape}},{{"latents",{1,channels,side,side}}});auto encode=[&](const Floats& input){auto pixels=chw(input,size,true);Floats noise(size_t(channels)*side*side);for(float& v:noise)v=flux1?gaussian(random):0;std::vector<Ort::Value> args;args.push_back(tensor(pixels,{1,3,size,size}));args.push_back(tensor(noise,noise_shape));auto r=graph.run(args);return values(r[0],{1,channels,side,side});};
  std::vector<Floats> tiles;for(auto& image:normal_images)tiles.push_back(encode(image));normal_tokens=ultra_tokens(ultra_atlas(tiles,side,channels),side*2,side*3,channels);ref_tokens=ultra_tokens(encode(ref_rgb),side,side,channels);auto black=encode(Floats(size_t(size)*size*3,0));black_tokens=ultra_tokens(ultra_atlas(std::vector<Floats>(6,black),side,channels),side*2,side*3,channels);}
 auto target_ids=ultra_ids(side*2,side*3,axes),normal_ids=ultra_ids(side*2,side*3,axes,flux1?0:10,flux1?side*2:0,flux1?side*3:0),reference_ids=ultra_ids(side,side,axes,flux1?0:20,flux1?side*4:0,flux1?side*6:0);Integers text_ids(512*axes,0);if(!flux1)for(int i=0;i<512;i++)text_ids[i*axes+3]=i;
 std::vector<std::vector<Floats>> materials;for(const char* pass:{"albedo","mr"}){
  Floats state(size_t(targets)*channels);for(float& v:state)v=gaussian(random);std::string stage=std::string("sampling_")+pass;event({{"event","stage"},{"stage",stage}});
  auto idtype=flux1?ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64:ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT;
  std::vector<TypedField> fields={{"latents",{1,-1,channels}},{"latent_ids",{1,-1,axes},idtype},{"normals",{1,-1,channels}},{"normal_ids",{1,-1,axes},idtype},{"reference",{1,-1,channels}},{"reference_ids",{1,-1,axes},idtype},{"text",{1,512,width}},{"text_ids",{1,512,axes},idtype}};
  if(flux1)fields.push_back({"pooled_text",{1,cw}});fields.push_back({"timestep",{1}});if(flux1)fields.push_back({"guidance",{1}});fields.push_back({"target_mask",{-1},ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64});fields.push_back({"normal_mask",{-1},ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64});if(!flux1)fields.push_back({"reference_mask",{-1},ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64});if(!flux1&&embedded_guidance)fields.push_back({"guidance",{1}});
  {TypedGraph graph(env,workspace,std::string(pass)+"_flow",threads,fields,{{"velocity",{1,-1,channels}},{"target_indices",{-1},ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64}});
   auto predict=[&](Floats& cond,float time){Floats times={time},scale={guidance};std::vector<Ort::Value> args;std::vector<Floats> floating_ids;floating_ids.reserve(4);auto ids=[&](Integers& v,std::vector<int64_t> shape){if(flux1)args.push_back(integer_tensor(v,shape));else{floating_ids.emplace_back(v.begin(),v.end());args.push_back(tensor(floating_ids.back(),shape));}};
    args.push_back(tensor(state,{1,targets,channels}));ids(target_ids,{1,targets,axes});args.push_back(tensor(normal_tokens,{1,targets,channels}));ids(normal_ids,{1,targets,axes});args.push_back(tensor(ref_tokens,{1,side*side,channels}));ids(reference_ids,{1,side*side,axes});args.push_back(tensor(cond,{1,512,width}));ids(text_ids,{1,512,axes});if(flux1)args.push_back(tensor(pooled,{1,cw}));args.push_back(tensor(times,{1}));if(flux1)args.push_back(tensor(scale,{1}));args.push_back(integer_tensor(target_mask,{targets}));args.push_back(integer_tensor(normal_mask,{targets}));if(!flux1)args.push_back(integer_tensor(reference_mask,{side*side}));if(!flux1&&embedded_guidance)args.push_back(tensor(scale,{1}));auto result=graph.run(args);
    size_t active=std::count(target_mask.begin(),target_mask.end(),int64_t(1));auto velocity=values(result[0],{1,int64_t(active),channels});auto info=result[1].GetTensorTypeAndShapeInfo();require(info.GetShape()==std::vector<int64_t>{int64_t(active)},"UltraTex index shape mismatch");auto indices=result[1].GetTensorData<int64_t>();size_t k=0;for(int i=0;i<targets;i++)if(target_mask[i])require(indices[k++]==i,"UltraTex foreground index mismatch");return velocity;};
   for(int step=0;step<steps;step++){float now=ultra_sigma(step,steps,size),delta=ultra_sigma(step+1,steps,size)-now;auto prediction=predict(text,now);if(!flux1){auto negative=predict(negative_text,now);for(size_t j=0;j<prediction.size();j++)prediction[j]=negative[j]+guidance*(prediction[j]-negative[j]);}size_t k=0;for(int row=0;row<targets;row++)if(target_mask[row])for(int j=0;j<channels;j++){auto& v=state[size_t(row)*channels+j];v+=delta*prediction[k++];require(std::isfinite(v),"Nonfinite UltraTex sample");}event({{"event","progress"},{"stage",stage},{"step",step+1},{"steps",steps}});}
  }
  for(int row=0;row<targets;row++)if(!mask_atlas[row])std::copy_n(black_tokens.begin()+size_t(row)*channels,channels,state.begin()+size_t(row)*channels);
  event({{"event","stage"},{"stage",std::string("decoding_")+pass}});std::vector<Floats> decoded;{TypedGraph graph(env,workspace,std::string(pass)+"_decoder",threads,{{"latents",{1,channels,side,side}}},{{"image",{1,3,size,size}}});for(int i=0;i<6;i++){auto tile=ultra_tile(state,i,side,channels);std::vector<Ort::Value> args;args.push_back(tensor(tile,{1,channels,side,side}));auto result=graph.run(args);auto rgb=values(result[0],{1,3,size,size});for(float& f:rgb)f=std::round(std::clamp(f*.5f+.5f,0.f,1.f)*255)/255;decoded.push_back(hwc(rgb,size));}}materials.push_back(std::move(decoded));
 }
 event({{"event","stage"},{"stage","baking_material"}});auto atlas=unwrap(mesh,atlas_size);auto bake_geometry=ultra_geometry(atlas.mesh);std::vector<ViewMaterial> views;for(int i=0;i<6;i++){ViewMaterial v;v.camera=ultra_camera(i);v.geometry=render_material(bake_geometry,v.camera,size);v.albedo=std::move(materials[0][i]);v.mr=std::move(materials[1][i]);for(size_t j=0;j<v.mr.size()/3;j++){v.mr[j*3+2]=v.mr[j*3];v.mr[j*3]=1;}views.push_back(std::move(v));}auto baked=bake_material(atlas,bake_geometry,views);material_glb(output,atlas,baked);event({{"event","materialCoverage"},{"coveredTexels",baked.covered},{"unobservedTexels",baked.unobserved},{"unobservedFill","nearest_observed_texel"}});event({{"event","complete"},{"output",output.string()}});
}
}

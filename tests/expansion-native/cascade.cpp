#include "../../native/spatial/uniforge.hpp"
#include "../../native/spatial/supra.hpp"
#include "../../native/spatial/sam.hpp"
#include <iostream>
int main(int argc,char** argv){using namespace lma_spatial;try{require(argc==2,"Need one cascade fixture");std::ifstream file(argv[1]);json p;file>>p;std::string op=p.at("operation");
 if(op=="generate"){events=stdout;if(sam_pipeline(p.at("command").at("pipeline").get<std::string>()))sam_generate(p.at("command"));else if(p.at("command").at("pipeline")=="supratex")supra_generate(p.at("command"));else uniforge_generate(p.at("command"));}
 else if(op=="sam_resize"){std::cout<<json(sam_resize(p.at("pixels").get<Floats>(),p.at("iw"),p.at("ih"),p.at("ow"),p.at("oh"),p.at("channels"),p.value("nearest",false))).dump();}
 else if(op=="sam_inputs"){SamImage image;image.w=p.at("width");image.h=p.at("height");image.rgb=p.at("rgb").get<Floats>();image.mask=p.at("mask").get<Floats>();image.points=p.at("points").get<Floats>();image.valid=p.at("valid").get<Floats>();auto result=sam_inputs(image,p.at("size"),p.at("preprocessing"),true);std::cout<<json({{"inputs",result.values},{"scale",result.moments.scale},{"shift",result.moments.shift}}).dump();}
 else if(op=="sam_occupancy"){int factor=1;std::mt19937 random(42);auto coords=sam_occupancy(p.at("occupancy").get<Floats>(),p.at("grid"),p.at("prune"),p.at("maximum"),factor,random);std::cout<<json({{"coords",coords},{"factor",factor}}).dump();}
 else if(op=="sam_pose"){SamMoments moments;moments.scale=p.at("scale");moments.shift=p.at("shift").get<std::array<float,3>>();std::cout<<sam_pose(p.at("values").get<Floats>(),sam_heads(p.at("heads")),moments,p.at("convention"),p.at("factor")).dump();}
 else if(op=="sam_sampling"){
  auto heads=sam_heads(p.at("heads"));SamNoise noise(uint32_t(p.at("seed").get<int>()));auto before=noise;auto first=before(sam_head_size(heads));auto fusion=sam_fusion(p.at("fusion"),p.at("structure"));std::vector<lma_sparse::Coord> coords;if(p.contains("coords"))coords=p.at("coords").get<std::vector<lma_sparse::Coord>>();auto schedule=sam_schedule(p.at("schedule"),p.at("steps"));json calls=json::array();
  auto predict=[&](size_t view,const Floats& x,float t,float d,int branch,bool capture){calls.push_back({{"view",view},{"state",x},{"t",t},{"d",d},{"branch",branch},{"capture",capture}});SamPrediction r;r.velocity=x;for(float& v:r.velocity)v=v*.1f+float(view+1)+branch*.3f;r.queries=p.at("queries");r.keys=5;r.heads=2;r.width=2;r.q.assign(r.queries*4,.1f*(view+1));r.k.resize(20);for(size_t i=0;i<20;i++)r.k[i]=std::sin(float(i+view));if(!fusion.structure)r.coarse=p.at("coarse").get<std::vector<lma_sparse::Coord>>();return r;};
  auto sample=sam_sample(p.at("views"),heads,schedule,fusion,coords,p.value("pointmapCfg",false),noise,predict);std::cout<<json({{"value",sample.value},{"weights",sample.weights},{"calls",calls},{"firstNoise",first}}).dump();
 }
 else if(op=="supra_visible"){auto coords=p.at("coords").get<std::vector<lma_sparse::Coord>>();std::cout<<json(supra_visible(coords,p.at("alpha").get<std::vector<uint8_t>>(),supra_camera(p.at("camera")),p.at("size"),p.at("grid"))).dump();}
 else if(op=="supra_messages"){std::cout<<json(supra_messages(p.at("raw").get<Floats>(),p.at("observed").get<std::vector<lma_sparse::Coord>>(),p.at("surface").get<std::vector<lma_sparse::Coord>>(),p.at("visible").get<std::vector<uint8_t>>(),p.at("shape").get<std::vector<lma_sparse::Coord>>(),p.at("normalization"))).dump();}
 else if(op=="fdg"){auto mesh=read_glb(p.at("mesh").get<std::string>());auto r=voxelize_dual_grid(mesh,p.at("grid"));std::cout<<json({{"coords",r.coords},{"vertices",r.vertices},{"flags",r.flags}}).dump();}
 else if(op=="handoff"){Mesh mesh;mesh.vertices=p.at("vertices").get<std::vector<Point>>();mesh.indices=p.at("indices").get<std::vector<uint32_t>>();std::cout<<json(surface_cells(mesh,p.at("grid"),p.value("maxRows",20000))).dump();}
 else if(op=="occupancy"){auto pair=occupancy_support(p.at("logits").get<Floats>(),p.at("grid"),p.at("maxRows"));std::cout<<json({{"low",pair.first},{"high",pair.second}}).dump();}
 else if(op=="guidance"){std::cout<<json(cascade_guidance(p.at("sample").get<Floats>(),p.at("positive").get<Floats>(),p.at("negative").get<Floats>(),p.at("time"),p.at("strength"),p.at("rescale"),p.at("dense"))).dump();}
 else if(op=="resize"){std::cout<<json(lanczos_image(p.at("pixels").get<Floats>(),p.at("input"),p.at("output"))).dump();}
 else if(op=="images"){std::vector<fs::path> paths;for(auto v:p.at("files"))paths.emplace_back(v.get<std::string>());auto result=cascade_images(paths);std::cout<<json({{"views",result.views},{"dino512",result.dino512},{"vggt",result.vggt},{"masks",result.masks}}).dump();}
 else if(op=="volume"){auto coords=p.at("coords").get<std::vector<lma_sparse::Coord>>();auto features=p.at("features").get<Floats>();MaterialVolume volume(coords,features,p.at("grid"),p.at("channels"));json out=json::array();for(auto v:p.at("points"))out.push_back(volume.sample(v.get<Point>()));std::cout<<out.dump();}
 else throw std::runtime_error("Unknown cascade fixture");return 0;
 }catch(const std::exception& e){std::cerr<<e.what();return 1;}}

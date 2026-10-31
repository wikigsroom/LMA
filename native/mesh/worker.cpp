#include "../worker_common.hpp"
#include "trellis_run.h"
using namespace lma_worker;
int main(int argc, char** argv) {
 if(argc == 2 && !std::strcmp(argv[1], "--info")) {
   std::puts("{\"engine\":\"trellis_native\",\"backend\":\"cpu\",\"pipelines\":[\"trellis2\",\"pixal3d\"],\"modelInferenceTested\":false,\"modelDownloads\":false}");
   return 0;
 }
 try {
  initialize(); require(argc==2,"Supply one private request"); auto value=request(argv[1]);
  require(value.at("type")=="mesh.generate","Unsupported 3D task"); std::string pipeline=value.at("pipeline");
  require(pipeline=="trellis2"||pipeline=="pixal3d","Unsupported 3D pipeline");
  auto params=value.at("parameters"); trellis::TrellisParams p; p.image=regular(value,"referenceImage");
  p.models=value.at("workspace"); p.output=value.at("output");
  require(std::filesystem::path(p.models).is_absolute() && std::filesystem::is_directory(p.models) &&
          std::filesystem::path(p.output).is_absolute() && !std::filesystem::exists(p.output),"Invalid private model/output path");
  p.family=pipeline=="pixal3d"?trellis::ModelFamily::Pixal3D:trellis::ModelFamily::Trellis;
  p.backend="CPU"; p.gpu=-1; p.sched=0; p.threads=integer(params,"threads",2,1,16);
  int resolution=integer(params,"resolution",512,512,1024); require(resolution==512||resolution==1024,"Unsupported 3D resolution"); p.set_res(resolution);
  p.texture=params.value("texture",pipeline=="trellis2"); require(!(pipeline=="pixal3d"&&resolution==512&&p.texture),"Pixal3D has no 512 texture flow");
  p.seed=uint32_t(integer(params,"seed",1234,0,2147483647)); p.steps=integer(params,"steps",12,1,50);
  p.faces=integer(params,"faces",30000,1000,150000); p.tex=integer(params,"atlas",1024,256,2048);
  p.gss=p.gsh=number(params,"guidance",7.5f,0,15); p.fov_deg=number(params,"fov",49.13f,10,120);
  p.webp=0; p.verbose=false; p.dump_bg=false; p.retopo=false;
  // Use the explicitly chosen BiRefNet if available; otherwise preserve PNG alpha / threshold matte.
  p.birefnet=std::filesystem::is_regular_file(std::filesystem::path(p.models)/"birefnet.gguf")?-1:0;
  event({{"event","execution"},{"details",{{"pipeline",pipeline},{"backend","cpu"},{"effectiveParameters",params},
       {"cameraFov","user_selected_no_MoGe"},{"textureRequested",p.texture},{"resolution",resolution}}}});
  event({{"event","stage"},{"stage","generating_mesh"}});
  require(trellis_run(p)==0 && std::filesystem::is_regular_file(p.output),"3D engine did not finish");
  event({{"event","complete"},{"output",p.output}}); return 0;
 } catch(const std::exception&) { if(events)event({{"event","error"},{"message","3D generation failed: check model components, image and available memory."}}); }
 return 1;
}

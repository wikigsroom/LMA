#include "../worker_common.hpp"
#include "trellis_run.h"
#include "transforms_json.h"
#include "proj_grid.h"
int trellis_run_mv(const trellis::TrellisParams&);
using namespace lma_worker;
static int selected_steps=12, selected_faces=30000;
int lma_mv_steps(){return selected_steps;}
int lma_mv_faces(){return selected_faces;}
void lma_mv_stage(const char* value){event({{"event","stage"},{"stage",value}});}
int main(int argc,char**argv) {
 if(argc==2 && !std::strcmp(argv[1],"--info")) {
  std::puts("{\"engine\":\"pixal_multiview\",\"backend\":\"cpu\",\"pipelines\":[\"pixal3d_mv\"],\"views\":4,\"modelInferenceTested\":false,\"modelDownloads\":false}");return 0;
 }
 try {
  initialize();require(argc==2,"Supply a private request");auto v=request(argv[1]);
  require(v.at("type")=="mesh.generate" && v.at("pipeline")=="pixal3d_mv","Unsupported multiview task");
  auto params=v.at("parameters");trellis::TrellisParams p;
  p.models=v.at("workspace");p.output=v.at("output");p.views=v.at("viewsDirectory");
  require(std::filesystem::path(p.models).is_absolute()&&std::filesystem::is_directory(p.models),"Invalid model workspace");
  require(std::filesystem::path(p.output).is_absolute()&&!std::filesystem::exists(p.output),"Invalid output path");
  require(std::filesystem::path(p.views).is_absolute()&&std::filesystem::is_directory(p.views),"Invalid view directory");
  p.gpu=-1;p.gpu_set=true;p.require_gpu=false;p.threads=integer(params,"threads",2,1,16);
  p.set_res(1024);p.texture=params.value("texture",true);p.webp=0;p.tex=integer(params,"atlas",1024,256,2048);
  p.max_tokens=integer(params,"maxTokens",8192,1024,49152);p.pixal3d_weights="mv";p.pixal3d_weights_set=true;
  p.seed=uint32_t(integer(params,"seed",1234,1,2147483647));p.gss=p.gsh=number(params,"guidance",7.5f,0,15);
  selected_steps=integer(params,"steps",12,1,50);selected_faces=integer(params,"faces",30000,1000,150000);
  const std::vector<std::string> names={"00_front.png","01_right.png","02_back.png","03_left.png"};
  for(const auto& name:names) {auto f=std::filesystem::path(p.views)/name;
    require(std::filesystem::is_regular_file(f)&&!std::filesystem::is_symlink(f)&&std::filesystem::file_size(f)<=16*1024*1024,"Missing or oversized view");
    std::ifstream input(f,std::ios::binary);unsigned char h[29]{};input.read(reinterpret_cast<char*>(h),29);
    const unsigned char signature[]={137,80,78,71,13,10,26,10};
    require(input.gcount()==29&&std::memcmp(h,signature,8)==0&&h[8]==0&&h[9]==0&&h[10]==0&&h[11]==13&&std::memcmp(h+12,"IHDR",4)==0,"Each view must be a PNG");
    auto u32=[](const unsigned char* p){return (uint32_t(p[0])<<24)|(uint32_t(p[1])<<16)|(uint32_t(p[2])<<8)|uint32_t(p[3]);};
    const uint64_t w=u32(h+16),height=u32(h+20);
    require(w>0&&height>0&&w*height<=4194304&&h[24]==8&&h[25]==6&&h[26]==0&&h[27]==0&&h[28]<=1,"Use bounded 8-bit RGBA PNG views");}
  trellis::TransformsFile cameras;std::string error;auto custom=params.value("cameraPoses",std::string());
  if(custom.empty()) {
   require(trellis::synthesize_canonical_rig(names,number(params,"meshScale",1,0.1f,10),cameras,error),"Cannot construct camera rig");
  } else {
   require(custom.size()<=16000,"Camera parameters exceed limits");auto j=json::parse(custom);
   require(j.is_object() && j.size()==1 && j.contains("frames") && j.at("frames").is_array() && j.at("frames").size()==4,"Supply exactly four camera frames");
   cameras.mesh_scale=number(params,"meshScale",1,0.1f,10);
   for(size_t i=0;i<4;++i) {
    auto f=j.at("frames").at(i);require(f.is_object()&&f.size()==2&&f.contains("transform_matrix")&&f.contains("camera_angle_x"),"Invalid camera fields");
    auto a=f.at("transform_matrix");require(a.is_array()&&a.size()==4,"Camera must be a 4x4 transform");
    trellis::TransformsFrame frame;frame.file_path=names[i];frame.camera_angle_x=f.at("camera_angle_x").get<float>();frame.has_camera_angle_x=true;
    require(std::isfinite(frame.camera_angle_x)&&frame.camera_angle_x>0&&frame.camera_angle_x<3.14159265f,"Invalid camera FOV");
    for(size_t row=0;row<4;++row) {require(a.at(row).is_array()&&a.at(row).size()==4,"Camera must be a 4x4 transform");
     for(size_t col=0;col<4;++col) {float n=a.at(row).at(col).get<float>();require(std::isfinite(n)&&std::abs(n)<=10000,"Invalid camera value");frame.transform_matrix[row*4+col]=n;}}
    require(std::abs(frame.transform_matrix[12])<1e-6f&&std::abs(frame.transform_matrix[13])<1e-6f&&std::abs(frame.transform_matrix[14])<1e-6f&&std::abs(frame.transform_matrix[15]-1)<1e-6f,"Camera must be affine");
    const auto& m=frame.transform_matrix;
    require(m[3]*m[3]+m[7]*m[7]+m[11]*m[11]>1e-12f,"Camera cannot be at the origin");
    for(int row=0;row<3;++row)for(int other=row;other<3;++other){
     float dot=0;for(int col=0;col<3;++col)dot+=m[row*4+col]*m[other*4+col];
     require(std::abs(dot-(row==other?1.f:0.f))<1e-3f,"Camera rotation must be orthonormal");}
    const float determinant=m[0]*(m[5]*m[10]-m[6]*m[9])-m[1]*(m[4]*m[10]-m[6]*m[8])+m[2]*(m[4]*m[9]-m[5]*m[8]);
    require(std::abs(determinant-1)<1e-3f,"Camera rotation cannot be a reflection");
    cameras.frames.push_back(frame);
   }
  }
  require(trellis::write_transforms_json((std::filesystem::path(p.views)/"transforms.json").string(),cameras,error),"Cannot persist selected cameras");
  event({{"event","execution"},{"details",{{"pipeline","pixal3d_mv"},{"backend","cpu"},{"views",4},{"effectiveParameters",params},{"cameraSource",custom.empty()?"canonical_turntable_explicit_scale":"user_camera_transforms"}}}});
  require(trellis_run_mv(p)==0&&std::filesystem::is_regular_file(p.output),"Multiview engine did not finish");
  event({{"event","complete"},{"output",p.output}});return 0;
 }catch(const std::exception&) {if(events)event({{"event","error"},{"message","Multiview generation failed: check four RGBA views, cameras, matching MV components and available memory."}});}
 return 1;
}

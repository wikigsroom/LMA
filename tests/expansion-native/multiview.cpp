#include "proj_grid.h"
#include "transforms_json.h"
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <filesystem>
int main(int argc,char** argv){
 using namespace trellis;int count=0;auto check=[&](bool v){if(!v)throw std::runtime_error("Camera/projection contract failed");++count;};
 const std::vector<std::string> names={"00_front.png","01_right.png","02_back.png","03_left.png"};TransformsFile tf;std::string error;
 check(synthesize_canonical_rig(names,1,tf,error));check(tf.frames.size()==4);check(std::abs(tf.camera_angle_x-float(M_PI/9))<1e-6);
 check(!synthesize_canonical_rig({"one.png","two.png","three.png"},1,tf,error));check(!synthesize_canonical_rig(names,0,tf,error));
 check(synthesize_canonical_rig(names,1,tf,error));
 for(const auto& f:tf.frames){double d=0;for(int row=0;row<3;row++)d+=f.transform_matrix[row*4+3]*f.transform_matrix[row*4+3];check(std::abs(std::sqrt(d)-3.119204998)<1e-5);}
 std::string path=(std::filesystem::path(argv[1])/"cameras.json").string();check(write_transforms_json(path,tf,error));TransformsFile parsed;check(load_transforms_json(path,parsed));check(parsed.frames.size()==4&&parsed.mesh_scale==1);
 double identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1},inverse[16];check(mat4_inverse_d(identity,inverse));bool equal=true;for(int i=0;i<16;i++)equal&=inverse[i]==identity[i];check(equal);
 double singular[16]={};check(!mat4_inverse_d(singular,inverse));
 float views[64]={};for(int v=0;v<4;v++)for(int i=0;i<16;i++)views[16*v+i]=float(identity[i]);
 views[16]=0;views[17]=-1;views[20]=1;views[21]=0;views[35]=3;views[59]=-2;
 std::vector<float> calc;mv_calc_mats(views,4,3,calc);check(calc.size()==64);
 const double front[16]={1,0,0,0,0,0,-1,-3,0,1,0,0,0,0,0,1};
 for(int v=0;v<4;v++){bool correct=true;for(int r=0;r<4;r++)for(int c=0;c<4;c++){double expected=0;for(int k=0;k<4;k++)expected+=front[r*4+k]*views[v*16+k*4+c];correct&=std::abs(calc[v*16+r*4+c]-expected)<1e-6;}check(correct);}
 Camera camera{};camera.fov_x=.6911f;camera.distance=2;camera.mesh_scale=1;camera.has_c2w=false;
 std::vector<float> constant(16*16,7.f);auto samples=proj_grid_sample(constant.data(),1,16,16,2,512,camera);check(samples.size()==8);for(float v:samples)check(std::abs(v-7)<1e-6);
 std::vector<float> pix,norm;std::vector<uint8_t> valid;proj_grid_project(2,512,camera,pix,norm,valid);
 for(int k=0;k<4;k++){check(std::abs(pix[k*2]+pix[(k+4)*2]-512)<1e-3);check(std::abs(pix[k*2+1]-pix[(k+4)*2+1])<1e-3);}
 std::cout<<"{\"passed\":"<<count<<",\"trained_model\":false}";return 0;
}

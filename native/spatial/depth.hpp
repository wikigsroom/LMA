#pragma once
#include "../rf_shape/geometry.hpp"
#include <Eigen/Core>
#include <unsupported/Eigen/NonLinearOptimization>
#include <unsupported/Eigen/NumericalDiff>
#include <random>
namespace lma_spatial {
using lma_worker::require;
struct DepthCamera {std::array<float,9> intrinsics{};std::array<float,16> world_to_camera{};};
inline DepthCamera da3_camera(const std::array<float,9>& pose,int h,int w){
 require(h>=2&&w>=2&&h<=2048&&w<=2048,"Invalid DA3 image dimensions");for(float x:pose)require(std::isfinite(x),"Nonfinite DA3 pose");
 float i=pose[3],j=pose[4],k=pose[5],r=pose[6],norm=i*i+j*j+k*k+r*r;require(norm>1e-20f,"Invalid DA3 rotation");float s=2.f/norm;
 std::array<float,9> R={1-s*(j*j+k*k),s*(i*j-k*r),s*(i*k+j*r),s*(i*j+k*r),1-s*(i*i+k*k),s*(j*k-i*r),s*(i*k-j*r),s*(j*k+i*r),1-s*(i*i+j*j)};
 DepthCamera out;for(int a=0;a<3;a++){for(int b=0;b<3;b++)out.world_to_camera[a*4+b]=R[b*3+a];for(int b=0;b<3;b++)out.world_to_camera[a*4+3]-=R[b*3+a]*pose[b];}out.world_to_camera[15]=1;
 out.intrinsics={float(w/2.)/std::max(std::tan(pose[8]/2.f),1e-6f),0,float(w/2.),0,float(h/2.)/std::max(std::tan(pose[7]/2.f),1e-6f),float(h/2.),0,0,1};return out;
}
struct FocalObjective {
 using Scalar=double;enum {InputsAtCompileTime=Eigen::Dynamic,ValuesAtCompileTime=Eigen::Dynamic};
 using InputType=Eigen::VectorXd;using ValueType=Eigen::VectorXd;using JacobianType=Eigen::MatrixXd;
 std::vector<std::array<double,5>> samples;
 int inputs()const{return 1;}int values()const{return int(samples.size()*2);}
 double focal(double shift)const{double num=0,den=0;for(const auto& s:samples){double z=s[2]+shift;if(std::abs(z)<1e-30)return std::numeric_limits<double>::quiet_NaN();for(int a=0;a<2;a++){double xy=s[a]/z;num+=xy*s[3+a];den+=xy*xy;}}return den>1e-30?num/den:std::numeric_limits<double>::quiet_NaN();}
 int operator()(const InputType& input,ValueType& value)const{double shift=input[0],f=focal(shift);if(!std::isfinite(f))return -1;value.resize(values());for(size_t n=0;n<samples.size();n++){const auto& s=samples[n];for(int a=0;a<2;a++)value[int(n*2+a)]=f*s[a]/(s[2]+shift)-s[3+a];}return 0;}
};
struct MoGeRecovery {float focal,shift;std::array<float,9> intrinsics;};
inline MoGeRecovery moge_recover(const std::vector<float>& points,const std::vector<float>& mask,int h,int w,float threshold){
 require(h>=2&&w>=2&&h<=2048&&w<=2048&&points.size()==size_t(h)*w*3&&mask.size()==size_t(h)*w&&std::isfinite(threshold),"Invalid MoGe point map");
 for(float x:points)require(std::isfinite(x),"Nonfinite MoGe points");for(float x:mask)require(std::isfinite(x),"Nonfinite MoGe mask");
 FocalObjective objective;double aspect=double(w)/h,span_x=aspect/std::sqrt(1+aspect*aspect),span_y=1/std::sqrt(1+aspect*aspect);
 for(int y=0;y<64;y++)for(int x=0;x<64;x++){int py=y*h/64,px=x*w/64;size_t row=size_t(py)*w+px;if(mask[row]<=threshold)continue;
  float u=float(-span_x*(w-1)/w+2*span_x*px/w),v=float(-span_y*(h-1)/h+2*span_y*py/h);
  objective.samples.push_back({points[row*3],points[row*3+1],points[row*3+2],u,v});}
 float focal=1,shift=0;
 if(objective.samples.size()>=2){Eigen::NumericalDiff<FocalObjective> numerical(objective);Eigen::LevenbergMarquardt<Eigen::NumericalDiff<FocalObjective>,double> solver(numerical);solver.parameters.ftol=1e-3;solver.parameters.maxfev=400;Eigen::VectorXd x(1);x[0]=0;int status=solver.minimize(x);
  require(status>0&&status<5&&std::isfinite(x[0]),"MoGe focal/shift fitting did not converge");shift=float(x[0]);focal=float(objective.focal(shift));require(std::isfinite(focal)&&focal>0,"Invalid recovered MoGe focal length");}
 float fx=float(focal/2*std::sqrt(1+aspect*aspect)/aspect),fy=float(focal/2*std::sqrt(1+aspect*aspect));return {focal,shift,{fx,0,.5f,0,fy,.5f,0,0,1}};
}
inline std::vector<float> da3_unproject(const std::vector<float>& depth,int h,int w,const std::array<float,9>& intrinsics,bool sam_axes){
 require(h>=2&&w>=2&&h<=2048&&w<=2048&&depth.size()==size_t(h)*w,"Invalid depth raster");for(float x:intrinsics)require(std::isfinite(x),"Nonfinite depth intrinsics");require(intrinsics[0]>0&&intrinsics[4]>0,"Invalid depth focal length");
 std::vector<float> points(depth.size()*3);float sign=sam_axes?-1.f:1.f;
 for(int y=0;y<h;y++)for(int x=0;x<w;x++){size_t row=size_t(y)*w+x;float z=depth[row];require(std::isfinite(z)&&z>=0,"Nonfinite or negative depth");points[row*3]=sign*(x-intrinsics[2])*z/intrinsics[0];points[row*3+1]=sign*(y-intrinsics[5])*z/intrinsics[4];points[row*3+2]=z;}return points;
}
inline float depth_quantile(std::vector<float> values,float q,std::mt19937& random,bool replacement){
 require(!values.empty()&&q>=0&&q<=1,"Invalid depth quantile");for(float x:values)require(std::isfinite(x),"Nonfinite depth quantile input");
 if(values.size()>100000){if(replacement){std::vector<float> sampled(100000);std::uniform_int_distribution<size_t> choose(0,values.size()-1);for(float& x:sampled)x=values[choose(random)];values=std::move(sampled);}else {std::shuffle(values.begin(),values.end(),random);values.resize(100000);}}
 std::sort(values.begin(),values.end());double index=double(q)*(values.size()-1);size_t low=size_t(index),high=std::min(low+1,values.size()-1);return values[low]+float(index-low)*(values[high]-values[low]);
}
inline float da3_nested_align(std::vector<float>& depth,std::vector<float>& confidence,const std::vector<float>& metric,const std::vector<float>& sky,std::vector<DepthCamera>& cameras,int h,int w,std::mt19937& random){
 size_t pixels=size_t(h)*w,n=pixels*cameras.size();require(h>=2&&w>=2&&h<=2048&&w<=2048&&!cameras.empty()&&cameras.size()<=8&&n<=8388608&&depth.size()==n&&confidence.size()==n&&metric.size()==n&&sky.size()==n,"Invalid DA3 nested tensors");
 std::vector<float> confidences,scaled(n);size_t nonsky=0;
 for(size_t i=0;i<n;i++){require(std::isfinite(depth[i])&&std::isfinite(confidence[i])&&std::isfinite(metric[i])&&std::isfinite(sky[i]),"Nonfinite DA3 nested fields");auto& K=cameras[i/pixels].intrinsics;scaled[i]=metric[i]*((K[0]+K[4])/2.f/300.f);if(sky[i]<.3f){nonsky++;confidences.push_back(confidence[i]);}}
 require(nonsky>10,"Insufficient DA3 non-sky alignment support");float median=depth_quantile(confidences,.5f,random,false);double num=0,den=0;
 for(size_t i=0;i<n;i++)if(confidence[i]>=median&&sky[i]<.3f&&scaled[i]>.01f&&depth[i]>.001f){num+=double(scaled[i])*depth[i];den+=double(depth[i])*depth[i];}
 float scale=float(num/std::max(den,1e-12));require(std::isfinite(scale)&&scale>0,"DA3 metric alignment has no valid scale");
 std::vector<float> nonsky_depth;for(size_t i=0;i<n;i++){depth[i]*=scale;if(sky[i]<.3f)nonsky_depth.push_back(depth[i]);}
 for(auto& camera:cameras)for(int a=0;a<3;a++)camera.world_to_camera[a*4+3]*=scale;
 float max_depth=std::min(depth_quantile(nonsky_depth,.99f,random,true),200.f);for(size_t i=0;i<n;i++)if(sky[i]>=.3f){depth[i]=max_depth;confidence[i]=1;}return scale;
}
}

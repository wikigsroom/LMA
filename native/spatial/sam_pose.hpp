#pragma once
#include "sam_sampling.hpp"
#include "sam_geometry.hpp"
#include <Eigen/Geometry>
namespace lma_spatial {
inline json sam_pose(const std::vector<float>& values,const std::vector<SamHead>& heads,const SamMoments& moments,const std::string& convention,int factor){
 require(factor==1||factor==2,"Invalid SAM structure downsample factor");if(convention=="default")return json::object();require(convention=="ScaleShiftInvariant"||convention=="ZeroPredictionScaleShiftInvariant"||convention=="ApparentSize"||convention=="DisparitySpace","Unsupported SAM pose convention");
 std::map<std::string,std::vector<float>> fields;size_t offset=0;for(auto& head:heads){require(offset+head.rows*head.channels<=values.size(),"Invalid SAM pose heads");fields[head.name]=std::vector<float>(values.begin()+offset,values.begin()+offset+head.rows*head.channels);offset+=head.rows*head.channels;}
 auto field=[&](const std::string& name,size_t size){auto found=fields.find(name);require(found!=fields.end()&&found->second.size()==size,"Missing or unmatched SAM pose head");lma_sparse::finite(found->second);return found->second;};
 auto translation=field("translation",3),scale=field("scale",3),ts=field("translation_scale",1);std::array<float,4> rotation{};
 if(fields.count("6drotation_normalized")||fields.count("6drotation")){bool normalized=fields.count("6drotation_normalized");auto raw=field(normalized?"6drotation_normalized":"6drotation",6);
  const float mean[6]={-.06366084883674913f,.008438224692279752f,.00017084786438302483f,.0007126610473540038f,-.0030916726538816417f,.5166093753457688f};const float stddev[6]={.6656971967514863f,.6787012271867754f,.30345010594844524f,.4394504420678794f,.39817973931717104f,.6176286868761914f};if(normalized)for(int i=0;i<6;i++)raw[i]=raw[i]*stddev[i]+mean[i];
  Eigen::Vector3f a(raw[0],raw[1],raw[2]),b(raw[3],raw[4],raw[5]);require(a.norm()>1e-12f,"Degenerate SAM pose rotation");a.normalize();b-=a.dot(b)*a;require(b.norm()>1e-12f,"Degenerate SAM pose basis");b.normalize();Eigen::Matrix3f matrix;matrix.col(0)=a;matrix.col(1)=b;matrix.col(2)=a.cross(b);Eigen::Quaternionf q(matrix);q.normalize();float sign=q.w()<0?-1.f:1.f;rotation={q.w()*sign,q.x()*sign,q.y()*sign,q.z()*sign};
 }else {auto q=field("quaternion",4);std::copy(q.begin(),q.end(),rotation.begin());float norm=0;for(float x:rotation)norm+=x*x;require(norm>1e-20f,"Invalid SAM quaternion");for(float& x:rotation)x/=std::sqrt(norm);}
 if(convention=="ZeroPredictionScaleShiftInvariant"){translation={0,0,0};scale={1.337f,1.337f,1.337f};ts={0};}
 float translation_scale=std::exp(ts[0]);for(float& x:scale)x=std::exp(x);float f=moments.scale;
 if(convention=="ApparentSize"){f*=translation_scale;for(float& x:translation)x*=f;}
 else if(convention=="DisparitySpace"){f*=translation_scale*std::exp(moments.shift[2]);translation[2]=1;for(int a=0;a<2;a++)translation[a]+=moments.shift[a];for(float& x:translation)x*=f;}
 else for(int a=0;a<3;a++)translation[a]=translation[a]*f+moments.shift[a];
 float isotropic=(scale[0]+scale[1]+scale[2])/3*f*factor;require(std::isfinite(isotropic)&&isotropic>0,"Nonfinite SAM pose scale");lma_sparse::finite(translation);return {{"translation",translation},{"rotationWXYZ",rotation},{"scale",{isotropic,isotropic,isotropic}},{"convention",convention}};
}
}

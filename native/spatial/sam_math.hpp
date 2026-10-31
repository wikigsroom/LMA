#pragma once
#include "sparse.hpp"
#include <functional>
namespace lma_spatial {
// The native coordinator observes projected/normalized source Q,K at warmup.
// Average heads before patch renormalization, matching MV-SAM3D; entropy of
// separate heads is a different algorithm and is intentionally not used.
inline std::vector<float> sam_patch_entropy(const std::vector<float>& q,const std::vector<float>& k,size_t queries,size_t keys,size_t heads,size_t width,size_t begin,size_t end){
 using lma_worker::require;
 require(heads>=1&&heads<=64&&width>=1&&width<=256&&queries>0&&keys>1&&keys<=16384&&begin<end&&end<=keys&&end-begin>1,"Invalid SAM attention entropy profile");
 require(q.size()==lma_sparse::bounded(queries,heads*width)&&k.size()==lma_sparse::bounded(keys,heads*width)&&uint64_t(queries)*keys*heads*width<=64000000000ULL,"SAM entropy work budget exceeded");lma_sparse::finite(q);lma_sparse::finite(k);
 std::vector<float> entropy(queries);std::vector<double> scores(keys),patch(end-begin);double scale=1/std::sqrt(double(width));
 for(size_t row=0;row<queries;row++){
  std::fill(patch.begin(),patch.end(),0);
  for(size_t head=0;head<heads;head++){double maximum=-std::numeric_limits<double>::infinity();for(size_t key=0;key<keys;key++){double sum=0;for(size_t d=0;d<width;d++)sum+=double(q[(row*heads+head)*width+d])*k[(key*heads+head)*width+d];scores[key]=sum*scale;maximum=std::max(maximum,scores[key]);}
   double total=0;for(double& x:scores){x=std::exp(x-maximum);total+=x;}require(total>0&&std::isfinite(total),"Invalid SAM entropy softmax");for(size_t key=begin;key<end;key++)patch[key-begin]+=scores[key]/total/heads;
  }
  double total=0,h=0;for(double x:patch)total+=x;total=std::max(total,1e-10);for(double x:patch){double p=x/total;h-=p*std::log(p+1e-10);}entropy[row]=float(h/std::log(double(end-begin)));
 }
 lma_sparse::finite(entropy);return entropy;
}
inline std::vector<std::vector<float>> sam_fusion_weights(const std::vector<std::vector<float>>& entropy,float alpha,float temperature,float minimum){
 using lma_worker::require;require(!entropy.empty()&&entropy.size()<=8&&alpha>=0&&alpha<=1000&&temperature>0&&temperature<=100&&minimum>=0&&minimum<=1,"Invalid SAM fusion parameters");
 size_t rows=entropy[0].size();require(rows>0&&rows<=lma_sparse::point_limit,"Invalid SAM weight support");for(auto& v:entropy){require(v.size()==rows,"Unaligned SAM view weights");lma_sparse::finite(v);}
 std::vector<std::vector<float>> weights(entropy.size(),std::vector<float>(rows));
 for(size_t row=0;row<rows;row++){double maximum=-std::numeric_limits<double>::infinity(),sum=0;for(auto& view:entropy)maximum=std::max(maximum,-double(alpha)*view[row]/temperature);
  for(size_t view=0;view<entropy.size();view++){weights[view][row]=float(std::exp(-double(alpha)*entropy[view][row]/temperature-maximum));sum+=weights[view][row];}
  double renorm=0;for(auto& view:weights){view[row]=std::max(float(view[row]/sum),minimum);renorm+=view[row];}for(auto& view:weights)view[row]=float(view[row]/renorm);
 }return weights;
}
inline std::vector<std::vector<float>> sam_expand_weights(const std::vector<std::vector<float>>& weights,const std::vector<lma_sparse::Coord>& coarse,const std::vector<lma_sparse::Coord>& original,int factor){
 using lma_worker::require;require(factor>=1&&factor<=16,"Invalid SAM weight pooling");lma_sparse::coordinates(coarse);lma_sparse::coordinates(original);
 std::map<lma_sparse::Coord,size_t> index;for(size_t i=0;i<coarse.size();i++)index.emplace(coarse[i],i);std::vector<std::vector<float>> output(weights.size(),std::vector<float>(original.size()));
 for(const auto& v:weights)require(v.size()==coarse.size(),"Unmatched coarse SAM weights");
 for(size_t row=0;row<original.size();row++){auto c=original[row];for(int a=1;a<4;a++)c[a]/=factor;auto found=index.find(c);require(found!=index.end(),"SAM attention coordinates do not match source pooling");for(size_t v=0;v<weights.size();v++)output[v][row]=weights[v][found->second];}return output;
}
inline std::vector<float> sam_cfg(const std::vector<float>& conditional,const std::vector<float>& unconditional,const std::vector<float>& without_points,float strength,float point_strength,bool pointmap_cfg){
 using lma_worker::require;require(conditional.size()==unconditional.size()&&(!pointmap_cfg||without_points.size()==conditional.size())&&std::isfinite(strength)&&std::isfinite(point_strength)&&strength>=0&&strength<=100&&point_strength>=0&&point_strength<=100,"Invalid SAM classifier-free guidance");
 lma_sparse::finite(conditional);lma_sparse::finite(unconditional);if(pointmap_cfg)lma_sparse::finite(without_points);
 std::vector<float> output(conditional.size());for(size_t i=0;i<output.size();i++)output[i]=pointmap_cfg?conditional[i]+point_strength*(conditional[i]-without_points[i])+strength*(without_points[i]-unconditional[i]):(1+strength)*conditional[i]-strength*unconditional[i];lma_sparse::finite(output);return output;
}
struct SamSchedule {int steps=25;float rescale=1,time_scale=1000;bool reversed=false,shortcut=false,no_shortcut=false;std::string solver="euler";};
using SamDynamics=std::function<std::vector<float>(const std::vector<float>&,float,float)>;
inline std::vector<float> sam_integrate(std::vector<float> state,const SamSchedule& schedule,const SamDynamics& dynamics,const std::function<void(int)>& progress={}){
 using lma_worker::require;require(!state.empty()&&state.size()<=lma_sparse::tensor_limit&&schedule.steps>=1&&schedule.steps<=100&&std::isfinite(schedule.rescale)&&schedule.rescale>0&&schedule.rescale<=100&&std::isfinite(schedule.time_scale)&&schedule.time_scale>0&&schedule.time_scale<=10000,"Invalid SAM schedule");
 require(schedule.solver=="euler"||schedule.solver=="midpoint"||schedule.solver=="rk4","Unsupported SAM ODE solver");lma_sparse::finite(state);
 auto time=[&](int step){double t=double(step)/schedule.steps;t=t/(1+(schedule.rescale-1)*(1-t));return float(schedule.reversed?1-t:t);};
 float shortcut=schedule.shortcut&&!schedule.no_shortcut?schedule.time_scale/schedule.steps:0;
 auto evaluate=[&](const std::vector<float>& value,float t){auto result=dynamics(value,t*schedule.time_scale,shortcut);require(result.size()==state.size(),"SAM velocity size mismatch");lma_sparse::finite(result);return result;};
 auto advance=[&](const std::vector<float>& value,const std::vector<float>& velocity,float step){std::vector<float> out(value.size());for(size_t i=0;i<out.size();i++)out[i]=value[i]+velocity[i]*step;return out;};
 for(int step=0;step<schedule.steps;step++){float t=time(step),dt=time(step+1)-t;auto a=evaluate(state,t);
  if(schedule.solver=="midpoint"){auto b=evaluate(advance(state,a,dt*.5f),t+dt*.5f);state=advance(state,b,dt);}
  else if(schedule.solver=="rk4"){auto b=evaluate(advance(state,a,dt*.5f),t+dt*.5f),c=evaluate(advance(state,b,dt*.5f),t+dt*.5f),d=evaluate(advance(state,c,dt),t+dt);for(size_t i=0;i<state.size();i++)state[i]+=dt/6.f*(a[i]+2*b[i]+2*c[i]+d[i]);}
  else state=advance(state,a,dt);
  lma_sparse::finite(state);if(progress)progress(step+1);
 }return state;
}
}

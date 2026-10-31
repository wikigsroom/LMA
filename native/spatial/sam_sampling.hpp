#pragma once
#include "sam_math.hpp"
#include <random>
#include <set>
namespace lma_spatial {
using lma_worker::require;
struct SamHead {std::string name;size_t rows=0,channels=0;float strength=0,point_strength=0,interval_start=0,interval_end=0;bool interval=false;};
struct SamPrediction {std::vector<float> velocity,q,k;std::vector<lma_sparse::Coord> coarse;size_t queries=0,keys=0,heads=0,width=0;};
using SamPredict=std::function<SamPrediction(size_t,const std::vector<float>&,float,float,int,bool)>;
struct SamNoise {std::mt19937 random;std::normal_distribution<float> normal;explicit SamNoise(uint32_t seed):random(seed){}std::vector<float> operator()(size_t n){require(n>0&&n<=lma_sparse::tensor_limit,"SAM noise budget exceeded");std::vector<float> value(n);for(float& x:value)x=normal(random);return value;}};
inline size_t sam_head_size(const std::vector<SamHead>& heads){size_t total=0;require(!heads.empty()&&heads.size()<=16,"Invalid SAM latent heads");std::set<std::string> names;for(const auto& h:heads){require(names.insert(h.name).second&&h.rows>0&&h.rows<=262144&&h.channels>=1&&h.channels<=512&&std::isfinite(h.strength)&&h.strength>=0&&h.strength<=100&&std::isfinite(h.point_strength)&&h.point_strength>=0&&h.point_strength<=100&&std::isfinite(h.interval_start)&&std::isfinite(h.interval_end)&&h.interval_start<=h.interval_end,"Invalid SAM latent head");total+=lma_sparse::bounded(h.rows,h.channels);require(total<=lma_sparse::tensor_limit,"SAM latent tensor budget exceeded");}require(names.count("shape"),"SAM shape head is required");return total;}
inline std::vector<float> sam_guided(size_t view,const std::vector<float>& state,float time,float shortcut,const std::vector<SamHead>& heads,bool pointmap,const SamPredict& predict,bool capture,SamPrediction& observed){
 auto conditional=predict(view,state,time,shortcut,0,capture);require(conditional.velocity.size()==state.size(),"SAM conditional width mismatch");if(capture)observed=conditional;
 bool guided=false;for(auto& head:heads)guided|=head.interval&&time>=head.interval_start&&time<=head.interval_end&&head.strength>0;
 // Publisher skips all CFG branches if every regular strength is zero,
 // including when a pointmap strength alone is nonzero.
 if(!guided)return conditional.velocity;
 auto uncond=predict(view,state,time,shortcut,1,false);SamPrediction no_points;if(pointmap)no_points=predict(view,state,time,shortcut,2,false);
 require(uncond.velocity.size()==state.size()&&(!pointmap||no_points.velocity.size()==state.size()),"SAM guidance branch mismatch");size_t offset=0;
 for(const auto& head:heads){bool active=head.interval&&time>=head.interval_start&&time<=head.interval_end;float s=active?head.strength:0,pm=active?head.point_strength:0;
  for(size_t i=offset;i<offset+head.rows*head.channels;i++){float c=conditional.velocity[i],u=uncond.velocity[i];conditional.velocity[i]=pointmap?c+pm*(c-no_points.velocity[i])+s*(no_points.velocity[i]-u):(1+s)*c-s*u;}offset+=head.rows*head.channels;}
 lma_sparse::finite(conditional.velocity);return conditional.velocity;
}
inline std::vector<float> sam_fuse(const std::vector<std::vector<float>>& predictions,const std::vector<SamHead>& heads,const std::vector<std::vector<float>>& weights){
 require(!predictions.empty()&&predictions.size()<=8,"Invalid SAM view count");size_t count=sam_head_size(heads);for(auto& p:predictions){require(p.size()==count,"Unmatched SAM view velocity");lma_sparse::finite(p);}require(weights.empty()||weights.size()==predictions.size(),"Unmatched SAM view weights");std::vector<float> result(count);size_t offset=0;
 for(const auto& head:heads){if(head.name!="shape"){std::copy_n(predictions[0].begin()+offset,head.rows*head.channels,result.begin()+offset);offset+=head.rows*head.channels;continue;}
  if(!weights.empty())for(auto& v:weights)require(v.size()==head.rows,"Unmatched SAM per-latent weights");
  for(size_t row=0;row<head.rows;row++)for(size_t ch=0;ch<head.channels;ch++){double sum=0;for(size_t view=0;view<predictions.size();view++)sum+=predictions[view][offset+row*head.channels+ch]*(weights.empty()?1./predictions.size():weights[view][row]);result[offset+row*head.channels+ch]=float(sum);}offset+=head.rows*head.channels;
 }lma_sparse::finite(result);return result;
}
struct SamFusion {bool enabled=true,structure=false;int warmup_steps=1,pooling=1;size_t patch_begin=1,patch_end=1370;float alpha=60,temperature=1,minimum=.001f;};
struct SamSample {std::vector<float> value;std::vector<std::vector<float>> weights;};
inline SamSample sam_sample(size_t views,const std::vector<SamHead>& heads,const SamSchedule& schedule,const SamFusion& fusion,const std::vector<lma_sparse::Coord>& coords,bool pointmap,SamNoise& noise,const SamPredict& predict,const std::function<void(int)>& progress={}){
 require(views>=1&&views<=8&&fusion.warmup_steps>=1&&fusion.warmup_steps<=100,"Invalid SAM sampling views");size_t count=sam_head_size(heads);SamSample result;std::vector<SamPrediction> observations(views);
 auto dynamics=[&](bool capture){return [&,capture](const std::vector<float>& value,float t,float d){std::vector<std::vector<float>> velocities;for(size_t view=0;view<views;view++)velocities.push_back(sam_guided(view,value,t,d,heads,pointmap,predict,capture,observations[view]));return sam_fuse(velocities,heads,result.weights);};};
 if(fusion.enabled&&views>1){SamNoise saved=noise;auto warmup=schedule;warmup.steps=fusion.structure?std::min(schedule.steps,fusion.warmup_steps):1;
  sam_integrate(noise(count),warmup,dynamics(true));std::vector<std::vector<float>> entropy;
  for(size_t view=0;view<views;view++){const auto& p=observations[view];entropy.push_back(sam_patch_entropy(p.q,p.k,p.queries,p.keys,p.heads,p.width,fusion.patch_begin,fusion.patch_end));if(!fusion.structure)require(p.coarse==observations[0].coarse,"SAM views returned different attention coordinates");}
  result.weights=sam_fusion_weights(entropy,fusion.alpha,fusion.temperature,fusion.minimum);
  if(!fusion.structure)result.weights=sam_expand_weights(result.weights,observations[0].coarse,coords,fusion.pooling);
  // Structure replay includes the normal distribution's cached sample. SLAT
  // deliberately consumes warmup noise before drawing a fresh main sample.
  if(fusion.structure)noise=saved;
 }
 result.value=sam_integrate(noise(count),schedule,dynamics(false),progress);return result;
}
}

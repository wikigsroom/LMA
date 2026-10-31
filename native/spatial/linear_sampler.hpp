#pragma once
#include "../worker_common.hpp"
namespace lma_spatial {
using namespace lma_worker;
// Exported UniPC coefficient programs contain no executable code or weights.
// Tensor slots are current sample/noise, corrected previous sample, and the
// previous three converted model outputs. History never crosses jobs/models.
class LinearSampler {
 json rows_;std::vector<float> last_,history_[3];size_t step_=0,count_;
 std::vector<float> evaluate(const json& coefficients,const std::vector<float>& sample,const std::vector<float>& noise){
  require(coefficients.is_array()&&coefficients.size()==6,"Invalid sampler coefficients");const std::vector<float>* slots[6]={&sample,&noise,&last_,&history_[0],&history_[1],&history_[2]};std::vector<float> out(count_,0);
  for(int k=0;k<6;k++){double a=coefficients[k];require(std::isfinite(a)&&std::abs(a)<1e8,"Invalid sampler coefficient");if(a==0)continue;require(slots[k]->size()==count_,"Missing sampler state");for(size_t j=0;j<count_;j++){out[j]+=float(a*(*slots[k])[j]);require(std::isfinite(out[j]),"Nonfinite sampler state");}}return out;
 }
public:
 float initial_noise=1;
 LinearSampler(const json& sampler,int steps,size_t count):count_(count){
  require(sampler.at("schema")=="lma.linear-unipc/1"&&sampler.at("diffusersVersion")=="0.35.1"&&steps>=1&&steps<=100&&count>0&&count<=32000000,"Unmatched sampler");
  require(sampler.at("slots")==json::array({"sample","noise","last_sample","model_latest","model_previous","model_oldest"}),"Sampler state order mismatch");
  auto profile=sampler.at("profiles").at(std::to_string(steps));rows_=profile.at("rows");require(rows_.is_array()&&rows_.size()==size_t(steps),"Sampler step profile missing");initial_noise=profile.at("initialNoiseSigma");require(std::isfinite(initial_noise)&&initial_noise>0&&initial_noise<=1000,"Invalid sampler noise scale");
 }
 float time() const{require(step_<rows_.size(),"Sampler finished");float t=rows_[step_].at("timestep");require(std::isfinite(t)&&t>=0&&t<=10000,"Invalid sampler timestep");return t;}
 void update(std::vector<float>& sample,const std::vector<float>& noise){
  require(step_<rows_.size()&&sample.size()==count_&&noise.size()==count_,"Sampler state shape mismatch");auto row=rows_[step_];auto converted=evaluate(row.at("model"),sample,noise),corrected=evaluate(row.at("lastSample"),sample,noise),next=evaluate(row.at("sample"),sample,noise);
  history_[2]=std::move(history_[1]);history_[1]=std::move(history_[0]);history_[0]=std::move(converted);last_=std::move(corrected);sample=std::move(next);step_++;
 }
};
}

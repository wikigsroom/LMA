#pragma once
#include "sparse.hpp"
#include <cstring>
namespace lma_sparse {
// UltraTex/SLA forward only: select K blocks using smoothed-key block means,
// then online softmax over selected original K/V. No dense Q*K allocation.
// CPU sums/tie ordering may differ from CUDA; no trained-output parity claim.
inline float bfloat(float x){uint32_t u;std::memcpy(&u,&x,4);u+=0x7fff+((u>>16)&1);u&=0xffff0000;std::memcpy(&x,&u,4);require(std::isfinite(x),"Block attention BF16 overflow");return x;}
inline Feats block_attention(const Feats& q,const Feats& k,const Feats& v,size_t batches,size_t heads,size_t length,size_t dim,const std::vector<int64_t>& policy){
 require(batches>=1&&batches<=8&&heads>=1&&heads<=64&&length>=1&&length<=65536&&dim>=1&&dim<=256&&batches*heads*length*dim<=tensor_limit,"Block attention dimensions exceed limits");
 require(q.size()==batches*heads*length*dim&&k.size()==q.size()&&v.size()==q.size()&&policy.size()==4,"Block attention tensor/policy mismatch");finite(q);finite(k);finite(v);
 int64_t qb=policy[0],kb=policy[1],ratio=policy[2],precision=policy[3];
 require(qb>=1&&qb<=1024&&kb>=1&&kb<=1024&&ratio>=1&&ratio<=1000000&&(precision==0||precision==1),"Block attention requires bounded blocks, ratio and FP32/BF16 policy");
 size_t qblocks=(length+size_t(qb)-1)/size_t(qb),kblocks=(length+size_t(kb)-1)/size_t(kb),top=std::min(kblocks,size_t((ratio*int64_t(kblocks))/1000000));
 require(top>0,"Block attention top-k has no keys for this support; select a compatible export");
 require(qblocks<=4000000/kblocks&&uint64_t(batches)*heads*length*std::min(length,top*size_t(kb))*dim<=32000000000ULL,"Block attention CPU work budget exceeded");
 Feats result(q.size());auto cast=[&](float x){return precision?bfloat(x):x;};float scale=1/std::sqrt(float(dim));
 for(size_t bh=0;bh<batches*heads;bh++){
  const size_t offset=bh*length*dim;Feats mean(dim,0),smooth(length*dim),pq(qblocks*dim,0),pk(kblocks*dim,0);
  // Publisher selection is computed before its BF16 execution cast. The
  // external graph's inputs are FP32, so selection preserves FP32 here.
  for(size_t i=0;i<length;i++)for(size_t d=0;d<dim;d++)mean[d]+=k[offset+i*dim+d];for(float& x:mean)x/=float(length);
  for(size_t i=0;i<length;i++)for(size_t d=0;d<dim;d++){smooth[i*dim+d]=k[offset+i*dim+d]-mean[d];pq[(i/size_t(qb))*dim+d]+=q[offset+i*dim+d];pk[(i/size_t(kb))*dim+d]+=smooth[i*dim+d];}
  for(size_t i=0;i<qblocks;i++)for(size_t d=0;d<dim;d++)pq[i*dim+d]/=float(std::min(size_t(qb),length-i*size_t(qb)));
  for(size_t i=0;i<kblocks;i++)for(size_t d=0;d<dim;d++)pk[i*dim+d]/=float(std::min(size_t(kb),length-i*size_t(kb)));
  Feats cq(length*dim),ck(length*dim),cv(length*dim);for(size_t i=0;i<cq.size();i++){cq[i]=cast(q[offset+i]);ck[i]=cast(k[offset+i]);cv[i]=cast(v[offset+i]);}
  for(size_t block=0;block<qblocks;block++){
   std::vector<std::pair<float,size_t>> ranked;ranked.reserve(kblocks);
   for(size_t j=0;j<kblocks;j++){float s=0;for(size_t d=0;d<dim;d++)s+=pq[block*dim+d]*pk[j*dim+d];require(std::isfinite(s),"Block selection score overflow");ranked.emplace_back(s,j);}
   // Torch topk(sorted=False) makes no tie/order guarantee. This portable
   // branch uses index order on ties and score order otherwise, explicitly.
   std::partial_sort(ranked.begin(),ranked.begin()+top,ranked.end(),[](const auto& a,const auto& b){return a.first==b.first?a.second<b.second:a.first>b.first;});
   for(size_t i=block*size_t(qb);i<std::min(length,(block+1)*size_t(qb));i++){
    float max=-INFINITY,total=0;Feats acc(dim,0),scores(size_t(kb),0);
    for(size_t b=0;b<top;b++){
     size_t begin=ranked[b].second*size_t(kb),count=std::min(size_t(kb),length-begin);float blockmax=-INFINITY;
     for(size_t j=0;j<count;j++){float s=0;for(size_t d=0;d<dim;d++)s+=cq[i*dim+d]*ck[(begin+j)*dim+d];scores[j]=s*scale;require(std::isfinite(scores[j]),"Block attention dot-product overflow");blockmax=std::max(blockmax,scores[j]);}
     float next=std::max(max,blockmax),alpha=std::exp(max-next);total*=alpha;for(float& x:acc)x*=alpha;
     for(size_t j=0;j<count;j++){float p=std::exp(scores[j]-next);total+=p;float dotp=cast(p);for(size_t d=0;d<dim;d++)acc[d]+=dotp*cv[(begin+j)*dim+d];}max=next;
    }
    require(total>0&&std::isfinite(total),"Invalid block attention normalization");for(size_t d=0;d<dim;d++)result[offset+i*dim+d]=cast(acc[d]/total);
   }
  }
 }
 finite(result);return result;
}
}

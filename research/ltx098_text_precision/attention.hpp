// SPDX-License-Identifier: MIT
// Isolated developer precision experiment; no model weights.
int bucket(int key,int query);
void precise_attention(ggml_tensor* dst,const ggml_tensor* q,const ggml_tensor* k,const ggml_tensor* v,int ith,int nth,void* tablep) {
    const int64_t width=q->ne[0],tokens=q->ne[1],heads=q->ne[2];
    const auto* qd=static_cast<const float*>(q->data);
    const auto* kd=static_cast<const float*>(k->data);
    const auto* vd=static_cast<const float*>(v->data);
    const auto* table=static_cast<const float*>(tablep);
    auto* output=static_cast<float*>(dst->data);
    std::vector<double> scores(static_cast<size_t>(tokens));
    for(int64_t job=ith;job<heads*tokens;job+=nth) {
        const auto head=job/tokens,query=job%tokens,base=head*tokens*width;
        double peak=-INFINITY;
        for(int64_t key=0;key<tokens;++key) {
            double sum=0;
            for(int64_t d=0;d<width;++d)sum+=double(qd[base+query*width+d])*kd[base+key*width+d];
            scores[key]=sum+table[bucket(static_cast<int>(key),static_cast<int>(query))*heads+head];
            peak=std::max(peak,scores[key]);
        }
        double total=0;
        for(auto& score:scores){score=std::exp(score-peak);total+=score;}
        for(int64_t d=0;d<width;++d) {
            double sum=0;
            for(int64_t key=0;key<tokens;++key)sum+=(scores[key]/total)*vd[base+key*width+d];
            output[base+query*width+d]=static_cast<float>(sum);
        }
    }
}

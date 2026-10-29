// SPDX-License-Identifier: MIT
// Isolated developer precision experiment; no model weights.
void precise_linear(ggml_tensor* dst,const ggml_tensor*,const ggml_tensor* weight,const ggml_tensor* input,int ith,int nth,void*) {
    const int64_t width=weight->ne[0],outputs=weight->ne[1],tokens=input->ne[1],total=outputs*tokens;
    const auto* w=static_cast<const float*>(weight->data);
    const auto* x=static_cast<const float*>(input->data);
    auto* y=static_cast<float*>(dst->data);
    for(int64_t i=ith;i<total;i+=nth) {
        const auto* roww=w+(i%outputs)*width;
        const auto* rowx=x+(i/outputs)*width;
        double a=0,b=0,c=0,d=0;
        for(int64_t k=0;k<width;k+=4) {
            a+=double(roww[k])*rowx[k];
            b+=double(roww[k+1])*rowx[k+1];
            c+=double(roww[k+2])*rowx[k+2];
            d+=double(roww[k+3])*rowx[k+3];
        }
        y[i]=static_cast<float>((a+b)+(c+d));
    }
}

// SPDX-License-Identifier: MIT
// Offline numerical candidate. No learned parameters or platform dependencies.
void accurate_normalize(ggml_tensor* dst,const ggml_tensor* input,const ggml_tensor* weight,int ith,int nth,void*) {
    const int64_t width=input->ne[0],rows=ggml_nelements(input)/width;
    const auto* x=static_cast<const float*>(input->data);
    const auto* w=static_cast<const float*>(weight->data);
    auto* y=static_cast<float*>(dst->data);
    for(int64_t row=ith;row<rows;row+=nth) {
        double a=0,b=0,c=0,d=0;
        for(int64_t k=0;k<width;k+=4) {
            const auto* p=x+row*width+k;
            a+=double(p[0])*p[0]; b+=double(p[1])*p[1];
            c+=double(p[2])*p[2]; d+=double(p[3])*p[3];
        }
        const double inverse=1.0/std::sqrt(((a+b)+(c+d))/double(width)+double(1e-6f));
        for(int64_t k=0;k<width;++k) y[row*width+k]=static_cast<float>(double(x[row*width+k])*inverse*double(w[k]));
    }
}
void accurate_geglu(ggml_tensor* dst,const ggml_tensor* gate,const ggml_tensor* up,int ith,int nth,void*) {
    const auto count=ggml_nelements(dst),begin=count*ith/nth,end=count*(ith+1)/nth;
    auto* y=static_cast<float*>(dst->data); const auto* g=static_cast<const float*>(gate->data); const auto* u=static_cast<const float*>(up->data);
    for(int64_t i=begin;i<end;++i) {
        const double v=g[i];
        y[i]=static_cast<float>((0.5*v*(1.0+std::tanh(0.7978845608028654*(v+0.044715*v*v*v))))*double(u[i]));
    }
}

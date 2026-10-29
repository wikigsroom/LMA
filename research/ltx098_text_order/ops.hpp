// SPDX-License-Identifier: MIT
// Preserve the original F32 NewGELU operation order, including the cubic term.
// No parameters or model-specific data are embedded here.
void original_order_geglu(ggml_tensor* dst,const ggml_tensor* gate,const ggml_tensor* up,int ith,int nth,void*) {
    const auto count=ggml_nelements(dst),begin=count*ith/nth,end=count*(ith+1)/nth;
    auto* y=static_cast<float*>(dst->data);
    const auto* g=static_cast<const float*>(gate->data);
    const auto* u=static_cast<const float*>(up->data);
    for(int64_t i=begin;i<end;++i) {
        const float v=g[i];
        const float cube=(v*v)*v;
        const float argument=0.7978845608028654f*(v+0.044715f*cube);
        y[i]=((0.5f*v)*(1.f+std::tanh(argument)))*u[i];
    }
}

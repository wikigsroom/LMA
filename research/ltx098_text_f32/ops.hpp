// SPDX-License-Identifier: MIT
// Match F32 square/mean/rsqrt/product staging at the validated T5 width 4096.
// Eight lanes, four streams, and groups of sixteen preserve the reviewed
// CPU reference's reduction order without requiring an x86 instruction set.
void staged_f32_normalize(ggml_tensor* dst,const ggml_tensor* input,const ggml_tensor* weight,int ith,int nth,void*) {
    const int64_t width=input->ne[0],rows=ggml_nelements(input)/width;
    const auto* x=static_cast<const float*>(input->data);
    const auto* w=static_cast<const float*>(weight->data);
    auto* y=static_cast<float*>(dst->data);
    for(int64_t row=ith;row<rows;row+=nth) {
        float streams[32]={};
        for(int64_t begin=0;begin<width;begin+=512) {
            float local[32]={};
            const int64_t end=std::min(width,begin+512);
            for(int64_t k=begin;k<end;++k) {
                const float value=x[row*width+k];
                const float square=value*value;
                local[(k-begin)%32]+=square;
            }
            for(int lane=0;lane<32;++lane) streams[lane]+=local[lane];
        }
        float total=0.f;
        for(int lane=0;lane<8;++lane) {
            float sum=streams[lane];
            sum+=streams[lane+8];sum+=streams[lane+16];sum+=streams[lane+24];
            total+=sum;
        }
        const float variance=total/static_cast<float>(width);
        const float inverse=1.f/std::sqrt(variance+1e-6f);
        for(int64_t k=0;k<width;++k) {
            const float normalized=x[row*width+k]*inverse;
            y[row*width+k]=normalized*w[k];
        }
    }
}

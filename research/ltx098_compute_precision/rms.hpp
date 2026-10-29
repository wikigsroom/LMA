// SPDX-License-Identifier: Apache-2.0
// Isolated CPU F32 reduction candidate; no parameters or model data.
void diagnostic_f32_rms(ggml_tensor* dst,const ggml_tensor* input,int ith,int nth,void* epsilon) {
    const int64_t width=input->ne[0],rows=ggml_nelements(input)/width;
    const auto* x=static_cast<const float*>(input->data);auto* y=static_cast<float*>(dst->data);
    const float eps=*static_cast<const float*>(epsilon);
    for(int64_t row=ith;row<rows;row+=nth) {
        float streams[32]={};
        for(int64_t begin=0;begin<width;begin+=512) {
            float local[32]={};
            for(int64_t k=begin;k<std::min(width,begin+512);++k) {
                const float v=x[row*width+k],square=v*v;
                local[(k-begin)%32]+=square;
            }
            for(int lane=0;lane<32;++lane)streams[lane]+=local[lane];
        }
        float total=0;
        for(int lane=0;lane<8;++lane) {
            float sum=streams[lane];sum+=streams[lane+8];sum+=streams[lane+16];sum+=streams[lane+24];total+=sum;
        }
        const float inverse=1.f/std::sqrt(total/static_cast<float>(width)+eps);
        for(int64_t k=0;k<width;++k)y[row*width+k]=x[row*width+k]*inverse;
    }
}
static float diagnostic_qk_epsilon=1e-5f;

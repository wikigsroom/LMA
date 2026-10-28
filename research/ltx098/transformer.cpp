// SPDX-License-Identifier: Apache-2.0
// Independent GGML port of Apache-licensed Lightricks/LTX-Video Transformer3DModel.
// No LLM-Hub implementation, model weights, tokenizer or model data are embedded.
#include "transformer.hpp"
#include "ggml.h"
#include "ggml-alloc.h"
#include "ggml-backend.h"
#include "ggml-cpu.h"
#include "gguf.h"
#ifdef LMA_LTX_VULKAN
#include "ggml-vulkan.h"
#endif
#include "json.hpp"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <map>
#include <set>
#include <stdexcept>

namespace lma::ltx098 {
using json = nlohmann::json;
static void require(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }
static bool finite(const std::vector<float>& values) { return std::all_of(values.begin(), values.end(), [](float v) { return std::isfinite(v); }); }
struct Context {
    ggml_context* value = nullptr;
    explicit Context(size_t bytes) { value = ggml_init({bytes, nullptr, true}); require(value != nullptr, "Graph metadata allocation failed"); }
    ~Context() { if (value) ggml_free(value); }
};
struct Transformer::Impl {
    gguf_context* metadata = nullptr;
    ggml_context* weights = nullptr;
    ggml_backend_t backend = nullptr;
    ggml_backend_buffer_t buffer = nullptr;
    std::map<std::string,ggml_tensor*> tensors;
    std::set<std::string> used;
    int dim = 0, heads = 0, layers = 0, channels = 0, caption = 0, threads = 0;
    float epsilon = 1e-6f, theta = 10000.f;
    uint64_t parameters = 0, weight_bytes = 0;
    std::string backend_name;
    ~Impl() {
        if (buffer) ggml_backend_buffer_free(buffer);
        if (weights) ggml_free(weights);
        if (metadata) gguf_free(metadata);
        if (backend) ggml_backend_free(backend);
    }
    ggml_tensor* weight(const std::string& name, int64_t first, int64_t second = 1) {
        auto found = tensors.find(name); require(found != tensors.end(), "Missing required transformer tensor");
        auto tensor = found->second;
        require(tensor->ne[0] == first && tensor->ne[1] == second && tensor->ne[2] == 1 && tensor->ne[3] == 1, "Transformer tensor shape mismatch");
        used.insert(name); return tensor;
    }
    void linear_weights(const std::string& name, int input, int output) { weight(name+".weight", input, output); weight(name+".bias", output); }
    ggml_tensor* matmul(ggml_context* ctx,ggml_tensor* a,ggml_tensor* b) {
        auto result=ggml_mul_mat(ctx,a,b);
        require(ggml_prec_set_acc(result,GGML_PREC_F32),"Cannot require float32 accumulation");
        require(ggml_prec_set_src(result,GGML_PREC_F32,1),"Cannot require float32 activation precision");
        return result;
    }
    void validate() {
        linear_weights("patchify_proj",channels,dim); linear_weights("proj_out",dim,channels); weight("scale_shift_table",dim,2);
        linear_weights("caption_projection.linear_1",caption,dim); linear_weights("caption_projection.linear_2",dim,dim);
        linear_weights("adaln_single.emb.timestep_embedder.linear_1",256,dim);
        linear_weights("adaln_single.emb.timestep_embedder.linear_2",dim,dim); linear_weights("adaln_single.linear",dim,6*dim);
        for(int i=0;i<layers;++i) {
            auto root="transformer_blocks."+std::to_string(i); weight(root+".scale_shift_table",dim,6);
            for(const auto& part : {std::string("attn1"),std::string("attn2")}) {
                auto name=root+"."+part;
                for(const auto& projection : {std::string("to_q"),std::string("to_k"),std::string("to_v"),std::string("to_out.0")}) linear_weights(name+"."+projection,dim,dim);
                weight(name+".q_norm.weight",dim); weight(name+".k_norm.weight",dim);
            }
            linear_weights(root+".ff.net.0.proj",dim,4*dim); linear_weights(root+".ff.net.2",4*dim,dim);
        }
        require(used.size()==tensors.size(),"Unexpected transformer tensors or wrong architecture"); used.clear();
    }
    ggml_tensor* linear(ggml_context* ctx, ggml_tensor* x, const std::string& name) {
        auto w=tensors.at(name+".weight"), b=tensors.at(name+".bias");
        return ggml_add(ctx,matmul(ctx,w,x),b);
    }
    ggml_tensor* rms(ggml_context* ctx,ggml_tensor* x,const std::string& name) {
        return ggml_mul(ctx,ggml_rms_norm(ctx,x,1e-5f),tensors.at(name+".weight"));
    }
    ggml_tensor* rope(ggml_context* ctx,ggml_tensor* x,ggml_tensor* cosine,ggml_tensor* sine) {
        auto even=ggml_view_3d(ctx,x,1,dim/2,x->ne[1],2*sizeof(float),dim*sizeof(float),0);
        auto odd=ggml_view_3d(ctx,x,1,dim/2,x->ne[1],2*sizeof(float),dim*sizeof(float),sizeof(float));
        auto rotated=ggml_reshape_2d(ctx,ggml_concat(ctx,ggml_neg(ctx,odd),even,0),dim,x->ne[1]);
        return ggml_add(ctx,ggml_mul(ctx,x,cosine),ggml_mul(ctx,rotated,sine));
    }
    ggml_tensor* attention(ggml_context* ctx,ggml_tensor* x,ggml_tensor* context,const std::string& name,
                           ggml_tensor* cosine,ggml_tensor* sine,ggml_tensor* mask) {
        auto q=rms(ctx,linear(ctx,x,name+".to_q"),name+".q_norm");
        auto k=rms(ctx,linear(ctx,context?context:x,name+".to_k"),name+".k_norm");
        auto v=linear(ctx,context?context:x,name+".to_v");
        if(!context) { q=rope(ctx,q,cosine,sine); k=rope(ctx,k,cosine,sine); }
        int64_t queries=x->ne[1], keys=v->ne[1], head=dim/heads;
        // The pinned Vulkan backend stages non-contiguous matrix inputs as F16.
        // Materialize head-major F32 tensors before attention matmul instead.
        q=ggml_cont(ctx,ggml_permute(ctx,ggml_reshape_3d(ctx,q,head,heads,queries),0,2,1,3));
        k=ggml_cont(ctx,ggml_permute(ctx,ggml_reshape_3d(ctx,k,head,heads,keys),0,2,1,3));
        v=ggml_cont(ctx,ggml_permute(ctx,ggml_reshape_3d(ctx,v,head,heads,keys),1,2,0,3));
        auto scores=ggml_scale(ctx,matmul(ctx,k,q),1.f/std::sqrt(float(head)));
        if(mask) scores=ggml_add(ctx,scores,mask);
        auto probabilities=ggml_soft_max(ctx,scores);
        auto result=matmul(ctx,v,probabilities);
        result=ggml_reshape_2d(ctx,ggml_cont(ctx,ggml_permute(ctx,result,0,2,1,3)),dim,queries);
        return linear(ctx,result,name+".to_out.0");
    }
    ggml_tensor* chunk(ggml_context* ctx,ggml_tensor* values,int index) {
        return ggml_view_2d(ctx,values,dim,values->ne[1],values->nb[1],index*dim*sizeof(float));
    }
    ggml_tensor* modulate(ggml_context* ctx,ggml_tensor* x,ggml_tensor* shift,ggml_tensor* scale) {
        return ggml_add(ctx,ggml_add(ctx,x,ggml_mul(ctx,x,scale)),shift);
    }
    ggml_tensor* gelu(ggml_context* ctx,ggml_tensor* x,ggml_tensor* one) {
        // ggml_gelu's CPU float16 lookup is not the publisher's float32 tanh path.
        auto cube=ggml_mul(ctx,ggml_mul(ctx,x,x),x);
        auto inner=ggml_scale(ctx,ggml_add(ctx,x,ggml_scale(ctx,cube,.044715f)),.7978845608028654f);
        return ggml_mul(ctx,ggml_scale(ctx,x,.5f),ggml_add(ctx,ggml_tanh(ctx,inner),one));
    }
};

Transformer::Transformer(const std::string& path,const std::string& selected,int count,bool allow_fixture):impl(new Impl) {
    auto& m=*impl;
    require(count>=1 && count<=32,"Thread count outside 1..32"); m.threads=count;
    require(selected=="cpu" || selected=="vulkan","Unsupported backend");
    m.metadata=gguf_init_from_file(path.c_str(),{true,&m.weights}); require(m.metadata && m.weights,"Invalid GGUF metadata");
    auto key=gguf_find_key(m.metadata,"general.architecture");
    require(key>=0 && gguf_get_kv_type(m.metadata,key)==GGUF_TYPE_STRING && std::string(gguf_get_val_str(m.metadata,key))=="lma-ltx-video-098","Wrong GGUF architecture");
    key=gguf_find_key(m.metadata,"ltx098.config"); require(key>=0 && gguf_get_kv_type(m.metadata,key)==GGUF_TYPE_STRING,"Missing LTX098 config");
    const char* raw=gguf_get_val_str(m.metadata,key); require(std::char_traits<char>::length(raw)<16384,"Oversized config"); auto cfg=json::parse(raw);
    auto number=[&](const char* name,int lo,int hi) { require(cfg.contains(name)&&cfg[name].is_number_integer(),"Invalid integer config"); require(cfg[name]>=lo&&cfg[name]<=hi,"Config outside bounds"); return cfg[name].get<int>(); };
    m.heads=number("num_attention_heads",1,32); int head=number("attention_head_dim",2,128); m.dim=m.heads*head;
    m.layers=number("num_layers",1,28); m.channels=number("in_channels",1,128); m.caption=number("caption_channels",1,4096);
    require(m.dim>=12 && m.dim<=2048 && m.dim%2==0,"Invalid hidden size"); require(number("out_channels",1,128)==m.channels,"Wrong output channels");
    require(number("cross_attention_dim",1,2048)==m.dim,"Wrong cross attention width");
    require(cfg.value("activation_fn",std::string())=="gelu-approximate" && cfg.value("standardization_norm",std::string())=="rms_norm" && cfg.value("qk_norm",std::string())=="rms_norm","Unsupported normalization or activation");
    require(cfg.value("attention_type",std::string())=="default" && cfg.value("adaptive_norm",std::string("single_scale_shift"))=="single_scale_shift","Unsupported block layout");
    require(!cfg.value("norm_elementwise_affine",true) && cfg.value("attention_bias",false) && !cfg.value("only_cross_attention",true) && !cfg.value("double_self_attention",true),"Unsupported architecture flags");
    require(cfg.value("positional_embedding_type",std::string())=="rope" && cfg.value("positional_embedding_theta",0.f)==10000.f && cfg.value("positional_embedding_max_pos",std::vector<int>())==std::vector<int>({20,2048,2048}),"Wrong rotary layout");
    require(cfg.value("norm_eps",0.f)==1e-6f && cfg.value("timestep_scale_multiplier",0.f)==1000.f && cfg.value("dropout",-1.f)==0.f,"Unsupported model constants");
    bool original=m.dim==2048&&m.heads==32&&head==64&&m.layers==28&&m.channels==128&&m.caption==4096;
    require(original||allow_fixture,"Synthetic shape requires explicit research fixture mode");
    int64_t total=gguf_get_n_tensors(m.metadata); require(total>0 && total<=1000,"Too many transformer tensors");
    for(int64_t i=0;i<total;++i) {
        const char* name=gguf_get_tensor_name(m.metadata,i); auto tensor=ggml_get_tensor(m.weights,name); require(tensor!=nullptr,"Missing GGUF tensor");
        require(tensor->type==GGML_TYPE_F32 || tensor->type==GGML_TYPE_F16,"Unreviewed tensor encoding");
        std::string tensor_name(name);
        require(tensor->type==GGML_TYPE_F32 || (tensor->ne[1]>1 && tensor_name.size()>7 && tensor_name.substr(tensor_name.size()-7)==".weight"),"Only dense weights may use float16");
        m.tensors.emplace(name,tensor); m.parameters+=ggml_nelements(tensor); m.weight_bytes+=ggml_nbytes(tensor);
    }
    m.validate();
    if(selected=="cpu") { m.backend=ggml_backend_cpu_init(); if(m.backend) ggml_backend_cpu_set_n_threads(m.backend,count); }
#ifdef LMA_LTX_VULKAN
    else {
        // This pinned backend's cooperative/subgroup paths may convert F32
        // inputs to F16 internally. Require baseline float32 GPU arithmetic;
        // F16 dense weight storage remains supported by the fallback shaders.
        // These flags affect this standalone worker process, never the system.
#ifdef _WIN32
        require(_putenv_s("GGML_VK_DISABLE_COOPMAT2","1")==0,"Cannot set Vulkan precision policy");
        require(_putenv_s("GGML_VK_DISABLE_COOPMAT","1")==0,"Cannot set Vulkan precision policy");
        require(_putenv_s("GGML_VK_DISABLE_F16","1")==0,"Cannot set Vulkan precision policy");
#else
        require(setenv("GGML_VK_DISABLE_COOPMAT2","1",1)==0,"Cannot set Vulkan precision policy");
        require(setenv("GGML_VK_DISABLE_COOPMAT","1",1)==0,"Cannot set Vulkan precision policy");
        require(setenv("GGML_VK_DISABLE_F16","1",1)==0,"Cannot set Vulkan precision policy");
#endif
        m.backend=ggml_backend_vk_init(0);
    }
#else
    else throw std::runtime_error("Vulkan was not compiled; no implicit CPU fallback");
#endif
    require(m.backend!=nullptr,"Selected backend unavailable"); m.backend_name=selected;
    m.buffer=ggml_backend_alloc_ctx_tensors(m.weights,m.backend); require(m.buffer!=nullptr,"Model weights exceed backend allocation");
    auto file=std::ifstream(std::filesystem::u8path(path),std::ios::binary); require(bool(file),"Unable to read GGUF weights");
    uint64_t data_offset=gguf_get_data_offset(m.metadata); file.seekg(0,std::ios::end); uint64_t length=uint64_t(file.tellg());
    std::vector<uint8_t> bytes;
    for(int64_t i=0;i<total;++i) {
        auto tensor=m.tensors.at(gguf_get_tensor_name(m.metadata,i)); uint64_t offset=gguf_get_tensor_offset(m.metadata,i), size=ggml_nbytes(tensor);
        require(data_offset<=length && offset<=length-data_offset && size<=length-data_offset-offset,"Truncated GGUF weights");
        bytes.resize(size); file.seekg(std::streamoff(data_offset+offset)); file.read(reinterpret_cast<char*>(bytes.data()),std::streamsize(size)); require(bool(file),"Unable to read complete tensor");
        ggml_backend_tensor_set(tensor,bytes.data(),0,size);
    }
}
Transformer::~Transformer()=default;

Result Transformer::forward(const Input& input) {
    auto& m=*impl; int n=input.tokens, text=input.text_tokens;
    require(n>=1&&n<=4096&&text>=1&&text<=256,"Input token count outside research budget");
    require(input.latents.size()==size_t(n*m.channels)&&input.context.size()==size_t(text*m.caption)&&input.coordinates.size()==size_t(3*n),"Input shape mismatch");
    require(input.timesteps.size()==1 || input.timesteps.size()==size_t(n),"Timestep must be global or per-token");
    require(input.text_mask.size()==size_t(text)&&std::any_of(input.text_mask.begin(),input.text_mask.end(),[](float v){return v==1.f;}),"Text mask must retain a token");
    require(finite(input.latents)&&finite(input.context)&&finite(input.coordinates)&&finite(input.timesteps)&&finite(input.text_mask),"Non-finite input");
    require(std::all_of(input.timesteps.begin(),input.timesteps.end(),[](float v){return v>=0&&v<=1;}),"Sigma outside 0..1");
    require(std::all_of(input.text_mask.begin(),input.text_mask.end(),[](float v){return v==0.f||v==1.f;}),"Text mask is not binary");
    Context ctx(32*1024*1024); auto c=ctx.value;
    std::vector<std::pair<ggml_tensor*,const std::vector<float>*>> bindings;
    auto tensor=[&](int width,int rows,const std::vector<float>& values) { auto t=ggml_new_tensor_2d(c,GGML_TYPE_F32,width,rows); ggml_set_input(t); bindings.push_back({t,&values}); return t; };
    auto x=tensor(m.channels,n,input.latents), context=tensor(m.caption,text,input.context);
    int times=int(input.timesteps.size()); std::vector<float> sinusoid(256*times),cosine(n*m.dim,1.f),sine(n*m.dim,0.f),bias(text);
    for(int j=0;j<times;++j) for(int i=0;i<128;++i) {
        float value=input.timesteps[j]*1000.f*std::exp(-std::log(10000.f)*float(i)/128.f);
        sinusoid[j*256+i]=std::cos(value); sinusoid[j*256+i+128]=std::sin(value);
    }
    for(int j=0;j<n;++j) for(int i=0;i<m.dim/6;++i) for(int axis=0;axis<3;++axis) {
        // Match float32 torch.linspace's symmetric endpoint evaluation.
        int frequencies=m.dim/6; float step=1.f/float(frequencies-1);
        float exponent=i<frequencies/2 ? step*float(i) : 1.f-step*float(frequencies-i-1);
        float frequency=std::pow(10000.f,exponent); frequency=frequency*float(3.14159265358979323846/2);
        float position=input.coordinates[axis*n+j]/float(axis==0?20:2048);
        float angle=frequency*(position*2.f-1.f); int offset=j*m.dim+m.dim%6+6*i+2*axis;
        cosine[offset]=cosine[offset+1]=std::cos(angle); sine[offset]=sine[offset+1]=std::sin(angle);
    }
    for(int i=0;i<text;++i) bias[i]=(1.f-input.text_mask[i])*-10000.f;
    std::vector<float> ones{1.f}; auto one=tensor(1,1,ones);
    auto co=tensor(m.dim,n,cosine),si=tensor(m.dim,n,sine),mask=tensor(text,1,bias),time=tensor(256,times,sinusoid);
    auto embedded=m.linear(c,ggml_silu(c,m.linear(c,time,"adaln_single.emb.timestep_embedder.linear_1")),"adaln_single.emb.timestep_embedder.linear_2");
    auto modulation=m.linear(c,ggml_silu(c,embedded),"adaln_single.linear");
    context=m.linear(c,m.gelu(c,m.linear(c,context,"caption_projection.linear_1"),one),"caption_projection.linear_2");
    x=m.linear(c,x,"patchify_proj");
    for(int layer=0;layer<m.layers;++layer) {
        auto root="transformer_blocks."+std::to_string(layer);
        auto table=ggml_reshape_2d(c,m.tensors.at(root+".scale_shift_table"),6*m.dim,1);
        auto mods=ggml_add(c,modulation,table);
        auto normalized=m.modulate(c,ggml_rms_norm(c,x,m.epsilon),m.chunk(c,mods,0),m.chunk(c,mods,1));
        x=ggml_add(c,x,ggml_mul(c,m.attention(c,normalized,nullptr,root+".attn1",co,si,nullptr),m.chunk(c,mods,2)));
        x=ggml_add(c,x,m.attention(c,x,context,root+".attn2",nullptr,nullptr,mask));
        normalized=m.modulate(c,ggml_rms_norm(c,x,m.epsilon),m.chunk(c,mods,3),m.chunk(c,mods,4));
        auto ff=m.linear(c,m.gelu(c,m.linear(c,normalized,root+".ff.net.0.proj"),one),root+".ff.net.2");
        x=ggml_add(c,x,ggml_mul(c,ff,m.chunk(c,mods,5)));
    }
    auto shift=ggml_add(c,embedded,ggml_view_1d(c,m.tensors.at("scale_shift_table"),m.dim,0));
    auto scale=ggml_add(c,embedded,ggml_view_1d(c,m.tensors.at("scale_shift_table"),m.dim,m.dim*sizeof(float)));
    x=m.linear(c,m.modulate(c,ggml_norm(c,x,1e-6f),shift,scale),"proj_out"); ggml_set_output(x);
    auto graph=ggml_new_graph_custom(c,16384,false); ggml_build_forward_expand(graph,x);
    auto allocator=ggml_gallocr_new(ggml_backend_get_default_buffer_type(m.backend)); require(allocator!=nullptr,"Graph allocator unavailable");
    struct Free { ggml_gallocr_t value; ~Free(){ggml_gallocr_free(value);} } cleanup{allocator};
    require(ggml_gallocr_alloc_graph(allocator,graph),"Graph compute allocation failed");
    for(const auto& binding:bindings) ggml_backend_tensor_set(binding.first,binding.second->data(),0,binding.second->size()*sizeof(float));
    require(ggml_backend_graph_compute(m.backend,graph)==GGML_STATUS_SUCCESS,"Transformer compute failed");
    Result result; result.velocity.resize(n*m.channels); ggml_backend_tensor_get(x,result.velocity.data(),0,result.velocity.size()*sizeof(float));
    require(finite(result.velocity),"Non-finite transformer output"); result.layers=m.layers; result.parameters=m.parameters;
    result.weight_bytes=m.weight_bytes; result.compute_bytes=ggml_gallocr_get_buffer_size(allocator,0); result.backend=m.backend_name; return result;
}
} // namespace lma::ltx098

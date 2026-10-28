// SPDX-License-Identifier: MIT
#include "graph.hpp"
#include "ggml.h"
#include "ggml-alloc.h"
#include "ggml-backend.h"
#include "gguf.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <map>
#include <utility>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#else
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#endif

namespace lma::ltx098::text {
namespace {
struct Mapping {
    void* data=nullptr; size_t bytes=0;
#ifdef _WIN32
    HANDLE file=INVALID_HANDLE_VALUE, mapping=nullptr;
#else
    int file=-1;
#endif
    ~Mapping() {
#ifdef _WIN32
        if(data) UnmapViewOfFile(data); if(mapping) CloseHandle(mapping); if(file!=INVALID_HANDLE_VALUE) CloseHandle(file);
#else
        if(data) ::munmap(data,bytes); if(file>=0) ::close(file);
#endif
    }
    void open(const std::filesystem::path& path) {
        bytes=static_cast<size_t>(std::filesystem::file_size(path)); require(bytes>0 && bytes<=size_t(8)*1024*1024*1024,"T5 file exceeds mapping limit");
#ifdef _WIN32
        file=CreateFileW(path.c_str(),GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
        require(file!=INVALID_HANDLE_VALUE,"Cannot open T5 mapping"); mapping=CreateFileMappingW(file,nullptr,PAGE_READONLY,0,0,nullptr);
        require(mapping!=nullptr,"Cannot create T5 mapping"); data=MapViewOfFile(mapping,FILE_MAP_READ,0,0,0);
#else
        file=::open(path.c_str(),O_RDONLY); require(file>=0,"Cannot open T5 mapping"); data=::mmap(nullptr,bytes,PROT_READ,MAP_PRIVATE,file,0);
        if(data==MAP_FAILED) data=nullptr;
#endif
        require(data!=nullptr,"Cannot map T5 weights");
    }
};
template<class T,void(*Free)(T*)> using Owned=std::unique_ptr<T,decltype(Free)>;
using Context=Owned<ggml_context,ggml_free>;
using Gguf=Owned<gguf_context,gguf_free>;
using Buffer=Owned<ggml_backend_buffer,ggml_backend_buffer_free>;
using Backend=Owned<ggml_backend,ggml_backend_free>;
using Allocator=Owned<ggml_gallocr,ggml_gallocr_free>;
void f32_geglu(ggml_tensor* dst,const ggml_tensor* gate,const ggml_tensor* up,int ith,int nth,void*) {
    const auto count=ggml_nelements(dst); const auto begin=count*ith/nth,end=count*(ith+1)/nth;
    auto* y=static_cast<float*>(dst->data); const auto* x=static_cast<const float*>(gate->data); const auto* u=static_cast<const float*>(up->data);
    for(int64_t i=begin;i<end;++i) { const float v=x[i]; y[i]=0.5f*v*(1.0f+std::tanh(0.7978845608028654f*(v+0.044715f*v*v*v)))*u[i]; }
}
int bucket(int key,int query) {
    int relative=key-query; int result=relative>0?16:0; int distance=std::abs(relative);
    return result+(distance<8 ? distance : std::min(15,8+static_cast<int>(std::log(static_cast<double>(distance)/8)/std::log(16.0)*8)));
}
}
struct Graph::State {
    Mapping mapping;
    Gguf metadata{nullptr,gguf_free}; Context tensors{nullptr,ggml_free}; Backend backend{nullptr,ggml_backend_free}; Buffer weights{nullptr,ggml_backend_buffer_free};
    Layout layout; Buffers buffers; int threads; Cancel cancel; Progress progress; std::map<std::string,ggml_tensor*> named;
    State(const Layout& l,int t,Cancel c,Progress p):layout(l),threads(t),cancel(std::move(c)),progress(std::move(p)) {}
    bool interrupted() noexcept { try{return cancel && cancel();}catch(...){return true;} }
    void stop(){require(!interrupted(),"T5 execution cancelled");}
    ggml_tensor* tensor(const std::string& name,int64_t a,int64_t b=1) {
        auto it=named.find(name);require(it!=named.end(),"Missing T5 tensor"); auto* t=it->second;
        require(t->ne[0]==a && t->ne[1]==b && t->ne[2]==1 && t->ne[3]==1,"Unexpected T5 tensor shape");return t;
    }
};
Graph::Graph(const std::filesystem::path& path,const Layout& layout,int threads,Cancel cancel,Progress progress)
    :state_(std::make_unique<State>(layout,threads,std::move(cancel),std::move(progress))) {
    auto& s=*state_;s.stop();s.mapping.open(path);ggml_context* ctx=nullptr;
    s.buffers.mapped_file_bytes=s.mapping.bytes;
    s.metadata.reset(gguf_init_from_file(path.u8string().c_str(),{true,&ctx}));s.tensors.reset(ctx);
    require(s.metadata && s.tensors,"Cannot read T5 GGUF tensors");
    require(gguf_get_n_tensors(s.metadata.get())==9*layout.layers+3,"Unexpected T5 tensor count");
    auto device=ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_CPU);require(device!=nullptr,"CPU backend missing");
    s.backend.reset(ggml_backend_dev_init(device,nullptr));require(s.backend!=nullptr,"Cannot initialize T5 CPU backend");
    auto reg=ggml_backend_dev_backend_reg(device);
    auto set_threads=reinterpret_cast<ggml_backend_set_n_threads_t>(ggml_backend_reg_get_proc_address(reg,"ggml_backend_set_n_threads"));
    auto set_abort=reinterpret_cast<ggml_backend_set_abort_callback_t>(ggml_backend_reg_get_proc_address(reg,"ggml_backend_set_abort_callback"));
    require(set_threads && set_abort,"Pinned CPU backend lacks thread/cancellation controls");set_threads(s.backend.get(),threads);
    set_abort(s.backend.get(),[](void* data){return static_cast<State*>(data)->interrupted();},&s);
    auto start=gguf_get_data_offset(s.metadata.get());require(start<s.mapping.bytes,"Invalid T5 data offset");
    auto* data=static_cast<unsigned char*>(s.mapping.data)+start;auto length=s.mapping.bytes-start;
    s.weights.reset(ggml_backend_cpu_buffer_from_ptr(data,length));require(s.weights!=nullptr,"Cannot wrap mapped T5 CPU weights");
    ggml_backend_buffer_set_usage(s.weights.get(),GGML_BACKEND_BUFFER_USAGE_WEIGHTS);
    std::vector<std::pair<size_t,size_t>> ranges;
    for(int64_t i=0;i<gguf_get_n_tensors(s.metadata.get());++i) {
        s.stop();const char* name=gguf_get_tensor_name(s.metadata.get(),i);auto* t=ggml_get_tensor(s.tensors.get(),name);require(t!=nullptr,"Missing GGUF tensor metadata");
        auto offset=gguf_get_tensor_offset(s.metadata.get(),i),bytes=ggml_nbytes(t);
        require(offset%32==0 && offset<=length && bytes<=length-offset,"T5 tensor extends outside mapped file");
        ranges.emplace_back(offset,offset+bytes);require(s.named.emplace(name,t).second,"Duplicate T5 tensor name");
        s.buffers.tensor_bytes+=bytes;
        require(ggml_backend_tensor_alloc(s.weights.get(),t,data+offset)==GGML_STATUS_SUCCESS,"Cannot bind mapped T5 tensor");
    }
    std::sort(ranges.begin(),ranges.end());for(size_t i=1;i<ranges.size();++i) require(ranges[i-1].second<=ranges[i].first,"Overlapping T5 weight ranges");
    s.tensor("token_embd.weight",layout.width,layout.vocabulary);require(s.tensor("enc.output_norm.weight",layout.width)->type==GGML_TYPE_F32,"T5 normalization must be F32");
    require(s.tensor("enc.blk.0.attn_rel_b.weight",layout.heads,32)->type==GGML_TYPE_F32,"T5 relative bias must be F32");
    for(int i=0;i<layout.layers;++i) {
        auto prefix="enc.blk."+std::to_string(i)+".";
        for(auto name:{"q","k","v","o"}) s.tensor(prefix+"attn_"+name+".weight",layout.width,layout.width);
        for(auto name:{"attn_norm.weight","ffn_norm.weight"}) require(s.tensor(prefix+name,layout.width)->type==GGML_TYPE_F32,"T5 normalization must be F32");
        s.tensor(prefix+"ffn_gate.weight",layout.width,layout.feed_forward);s.tensor(prefix+"ffn_up.weight",layout.width,layout.feed_forward);
        s.tensor(prefix+"ffn_down.weight",layout.feed_forward,layout.width);
    }
    s.stop();
}
Graph::~Graph()=default;
Buffers Graph::buffers() const {return state_->buffers;}
std::vector<float> Graph::encode(const Tokens& ids) {
    auto& s=*state_;s.stop(); const auto& l=s.layout;const int n=static_cast<int>(ids.size()),head=l.width/l.heads;
    Context ctx(ggml_init({16*1024*1024,nullptr,true}),ggml_free);require(ctx!=nullptr,"Cannot allocate T5 graph metadata");auto* c=ctx.get();
    auto* tokens=ggml_new_tensor_1d(c,GGML_TYPE_I32,n);ggml_set_input(tokens);
    auto* bias=ggml_new_tensor_3d(c,GGML_TYPE_F32,n,n,l.heads);ggml_set_input(bias);
    auto normalize=[&](ggml_tensor* x,const std::string& name){return ggml_mul(c,ggml_rms_norm(c,x,1e-6f),s.tensor(name,l.width));};
    // Quantized CPU matmuls otherwise round F32 activations to Q8 internally.
    // Cast only each matrix needed by the next matmul. The graph allocator
    // reuses its dead temporary, so the full F32 checkpoint is never resident.
    auto matrix=[&](const std::string& name,int64_t a,int64_t b){auto* w=s.tensor(name,a,b);return w->type==GGML_TYPE_F32?w:ggml_cast(c,w,GGML_TYPE_F32);};
    auto* x=ggml_get_rows(c,s.tensor("token_embd.weight",l.width,l.vocabulary),tokens);
    for(int i=0;i<l.layers;++i) {
        auto prefix="enc.blk."+std::to_string(i)+".";auto* normalized=normalize(x,prefix+"attn_norm.weight");
        auto project=[&](const char* name){auto* p=ggml_mul_mat(c,matrix(prefix+"attn_"+name+".weight",l.width,l.width),normalized);return ggml_cont(c,ggml_permute(c,ggml_reshape_3d(c,p,head,l.heads,n),0,2,1,3));};
        auto* q=project("q");auto* k=project("k");auto* v=project("v");
        auto* scores=ggml_mul_mat(c,k,q);require(ggml_prec_set_acc(scores,GGML_PREC_F32),"Cannot select F32 T5 attention accumulation");
        auto* attention=ggml_soft_max(c,ggml_add(c,scores,bias));
        auto* values=ggml_cont(c,ggml_transpose(c,v));auto* mixed=ggml_mul_mat(c,values,attention);
        mixed=ggml_cont(c,ggml_permute(c,mixed,0,2,1,3));mixed=ggml_reshape_2d(c,mixed,l.width,n);
        x=ggml_add(c,x,ggml_mul_mat(c,matrix(prefix+"attn_o.weight",l.width,l.width),mixed));
        normalized=normalize(x,prefix+"ffn_norm.weight");
        auto* gate=ggml_mul_mat(c,matrix(prefix+"ffn_gate.weight",l.width,l.feed_forward),normalized);
        auto* up=ggml_mul_mat(c,matrix(prefix+"ffn_up.weight",l.width,l.feed_forward),normalized);
        auto* activated=ggml_map_custom2(c,gate,up,f32_geglu,GGML_N_TASKS_MAX,nullptr);
        x=ggml_add(c,x,ggml_mul_mat(c,matrix(prefix+"ffn_down.weight",l.feed_forward,l.width),activated));
    }
    auto* output=normalize(x,"enc.output_norm.weight");ggml_set_output(output);
    auto* graph=ggml_new_graph_custom(c,4096,false);ggml_build_forward_expand(graph,output);
    Allocator allocator(ggml_gallocr_new(ggml_backend_get_default_buffer_type(s.backend.get())),ggml_gallocr_free);
    require(allocator && ggml_gallocr_alloc_graph(allocator.get(),graph),"Cannot allocate T5 graph buffers");
    s.buffers.peak_compute_bytes=std::max<uint64_t>(s.buffers.peak_compute_bytes,ggml_gallocr_get_buffer_size(allocator.get(),0));
    ggml_backend_tensor_set(tokens,ids.data(),0,ids.size()*sizeof(int32_t));
    std::vector<float> relative(static_cast<size_t>(n)*n*l.heads);
    const auto* table=static_cast<const float*>(s.tensor("enc.blk.0.attn_rel_b.weight",l.heads,32)->data);
    for(int h=0;h<l.heads;++h) for(int query=0;query<n;++query) for(int key=0;key<n;++key) relative[(static_cast<size_t>(h)*n+query)*n+key]=table[bucket(key,query)*l.heads+h];
    ggml_backend_tensor_set(bias,relative.data(),0,relative.size()*sizeof(float));s.stop();
    if(s.progress) s.progress("t5_compute",0,n);
    auto result=ggml_backend_graph_compute(s.backend.get(),graph);
    if(s.interrupted()) throw std::runtime_error("T5 cancelled during neural evaluation");
    require(result==GGML_STATUS_SUCCESS,"Local T5 graph failed");
    std::vector<float> data(static_cast<size_t>(n)*l.width);ggml_backend_tensor_get(output,data.data(),0,data.size()*sizeof(float));
    for(float value:data) require(std::isfinite(value),"Non-finite T5 embedding");s.stop();return data;
}
}

#pragma once
#include "../rf_shape/ort.hpp"
#include "sparse.hpp"
#include "block_attention.hpp"
namespace lma_sparse {
enum class Operation {Conv,Pool,Subdivide,SpatialToChannel,Attention,BlockAttention,ExactJoin,RoutedAttention,WindowAttention};
struct Kernel {
 const OrtApi& api;Operation operation;
 Kernel(const OrtApi& a,Operation kind):api(a),operation(kind){}
 template<class T> static std::vector<T> data(Ort::ConstValue v,ONNXTensorElementDataType dtype,std::vector<int64_t>* shape=nullptr){
  require(v.IsTensor(),"Custom sparse input must be a tensor");auto ti=v.GetTensorTypeAndShapeInfo();require(ti.GetElementType()==dtype&&ti.GetElementCount()<=64000000,"Invalid sparse input dtype/size");if(shape)*shape=ti.GetShape();auto n=ti.GetElementCount();const T* p=v.GetTensorData<T>();return n?std::vector<T>(p,p+n):std::vector<T>{};
 }
 template<class T> static void output(Ort::KernelContext& ctx,size_t index,const std::vector<T>& values,const std::vector<int64_t>& shape){
  auto out=ctx.GetOutput(index,shape);require(out.GetTensorTypeAndShapeInfo().GetElementCount()==values.size(),"Sparse output size mismatch");std::copy(values.begin(),values.end(),out.GetTensorMutableData<T>());
 }
 static std::vector<Coord> coords(Ort::ConstValue v){std::vector<int64_t> s;auto d=data<int64_t>(v,ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64,&s);require(s.size()==2&&s[1]==4&&s[0]>=0&&s[0]<=int64_t(point_limit),"Sparse coordinates must be int64[N,4]");std::vector<Coord> out;out.resize(size_t(s[0]));for(size_t i=0;i<out.size();i++)std::copy_n(d.begin()+i*4,4,out[i].begin());return out;}
 static void packed(Ort::KernelContext& ctx,const Packed& p,bool child){output(ctx,0,p.feats,{int64_t(p.coords.size()),int64_t(p.channels)});std::vector<int64_t> c;c.reserve(p.coords.size()*4);for(auto row:p.coords)c.insert(c.end(),row.begin(),row.end());output(ctx,1,c,{int64_t(p.coords.size()),4});output(ctx,2,p.inverse,{int64_t(p.inverse.size())});if(child)output(ctx,3,p.child,{int64_t(p.child.size())});}
 void compute(OrtKernelContext* raw){
  Ort::KernelContext ctx(raw);
  if(operation==Operation::ExactJoin){
   auto full=coords(ctx.GetInput(0)),selected=coords(ctx.GetInput(1));coordinates(full);coordinates(selected);
   std::unordered_map<Coord,int64_t,Hash> rows;rows.reserve(full.size());for(size_t i=0;i<full.size();i++)rows.emplace(full[i],int64_t(i));
   std::vector<int64_t> result;result.reserve(selected.size());for(const auto& p:selected){auto found=rows.find(p);require(found!=rows.end(),"Observed coordinates must be an exact subset");result.push_back(found->second);}
   output(ctx,0,result,{int64_t(result.size())});return;
  }
  std::vector<int64_t> fs;auto f=data<float>(ctx.GetInput(0),ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT,&fs);
  if(operation==Operation::WindowAttention){
   std::vector<int64_t> ks,vs,ps;auto k=data<float>(ctx.GetInput(1),ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT,&ks),v=data<float>(ctx.GetInput(2),ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT,&vs);auto c=coords(ctx.GetInput(3));auto policy=data<int64_t>(ctx.GetInput(4),ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64,&ps);
   require(fs.size()==3&&ks==fs&&vs.size()==3&&vs[0]==fs[0]&&vs[1]==fs[1]&&fs[0]==int64_t(c.size())&&ps==std::vector<int64_t>{6},"Window attention requires Q/K/V[N,H,D], coordinates[N,4] and policy[6]");coordinates(c);finite(f);finite(k);finite(v);
   for(size_t j=0;j<3;j++)require(policy[j]>=1&&policy[j]<=1024&&policy[j+3]>=0&&policy[j+3]<=1024,"Invalid source shifted-window policy");
   std::map<Coord,std::vector<size_t>> groups;for(size_t i=0;i<c.size();i++){Coord key=c[i];for(size_t j=0;j<3;j++)key[j+1]=(key[j+1]+policy[j+3])/policy[j];groups[key].push_back(i);}
   size_t qw=size_t(fs[1]*fs[2]),vw=size_t(vs[1]*vs[2]);require(qw>0&&vw>0,"Invalid window attention width");Feats result(bounded(c.size(),vw));uint64_t work=0;
   for(const auto& group:groups){const auto& rows=group.second;work+=uint64_t(rows.size())*rows.size()*uint64_t(fs[1])*(uint64_t(fs[2])+uint64_t(vs[2]));require(work<=64000000000ULL,"Shifted-window attention work budget exceeded");Feats qg,kg,vg;qg.reserve(rows.size()*qw);kg.reserve(rows.size()*qw);vg.reserve(rows.size()*vw);for(size_t row:rows){qg.insert(qg.end(),f.begin()+row*qw,f.begin()+(row+1)*qw);kg.insert(kg.end(),k.begin()+row*qw,k.begin()+(row+1)*qw);vg.insert(vg.end(),v.begin()+row*vw,v.begin()+(row+1)*vw);}auto value=attention(qg,kg,vg,rows.size(),rows.size(),size_t(fs[1]),size_t(fs[2]),size_t(vs[2]),{int64_t(rows.size())},{int64_t(rows.size())});for(size_t i=0;i<rows.size();i++)std::copy_n(value.begin()+i*vw,vw,result.begin()+rows[i]*vw);}
   output(ctx,0,result,{fs[0],fs[1],vs[2]});return;
  }
  if(operation==Operation::RoutedAttention){
   std::vector<int64_t> ks,vs,rs;auto k=data<float>(ctx.GetInput(1),ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT,&ks),v=data<float>(ctx.GetInput(2),ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT,&vs);auto route=data<int64_t>(ctx.GetInput(3),ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64,&rs);
   require(fs.size()==3&&ks.size()==4&&vs.size()==4&&ks[0]>0&&ks[0]<=16&&ks[1]>0&&ks[2]==fs[1]&&ks[3]==fs[2]&&vs[0]==ks[0]&&vs[1]==ks[1]&&vs[2]==ks[2]&&vs[3]>0&&rs==std::vector<int64_t>{fs[0]},"Routed attention requires Q[N,H,D], K/V[V,T,H,D], selected[N]");
   size_t qw=size_t(fs[1]*fs[2]),kw=size_t(ks[1])*qw,vw=size_t(vs[1]*vs[2]*vs[3]);std::vector<std::vector<size_t>> groups;groups.resize(size_t(ks[0]));
   for(size_t i=0;i<route.size();i++){require(route[i]>=0&&route[i]<ks[0],"Selected real view is out of range");groups[size_t(route[i])].push_back(i);}
   std::vector<float> qpacked,kpacked,vpacked;std::vector<int64_t> ql,kl;std::vector<size_t> order;order.reserve(route.size());qpacked.reserve(f.size());
   for(size_t g=0;g<groups.size();g++)if(!groups[g].empty()){
    ql.push_back(int64_t(groups[g].size()));kl.push_back(ks[1]);
    for(size_t row:groups[g]){order.push_back(row);qpacked.insert(qpacked.end(),f.begin()+row*qw,f.begin()+(row+1)*qw);}
    kpacked.insert(kpacked.end(),k.begin()+g*kw,k.begin()+(g+1)*kw);vpacked.insert(vpacked.end(),v.begin()+g*vw,v.begin()+(g+1)*vw);
   }
   auto packed_result=attention(qpacked,kpacked,vpacked,size_t(fs[0]),size_t(ks[1])*ql.size(),size_t(fs[1]),size_t(fs[2]),size_t(vs[3]),ql,kl);
   size_t width=size_t(fs[1]*vs[3]);std::vector<float> result(packed_result.size());for(size_t i=0;i<order.size();i++)std::copy_n(packed_result.begin()+i*width,width,result.begin()+order[i]*width);
   output(ctx,0,result,{fs[0],fs[1],vs[3]});return;
  }
  if(operation==Operation::BlockAttention){
   std::vector<int64_t> ks,vs,ps;auto k=data<float>(ctx.GetInput(1),ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT,&ks),v=data<float>(ctx.GetInput(2),ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT,&vs);auto policy=data<int64_t>(ctx.GetInput(3),ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64,&ps);
   require(fs.size()==4&&ks==fs&&vs==fs&&ps==std::vector<int64_t>{4}&&fs[0]>0&&fs[1]>0&&fs[2]>0&&fs[3]>0,"Block attention requires matching [B,H,L,D] and policy[4]");
   output(ctx,0,block_attention(f,k,v,size_t(fs[0]),size_t(fs[1]),size_t(fs[2]),size_t(fs[3]),policy),fs);return;
  }
  if(operation==Operation::Attention){
   std::vector<int64_t> ks,vs;auto k=data<float>(ctx.GetInput(1),ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT,&ks),v=data<float>(ctx.GetInput(2),ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT,&vs);
   require(fs.size()==3&&ks.size()==3&&vs.size()==3&&fs[1]==ks[1]&&ks[1]==vs[1]&&fs[2]==ks[2]&&ks[0]==vs[0]&&fs[0]>=0&&ks[0]>=0&&vs[2]>0,"Packed attention requires [T,H,D]");
   auto ql=data<int64_t>(ctx.GetInput(3),ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64),kl=data<int64_t>(ctx.GetInput(4),ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64);
   auto result=attention(f,k,v,size_t(fs[0]),size_t(ks[0]),size_t(fs[1]),size_t(fs[2]),size_t(vs[2]),ql,kl);output(ctx,0,result,{fs[0],fs[1],vs[2]});return;
  }
  auto c=coords(ctx.GetInput(1));require(fs.size()==2&&fs[0]==int64_t(c.size())&&fs[1]>0,"Sparse features require [N,C]");size_t channels=size_t(fs[1]);
  if(operation==Operation::Conv){std::vector<int64_t> ws;auto w=data<float>(ctx.GetInput(2),ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT,&ws),bias=data<float>(ctx.GetInput(3),ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT);auto dilation=data<int64_t>(ctx.GetInput(4),ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64);
   require(ws.size()==5&&ws[0]>0&&ws[4]==fs[1]&&dilation.size()==3,"Sparse convolution weight layout mismatch");auto result=submanifold_conv(f,c,channels,w,size_t(ws[0]),{ws[1],ws[2],ws[3]},bias,{dilation[0],dilation[1],dilation[2]});output(ctx,0,result,{fs[0],ws[0]});
  }else if(operation==Operation::Pool){auto args=data<int64_t>(ctx.GetInput(2),ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64);require(args.size()==4&&args[3]>=0&&args[3]<=2,"Pool requires three factors and an explicit reduction policy");packed(ctx,pool(f,c,channels,{args[0],args[1],args[2]},int(args[3])),false);
  }else if(operation==Operation::Subdivide){auto mask=data<int64_t>(ctx.GetInput(2),ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64),order=data<int64_t>(ctx.GetInput(3),ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64);require(order.size()==1&&order[0]>=0&&order[0]<=1,"Missing subdivision order");packed(ctx,subdivide(f,c,channels,mask,int(order[0])),true);
  }else{auto factor=data<int64_t>(ctx.GetInput(2),ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64);require(factor.size()==1&&factor[0]>=1&&factor[0]<=4,"Invalid spatial-channel factor");packed(ctx,spatial_to_channel(f,c,channels,int(factor[0])),true);}
 }
 OrtStatusPtr ComputeV2(OrtKernelContext* raw)noexcept{try{compute(raw);return nullptr;}catch(const std::exception& e){return api.CreateStatus(ORT_RUNTIME_EXCEPTION,e.what());}catch(...){return api.CreateStatus(ORT_RUNTIME_EXCEPTION,"Sparse CPU operation failed");}}
};
struct Op:Ort::CustomOpBase<Op,Kernel,true>{
 Operation operation;const char* name;Op(Operation kind,const char* id):operation(kind),name(id){version=17;start_ver_=end_ver_=1;}
 const char* GetName()const{return name;}
 size_t GetInputTypeCount()const{return operation==Operation::ExactJoin?2:operation==Operation::Conv||operation==Operation::Attention||operation==Operation::WindowAttention?5:operation==Operation::Subdivide||operation==Operation::BlockAttention||operation==Operation::RoutedAttention?4:3;}
 ONNXTensorElementDataType GetInputType(size_t i)const{
  if(operation==Operation::ExactJoin)return ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64;
  if(operation==Operation::Conv)return i==0||i==2||i==3?ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT:ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64;
  if(operation==Operation::Attention||operation==Operation::BlockAttention||operation==Operation::RoutedAttention||operation==Operation::WindowAttention)return i<3?ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT:ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64;
  return i==0?ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT:ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64;
 }
 size_t GetOutputTypeCount()const{return operation==Operation::Conv||operation==Operation::Attention||operation==Operation::BlockAttention||operation==Operation::ExactJoin||operation==Operation::RoutedAttention||operation==Operation::WindowAttention?1:operation==Operation::Pool?3:4;}
 ONNXTensorElementDataType GetOutputType(size_t i)const{return operation==Operation::ExactJoin?ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64:i==0?ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT:ONNX_TENSOR_ELEMENT_DATA_TYPE_INT64;}
 OrtStatusPtr CreateKernelV2(const OrtApi& api,const OrtKernelInfo*,void** out)const noexcept{try{*out=new Kernel(api,operation);return nullptr;}catch(...){return api.CreateStatus(ORT_RUNTIME_EXCEPTION,"Cannot allocate sparse CPU operation");}}
};
// Domain and op objects must outlive every session that refers to them.
struct Domain {
 Op conv{Operation::Conv,"SubmanifoldConv3D"},pool{Operation::Pool,"Pool3D"},subdivide{Operation::Subdivide,"Subdivide3D"},channel{Operation::SpatialToChannel,"SpatialToChannel3D"},attention{Operation::Attention,"PackedAttention"};
 Op block{Operation::BlockAttention,"BlockSparseAttention"},join{Operation::ExactJoin,"ExactCoordinateJoin"};
 Op routed{Operation::RoutedAttention,"RoutedViewAttention"};
 Op window{Operation::WindowAttention,"WindowAttention"};
 Ort::CustomOpDomain domain{"lma.spatial"};
 Domain(){domain.Add(&conv);domain.Add(&pool);domain.Add(&subdivide);domain.Add(&channel);domain.Add(&attention);domain.Add(&block);domain.Add(&join);domain.Add(&routed);domain.Add(&window);}
 void add(Ort::SessionOptions& options){options.Add(domain);}
};
}

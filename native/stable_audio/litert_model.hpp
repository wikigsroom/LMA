// SPDX-License-Identifier: MIT
#pragma once
#include "policy.hpp"
#include "litert/c/litert_environment.h"
#include "litert/c/litert_model.h"
#include "litert/c/litert_model_types.h"
#include "litert/c/litert_options.h"
#include "litert/c/litert_opaque_options.h"
#include "litert/c/litert_compiled_model.h"
#include "litert/c/litert_tensor_buffer.h"
#include <cstdlib>
#include <memory>

namespace lma_sao {
inline void check(LiteRtStatus status,const char* stage) {if(status!=kLiteRtStatusOk)throw std::runtime_error(std::string(stage)+" (LiteRT status "+std::to_string(int(status))+")");}
template<typename T,void(*Destroy)(T)> struct Handle {
    T value=nullptr;Handle()=default;Handle(const Handle&)=delete;Handle& operator=(const Handle&)=delete;
    ~Handle(){if(value)Destroy(value);}operator T()const{return value;}
};
using Environment=Handle<LiteRtEnvironment,LiteRtDestroyEnvironment>;
using Buffer=Handle<LiteRtTensorBuffer,LiteRtDestroyTensorBuffer>;
struct Tensor {LiteRtElementType type;std::vector<int> dimensions;};
inline Tensor f32(std::initializer_list<int> shape){return {kLiteRtElementTypeFloat32,shape};}
inline Tensor i64(std::initializer_list<int> shape){return {kLiteRtElementTypeInt64,shape};}
inline size_t tensor_bytes(const LiteRtRankedTensorType& actual,const Tensor& expected) {
    require(actual.element_type==expected.type && actual.layout.rank==expected.dimensions.size() && !actual.layout.has_strides,"TFLite tensor dtype, rank or strides differ from the pinned export");
    size_t elements=1;for(size_t d=0;d<expected.dimensions.size();d++){require(actual.layout.dimensions[d]==expected.dimensions[d],"TFLite tensor dimensions differ from the pinned export");elements*=size_t(expected.dimensions[d]);}
    return elements*(expected.type==kLiteRtElementTypeInt64?8:4);
}
// Own resources in reverse destruction order: buffers -> compiled -> options -> model.
class Model {
    Handle<LiteRtModel,LiteRtDestroyModel> model;
    Handle<LiteRtOptions,LiteRtDestroyOptions> options;
    Handle<LiteRtCompiledModel,LiteRtDestroyCompiledModel> compiled;
    std::vector<std::unique_ptr<Buffer>> input_owner,output_owner;
    std::vector<LiteRtTensorBuffer> inputs,outputs;
    std::vector<size_t> input_bytes,output_bytes;
    static void transfer(LiteRtTensorBuffer b,void* data,size_t bytes,bool write) {
        void* address=nullptr;check(LiteRtLockTensorBuffer(b,&address,write?kLiteRtTensorBufferLockModeWrite:kLiteRtTensorBufferLockModeRead),"Cannot lock CPU tensor");
        if(!address){LiteRtUnlockTensorBuffer(b);throw std::runtime_error("CPU tensor mapping is null");}
        if(write)std::memcpy(address,data,bytes);else std::memcpy(data,address,bytes);
        check(LiteRtUnlockTensorBuffer(b),"Cannot unlock CPU tensor");
    }
public:
    Model(LiteRtEnvironment env,const std::string& path,int threads,const std::vector<Tensor>& ins,const std::vector<Tensor>& outs) {
        check(LiteRtCreateModelFromFile(env,path.c_str(),&model.value),"Cannot read user-selected TFLite model");
        LiteRtParamIndex count=0;check(LiteRtGetNumModelSignatures(model,&count),"Cannot inspect model signatures");require(count==1,"Expected exactly one exported signature");
        LiteRtSignature signature=nullptr;check(LiteRtGetModelSignature(model,0,&signature),"Cannot read signature");
        std::vector<LiteRtRankedTensorType> input_types,output_types;
        for(int side=0;side<2;side++) {
            const auto& specs=side==0?ins:outs;auto& types=side==0?input_types:output_types;auto& sizes=side==0?input_bytes:output_bytes;
            check(side==0?LiteRtGetNumSignatureInputs(signature,&count):LiteRtGetNumSignatureOutputs(signature,&count),"Cannot inspect tensor count");require(size_t(count)==specs.size(),"TFLite input/output count differs from the pinned export");
            for(size_t i=0;i<specs.size();i++) {
                LiteRtTensor tensor=nullptr;check(side==0?LiteRtGetSignatureInputTensorByIndex(signature,int(i),&tensor):LiteRtGetSignatureOutputTensorByIndex(signature,int(i),&tensor),"Cannot inspect tensor");
                LiteRtRankedTensorType type{};check(LiteRtGetRankedTensorType(tensor,&type),"Cannot inspect tensor type");sizes.push_back(tensor_bytes(type,specs[i]));types.push_back(type);
            }
        }
        check(LiteRtCreateOptions(&options.value),"Cannot create LiteRT options");check(LiteRtSetOptionsHardwareAccelerators(options,kLiteRtHwAcceleratorCpu),"Cannot restrict execution to CPU");
        std::string toml=cpu_options(threads);auto* payload=static_cast<char*>(std::malloc(toml.size()+1));require(payload!=nullptr,"Cannot allocate CPU options");std::memcpy(payload,toml.c_str(),toml.size()+1);
        Handle<LiteRtOpaqueOptions,LiteRtDestroyOpaqueOptions> opaque;LiteRtStatus status=LiteRtCreateOpaqueOptions("xnnpack",payload,std::free,&opaque.value);
        if(status!=kLiteRtStatusOk){std::free(payload);check(status,"Cannot encode CPU options");}
        check(LiteRtAddOpaqueOptions(options,opaque),"Cannot attach CPU options");opaque.value=nullptr;
        check(LiteRtCreateCompiledModel(env,model,options,&compiled.value),"Cannot compile selected graph on CPU; verify matching LiteRT export and available memory");
        for(int side=0;side<2;side++) {
            auto& types=side==0?input_types:output_types;auto& owners=side==0?input_owner:output_owner;auto& buffers=side==0?inputs:outputs;const auto& sizes=side==0?input_bytes:output_bytes;
            for(size_t i=0;i<types.size();i++) {
                LiteRtTensorBufferRequirements req=nullptr;check(side==0?LiteRtGetCompiledModelInputBufferRequirements(compiled,0,int(i),&req):LiteRtGetCompiledModelOutputBufferRequirements(compiled,0,int(i),&req),"Cannot read CPU tensor requirements");
                auto owner=std::make_unique<Buffer>();check(LiteRtCreateManagedTensorBufferFromRequirements(env,&types[i],req,&owner->value),"Cannot allocate CPU tensor");size_t available=0;check(LiteRtGetTensorBufferSize(*owner,&available),"Cannot inspect CPU buffer size");require(available>=sizes[i],"CPU tensor buffer is too small");buffers.push_back(*owner);owners.push_back(std::move(owner));
            }
        }
    }
    template<typename T> void write(size_t index,const std::vector<T>& data) {require(index<inputs.size() && data.size()*sizeof(T)==input_bytes[index],"Input tensor size differs");transfer(inputs[index],const_cast<T*>(data.data()),input_bytes[index],true);}
    std::vector<float> read(size_t index) {require(index<outputs.size() && output_bytes[index]%4==0,"Output tensor differs");std::vector<float> data(output_bytes[index]/4);transfer(outputs[index],data.data(),output_bytes[index],false);for(float value:data)require(std::isfinite(value),"Nonfinite model output");return data;}
    void run() {check(LiteRtRunCompiledModel(compiled,0,inputs.size(),inputs.data(),outputs.size(),outputs.data()),"CPU inference failed");}
};
}

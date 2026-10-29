#include "../local_prepare/io.hpp"
#include "contract.hpp"
#include <cfenv>

namespace {
using namespace lma_prepare;
const std::string output_tensor="model.diffusion_model.time_embed.0.bias";
const std::map<std::string,std::vector<uint64_t>> selected={
    {"time_embedding.cond_proj.weight",{320,256}},
    {"time_embedding.linear_1.weight",{1280,320}},
    {"time_embedding.linear_1.bias",{1280}}
};
struct Plan {std::vector<Tensor> tensors;uint64_t header_bytes=0;std::string header_sha;};
Plan inspect(File& source,Sha256& hash,const Json& contract,bool fixture) {
    require(source.size>=10,"Truncated safetensors prefix");
    std::array<uint8_t,8> prefix{};source.read(prefix.data(),prefix.size());hash.update(prefix.data(),prefix.size());
    auto bytes=le(prefix.data(),8);require(bytes>=2&&bytes<=16*1024*1024&&bytes<=source.size-8,"Invalid safetensors header length");
    if(!fixture)require(bytes==contract.at("source_header_bytes"),"Unexpected conditioned UNet header length");
    std::string raw(static_cast<size_t>(bytes),'\0');source.read(raw.data(),raw.size());hash.update(raw.data(),raw.size());
    Plan plan;plan.header_bytes=bytes;plan.header_sha=sha(raw.data(),raw.size());
    if(!fixture)require(plan.header_sha==contract.at("source_header_sha256"),"Conditioned UNet header differs from pinned source");
    auto header=parse(raw);require(header.is_object(),"Expected safetensors header object");std::set<std::string> found;
    for(const auto& entry:header.items()) {
        if(entry.key()=="__metadata__") {require(entry.value().is_object(),"Invalid metadata");continue;}
        require(!entry.key().empty()&&entry.key().size()<=256&&entry.key().find('\0')==std::string::npos,"Invalid tensor name");
        fields(entry.value(),{"dtype","shape","data_offsets"});const auto& item=entry.value();Tensor t;t.name=entry.key();t.dtype=string(item.at("dtype"),8);
        require(t.dtype=="F32","Conditioned source must contain original F32 tensors");
        const auto& shape=item.at("shape");require(shape.is_array()&&!shape.empty()&&shape.size()<=5,"Invalid tensor rank");
        for(const auto& v:shape){auto n=number(v,1,1000000);require(t.elements<=uint64_t(std::numeric_limits<int64_t>::max())/n,"Tensor shape overflow");t.elements*=n;t.shape.push_back(n);}
        const auto& range=item.at("data_offsets");require(range.is_array()&&range.size()==2,"Invalid tensor offsets");
        t.first=number(range[0],0,source.size-8-bytes);t.last=number(range[1],t.first,source.size-8-bytes);
        require(t.elements<=(source.size-8-bytes)/4&&t.last-t.first==4*t.elements,"Tensor byte/shape mismatch");
        auto match=selected.find(t.name);t.selected=match!=selected.end();
        if(t.selected){require(t.shape==match->second,"Conditioning tensor shape mismatch");found.insert(t.name);}
        if(fixture)require(t.selected,"Unreviewed fixture tensor");
        plan.tensors.push_back(std::move(t));require(plan.tensors.size()<=10000,"Tensor count outside budget");
    }
    require(found.size()==selected.size(),"Missing conditioning tensor");
    require(plan.tensors.size()==(fixture?selected.size():contract.at("source_tensor_count").get<size_t>()),"Conditioned source tensor count mismatch");
    std::sort(plan.tensors.begin(),plan.tensors.end(),[](const Tensor& a,const Tensor& b){return a.first<b.first;});
    uint64_t previous=0;for(const auto& t:plan.tensors){require(t.first==previous,"Tensor ranges overlap or leave unreviewed bytes");previous=t.last;}
    require(previous==source.size-8-bytes,"Unexpected checkpoint trailing data");return plan;
}
std::vector<float> decode(const std::vector<uint8_t>& bytes,bool cast_half) {
    require(bytes.size()%4==0,"Invalid F32 buffer");std::vector<float> out(bytes.size()/4);
    for(size_t i=0;i<out.size();++i) {
        auto bits=static_cast<uint32_t>(le(bytes.data()+4*i,4));require((bits&0x7f800000)!=0x7f800000,"Non-finite trained parameter");
        if(cast_half)bits=half_to_float(float_to_half(bits));
        std::memcpy(&out[i],&bits,4);require(std::isfinite(out[i]),"Non-finite converted parameter");
    }
    return out;
}
std::vector<uint8_t> fold(const std::map<std::string,std::vector<uint8_t>>& captured,const Json& contract) {
    require(std::numeric_limits<float>::is_iec559&&sizeof(float)==4&&std::numeric_limits<double>::is_iec559&&sizeof(double)==8,
            "IEEE-754 F32/F64 required");require(std::fegetround()==FE_TONEAREST,"Nearest ties-to-even rounding required");
    auto cond=decode(captured.at("time_embedding.cond_proj.weight"),false);
    auto weight=decode(captured.at("time_embedding.linear_1.weight"),true);
    auto bias=decode(captured.at("time_embedding.linear_1.bias"),false);
    std::array<float,256> guidance{};const auto& constants=contract.at("guidance_u32_le");
    require(constants.is_array()&&constants.size()==guidance.size()&&contract.at("mathematical_constants_only")==true&&contract.at("learned_data_embedded")==false,
            "Invalid model-free mathematical constants");
    std::vector<uint8_t> constant_bytes;
    for(size_t i=0;i<guidance.size();++i){auto bits=static_cast<uint32_t>(number(constants[i],0,0xffffffff));std::memcpy(&guidance[i],&bits,4);append(constant_bytes,bits,4);require(std::isfinite(guidance[i]),"Non-finite guidance constant");}
    require(sha(constant_bytes.data(),constant_bytes.size())==contract.at("guidance_bytes_sha256"),"Guidance constants differ from contract");
    std::array<float,320> offset{};
    for(size_t row=0;row<offset.size();++row){double sum=0;for(size_t i=0;i<guidance.size();++i)sum+=double(cond[row*guidance.size()+i])*double(guidance[i]);offset[row]=static_cast<float>(sum);require(std::isfinite(offset[row]),"Condition projection overflow");}
    std::vector<uint8_t> out;out.reserve(1280*4);
    for(size_t row=0;row<bias.size();++row){double sum=0;for(size_t i=0;i<offset.size();++i)sum+=double(weight[row*offset.size()+i])*double(offset[i]);
        float delta=static_cast<float>(sum);float result=static_cast<float>(double(bias[row])+double(delta));
        require(std::isfinite(result)&&std::isfinite(delta),"Folded bias overflow");uint32_t bits=0;std::memcpy(&bits,&result,4);append(out,bits,4);}
    return out;
}
std::vector<uint8_t> make_gguf(const std::vector<uint8_t>& payload,const Json& contract,const std::string& source_sha) {
    require(payload.size()==5120,"Invalid folded bias size");std::vector<uint8_t> out={'G','G','U','F'};append(out,3,4);append(out,1,8);
    const std::vector<std::pair<std::string,std::string>> metadata={
        {"lma.overlay.schema","lma.condition-bias-overlay/1"},{"lma.overlay.algorithm",contract.at("algorithm").get<std::string>()},
        {"lma.overlay.source_sha256",source_sha},{"lma.overlay.base_sha256",contract.at("base").at("sha256").get<std::string>()},
        {"lma.overlay.distilled_guidance","8.5"},{"lma.overlay.sampler_cfg","1"}};
    append(out,metadata.size(),8);for(const auto& item:metadata){append_string(out,item.first);append(out,8,4);append_string(out,item.second);}
    append_string(out,output_tensor);append(out,1,4);append(out,1280,8);append(out,0,4);append(out,0,8);
    out.resize(static_cast<size_t>(aligned(out.size())),0);out.insert(out.end(),payload.begin(),payload.end());return out;
}
int run(const std::vector<std::string>& args) {
    try {
        require(args.size()==2||(args.size()==3&&args[1]=="--fixture"),"Usage: lma_lcm_prepare [--fixture] REQUEST.json");bool fixture=args.size()==3;
        auto request=parse(read_request(local_path(args.back())));fields(request,{"operation","checkpoint","expected_source_bytes","expected_source_sha256","storage_root","output_name","cancel_file","max_output_bytes"});
        require(string(request.at("operation"),32)=="fold_condition_bias","Unknown preparation operation");
        auto contract=Json::parse(lma_lcm_contract);Cancel cancel;if(request.contains("cancel_file"))cancel.file=local_path(request.at("cancel_file"));cancel.check();
        File source(local_path(request.at("checkpoint")));auto expected_bytes=number(request.at("expected_source_bytes"),10,uint64_t(std::numeric_limits<int64_t>::max()));
        auto expected_sha=string(request.at("expected_source_sha256"),64);require(digest(expected_sha)&&source.size==expected_bytes,"Source byte/hash identity mismatch");
        if(!fixture)require(expected_sha==contract.at("source").at("sha256")&&expected_bytes==contract.at("source").at("bytes"),"No signed conditioning contract for this source");
        Sha256 source_hash;auto plan=inspect(source,source_hash,contract,fixture);cancel.check();
        // The exact output size is known without reading trained values.
        auto expected_output=make_gguf(std::vector<uint8_t>(5120),contract,expected_sha).size();
        require(expected_output<=number(request.at("max_output_bytes"),1,64*1024),"Output exceeds selected storage budget");
        auto root=fs::canonical(local_path(request.at("storage_root")));require(fs::is_directory(root),"Missing storage directory");local_path(root.u8string());
        require(fs::space(root).available>=expected_output+1024*1024,"Insufficient local storage");
        Transaction transaction(root,output_name(request.at("output_name")),{"lcm-condition-bias.gguf","conversion.json"});
        std::vector<uint8_t> buffer(chunk_bytes);std::map<std::string,std::vector<uint8_t>> captured;
        uint64_t done=8+plan.header_bytes,next_progress=done;progress("verify_source",done,source.size);
        for(const auto& tensor:plan.tensors){if(tensor.selected)captured[tensor.name].reserve(static_cast<size_t>(tensor.last-tensor.first));
            for(uint64_t remaining=tensor.last-tensor.first;remaining;){cancel.check();auto count=static_cast<size_t>(std::min<uint64_t>(remaining,buffer.size()));
                source.read(buffer.data(),count);source_hash.update(buffer.data(),count);remaining-=count;done+=count;
                if(tensor.selected)captured[tensor.name].insert(captured[tensor.name].end(),buffer.begin(),buffer.begin()+count);
                if(done>=next_progress){progress("verify_source",done,source.size);next_progress=done+64*1024*1024;}}
        }
        cancel.check();source.unchanged();require(done==source.size,"Source byte accounting mismatch");auto actual_sha=source_hash.finish();require(actual_sha==expected_sha,"Source SHA-256 mismatch; output discarded");
        auto payload=fold(captured,contract);auto output=make_gguf(payload,contract,actual_sha);require(output.size()==expected_output,"Output byte accounting mismatch");
        std::string output_sha;
        {File target(transaction.stage/"lcm-condition-bias.gguf",true);target.write(output.data(),output.size());target.flush();target.seek(0);
            std::vector<uint8_t> check(output.size());target.read(check.data(),check.size());require(check==output,"Output read-back mismatch");output_sha=sha(check.data(),check.size());}
        Json record={{"schema","lma.lcm-native-prepare/1"},{"ok",true},{"operation","fold_condition_bias"},{"fixture",fixture},
            {"algorithm",contract.at("algorithm")},{"source_bytes",source.size},{"source_sha256_verified",true},{"source_sha256",actual_sha},
            {"source_header_bytes",plan.header_bytes},{"source_header_sha256",plan.header_sha},{"source_tensor_count",plan.tensors.size()},
            {"source_streamed_bytes",done},{"source_retained",true},{"base_sha256",contract.at("base").at("sha256")},
            {"distilled_guidance",8.5},{"sampler_cfg",1.0},{"guidance_bytes_sha256",contract.at("guidance_bytes_sha256")},
            {"output_file","lcm-condition-bias.gguf"},{"output_bytes",output.size()},{"output_sha256",output_sha},
            {"payload_bytes",payload.size()},{"payload_sha256",sha(payload.data(),payload.size())},{"output_tensor",output_tensor},{"output_shape",Json({1280})},
            {"selected_parameter_bytes",1971200},{"input_chunk_bytes",chunk_bytes},{"whole_checkpoint_allocated",false},
            {"mathematical_constants_only",true},{"model_data_embedded",false},{"model_inference",false},{"packaged_in_apk",false},
            {"production_app_integrated",false},{"physical_android",false},{"image_quality_accepted",false},{"complete_release_accepted",false}};
        {File receipt(transaction.stage/"conversion.json",true);auto text=record.dump(2)+"\n";receipt.write(text.data(),text.size());receipt.flush();}
        cancel.check();source.unchanged();transaction.commit();progress("committed",output.size(),output.size());std::cout<<record.dump()<<std::endl;return 0;
    } catch(const std::exception& error){std::cout<<Json{{"ok",false},{"error",error.what()}}.dump(-1,' ',false,Json::error_handler_t::replace)<<std::endl;return 1;}
}
}
#ifdef _WIN32
int wmain(int argc,wchar_t** argv){std::vector<std::string> args;for(int i=0;i<argc;++i){int n=WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,argv[i],-1,nullptr,0,nullptr,nullptr);if(n<=0)return 2;
    std::string text(static_cast<size_t>(n),'\0');WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,argv[i],-1,text.data(),n,nullptr,nullptr);text.pop_back();args.push_back(text);}return run(args);}
#else
int main(int argc,char** argv){return run(std::vector<std::string>(argv,argv+argc));}
#endif

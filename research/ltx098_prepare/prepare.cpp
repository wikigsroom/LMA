#include "../local_prepare/io.hpp"
#include "contract.hpp"

namespace {
using namespace lma_prepare;
constexpr const char* prefix = "model.diffusion_model.";
struct Plan {
    Json config;std::vector<Tensor> tensors;std::vector<uint8_t> header;std::string header_sha,layout_sha;
    uint64_t source_header_bytes=0,total_parameters=0,selected_count=0,output_bytes=0;
};
Plan inspect(File& source, Sha256& source_hash, bool fixture) {
    auto checkpoint=read_safetensors(source,source_hash);
    Plan plan;plan.header_sha=checkpoint.header_sha;plan.source_header_bytes=checkpoint.header_bytes;
    auto full_config=checkpoint.config;
    require(full_config.is_object()&&full_config.contains("transformer")&&full_config.at("transformer").is_object(),"Missing transformer config");
    plan.config=full_config.at("transformer");auto contract=Json::parse(lma_ltx_contract);
    std::set<std::string> flexible={"num_attention_heads","attention_head_dim","cross_attention_dim","caption_channels","in_channels","out_channels","num_layers"};
    for(const auto& entry:contract.at("checkpoint_transformer_config").items()) {
        if(entry.key()[0]=='_'||(fixture&&flexible.count(entry.key()))) continue;
        require(plan.config.contains(entry.key()),"Missing old transformer constant: "+entry.key());
        const auto& value=plan.config.at(entry.key());const auto& expected=entry.value();
        bool type=(expected.is_number_integer()?value.is_number_integer():value.type()==expected.type());
        require(type&&value==expected,"Unsupported old transformer constant: "+entry.key());
    }
    if(fixture) {
        for(const auto& key:flexible) number(plan.config.at(key),1,1000000);
        auto width=plan.config.at("num_attention_heads").get<uint64_t>()*plan.config.at("attention_head_dim").get<uint64_t>();
        auto layers=plan.config.at("num_layers").get<int>();
        require(plan.config.at("num_attention_heads")==2&&(width==24||width==32)&&plan.config.at("cross_attention_dim")==width&&
                plan.config.at("caption_channels")==32&&plan.config.at("in_channels")==8&&plan.config.at("out_channels")==8&&
                (layers==2||layers==3||layers==28),"Unreviewed fixture architecture");
    } else require(full_config.contains("allowed_inference_steps")&&full_config.at("allowed_inference_steps")==Json({1.,.9937,.9875,.9812,.975,.9094,.725,.4219}),"Unsupported distilled schedule");
    nlohmann::json layout=nlohmann::json::object();uint64_t offset=0;
    for(auto t:checkpoint.tensors) {
        t.selected=t.name.compare(0,std::strlen(prefix),prefix)==0;
        if(t.selected) {
            auto name=t.name.substr(std::strlen(prefix));require(!name.empty(),"Empty DiT tensor name");layout[name]=t.shape;
            t.half=t.shape.size()==2&&name.size()>=7&&name.compare(name.size()-7,7,".weight")==0;
            t.output_bytes=t.elements*(t.half?2:4);t.destination=offset;offset+=aligned(t.output_bytes);
            require(offset<=uint64_t(std::numeric_limits<int64_t>::max()),"Output size overflow");
            plan.total_parameters+=t.elements;++plan.selected_count;
        }
        plan.tensors.push_back(std::move(t));require(plan.tensors.size()<=10000,"Tensor count outside budget");
    }
    auto layout_text=layout.dump(-1,' ',true);plan.layout_sha=sha(layout_text.data(),layout_text.size());
    if(fixture) require(plan.selected_count==15+25*plan.config.at("num_layers").get<uint64_t>(),"Incomplete fixture transformer");
    else require(plan.selected_count==contract.at("checkpoint_transformer_tensors")&&plan.total_parameters==contract.at("checkpoint_transformer_parameters")&&
                 plan.layout_sha==contract.at("checkpoint_transformer_layout_sha256"),"Transformer layout differs from exact old checkpoint");
    plan.output_bytes=offset;return plan;
}
void make_header(Plan& plan, const std::string& source_sha) {
    auto& out=plan.header;out.insert(out.end(),{'G','G','U','F'});append(out,3,4);append(out,plan.selected_count,8);append(out,3,8);
    for(const auto& kv:std::vector<std::pair<std::string,std::string>>{{"general.architecture","lma-ltx-video-098"},{"ltx098.config",plan.config.dump(-1,' ',true)},{"ltx098.source_sha256",source_sha}}) {
        append_string(out,kv.first);append(out,8,4);append_string(out,kv.second);
    }
    for(const auto& t:plan.tensors) if(t.selected) {
        append_string(out,t.name.substr(std::strlen(prefix)));append(out,t.shape.size(),4);
        for(auto i=t.shape.rbegin();i!=t.shape.rend();++i) append(out,*i,8);
        append(out,t.half?1:0,4);append(out,t.destination,8);
    }
    out.resize(static_cast<size_t>(aligned(out.size())),0);plan.output_bytes+=out.size();
}
void transform(const Tensor& t, const std::vector<uint8_t>& input, size_t count, std::vector<uint8_t>& output) {
    size_t stride=t.dtype=="F32"?4:2,step=t.half?2:4;output.resize(count/stride*step);
    for(size_t i=0,j=0;i<count;i+=stride,j+=step) {
        uint32_t value=t.dtype=="BF16"?static_cast<uint32_t>(le(input.data()+i,2)<<16):
                       t.dtype=="F16"?half_to_float(static_cast<uint16_t>(le(input.data()+i,2))):static_cast<uint32_t>(le(input.data()+i,4));
        require((value&0x7f800000)!=0x7f800000,"Non-finite trained parameter");
        if(t.half) {float f;std::memcpy(&f,&value,4);require(std::abs(f)<=65504.f,"FP16 tensor overflow");value=float_to_half(value);}
        for(size_t k=0;k<step;++k) output[j+k]=static_cast<uint8_t>(value>>(8*k));
    }
}
int run(const std::vector<std::string>& args) {
    try {
        require(args.size()==2||(args.size()==3&&args[1]=="--fixture"),"Usage: lma_ltx098_prepare [--fixture] REQUEST.json");bool fixture=args.size()==3;
        auto request=parse(read_request(local_path(args.back())));
        fields(request,{"operation","checkpoint","expected_source_bytes","expected_source_sha256","storage_root","output_name","cancel_file","max_output_bytes"});
        auto operation=string(request.at("operation"),32);require(operation=="inspect_dit"||operation=="convert_dit","Unknown preparation operation");
        Cancel cancel;if(request.contains("cancel_file"))cancel.file=local_path(request.at("cancel_file"));cancel.check();
        auto checkpoint=local_path(request.at("checkpoint"));File source(checkpoint);auto expected_bytes=number(request.at("expected_source_bytes"),10,uint64_t(std::numeric_limits<int64_t>::max()));
        require(source.size==expected_bytes,"Source byte identity mismatch");auto expected_sha=string(request.at("expected_source_sha256"),64);require(digest(expected_sha),"Invalid source SHA-256");
        Sha256 source_hash;auto plan=inspect(source,source_hash,fixture);make_header(plan,expected_sha);cancel.check();
        if(request.contains("max_output_bytes"))require(plan.output_bytes<=number(request.at("max_output_bytes"),1,uint64_t(std::numeric_limits<int64_t>::max())),"Output exceeds selected storage budget");
        Json record={{"schema","lma.ltx098-native-prepare/1"},{"ok",true},{"operation",operation},{"fixture",fixture},
            {"source_bytes",source.size},{"expected_source_sha256",expected_sha},{"source_header_bytes",plan.source_header_bytes},{"source_header_sha256",plan.header_sha},
            {"source_sha256_verified",false},{"source_tensor_count",plan.tensors.size()},{"tensors",plan.selected_count},{"parameters",plan.total_parameters},
            {"layout_sha256",plan.layout_sha},{"output_bytes",plan.output_bytes},{"gguf_header_sha256",sha(plan.header.data(),plan.header.size())},
            {"dense_storage","F16"},{"other_storage","F32"},{"model_data_embedded",false},{"model_inference",false},
            {"packaged_in_apk",false},{"engine_registered",false},{"physical_android",false},{"complete_video_pipeline",false}};
        if(operation=="inspect_dit") {require(!request.contains("storage_root")&&!request.contains("output_name"),"Inspection does not accept an output");source.unchanged();std::cout<<record.dump()<<std::endl;return 0;}
        auto root=fs::canonical(local_path(request.at("storage_root")));require(fs::is_directory(root),"Missing storage directory");local_path(root.u8string());
        auto space=fs::space(root);require(space.available>=plan.output_bytes+1024*1024,"Insufficient local storage");
        Transaction transaction(root,output_name(request.at("output_name")));
        uint64_t source_done=8+plan.source_header_bytes,output_written=plan.header.size();
        {
            File target(transaction.stage/"ltx098-dit.gguf",true);target.write(plan.header.data(),plan.header.size());
            // Pre-size through the owned handle, so arbitrary source/header tensor order stays bounded.
            uint8_t zero=0;target.seek(plan.output_bytes-1);target.write(&zero,1);
            std::vector<uint8_t> input(chunk_bytes),output;output.reserve(2*chunk_bytes);std::array<uint8_t,32> padding{};
            std::sort(plan.tensors.begin(),plan.tensors.end(),[](const Tensor& a,const Tensor& b){return a.first<b.first;});
            progress("convert",source_done,source.size);uint64_t next_progress=source_done+64*1024*1024;
            for(const auto& t:plan.tensors) {
                uint64_t destination=plan.header.size()+t.destination;
                for(uint64_t remaining=t.last-t.first;remaining;) {
                    cancel.check();size_t count=static_cast<size_t>(std::min<uint64_t>(remaining,input.size()));source.read(input.data(),count);source_hash.update(input.data(),count);source_done+=count;remaining-=count;
                    if(t.selected) {transform(t,input,count,output);target.seek(destination);target.write(output.data(),output.size());destination+=output.size();output_written+=output.size();}
                    if(source_done>=next_progress) {progress("convert",source_done,source.size);next_progress=source_done+64*1024*1024;}
                }
                if(t.selected) {size_t pad=static_cast<size_t>(aligned(t.output_bytes)-t.output_bytes);target.seek(destination);target.write(padding.data(),pad);output_written+=pad;}
            }
            cancel.check();source.unchanged();auto actual_sha=source_hash.finish();require(actual_sha==expected_sha,"Source SHA-256 mismatch; output discarded");
            require(source_done==source.size&&output_written==plan.output_bytes,"Streaming byte accounting mismatch");target.flush();
            Sha256 output_hash;target.seek(0);uint64_t remaining=plan.output_bytes;progress("verify_output",0,remaining);next_progress=64*1024*1024;
            while(remaining) {cancel.check();size_t count=static_cast<size_t>(std::min<uint64_t>(remaining,input.size()));target.read(input.data(),count);output_hash.update(input.data(),count);remaining-=count;
                if(plan.output_bytes-remaining>=next_progress){progress("verify_output",plan.output_bytes-remaining,plan.output_bytes);next_progress=plan.output_bytes-remaining+64*1024*1024;}}
            record["source_sha256_verified"]=true;record["source_sha256"]=actual_sha;record["output_sha256"]=output_hash.finish();
            record["source_streamed_bytes"]=source_done;record["output_written_bytes"]=output_written;
            record["input_chunk_bytes"]=chunk_bytes;record["output_chunk_capacity_bytes"]=2*chunk_bytes;
            record["complete_tensor_allocated"]=false;record["source_retained"]=true;
        }
        {File receipt(transaction.stage/"conversion.json",true);auto text=record.dump(2)+"\n";receipt.write(text.data(),text.size());receipt.flush();}
        cancel.check();source.unchanged();transaction.commit();progress("committed",plan.output_bytes,plan.output_bytes);std::cout<<record.dump()<<std::endl;return 0;
    } catch(const std::exception& error) {
        // Windows filesystem diagnostics may use the system code page. Always
        // return a valid UTF-8 JSON failure even when that diagnostic is not UTF-8.
        std::cout<<Json{{"ok",false},{"error",error.what()}}.dump(-1,' ',false,Json::error_handler_t::replace)<<std::endl;return 1;
    }
}
}
#ifdef _WIN32
int wmain(int argc,wchar_t** argv) {
    std::vector<std::string> args;
    for(int i=0;i<argc;++i) {int n=WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,argv[i],-1,nullptr,0,nullptr,nullptr);if(n<=0)return 2;
        std::string text(static_cast<size_t>(n),'\0');WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,argv[i],-1,text.data(),n,nullptr,nullptr);text.pop_back();args.push_back(text);}
    return run(args);
}
#else
int main(int argc,char** argv) {return run(std::vector<std::string>(argv,argv+argc));}
#endif

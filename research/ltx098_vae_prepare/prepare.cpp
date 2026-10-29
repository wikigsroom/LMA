#include "../local_prepare/io.hpp"
#include "contract.hpp"
#include <memory>

namespace {
using namespace lma_prepare;
constexpr uint64_t receipt_reserve=1024*1024;
Json compiled_contract(){const auto* text=reinterpret_cast<const char*>(vae_contract_bytes);return Json::parse(text,text+sizeof(vae_contract_bytes));}
struct Route {size_t stage;uint64_t offset,bytes;};
struct Plan {
    Checkpoint checkpoint;Json contract,manifest;
    std::map<std::string,std::vector<Route>> routes;
    std::string manifest_text,contract_sha;
    uint64_t asset_bytes=0,parameter_bytes=0;
};
Plan inspect(File& source,Sha256& source_hash) {
    Plan plan;plan.contract=compiled_contract();
    require(plan.contract.at("schema")=="lma.ltx098-vae-prepare-contract/1"&&!plan.contract.at("model_data_embedded").get<bool>(),"Invalid compiled preparation contract");
    plan.contract_sha=sha(vae_contract_bytes,sizeof(vae_contract_bytes));
    plan.checkpoint=read_safetensors(source,source_hash);const auto& config=plan.checkpoint.config;
    require(config.contains("vae")&&nlohmann::json(config.at("vae"))==nlohmann::json(plan.contract.at("vae_config")),"Unsupported old VAE configuration");
    const auto& expected=plan.contract.at("layout");std::set<std::string> observed;uint64_t decoder_parameters=0,decoder_tensors=0;
    for(const auto& tensor:plan.checkpoint.tensors) {
        if(tensor.name.compare(0,12,"vae.decoder.")==0) {
            ++decoder_tensors;decoder_parameters+=tensor.elements;require(expected.contains(tensor.name),"Unknown old decoder tensor");
        }
        if(expected.contains(tensor.name)) {
            require(Json(tensor.shape)==expected.at(tensor.name),"Different old decoder/statistics shape");observed.insert(tensor.name);
        }
    }
    require(observed.size()==134&&decoder_tensors==132&&decoder_parameters==552814641,"Incomplete old decoder/statistics layout");
    const auto& graphs=plan.contract.at("graphs");require(graphs.is_array()&&graphs.size()==9,"Invalid compiled graph list");
    for(size_t i=0;i<9;++i) {
        const auto& graph=graphs.at(i);std::string name="stage-0"+std::to_string(i)+".onnx";
        require(graph.at("file")==name&&graph.at("data_file")==name+".data","Invalid compiled asset name");
        plan.asset_bytes+=graph.at("bytes").get<uint64_t>()+graph.at("data_bytes").get<uint64_t>();
        plan.parameter_bytes+=graph.at("data_bytes").get<uint64_t>();
    }
    std::array<uint64_t,9> next{};require(plan.contract.at("routes").size()==138,"Invalid compiled route count");
    for(const auto& item:plan.contract.at("routes")) {
        auto key=item.at("source").get<std::string>();require(observed.count(key)!=0&&item.at("transform")=="reshape_f32","Invalid compiled parameter route");
        auto stage=static_cast<size_t>(number(item.at("stage"),0,8));auto offset=number(item.at("offset"),0,1500000000),bytes=number(item.at("bytes"),4,1500000000);
        require(offset==next[stage],"Noncontiguous compiled output plan");next[stage]+=bytes;
        uint64_t elements=1;for(const auto& dimension:expected.at(key))elements*=dimension.get<uint64_t>();
        require(elements*4==bytes,"Compiled source/output size mismatch");plan.routes[key].push_back({stage,offset,bytes});
    }
    require(plan.routes.size()==134,"A learned parameter was omitted");
    for(size_t i=0;i<9;++i)require(next[i]==graphs[i].at("data_bytes"),"Incomplete compiled parameter file");
    plan.manifest=plan.contract.at("manifest");plan.manifest_text=plan.manifest.dump(2)+"\n";return plan;
}
void expand(const Tensor& tensor,const std::vector<uint8_t>& input,size_t bytes,std::vector<uint8_t>& output) {
    auto stride=tensor.dtype=="F32"?4u:2u;output.resize(bytes/stride*4);
    bool positive=tensor.name=="vae.per_channel_statistics.std-of-means"||tensor.name=="vae.decoder.timestep_scale_multiplier";
    for(size_t i=0,j=0;i<bytes;i+=stride,j+=4) {
        uint32_t bits=tensor.dtype=="BF16"?static_cast<uint32_t>(le(input.data()+i,2)<<16):
            tensor.dtype=="F16"?half_to_float(static_cast<uint16_t>(le(input.data()+i,2))):static_cast<uint32_t>(le(input.data()+i,4));
        require((bits&0x7f800000)!=0x7f800000,"Non-finite trained VAE parameter");
        if(positive){float value;std::memcpy(&value,&bits,4);require(value>0,"Non-positive trained decoder statistics/multiplier");}
        for(size_t k=0;k<4;++k)output[j+k]=static_cast<uint8_t>(bits>>(8*k));
    }
}
int run(const std::vector<std::string>& args) {
    try {
        require(args.size()==2,"Usage: lma_ltx098_vae_prepare REQUEST.json");auto request=parse(read_request(local_path(args[1])));
        fields(request,{"operation","checkpoint","expected_source_bytes","expected_source_sha256","graph_root","storage_root","output_name","cancel_file","max_output_bytes"});
        auto operation=string(request.at("operation"),32);require(operation=="inspect_vae"||operation=="convert_vae","Unknown preparation operation");
        Cancel cancel;if(request.contains("cancel_file"))cancel.file=local_path(request.at("cancel_file"));cancel.check();
        auto checkpoint_path=local_path(request.at("checkpoint"));File source(checkpoint_path);
        auto expected_bytes=number(request.at("expected_source_bytes"),10,uint64_t(std::numeric_limits<int64_t>::max()));
        auto expected_sha=string(request.at("expected_source_sha256"),64);require(digest(expected_sha),"Invalid source SHA-256");
        auto contract=compiled_contract();const auto& identity=contract.at("checkpoint");
        require(source.size==expected_bytes&&expected_bytes==identity.at("bytes"),"Source byte identity mismatch");
        require(expected_sha==identity.at("sha256"),"Unsupported source SHA-256; exact old checkpoint required");
        Sha256 source_hash;auto plan=inspect(source,source_hash);cancel.check();
        uint64_t required=plan.asset_bytes+plan.manifest_text.size()+receipt_reserve;
        if(request.contains("max_output_bytes"))require(required<=number(request.at("max_output_bytes"),1,uint64_t(std::numeric_limits<int64_t>::max())),"Output exceeds selected storage budget");
        Json record={{"schema","lma.ltx098-native-vae-prepare/1"},{"ok",true},{"operation",operation},
            {"source_bytes",source.size},{"expected_source_sha256",expected_sha},{"source_header_sha256",plan.checkpoint.header_sha},
            {"source_sha256_verified",false},{"source_tensor_count",plan.checkpoint.tensors.size()},{"decoder_tensors",132},{"decoder_parameters",552814641},
            {"learned_source_tensors",134},{"external_initializers",138},{"graphs",9},{"asset_files",18},{"asset_bytes",plan.asset_bytes},
            {"parameter_bytes",plan.parameter_bytes},{"manifest_bytes",plan.manifest_text.size()},{"required_free_bytes",required},{"contract_sha256",plan.contract_sha},
            {"model_data_embedded",false},{"model_inference",false},{"engine_registered",false},{"packaged_in_apk",false},{"physical_android",false},{"complete_video_pipeline",false}};
        if(operation=="inspect_vae") {
            require(!request.contains("storage_root")&&!request.contains("output_name")&&!request.contains("graph_root"),"Inspection does not accept output/graph paths");
            source.unchanged();std::cout<<record.dump()<<std::endl;return 0;
        }
        auto root=fs::canonical(local_path(request.at("storage_root")));require(fs::is_directory(root),"Missing storage directory");local_path(root.u8string());
        auto graph_root=fs::canonical(local_path(request.at("graph_root")));require(fs::is_directory(graph_root),"Missing packaged architecture graphs");local_path(graph_root.u8string());
        require(fs::space(root).available>=required,"Insufficient local storage");
        std::vector<std::string> owned={"ltx098-vae.json","preparation.json"};
        for(const auto& graph:plan.contract.at("graphs")){owned.push_back(graph.at("file"));owned.push_back(graph.at("data_file"));}
        Transaction transaction(root,output_name(request.at("output_name")),owned);std::vector<uint8_t> input(chunk_bytes),output;output.reserve(2*chunk_bytes);
        Json assets=Json::array();uint64_t written=0;
        for(const auto& graph:plan.contract.at("graphs")) {
            cancel.check();auto name=graph.at("file").get<std::string>();File template_file(graph_root/name);
            require(template_file.size==graph.at("bytes"),"Packaged architecture graph size mismatch");
            File destination(transaction.stage/name,true);Sha256 hash;
            for(uint64_t remaining=template_file.size;remaining;){cancel.check();auto count=static_cast<size_t>(std::min<uint64_t>(remaining,input.size()));template_file.read(input.data(),count);hash.update(input.data(),count);destination.write(input.data(),count);remaining-=count;written+=count;}
            template_file.unchanged();auto actual=hash.finish();require(actual==graph.at("sha256"),"Packaged architecture graph SHA-256 mismatch");destination.flush();
            assets.push_back(Json{{"file",name},{"bytes",template_file.size},{"sha256",actual}});
        }
        uint64_t source_done=8+plan.checkpoint.header_bytes,parameters_written=0;
        {
            std::vector<std::unique_ptr<File>> destinations;
            for(const auto& graph:plan.contract.at("graphs")) {
                auto name=graph.at("data_file").get<std::string>();auto destination=std::make_unique<File>(transaction.stage/name,true);
                uint8_t zero=0;destination->seek(graph.at("data_bytes").get<uint64_t>()-1);destination->write(&zero,1);destinations.push_back(std::move(destination));
            }
            std::sort(plan.checkpoint.tensors.begin(),plan.checkpoint.tensors.end(),[](const Tensor& a,const Tensor& b){return a.first<b.first;});
            progress("convert",source_done,source.size);uint64_t next_progress=source_done+64*1024*1024;
            for(const auto& tensor:plan.checkpoint.tensors) {
                auto routes=plan.routes.find(tensor.name);uint64_t converted_offset=0;
                for(uint64_t remaining=tensor.last-tensor.first;remaining;) {
                    cancel.check();auto count=static_cast<size_t>(std::min<uint64_t>(remaining,input.size()));source.read(input.data(),count);source_hash.update(input.data(),count);source_done+=count;remaining-=count;
                    if(routes!=plan.routes.end()) {
                        expand(tensor,input,count,output);
                        for(const auto& route:routes->second){require(converted_offset+output.size()<=route.bytes,"Parameter output overflow");auto& destination=*destinations.at(route.stage);destination.seek(route.offset+converted_offset);destination.write(output.data(),output.size());parameters_written+=output.size();}
                        converted_offset+=output.size();
                    }
                    if(source_done>=next_progress){progress("convert",source_done,source.size);next_progress=source_done+64*1024*1024;}
                }
                if(routes!=plan.routes.end())require(converted_offset==routes->second.front().bytes,"Incomplete learned parameter conversion");
            }
            cancel.check();source.unchanged();require(source_done==source.size&&source_hash.finish()==expected_sha,"Source SHA-256 mismatch; output discarded");
            require(parameters_written==plan.parameter_bytes,"Parameter byte accounting mismatch");record["source_sha256_verified"]=true;record["source_sha256"]=expected_sha;
            for(size_t i=0;i<9;++i) {
                auto& destination=*destinations[i];const auto& graph=plan.contract.at("graphs")[i];uint64_t size=graph.at("data_bytes");destination.flush();destination.seek(0);Sha256 hash;progress("verify_output",0,size);
                for(uint64_t remaining=size;remaining;){cancel.check();auto count=static_cast<size_t>(std::min<uint64_t>(remaining,input.size()));destination.read(input.data(),count);hash.update(input.data(),count);remaining-=count;}
                auto actual=hash.finish();require(actual==graph.at("data_sha256"),"Converted parameter-file SHA-256 mismatch");
                assets.push_back(Json{{"file",graph.at("data_file")},{"bytes",size},{"sha256",actual}});written+=size;
            }
        }
        require(written==plan.asset_bytes,"Asset byte accounting mismatch");
        {File manifest(transaction.stage/"ltx098-vae.json",true);manifest.write(plan.manifest_text.data(),plan.manifest_text.size());manifest.flush();}
        record["assets"]=assets;record["source_streamed_bytes"]=source_done;record["asset_written_bytes"]=written;record["parameter_written_bytes"]=parameters_written;
        record["manifest_sha256"]=sha(plan.manifest_text.data(),plan.manifest_text.size());record["input_chunk_bytes"]=chunk_bytes;record["output_chunk_capacity_bytes"]=2*chunk_bytes;
        record["complete_tensor_allocated"]=false;record["source_retained"]=true;record["graph_sha256_verified"]=true;record["parameter_sha256_verified"]=true;
        {File receipt(transaction.stage/"preparation.json",true);auto text=record.dump(2)+"\n";receipt.write(text.data(),text.size());receipt.flush();}
        cancel.check();source.unchanged();transaction.commit();progress("committed",written,written);std::cout<<record.dump()<<std::endl;return 0;
    } catch(const std::exception& error) {
        std::cout<<Json{{"ok",false},{"error",error.what()}}.dump(-1,' ',false,Json::error_handler_t::replace)<<std::endl;return 1;
    }
}
}
#ifdef _WIN32
int wmain(int argc,wchar_t** argv) {
    std::vector<std::string> args;
    for(int i=0;i<argc;++i){int n=WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,argv[i],-1,nullptr,0,nullptr,nullptr);if(n<=0)return 2;
        std::string text(static_cast<size_t>(n),'\0');WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,argv[i],-1,text.data(),n,nullptr,nullptr);text.pop_back();args.push_back(text);}
    return run(args);
}
#else
int main(int argc,char** argv){return run(std::vector<std::string>(argv,argv+argc));}
#endif

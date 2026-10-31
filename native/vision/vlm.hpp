#pragma once
#include "llama.h"
#include "mtmd.h"
#include "mtmd-helper.h"

namespace lma_vision {
inline const char* parts_grammar(){return R"GBNF(root ::= "{" ws "\"parts\"" ws ":" ws "[" ws part (ws "," ws part){0,15} ws "]" ws "}"
part ::= "{" ws "\"name\"" ws ":" ws "\"" char{1,64} "\"" ws "}"
char ::= [^"\\\x00-\x1F] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F]{4})
ws ::= [ \t\n\r]{0,8}
)GBNF";}
inline json validate_parts(const std::string& text){
 require(text.size()>0&&text.size()<=32768,"Missing/incomplete part identification");auto root=json::parse(text);require(root.is_object()&&root.size()==1&&root.contains("parts")&&root.at("parts").is_array(),"Invalid parts result");const auto& parts=root.at("parts");require(parts.size()>=1&&parts.size()<=16,"Part count exceeds profile");std::set<std::string> names;
 for(const auto& p:parts){require(p.is_object()&&p.size()==1&&p.at("name").is_string(),"Invalid part name");auto name=p.at("name").get<std::string>();require(!name.empty()&&name.size()<=256&&names.insert(name).second,"Empty/duplicate part name");for(unsigned char c:name)require(c>=32,"Control character in part name");}return root;
}
inline std::string piece(const llama_vocab* vocab,llama_token token){std::vector<char> value(256);int n=llama_token_to_piece(vocab,token,value.data(),int(value.size()),0,false);if(n<0){require(n>=-8192,"Oversized token piece");value.resize(size_t(-n));n=llama_token_to_piece(vocab,token,value.data(),int(value.size()),0,false);}require(n>=0,"Cannot decode token");return std::string(value.data(),size_t(n));}
inline void identify_parts(const json& command){
 require(command.at("type")=="text.generate"&&command.at("pipeline")=="vlm_parts","VLM recipe mismatch");auto p=command.at("parameters");for(auto it=p.begin();it!=p.end();it++)require(it.key()=="threads"||it.key()=="context"||it.key()=="maxTokens"||it.key()=="imageTokens","Unknown VLM parameter");
 int threads=integer(p,"threads",2,1,16),context=integer(p,"context",4096,512,16384),max_tokens=integer(p,"maxTokens",512,32,2048),image_tokens=integer(p,"imageTokens",1024,64,4096);require(max_tokens<context&&image_tokens<context,"VLM context budget is too small");
 fs::path workspace=command.at("workspace").get<std::string>(),output=command.at("output").get<std::string>();require(workspace.is_absolute()&&fs::is_directory(workspace)&&output.is_absolute()&&!fs::exists(output),"Invalid private VLM workspace");workspace=fs::canonical(workspace);
 require(command.at("components").size()==2,"Select only model and matched mmproj");for(auto it=command.at("components").begin();it!=command.at("components").end();it++){require(it.key()=="model"||it.key()=="mmproj","Unknown VLM component");fs::path file=regular(command.at("components"),it.key().c_str());require(fs::canonical(file).parent_path()==workspace&&file.filename()==it.key()+".gguf","VLM component escaped workspace");}
 auto image=load(regular(command,"referenceImage"));std::vector<uint8_t> rgb(size_t(image.width)*image.height*3);for(size_t i=0;i<rgb.size()/3;i++)for(int c=0;c<3;c++)rgb[i*3+c]=image.rgba[i*4+c];image.rgba.clear();
 auto silence=[](ggml_log_level,const char*,void*){};llama_log_set(silence,nullptr);mtmd_helper_log_set(silence,nullptr);llama_backend_init();
 struct Backend {~Backend(){llama_backend_free();}} backend;
 event({{"event","stage"},{"stage","loading_vision_model"}});auto mp=llama_model_default_params();mp.n_gpu_layers=0;mp.load_mode=LLAMA_LOAD_MODE_MMAP;
 std::unique_ptr<llama_model,decltype(&llama_model_free)> model(llama_model_load_from_file((workspace/"model.gguf").string().c_str(),mp),llama_model_free);require(bool(model),"Cannot load selected VLM GGUF");
 auto trained=llama_model_n_ctx_train(model.get());require(trained>=512,"Unknown VLM training context");context=std::min(context,int(trained));require(max_tokens<context&&image_tokens<context,"VLM selected limits exceed trained context");
 auto cp=llama_context_default_params();cp.n_ctx=uint32_t(context);cp.n_batch=uint32_t(std::min(context,512));cp.n_ubatch=cp.n_batch;cp.n_threads=threads;cp.n_threads_batch=threads;cp.flash_attn_type=LLAMA_FLASH_ATTN_TYPE_DISABLED;
 std::unique_ptr<llama_context,decltype(&llama_free)> ctx(llama_init_from_model(model.get(),cp),llama_free);require(bool(ctx),"Cannot allocate local VLM context");
 auto vp=mtmd_context_params_default();vp.use_gpu=false;vp.n_threads=threads;vp.warmup=false;vp.print_timings=false;vp.image_min_tokens=64;vp.image_max_tokens=image_tokens;vp.flash_attn_type=LLAMA_FLASH_ATTN_TYPE_DISABLED;
 std::unique_ptr<mtmd_context,decltype(&mtmd_free)> vision(mtmd_init_from_file((workspace/"mmproj.gguf").string().c_str(),model.get(),vp),mtmd_free);require(bool(vision)&&mtmd_support_vision(vision.get()),"Incompatible local model/mmproj vision pair");
 std::unique_ptr<mtmd_bitmap,decltype(&mtmd_bitmap_free)> bitmap(mtmd_bitmap_init(uint32_t(image.width),uint32_t(image.height),rgb.data()),mtmd_bitmap_free);require(bool(bitmap),"Cannot prepare image bitmap");
 std::string prompt=std::string(mtmd_default_marker())+"\nIdentify the distinct physical components of the main object for a part-based 3D reconstruction. Return JSON only: {\"parts\":[{\"name\":\"short component name\"}]}. Use 1 to 16 unique visible parts. Do not include background, explanation, markdown, or hidden reasoning.";
 auto tmpl=llama_model_chat_template(model.get(),nullptr);require(tmpl&&*tmpl,"Selected VLM has no supported chat template");llama_chat_message msg{"user",prompt.c_str()};std::vector<char> formatted(16384);int n=llama_chat_apply_template(tmpl,&msg,1,true,formatted.data(),int(formatted.size()));require(n>0&&n<int(formatted.size()),"Unsupported/oversized selected VLM chat template");
 mtmd_input_text text{formatted.data(),size_t(n),true,true};const mtmd_bitmap* bitmap_ptr=bitmap.get();std::unique_ptr<mtmd_input_chunks,decltype(&mtmd_input_chunks_free)> chunks(mtmd_input_chunks_init(),mtmd_input_chunks_free);
 require(bool(chunks)&&mtmd_tokenize(vision.get(),chunks.get(),&text,&bitmap_ptr,1)==0,"Cannot tokenize selected vision input");auto input_tokens=mtmd_helper_get_n_tokens(chunks.get());auto input_positions=mtmd_helper_get_n_pos(chunks.get());require(input_tokens>0&&input_tokens<=32768&&input_positions>0&&input_positions+max_tokens<context,"Image/text/output exceed VLM context");
 event({{"event","execution"},{"details",{{"pipeline","vlm_parts"},{"backend","cpu"},{"sourceRevision","b29c606e28a01b1bc8c1351026a0fa6e616bf6c4"},{"context",context},{"imageTokenLimit",image_tokens},{"promptTokens",input_tokens},{"sampling","grammar_greedy"}}}});event({{"event","stage"},{"stage","identifying_parts"}});
 llama_pos past=0;require(mtmd_helper_eval_chunks(vision.get(),ctx.get(),chunks.get(),0,0,int(cp.n_batch),true,&past)==0,"Local image/text evaluation failed");
 const auto* vocab=llama_model_get_vocab(model.get());std::unique_ptr<llama_sampler,decltype(&llama_sampler_free)> sampler(llama_sampler_chain_init(llama_sampler_chain_default_params()),llama_sampler_free);auto* grammar=llama_sampler_init_grammar(vocab,parts_grammar(),"root");require(bool(sampler)&&grammar,"Cannot initialize JSON constrained generation");llama_sampler_chain_add(sampler.get(),grammar);llama_sampler_chain_add(sampler.get(),llama_sampler_init_greedy());
 std::string content;int used=0;bool stopped=false;
 for(int i=0;i<max_tokens;i++){llama_token token=llama_sampler_sample(sampler.get(),ctx.get(),-1);used++;if(llama_vocab_is_eog(vocab,token)){stopped=true;break;}content+=piece(vocab,token);require(content.size()<=32768,"VLM output exceeds local limit");auto batch=llama_batch_get_one(&token,1);require(llama_decode(ctx.get(),batch)==0,"VLM token evaluation failed");past++;event({{"event","progress"},{"stage","identifying_parts"},{"step",i+1},{"steps",max_tokens}});}
 require(stopped,"VLM output limit reached before complete parts JSON; increase the per-model limit");auto parts=validate_parts(content);event({{"event","execution"},{"details",{{"partIdentification",parts},{"partCount",parts.at("parts").size()}}}});
 json result={{"schema","lma.text-result/1"},{"content",parts.dump()},{"reasoning",""},{"finishReason","stop"},{"usage",{{"prompt_tokens",input_tokens},{"completion_tokens",used},{"total_tokens",input_tokens+size_t(used)}}}};std::ofstream stream(output,std::ios::binary);stream<<result.dump();stream.flush();require(bool(stream),"Cannot persist parts result");stream.close();event({{"event","complete"},{"output",output.string()}});
}
}

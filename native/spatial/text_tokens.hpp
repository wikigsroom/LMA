#pragma once
#include "typed_graph.hpp"
#include "tokenizers/hf_tokenizer.h"
#include "sentencepiece_processor.h"
namespace lma_spatial {
struct TokenInputs{Integers ids,mask;};
inline TokenInputs bpe_tokens(const fs::path& path,const std::string& prompt,int length,int64_t vocab,int pad,bool qwen){
 require(length>=2&&length<=512&&prompt.size()<=65536&&fs::is_regular_file(path)&&fs::file_size(path)<=32*1024*1024,"Text/tokenizer bounds exceeded");
 HFTokenizer tokenizer(path.u8string());tokenizer.validate_vocab_size(vocab);require(pad>=0&&pad<vocab,"Invalid text padding ID");tokenizer.set_padding(pad,false);
 std::string text=prompt;
 if(qwen){
  require(tokenizer.token_to_id("<|im_start|>")>=0&&tokenizer.token_to_id("<|im_end|>")>=0,"Select a matched Qwen3 tokenizer");
  // Fixed Qwen3 single user / no tools / enable_thinking=false template.
  text="<|im_start|>user\n"+prompt+"<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n";
 }
 std::vector<int> raw;std::string error;require(tokenizer.encode(text,raw,nullptr,&error),"BPE tokenization failed");std::vector<float> mask(raw.size(),1);
 tokenizer.pad_tokens(raw,nullptr,&mask,size_t(length),size_t(length),false);require(raw.size()==size_t(length)&&mask.size()==raw.size(),"Text padding failed");
 TokenInputs result;for(size_t i=0;i<raw.size();i++){require(raw[i]>=0&&raw[i]<vocab,"Text token outside embedding table");result.ids.push_back(raw[i]);result.mask.push_back(mask[i]!=0);}return result;
}
inline TokenInputs t5_tokens(const fs::path& path,const std::string& prompt,int length,int64_t vocab){
 require(length>=2&&length<=512&&prompt.size()<=65536&&fs::is_regular_file(path)&&fs::file_size(path)<=16*1024*1024,"T5 tokenizer bounds exceeded");
 sentencepiece::SentencePieceProcessor processor;require(processor.LoadFromSerializedProto(bytes(path,16*1024*1024)).ok(),"Select a valid T5 SentencePiece model");require(processor.eos_id()==1&&processor.pad_id()==0&&processor.GetPieceSize()<=vocab,"Unmatched T5 vocabulary");
 // T5 legacy tokenizer's default add_dummy_prefix and normalization are read
 // from the user's .model. Preserve sentinel tokens without embedding a vocab.
 std::vector<int> raw;size_t at=0;
 while(at<prompt.size()){
  size_t begin=at,end=std::string::npos;int sentinel=-1;
  while((begin=prompt.find("<extra_id_",begin))!=std::string::npos){
   end=prompt.find('>',begin+10);
   if(end!=std::string::npos&&end>begin+10&&end-begin<=12){auto digits=prompt.substr(begin+10,end-begin-10);if(digits.find_first_not_of("0123456789")==std::string::npos){int value=std::stoi(digits);if(value<100&&std::to_string(value)==digits){sentinel=value;break;}}}
   begin+=10;
  }
  if(sentinel<0){begin=prompt.size();end=std::string::npos;}
  if(begin>at){std::vector<int> part;require(processor.Encode(prompt.substr(at,begin-at),&part).ok(),"T5 tokenization failed");raw.insert(raw.end(),part.begin(),part.end());}
  if(end==std::string::npos)break;raw.push_back(processor.GetPieceSize()+99-sentinel);at=end+1;
 }
 if(raw.empty()||raw.back()!=1)raw.push_back(1);if(raw.size()>size_t(length)){raw.resize(length);raw.back()=1;}
 TokenInputs result;for(int id:raw){require(id>=0&&id<vocab,"T5 token outside embedding table");result.ids.push_back(id);result.mask.push_back(1);}result.ids.resize(length,0);result.mask.resize(length,0);return result;
}
}

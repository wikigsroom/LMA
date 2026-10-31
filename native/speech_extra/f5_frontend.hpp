#pragma once
#include "../worker_common.hpp"
#include "f5_official.hpp"
#include <unordered_map>
#include <sstream>
namespace lma_f5 {
inline bool active = false;
inline size_t maximum_mel_frames = 2812;
inline std::unordered_map<std::string, std::vector<std::string>> dictionary;
inline std::vector<std::string> chars(const std::string& value) {
    std::vector<std::string> out;
    for (size_t i=0; i<value.size();) {
        unsigned char c=value[i]; size_t n=c<128?1:c>=0xc2&&c<=0xdf?2:c>=0xe0&&c<=0xef?3:c>=0xf0&&c<=0xf4?4:0;
        lma_worker::require(n && i+n<=value.size(), "Invalid UTF-8");
        for(size_t j=1;j<n;++j) lma_worker::require((uint8_t(value[i+j])&0xc0)==0x80,"Invalid UTF-8 continuation");
        if(n==3) lma_worker::require(!(c==0xe0 && uint8_t(value[i+1])<0xa0) && !(c==0xed && uint8_t(value[i+1])>=0xa0),"Invalid UTF-8 scalar");
        if(n==4) lma_worker::require(!(c==0xf0 && uint8_t(value[i+1])<0x90) && !(c==0xf4 && uint8_t(value[i+1])>=0x90),"Invalid UTF-8 scalar");
        out.push_back(value.substr(i,n)); i+=n;
    }
    return out;
}
inline std::string tone3(const std::string& input) {
    const std::vector<std::string> marked = chars("āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ");
    const std::string bases = "aaaaeeeeiiiioooouuuuvvvv";
    std::string output; int tone=0;
    for(const auto& ch: chars(input)) {
        auto found=std::find(marked.begin(),marked.end(),ch);
        if(found!=marked.end()) { size_t index=size_t(found-marked.begin()); output+=bases[index]; tone=int(index%4)+1; }
        else if(ch=="ü") output+='v'; else output+=ch;
    }
    if(tone) output+=char('0'+tone);
    return output;
}
inline void load(const std::string& path, bool phrases) {
    lma_worker::require(std::filesystem::file_size(path)<=64*1024*1024, "Pinyin resource exceeds limits");
    std::ifstream in(path); std::string line; size_t count=0;
    while(std::getline(in,line)) {
        if(line.empty() || line[0]=='#') continue;
        auto colon=line.find(':'); if(colon==std::string::npos) continue;
        std::string key=line.substr(0,colon), value=line.substr(colon+1);
        auto comment=value.find('#'); if(comment!=std::string::npos) value.resize(comment);
        if(!phrases) {
            if(key.rfind("U+",0)!=0) continue;
            unsigned cp=unsigned(std::stoul(key.substr(2),nullptr,16));
            lma_worker::require(cp && !(cp>=0xd800 && cp<=0xdfff), "Invalid pinyin scalar");
            key.clear();
            if(cp<=0x7f) key+=char(cp);
            else if(cp<=0x7ff) { key+=char(0xc0|(cp>>6)); key+=char(0x80|(cp&63)); }
            else if(cp<=0xffff) { key+=char(0xe0|(cp>>12)); key+=char(0x80|((cp>>6)&63)); key+=char(0x80|(cp&63)); }
            else if(cp<=0x10ffff) { key+=char(0xf0|(cp>>18)); key+=char(0x80|((cp>>12)&63)); key+=char(0x80|((cp>>6)&63)); key+=char(0x80|(cp&63)); }
            else throw std::runtime_error("Invalid pinyin codepoint");
            auto comma=value.find(','); if(comma!=std::string::npos) value.resize(comma);
        }
        auto letters=chars(key); if(letters.empty()||letters.size()>16) continue;
        std::istringstream tokens(value); std::vector<std::string> pronunciation; std::string token;
        while(tokens>>token) pronunciation.push_back(tone3(token));
        if(pronunciation.size()!=letters.size()) continue;
        dictionary[key]=std::move(pronunciation);
        lma_worker::require(++count<=2000000, "Pinyin resource entry limit");
    }
    lma_worker::require(count>0, "Pinyin resource has no usable entries");
}
inline std::vector<int32_t> tokenize(const std::unordered_map<std::string,int32_t>& vocab, const std::string& value) {
    if(lma_f5_official::selected)return lma_f5_official::selected->tokenize(vocab,value);
    std::vector<int32_t> result; auto letters=chars(value);
    auto emit=[&](const std::string& token) {
        auto item=vocab.find(token); lma_worker::require(item!=vocab.end(), "Text pronunciation is outside the selected F5 vocabulary");
        result.push_back(item->second);
    };
    for(size_t i=0;i<letters.size();) {
        bool found=false;
        for(size_t n=std::min<size_t>(16,letters.size()-i);n>0;--n) {
            std::string key;for(size_t j=0;j<n;++j)key+=letters[i+j];
            auto item=dictionary.find(key); if(item==dictionary.end())continue;
            for(const auto& syllable:item->second) { emit(" "); emit(syllable); }
            i+=n;found=true;break;
        }
        if(found)continue;
        const auto& ch=letters[i++];
        if(ch=="，") emit(","); else if(ch=="。") emit("."); else if(ch=="！")emit("!");
        else if(ch=="？")emit("?"); else if(ch=="；")emit(";"); else if(ch=="：")emit(":");
        else if(ch=="\n"||ch=="\r"||ch=="\t")emit(" "); else emit(ch);
    }
    return result;
}
}

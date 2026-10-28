// SPDX-License-Identifier: Apache-2.0
// SoulX text/protocol/window/RAS ports. See NOTICE for pinned upstream sources.
#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <functional>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>

namespace lma::soulx::language {
using Tokens=std::vector<int32_t>;
using Tokenize=std::function<Tokens(const std::string&)>;
inline void require(bool ok,const char* error){if(!ok)throw std::invalid_argument(error);}
inline bool chinese(uint32_t c){return c>=0x4e00 && c<=0x9fff;}
inline bool english(uint32_t c){return c>='A' && c<='Z' || c>='a' && c<='z';}
inline bool whitespace(uint32_t c){return c>=9 && c<=13 || c>=28 && c<=32 || c==0x85 || c==0xa0 || c==0x1680 || c>=0x2000 && c<=0x200a || c==0x2028 || c==0x2029 || c==0x202f || c==0x205f || c==0x3000;}
inline std::vector<uint32_t> unicode(const std::string& text){
    require(text.size()<=65536,"SoulX text exceeds the input byte limit");std::vector<uint32_t> result;
    for(size_t i=0;i<text.size();){
        uint32_t first=static_cast<unsigned char>(text[i++]),c=first;int tail=0;
        if(first>=0xc2 && first<=0xdf){c=first&31;tail=1;}
        else if(first>=0xe0 && first<=0xef){c=first&15;tail=2;}
        else if(first>=0xf0 && first<=0xf4){c=first&7;tail=3;}
        else require(first<0x80,"Invalid SoulX UTF-8 leading byte");
        for(int j=0;j<tail;++j){require(i<text.size(),"Truncated SoulX UTF-8");auto b=static_cast<unsigned char>(text[i++]);require((b&0xc0)==0x80,"Invalid SoulX UTF-8 continuation");c=(c<<6)|(b&63);}
        require(c && c<=0x10ffff && !(c>=0xd800 && c<=0xdfff) && (tail!=1 || c>=0x80) && (tail!=2 || c>=0x800) && (tail!=3 || c>=0x10000),"Invalid/overlong SoulX UTF-8 codepoint");result.push_back(c);
    }return result;
}
inline std::string utf8(const std::vector<uint32_t>& points){
    std::string result;for(auto c:points){
        if(c<0x80)result+=static_cast<char>(c);
        else if(c<0x800){result+=static_cast<char>(0xc0|(c>>6));result+=static_cast<char>(0x80|(c&63));}
        else if(c<0x10000){result+=static_cast<char>(0xe0|(c>>12));result+=static_cast<char>(0x80|((c>>6)&63));result+=static_cast<char>(0x80|(c&63));}
        else{result+=static_cast<char>(0xf0|(c>>18));result+=static_cast<char>(0x80|((c>>12)&63));result+=static_cast<char>(0x80|((c>>6)&63));result+=static_cast<char>(0x80|(c&63));}
    }return result;
}
inline std::string normalize(const std::string& text){
    auto points=unicode(text);
    // Match Python re.sub's non-overlapping behavior, including the consumed
    // right-hand character, rather than repeatedly removing every CJK space.
    for(int pass=0;pass<3;++pass){
        std::vector<uint32_t> next;
        for(size_t i=0;i<points.size();){
            auto c=points[i++];next.push_back(c);size_t j=i;while(j<points.size() && whitespace(points[j]))++j;
            bool left=pass==1?english(c):chinese(c),right=j<points.size() && (pass==2?english(points[j]):chinese(points[j]));
            if(j>i && left && right){next.push_back(points[j]);i=j+1;}
        }points.swap(next);
    }
    if(!points.empty()){if(chinese(points.back()))points.push_back(0x3002);else if(english(points.back()))points.push_back('.');}
    return utf8(points);
}
inline void plain_text(const std::string& text){
    unicode(text);
    for(const char* reserved:{"<|SPEAKER_","<|text_start|>","<|text_end|>","<|semantic_token_start|>","<|semantic_token_end|>","<|task_podcast|>"})
        require(text.find(reserved)==std::string::npos,"SoulX transcript contains a structural control token");
}
inline std::string format_text(const std::string& text,int speaker,bool first_reference){
    require(speaker>=0 && speaker<4,"SoulX speaker index must be 0 to 3");plain_text(text);
    return std::string(first_reference?"<|task_podcast|>":"")+"<|SPEAKER_"+std::to_string(speaker)+"|><|text_start|>"+normalize(text)+"<|text_end|><|semantic_token_start|>";
}
struct Layout{int32_t vocabulary=0,offset=0,eos=0,audio_start=0;};
inline void valid_layout(const Layout& x){require(x.vocabulary>=6561 && x.vocabulary<=262144 && x.offset>0 && x.offset<=x.vocabulary-6561 && x.eos>=0 && x.eos<x.offset && x.audio_start>=0 && x.audio_start<x.offset && x.eos!=x.audio_start,"Invalid SoulX language token layout");}
inline Tokens audio(const Tokens& codes,const Layout& x){valid_layout(x);require(!codes.empty() && codes.size()<=375,"SoulX reference code count must be 1 to 375");Tokens result;for(auto code:codes){require(code>=0 && code<6561,"Invalid SoulX reference semantic code");result.push_back(x.offset+code);}result.push_back(x.eos);return result;}
inline void append(Tokens& to,const Tokens& from){to.insert(to.end(),from.begin(),from.end());}
struct Reference{std::string text;Tokens codes;};
struct Turn{std::string text;int speaker=0;};
struct Window{int max_turns=10,threshold=6192,history=2,text_history=2;};
class History{
    Layout layout_;Window policy_;std::vector<Tokens> prompts_,texts_;Tokens active_;size_t references_=0,valid_=0;
public:
    size_t resets=0;
    History(const std::vector<Reference>& refs,const Layout& layout,const Window& policy,const Tokenize& tokenize):layout_(layout),policy_(policy),references_(refs.size()),valid_(refs.size()){
        valid_layout(layout_);require(!refs.empty() && refs.size()<=4,"SoulX requires 1 to 4 references");
        require(policy.history>=1 && policy.history<=8 && policy.text_history>=0 && policy.text_history<=16 && policy.max_turns>=static_cast<int>(refs.size())+policy.history && policy.max_turns<=64 && policy.threshold>=128 && policy.threshold<=8192,"Invalid SoulX history window");
        for(size_t i=0;i<refs.size();++i){auto tokens=tokenize(format_text(refs[i].text,static_cast<int>(i),i==0));require(!tokens.empty() && tokens.back()==layout.audio_start,"Wrong SoulX reference text protocol");append(tokens,audio(refs[i].codes,layout));prompts_.push_back(tokens);texts_.push_back(tokens);append(active_,tokens);}
    }
    Tokens input(const Turn& turn,int context,int reserve,const Tokenize& tokenize){
        require(turn.speaker>=0 && static_cast<size_t>(turn.speaker)<references_,"SoulX turn selects a missing reference");require(!turn.text.empty(),"SoulX target text is empty");
        auto target=tokenize(format_text(turn.text,turn.speaker,false));require(!target.empty() && target.back()==layout_.audio_start,"Wrong SoulX turn text protocol");
        require(context>=256 && context<=8192 && reserve>=1 && reserve<=3000,"Invalid SoulX context/output reservation");
        if(valid_>static_cast<size_t>(policy_.max_turns) || active_.size()>static_cast<size_t>(policy_.threshold) || active_.size()+target.size()+reserve>static_cast<size_t>(context)){
            size_t tail=std::min(static_cast<size_t>(policy_.history),texts_.size()-references_);
            size_t end=texts_.size()-tail;
            size_t start=std::max(references_,end>static_cast<size_t>(policy_.text_history)?end-policy_.text_history:0);
            Tokens rebuilt;for(size_t i=0;i<references_;++i)append(rebuilt,texts_[i]);
            for(size_t i=start;i<end;++i)append(rebuilt,texts_[i]);
            for(size_t i=prompts_.size()-tail;i<prompts_.size();++i)append(rebuilt,prompts_[i]);
            active_.swap(rebuilt);valid_=references_+texts_.size()-start;++resets;
        }
        require(active_.size()+target.size()+reserve<=static_cast<size_t>(context),"SoulX required reference/history/target/output exceed context; reduce the explicit profile");
        Tokens result=active_;append(result,target);return result;
    }
    void accept(const Turn& turn,const Tokens& generated,const Tokenize& tokenize){
        require(!generated.empty(),"Empty SoulX generation cannot enter history");
        auto text=tokenize(format_text(turn.text,turn.speaker,false));Tokens complete=text;
        for(size_t i=0;i<generated.size();++i){auto token=generated[i];require(token>=layout_.offset && token<layout_.offset+6561 || token==layout_.eos && i+1==generated.size(),"Non-semantic SoulX generation cannot enter history");}
        append(complete,generated);if(generated.back()!=layout_.eos)complete.push_back(layout_.eos); // Context delimiter after an explicitly truncated turn, not a generated token.
        append(active_,complete);prompts_.push_back(complete);text.pop_back();texts_.push_back(text);++valid_;
    }
};
struct Sampling{double temperature=.6,repetition=1.25,top_p=.9,tau=.2;int top_k=100,minimum=8,maximum=3000,window=25;bool ras=true;};
inline void valid_sampling(const Sampling& p){
    require(std::isfinite(p.temperature) && p.temperature>=0 && p.temperature<=3 && std::isfinite(p.repetition) && p.repetition>0 && p.repetition<=10 && std::isfinite(p.top_p) && p.top_p>0 && p.top_p<=1 && std::isfinite(p.tau) && p.tau>0 && p.tau<=1 && p.top_k>=0 && p.top_k<=262144 && p.minimum>=0 && p.maximum>=1 && p.maximum<=3000 && p.minimum<p.maximum && p.window>=1 && p.window<=256,"Invalid SoulX sampling profile");
    require(p.temperature!=0 || !p.ras,"Greedy SoulX decoding requires explicit use_ras=false");
}
inline std::vector<double> probabilities(const std::vector<double>& logits){
    double peak=*std::max_element(logits.begin(),logits.end());require(std::isfinite(peak),"SoulX logits contain no finite choice");std::vector<double> result(logits.size());double total=0;
    for(size_t i=0;i<logits.size();++i){result[i]=std::exp(logits[i]-peak);total+=result[i];}require(total>0 && std::isfinite(total),"Invalid SoulX probability mass");for(auto& p:result)p/=total;return result;
}
inline std::vector<double> scores(const std::vector<float>& raw,const Tokens& generated,const Layout& layout,const Sampling& p){
    valid_layout(layout);valid_sampling(p);require(raw.size()==static_cast<size_t>(layout.vocabulary),"Wrong SoulX logits vocabulary");std::vector<double> result(raw.begin(),raw.end());
    for(auto x:result)require(std::isfinite(x),"Non-finite SoulX neural logits");
    // HF repetition processor ignores the prompt and applies once per unique
    // generated token. RAS may then undo ALL processors, exactly as upstream.
    Tokens unique=generated;std::sort(unique.begin(),unique.end());unique.erase(std::unique(unique.begin(),unique.end()),unique.end());
    for(auto token:unique){require(token>=0 && token<layout.vocabulary,"Invalid SoulX generated history ID");result[token]=result[token]<0?result[token]*p.repetition:result[token]/p.repetition;}
    if(generated.size()<static_cast<size_t>(p.minimum))result[layout.eos]=-std::numeric_limits<double>::infinity();
    if(p.temperature==0)return result;
    for(auto& x:result)x/=p.temperature;
    if(p.top_k>0 && static_cast<size_t>(p.top_k)<result.size()){
        auto ordered=result;std::nth_element(ordered.begin(),ordered.begin()+p.top_k-1,ordered.end(),std::greater<double>());double cutoff=ordered[p.top_k-1];for(auto& x:result)if(x<cutoff)x=-std::numeric_limits<double>::infinity();
    }
    if(p.top_p<1){
        auto probs=probabilities(result);std::vector<size_t> order;for(size_t i=0;i<result.size();++i)if(std::isfinite(result[i]))order.push_back(i);
        std::stable_sort(order.begin(),order.end(),[&](size_t a,size_t b){return result[a]<result[b];});double cumulative=0;
        for(size_t j=0;j+1<order.size();++j){auto i=order[j];cumulative+=probs[i];if(cumulative<=1-p.top_p)result[i]=-std::numeric_limits<double>::infinity();}
    }return result;
}
inline int32_t draw(const std::vector<double>& probs,double uniform){require(std::isfinite(uniform) && uniform>=0 && uniform<1,"SoulX uniform draw must be [0,1)");double cumulative=0;int32_t last=-1;for(size_t i=0;i<probs.size();++i)if(probs[i]>0){last=static_cast<int32_t>(i);cumulative+=probs[i];if(uniform<cumulative)return last;}require(last>=0,"Empty SoulX distribution");return last;}
struct Sample{int32_t token;bool ras_reset=false;};
inline Sample sample(const std::vector<float>& raw,const Tokens& generated,const Tokens& all_input,const Layout& layout,const Sampling& p,double candidate_uniform,double final_uniform){
    auto processed=scores(raw,generated,layout,p);
    if(p.temperature==0)return {static_cast<int32_t>(std::max_element(processed.begin(),processed.end())-processed.begin()),false};
    bool reset=false;if(p.ras){auto candidate=draw(probabilities(processed),candidate_uniform);size_t repeated=1;size_t start=all_input.size()>static_cast<size_t>(p.window)?all_input.size()-p.window:0;for(size_t i=start;i<all_input.size();++i)if(all_input[i]==candidate)++repeated;reset=repeated>=p.window*p.tau;}
    return {draw(probabilities(reset?std::vector<double>(raw.begin(),raw.end()):processed),final_uniform),reset};
}
}

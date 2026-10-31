#pragma once
#include "../worker_common.hpp"
#include <array>
#include <unordered_map>

// CPU implementation of the pinned rjieba 0.2.2 / jieba-rs 0.11 DAG+HMM
// contract. Linguistic tables are explicit, user-selected assets, never APK data.
// Attribution and precise source identities: third_party/f5-frontend-source-lock.json.
namespace lma_f5_official {
using lma_worker::require;
using Json = nlohmann::json;
struct Text {
    std::vector<std::string> chars;
    std::vector<uint32_t> cp;
    explicit Text(const std::string& s) {
        require(s.size() <= 65536, "F5 text exceeds frontend byte budget");
        for(size_t i=0;i<s.size();) {
            uint8_t c=uint8_t(s[i]);size_t n=c<128?1:c>=0xc2&&c<=0xdf?2:c>=0xe0&&c<=0xef?3:c>=0xf0&&c<=0xf4?4:0;
            require(n&&n<=s.size()-i,"Invalid F5 UTF-8");
            uint32_t v=c&uint8_t(n==1?127:n==2?31:n==3?15:7);
            for(size_t k=1;k<n;k++){uint8_t d=uint8_t(s[i+k]);require((d&0xc0)==0x80,"Invalid UTF-8 continuation");v=(v<<6)|(d&63);}
            require((n==1||v>=uint32_t(n==2?128:n==3?2048:65536))&&v<=0x10ffff&&!(v>=0xd800&&v<=0xdfff),"Invalid UTF-8 scalar");
            chars.push_back(s.substr(i,n));cp.push_back(v);i+=n;
        }
        require(chars.size()<=12000,"F5 text exceeds frontend character budget");
    }
    std::string part(size_t a,size_t b)const {std::string s;for(size_t i=a;i<b;i++)s+=chars.at(i);return s;}
};
inline bool range(uint32_t c,uint32_t a,uint32_t b){return c>=a&&c<=b;}
inline bool alpha(uint32_t c){return range(c,'a','z')||range(c,'A','Z')||range(c,'0','9');}
inline bool cjk(uint32_t c){
    return range(c,0x4e00,0x9fff)||range(c,0x3400,0x4dbf)||range(c,0xf900,0xfaff)||range(c,0x20000,0x2a6df)||
        range(c,0x2a700,0x2b73f)||range(c,0x2b740,0x2b81f)||range(c,0x2b820,0x2ceaf)||range(c,0x2ceb0,0x2ebef)||range(c,0x2f800,0x2fa1f);
}
inline bool block(uint32_t c){return cjk(c)||alpha(c)||c=='+'||c=='#'||c=='&'||c=='.'||c=='_'||c=='%'||c=='-';}
inline bool chinese(uint32_t c){return range(c,0x3100,0x9fff);}
struct Node {
    std::unordered_map<uint32_t,size_t> next;
    double frequency=0;
    std::vector<std::string> pronunciation;
};
class Trie {
public:
    std::vector<Node> nodes{1};
    size_t add(const std::string& word) {
        Text t(word);require(!t.cp.empty()&&t.cp.size()<=128,"Invalid frontend dictionary key");size_t id=0;
        for(auto c:t.cp){auto it=nodes[id].next.find(c);if(it!=nodes[id].next.end()){id=it->second;continue;}
            require(nodes.size()<3000000,"Frontend trie exceeds node budget");size_t n=nodes.size();nodes.emplace_back();nodes[id].next.emplace(c,n);id=n;}
        return id;
    }
    const Node* find(const Text& t,size_t a,size_t b)const {
        size_t id=0;for(size_t i=a;i<b;i++){auto it=nodes[id].next.find(t.cp[i]);if(it==nodes[id].next.end())return nullptr;id=it->second;}return &nodes[id];
    }
};
class Frontend {
    Trie words_,pinyin_;
    double logtotal_=0;
    std::array<double,4> initial_{};
    std::array<std::array<double,4>,4> transitions_{};
    std::unordered_map<uint32_t,std::array<double,4>> emissions_;
    static constexpr double missing=-3.14e100;
    std::array<double,4> emit(uint32_t cp)const {auto i=emissions_.find(cp);return i==emissions_.end()?std::array<double,4>{missing,missing,missing,missing}:i->second;}
    void hmm(const Text& t,size_t a,size_t b,std::vector<std::string>& out)const {
        size_t i=a;
        while(i<b){bool matched=range(t.cp[i],0x4e00,0x9fd5);size_t j=i+1;while(j<b&&range(t.cp[j],0x4e00,0x9fd5)==matched)++j;
            if(matched&&j-i>1){
                constexpr int prev[4][2]={{1,3},{0,2},{0,2},{1,3}};
                std::vector<std::array<int,4>> back(j-i);std::vector<int> path(j-i);auto e=emit(t.cp[i]);std::array<double,4> score{};
                for(int s=0;s<4;s++)score[s]=initial_[s]+e[s];
                for(size_t k=i+1;k<j;k++){e=emit(t.cp[k]);std::array<double,4> next{};for(int s=0;s<4;s++){
                    int p=prev[s][0],q=prev[s][1];double v=score[p]+transitions_[p][s]+e[s],w=score[q]+transitions_[q][s]+e[s];
                    next[s]=v>w?v:w;back[k-i][s]=v>w?p:q;
                }score=next;}
                int s=score[1]>score[3]?1:3;path.back()=s;for(size_t k=j-i-1;k>0;k--){s=back[k][s];path[k-1]=s;}
                size_t begin=i,next=i;for(size_t k=i;k<j;k++)switch(path[k-i]){case 0:begin=k;break;case 1:out.push_back(t.part(begin,k+1));next=k+1;break;case 3:out.push_back(t.chars[k]);next=k+1;break;}
                if(next<j)out.push_back(t.part(next,j));
            }else if(matched)out.push_back(t.part(i,j));
            else {
                size_t k=i;
                while(k<j){size_t end=k;
                    if(alpha(t.cp[k])){while(end<j){while(end<j&&alpha(t.cp[end]))end++;if(end+1<j&&(t.cp[end]=='.'||t.cp[end]=='_'||t.cp[end]=='-')&&alpha(t.cp[end+1]))end++;else break;}if(end<j&&t.cp[end]=='%')end++;}
                    else {do{end++;}while(end<j&&!alpha(t.cp[end]));}
                    out.push_back(t.part(k,end));k=end;
                }
            }
            i=j;
        }
    }
    void dag(const Text& t,size_t a,size_t b,std::vector<std::string>& out)const {
        size_t n=b-a;std::vector<double> scores(n+1,0);std::vector<size_t> route(n);
        for(size_t i=n;i-->0;){size_t id=0,best=i+1;double value=-std::numeric_limits<double>::infinity();bool found=false;
            for(size_t j=i;j<n;j++){auto it=words_.nodes[id].next.find(t.cp[a+j]);if(it==words_.nodes[id].next.end())break;id=it->second;
                double f=words_.nodes[id].frequency;if(f<=0)continue;double v=std::log(f)-logtotal_+scores[j+1];
                if(!found||v>value||(v==value&&j+1>best)){value=v;best=j+1;found=true;}}
            if(!found)value=-logtotal_+scores[i+1];scores[i]=value;route[i]=best;
        }
        auto run=[&](size_t x,size_t y){
            if(y-x==1){out.push_back(t.chars[a+x]);return;}
            auto node=words_.find(t,a+x,a+y);
            if(node&&node->frequency>0)for(size_t i=x;i<y;i++)out.push_back(t.chars[a+i]);else hmm(t,a+x,a+y,out);
        };
        size_t x=0,left=0;bool pending=false;
        while(x<n){size_t y=route[x];if(y-x==1){if(!pending){left=x;pending=true;}}
            else {if(pending){run(left,x);pending=false;}out.push_back(t.part(a+x,a+y));}x=y;}
        if(pending)run(left,n);
    }
    std::vector<std::string> pinyin(const std::string& word)const {
        // pypinyin's strict forward maximum matching. Every finite phrase and
        // character entry is converted with the exact pinned ToneSandhiMixin at
        // asset preparation time; there is no runtime Python or guessed reading.
        Text t(word);std::vector<std::string> out;
        for(size_t i=0;i<t.cp.size();){size_t id=0,end=i;const Node* chosen=nullptr;
            for(size_t j=i;j<t.cp.size();j++){auto it=pinyin_.nodes[id].next.find(t.cp[j]);if(it==pinyin_.nodes[id].next.end())break;id=it->second;
                if(!pinyin_.nodes[id].pronunciation.empty()){end=j+1;chosen=&pinyin_.nodes[id];}}
            if(chosen){out.insert(out.end(),chosen->pronunciation.begin(),chosen->pronunciation.end());i=end;}
            else {out.push_back(t.chars[i]);i++;}
        }return out;
    }
    static void probability(double v){require(std::isfinite(v)&&v<=0&&v>=-1e101,"Invalid HMM probability");}
public:
    explicit Frontend(const Json& j) {
        require(j.at("schema")=="lma.f5-frontend/1"&&j.at("rjiebaVersion")=="0.2.2"&&j.at("jiebaRsVersion")=="0.11.0"&&j.at("pypinyinVersion")=="0.55.0","Unmatched F5 frontend asset");
        require(j.at("words").is_object()&&j.at("words").size()>0&&j.at("words").size()<=1000000,"Invalid segmentation dictionary size");
        double total=0;for(auto it=j.at("words").begin();it!=j.at("words").end();++it){double f=it.value();require(std::isfinite(f)&&f>=0&&f<=1e12&&std::floor(f)==f,"Invalid segmentation frequency");words_.nodes[words_.add(it.key())].frequency=f;total+=f;}
        require(std::isfinite(total)&&total>0&&total<=1e15,"Invalid segmentation frequency sum");logtotal_=std::log(total);
        const auto& h=j.at("hmm");initial_=h.at("initial").get<std::array<double,4>>();transitions_=h.at("transition").get<std::array<std::array<double,4>,4>>();
        for(double v:initial_)probability(v);for(auto row:transitions_)for(double v:row)probability(v);
        require(h.at("emission").is_object()&&h.at("emission").size()<=65536,"Invalid HMM emission count");
        for(auto it=h.at("emission").begin();it!=h.at("emission").end();++it){Text t(it.key());require(t.cp.size()==1,"HMM emission requires one scalar");auto values=it.value().get<std::array<double,4>>();for(double v:values)probability(v);emissions_[t.cp[0]]=values;}
        require(j.at("pinyin").is_object()&&j.at("pinyin").size()>0&&j.at("pinyin").size()<=500000,"Invalid pronunciation table size");
        for(auto it=j.at("pinyin").begin();it!=j.at("pinyin").end();++it){Text t(it.key());auto value=it.value().get<std::vector<std::string>>();require(value.size()==t.cp.size(),"F5 pinyin alignment mismatch");for(const auto& v:value)require(!v.empty()&&v.size()<=64,"Invalid pinyin token");pinyin_.nodes[pinyin_.add(it.key())].pronunciation=std::move(value);}
    }
    std::vector<std::string> segment(const std::string& text)const {
        Text t(text);std::vector<std::string> out;
        for(size_t i=0;i<t.cp.size();){bool matched=block(t.cp[i]);size_t j=i+1;while(j<t.cp.size()&&block(t.cp[j])==matched)++j;
            if(matched)dag(t,i,j,out);else for(size_t k=i;k<j;k++){if(t.cp[k]=='\r'&&k+1<j&&t.cp[k+1]=='\n'){out.push_back("\r\n");k++;}else out.push_back(t.chars[k]);}i=j;}
        return out;
    }
    std::vector<std::string> tokens(const std::string& input)const {
        Text t(input);std::string transformed;
        for(const auto& c:t.chars){if(c==";")transformed+=",";else if(c=="“"||c=="”")transformed+='"';else if(c=="‘"||c=="’")transformed+='\'';else transformed+=c;}
        std::vector<std::string> out;
        for(const auto& word:segment(transformed)){
            Text w(word);bool ascii=word.size()==w.cp.size();
            if(ascii){if(!out.empty()&&word.size()>1&&out.back()!=" "&&out.back()!=":"&&out.back()!="'"&&out.back()!="\"")out.push_back(" ");out.insert(out.end(),w.chars.begin(),w.chars.end());}
            else if(word.size()==3*w.cp.size()){auto pronunciation=pinyin(word);require(pronunciation.size()==w.cp.size(),"F5 pronunciation alignment mismatch");for(size_t i=0;i<w.cp.size();i++){if(chinese(w.cp[i]))out.push_back(" ");out.push_back(pronunciation[i]);}}
            else for(size_t i=0;i<w.cp.size();i++){if(w.cp[i]<256)out.push_back(w.chars[i]);else if(chinese(w.cp[i])){out.push_back(" ");auto p=pinyin(w.chars[i]);out.insert(out.end(),p.begin(),p.end());}else out.push_back(w.chars[i]);}
        }
        require(out.size()<=24000,"F5 token budget exceeded");return out;
    }
    std::vector<int32_t> tokenize(const std::unordered_map<std::string,int32_t>& vocab,const std::string& value)const {
        std::vector<int32_t> out;for(const auto& token:tokens(value)){auto it=vocab.find(token);out.push_back(it==vocab.end()?0:it->second);}return out;
    }
};
inline std::unique_ptr<Frontend> selected;
inline void load(const std::string& path){
    require(std::filesystem::is_regular_file(path)&&!std::filesystem::is_symlink(path)&&std::filesystem::file_size(path)<=96*1024*1024,"Invalid F5 frontend file");
    std::ifstream in(path,std::ios::binary);Json j;in>>j;selected=std::make_unique<Frontend>(j);
}
}

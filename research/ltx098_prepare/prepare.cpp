#ifdef _WIN32
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#else
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>
#endif
#include <json.hpp>
#include "contract.hpp"
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
namespace fs = std::filesystem;
using Json = nlohmann::ordered_json;
constexpr size_t chunk_bytes = 4 * 1024 * 1024;
constexpr const char* prefix = "model.diffusion_model.";
void require(bool ok, const std::string& message) { if (!ok) throw std::invalid_argument(message); }
void require(bool ok, const char* message) { if (!ok) throw std::invalid_argument(message); }
uint32_t rotr(uint32_t x, unsigned n) { return (x >> n) | (x << (32 - n)); }

// Bounded SHA-256: source bytes are hashed exactly once while they are consumed.
class Sha256 {
    std::array<uint32_t, 8> h{{0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19}};
    std::array<uint8_t, 64> tail{};
    uint64_t total = 0;
    size_t used = 0;
    void block(const uint8_t* p) {
        static constexpr uint32_t k[64] = {
            0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
            0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
            0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
            0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
            0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
            0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
            0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
            0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
        uint32_t w[64];
        for (int i=0;i<16;++i) w[i]=(uint32_t(p[4*i])<<24)|(uint32_t(p[4*i+1])<<16)|(uint32_t(p[4*i+2])<<8)|p[4*i+3];
        for (int i=16;i<64;++i) w[i]=w[i-16]+(rotr(w[i-15],7)^rotr(w[i-15],18)^(w[i-15]>>3))+w[i-7]+(rotr(w[i-2],17)^rotr(w[i-2],19)^(w[i-2]>>10));
        auto a=h[0],b=h[1],c=h[2],d=h[3],e=h[4],f=h[5],g=h[6],v=h[7];
        for (int i=0;i<64;++i) {
            uint32_t t=v+(rotr(e,6)^rotr(e,11)^rotr(e,25))+((e&f)^((~e)&g))+k[i]+w[i];
            uint32_t u=(rotr(a,2)^rotr(a,13)^rotr(a,22))+((a&b)^(a&c)^(b&c));
            v=g;g=f;f=e;e=d+t;d=c;c=b;b=a;a=t+u;
        }
        h[0]+=a;h[1]+=b;h[2]+=c;h[3]+=d;h[4]+=e;h[5]+=f;h[6]+=g;h[7]+=v;
    }
public:
    void update(const void* raw, size_t n) {
        require(n <= std::numeric_limits<uint64_t>::max()/8-total, "SHA length overflow");
        total+=n;const auto* p=static_cast<const uint8_t*>(raw);
        if (used) {size_t count=std::min(n,64-used);std::memcpy(tail.data()+used,p,count);used+=count;p+=count;n-=count;
            if (used==64) {block(tail.data());used=0;}}
        while(n>=64) {block(p);p+=64;n-=64;}
        if(n) {std::memcpy(tail.data(),p,n);used=n;}
    }
    std::string finish() {
        uint64_t bits=total*8;tail[used++]=0x80;
        if(used>56) {std::fill(tail.begin()+used,tail.end(),0);block(tail.data());used=0;}
        std::fill(tail.begin()+used,tail.begin()+56,0);
        for(int i=0;i<8;++i) tail[63-i]=static_cast<uint8_t>(bits>>(8*i));
        block(tail.data());static const char hex[]="0123456789abcdef";std::string s;
        for(uint32_t x:h) for(int i=7;i>=0;--i) s+=hex[(x>>(i*4))&15];
        return s;
    }
};
std::string sha(const void* p, size_t size) {Sha256 h;h.update(p,size);return h.finish();}
Json parse(const std::string& raw) {
    std::vector<std::set<std::string>> seen;
    auto callback=[&](int depth, Json::parse_event_t event, Json& value) {
        require(depth<=32,"JSON nesting outside budget");
        if(event==Json::parse_event_t::object_start) seen.emplace_back();
        else if(event==Json::parse_event_t::key) require(!seen.empty()&&seen.back().insert(value.get<std::string>()).second,"Duplicate JSON key");
        else if(event==Json::parse_event_t::object_end) seen.pop_back();
        require(seen.size()<=32,"JSON nesting outside budget");return true;
    };
    return Json::parse(raw,callback);
}
uint64_t number(const Json& value, uint64_t low, uint64_t high) {
    require(value.is_number_integer(),"Expected bounded integer");
    if(!value.is_number_unsigned()) require(value.get<int64_t>()>=0,"Negative integer");
    auto n=value.get<uint64_t>();require(n>=low&&n<=high,"Integer outside budget");return n;
}
std::string string(const Json& value, size_t limit) {
    require(value.is_string(),"Expected string");auto s=value.get<std::string>();
    require(!s.empty()&&s.size()<=limit&&s.find('\0')==std::string::npos,"Invalid bounded string");return s;
}
void fields(const Json& obj, const std::set<std::string>& allowed) {
    require(obj.is_object(),"Expected JSON object");for(const auto& item:obj.items()) require(allowed.count(item.key())!=0,"Unknown field: "+item.key());
}
bool digest(const std::string& s) {return s.size()==64&&s.find_first_not_of("0123456789abcdef")==std::string::npos;}
fs::path local_path(const Json& value) {
    auto s=string(value,4096);require(s.find("://")==std::string::npos,"Expected local path");
    auto p=fs::u8path(s);require(p.is_absolute(),"Expected absolute local path");
#ifdef _WIN32
    require(p.root_name().native().size()==2&&p.root_name().native()[1]==L':',"UNC/device paths unsupported");
    require(GetDriveTypeW(p.root_path().c_str())!=DRIVE_REMOTE,"Network drive unsupported");
    require(s.find(':',2)==std::string::npos,"Alternate stream unsupported");
#endif
    return p.lexically_normal();
}
struct Cancel {
    fs::path file;
    void check() const {if(!file.empty()) require(!fs::exists(file),"Cancelled");}
};

class File {
#ifdef _WIN32
    HANDLE h=INVALID_HANDLE_VALUE;
    BY_HANDLE_FILE_INFORMATION initial{};
#else
    int h=-1;
    struct stat initial{};
#endif
public:
    uint64_t size=0;
    File(const fs::path& p, bool create=false) {
#ifdef _WIN32
        h=CreateFileW(p.c_str(),create?GENERIC_READ|GENERIC_WRITE:GENERIC_READ,create?0:FILE_SHARE_READ,nullptr,
                      create?CREATE_NEW:OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL|FILE_FLAG_OPEN_REPARSE_POINT,nullptr);
        if(h==INVALID_HANDLE_VALUE) throw std::runtime_error("Cannot open local file exclusively");
        if(!GetFileInformationByHandle(h,&initial)||(initial.dwFileAttributes&(FILE_ATTRIBUTE_REPARSE_POINT|FILE_ATTRIBUTE_DIRECTORY))) {
            CloseHandle(h);h=INVALID_HANDLE_VALUE;throw std::invalid_argument("Expected regular non-link file");}
        size=(uint64_t(initial.nFileSizeHigh)<<32)|initial.nFileSizeLow;
#else
        h=::open(p.c_str(),(create?O_CREAT|O_EXCL|O_RDWR:O_RDONLY)|O_CLOEXEC|O_NOFOLLOW,0600);
        if(h<0) throw std::runtime_error("Cannot open local file exclusively");
        if(fstat(h,&initial)||!S_ISREG(initial.st_mode)) {::close(h);h=-1;throw std::invalid_argument("Expected regular non-link file");}
        size=static_cast<uint64_t>(initial.st_size);
#endif
    }
    File(const File&)=delete;File& operator=(const File&)=delete;
    ~File() {
#ifdef _WIN32
        if(h!=INVALID_HANDLE_VALUE) CloseHandle(h);
#else
        if(h>=0) ::close(h);
#endif
    }
    void seek(uint64_t offset) {
        require(offset<=uint64_t(std::numeric_limits<int64_t>::max()),"Offset overflow");
#ifdef _WIN32
        LARGE_INTEGER o;o.QuadPart=static_cast<LONGLONG>(offset);require(SetFilePointerEx(h,o,nullptr,FILE_BEGIN)!=0,"File seek failed");
#else
        require(lseek(h,static_cast<off_t>(offset),SEEK_SET)>=0,"File seek failed");
#endif
    }
    void read(void* data, size_t count) {
        auto* p=static_cast<uint8_t*>(data);
        while(count) {
            auto n=static_cast<uint32_t>(std::min(count,chunk_bytes));
#ifdef _WIN32
            DWORD got=0;require(ReadFile(h,p,n,&got,nullptr)!=0&&got>0,"File read failed or source truncated");
#else
            auto got=::read(h,p,n);require(got>0,"File read failed or source truncated");
#endif
            p+=got;count-=static_cast<size_t>(got);
        }
    }
    void write(const void* data, size_t count) {
        const auto* p=static_cast<const uint8_t*>(data);
        while(count) {
            auto n=static_cast<uint32_t>(std::min(count,chunk_bytes));
#ifdef _WIN32
            DWORD got=0;require(WriteFile(h,p,n,&got,nullptr)!=0&&got>0,"File write failed");
#else
            auto got=::write(h,p,n);require(got>0,"File write failed");
#endif
            p+=got;count-=static_cast<size_t>(got);
        }
    }
    void flush() {
#ifdef _WIN32
        require(FlushFileBuffers(h)!=0,"File flush failed");
#else
        require(fsync(h)==0,"File flush failed");
#endif
    }
    void unchanged() const {
#ifdef _WIN32
        BY_HANDLE_FILE_INFORMATION now{};require(GetFileInformationByHandle(h,&now)!=0,"Source stat failed");
        require(now.dwVolumeSerialNumber==initial.dwVolumeSerialNumber&&now.nFileIndexHigh==initial.nFileIndexHigh&&now.nFileIndexLow==initial.nFileIndexLow&&
                now.nFileSizeHigh==initial.nFileSizeHigh&&now.nFileSizeLow==initial.nFileSizeLow&&
                CompareFileTime(&now.ftLastWriteTime,&initial.ftLastWriteTime)==0,"Source changed during conversion");
#else
        struct stat now{};require(fstat(h,&now)==0,"Source stat failed");
        require(now.st_dev==initial.st_dev&&now.st_ino==initial.st_ino&&now.st_size==initial.st_size&&
                now.st_mtim.tv_sec==initial.st_mtim.tv_sec&&now.st_mtim.tv_nsec==initial.st_mtim.tv_nsec,"Source changed during conversion");
#endif
    }
};
std::string read_request(const fs::path& path) {
    File file(path);require(file.size>=2&&file.size<=32768,"Request outside budget");std::string text(static_cast<size_t>(file.size),'\0');
    file.read(text.data(),text.size());file.unchanged();return text;
}
uint64_t le(const uint8_t* p, size_t count) {uint64_t n=0;for(size_t i=0;i<count;++i)n|=uint64_t(p[i])<<(8*i);return n;}
void append(std::vector<uint8_t>& out, uint64_t n, size_t count) {for(size_t i=0;i<count;++i)out.push_back(static_cast<uint8_t>(n>>(8*i)));}
void append_string(std::vector<uint8_t>& out, const std::string& s) {append(out,s.size(),8);out.insert(out.end(),s.begin(),s.end());}
uint64_t aligned(uint64_t n) {require(n<=uint64_t(std::numeric_limits<int64_t>::max())-31,"Tensor size overflow");return (n+31)/32*32;}

struct Tensor {std::string name,dtype;std::vector<uint64_t> shape;uint64_t first=0,last=0,elements=1,destination=0,output_bytes=0;bool selected=false,half=false;};
struct Plan {
    Json config;std::vector<Tensor> tensors;std::vector<uint8_t> header;std::string header_sha,layout_sha;
    uint64_t source_header_bytes=0,total_parameters=0,selected_count=0,output_bytes=0;
};
Plan inspect(File& source, Sha256& source_hash, bool fixture) {
    require(source.size>=10,"Truncated safetensors prefix");std::array<uint8_t,8> prefix_bytes{};source.read(prefix_bytes.data(),8);source_hash.update(prefix_bytes.data(),8);
    auto count=le(prefix_bytes.data(),8);require(count>=2&&count<=16*1024*1024&&count<=source.size-8,"Invalid safetensors header length");
    std::string raw(static_cast<size_t>(count),'\0');source.read(raw.data(),raw.size());source_hash.update(raw.data(),raw.size());
    Plan plan;plan.header_sha=sha(raw.data(),raw.size());plan.source_header_bytes=count;
    auto header=parse(raw);require(header.is_object()&&header.contains("__metadata__"),"Missing safetensors metadata");
    auto metadata=header.at("__metadata__");require(metadata.is_object()&&metadata.contains("config"),"Missing publisher config");
    auto full_config=parse(string(metadata.at("config"),1024*1024));
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
    for(const auto& entry:header.items()) {
        if(entry.key()=="__metadata__") continue;
        require(!entry.key().empty()&&entry.key().size()<=256&&entry.key().find('\0')==std::string::npos,"Invalid tensor name");
        fields(entry.value(),{"dtype","shape","data_offsets"});const auto& item=entry.value();Tensor t;t.name=entry.key();t.dtype=string(item.at("dtype"),8);
        require(t.dtype=="BF16"||t.dtype=="F16"||t.dtype=="F32","Unsupported dtype");
        auto shape=item.at("shape");require(shape.is_array()&&shape.size()<=5,"Invalid tensor rank");
        for(const auto& v:shape) {auto n=number(v,1,1000000);require(t.elements<=uint64_t(std::numeric_limits<int64_t>::max())/n,"Tensor shape overflow");t.elements*=n;t.shape.push_back(n);}
        auto offsets=item.at("data_offsets");require(offsets.is_array()&&offsets.size()==2,"Invalid tensor offsets");
        t.first=number(offsets[0],0,source.size-8-count);t.last=number(offsets[1],t.first,source.size-8-count);
        auto size=t.dtype=="F32"?4u:2u;require(t.elements<=(source.size-8-count)/size&&t.last-t.first==t.elements*size,"Tensor byte/shape mismatch");
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
    require(!plan.tensors.empty(),"Empty checkpoint");auto sorted=plan.tensors;
    std::sort(sorted.begin(),sorted.end(),[](const Tensor& a,const Tensor& b){return a.first<b.first;});uint64_t previous=0;
    for(const auto& t:sorted) {require(t.first==previous,"Tensor ranges overlap or leave unreviewed bytes");previous=t.last;}
    require(previous==source.size-8-count,"Unexpected checkpoint trailing data");
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
// Exact IEEE-754 conversions, round to nearest with ties to even; no FP16 CPU extension.
uint32_t half_to_float(uint16_t h) {
    uint32_t sign=uint32_t(h&0x8000)<<16,exp=(h>>10)&31,mant=h&1023;
    if(exp==31) return sign|0x7f800000|(mant<<13);
    if(!exp) {if(!mant)return sign;int exponent=-14;while(!(mant&1024)){mant<<=1;--exponent;}return sign|(uint32_t(exponent+127)<<23)|((mant&1023)<<13);}
    return sign|((exp+112)<<23)|(mant<<13);
}
uint16_t float_to_half(uint32_t f) {
    uint16_t sign=static_cast<uint16_t>((f>>16)&0x8000);int exp=static_cast<int>((f>>23)&255)-127+15;uint32_t mant=f&0x7fffff;
    if(exp<=0) {
        if(exp<-10)return sign;mant|=0x800000;unsigned shift=static_cast<unsigned>(14-exp);uint32_t q=mant>>shift,rem=mant&((uint32_t(1)<<shift)-1),mid=uint32_t(1)<<(shift-1);
        if(rem>mid||(rem==mid&&(q&1)))++q;return static_cast<uint16_t>(sign|q);
    }
    uint32_t q=mant>>13,rem=mant&8191;if(rem>4096||(rem==4096&&(q&1))) {if(++q==1024) {q=0;++exp;}}
    require(exp<31,"FP16 tensor overflow");return static_cast<uint16_t>(sign|(static_cast<unsigned>(exp)<<10)|q);
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
std::string output_name(const Json& value) {
    auto name=string(value,96);require(name!="."&&name!=".."&&name.front()!='.'&&name.back()!='.'&&
        name.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")==std::string::npos,"Invalid output basename");
    std::string stem=name.substr(0,name.find('.'));for(auto& ch:stem)if(ch>='a'&&ch<='z')ch=static_cast<char>(ch-'a'+'A');
    require(stem!="CON"&&stem!="PRN"&&stem!="AUX"&&stem!="NUL"&&
            !(stem.size()==4&&(stem.substr(0,3)=="COM"||stem.substr(0,3)=="LPT")&&stem[3]>='0'&&stem[3]<='9'),"Reserved output basename");return name;
}
bool entry_exists(const fs::path& p) {std::error_code ec;auto st=fs::symlink_status(p,ec);return st.type()!=fs::file_type::not_found&&st.type()!=fs::file_type::none;}
class Transaction {
    bool committed=false;
public:
    fs::path stage,final;
    Transaction(const fs::path& root,const std::string& name) : final(root/fs::u8path(name)) {
        require(!entry_exists(final),"Output directory already exists");
        auto tick=std::chrono::steady_clock::now().time_since_epoch().count();
        for(unsigned i=0;i<100;++i) {auto candidate=root/fs::u8path(".ltx098-prepare-"+std::to_string(tick)+"-"+std::to_string(i));
            std::error_code ec;if(fs::create_directory(candidate,ec)){stage=candidate;return;}}
        throw std::runtime_error("Cannot create exclusive staging directory");
    }
    ~Transaction() {
        if(!committed&&!stage.empty()) {
            // Only known files within this freshly created directory; never recursively delete.
            for(const auto* name:{"ltx098-dit.gguf","conversion.json"}) {std::error_code ec;fs::remove(stage/name,ec);}
            std::error_code ec;fs::remove(stage,ec);
        }
    }
    void commit() {
#ifdef _WIN32
        require(MoveFileExW(stage.c_str(),final.c_str(),MOVEFILE_WRITE_THROUGH)!=0,"Cannot commit without replacing existing output");
#else
        require(syscall(SYS_renameat2,AT_FDCWD,stage.c_str(),AT_FDCWD,final.c_str(),1)==0,"Cannot commit without replacing existing output");
#endif
        committed=true;
    }
};
void progress(const std::string& phase,uint64_t done,uint64_t total) {std::cerr<<Json{{"phase",phase},{"bytes",done},{"total_bytes",total}}.dump()<<std::endl;}
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

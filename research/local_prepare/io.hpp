#pragma once
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
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace lma_prepare {
namespace fs = std::filesystem;
using Json = nlohmann::ordered_json;
constexpr size_t chunk_bytes = 4 * 1024 * 1024;
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
struct Checkpoint {Json config;std::vector<Tensor> tensors;std::string header_sha;uint64_t header_bytes=0;};
Checkpoint read_safetensors(File& source,Sha256& source_hash) {
    require(source.size>=10,"Truncated safetensors prefix");std::array<uint8_t,8> prefix_bytes{};source.read(prefix_bytes.data(),8);source_hash.update(prefix_bytes.data(),8);
    auto count=le(prefix_bytes.data(),8);require(count>=2&&count<=16*1024*1024&&count<=source.size-8,"Invalid safetensors header length");
    std::string raw(static_cast<size_t>(count),'\0');source.read(raw.data(),raw.size());source_hash.update(raw.data(),raw.size());
    Checkpoint checkpoint;checkpoint.header_sha=sha(raw.data(),raw.size());checkpoint.header_bytes=count;
    auto header=parse(raw);require(header.is_object()&&header.contains("__metadata__"),"Missing safetensors metadata");
    const auto& metadata=header.at("__metadata__");require(metadata.is_object()&&metadata.contains("config"),"Missing publisher config");
    checkpoint.config=parse(string(metadata.at("config"),1024*1024));require(checkpoint.config.is_object(),"Invalid publisher config");
    for(const auto& entry:header.items()) {
        if(entry.key()=="__metadata__")continue;
        require(!entry.key().empty()&&entry.key().size()<=256&&entry.key().find('\0')==std::string::npos,"Invalid tensor name");
        fields(entry.value(),{"dtype","shape","data_offsets"});const auto& item=entry.value();Tensor t;t.name=entry.key();t.dtype=string(item.at("dtype"),8);
        require(t.dtype=="BF16"||t.dtype=="F16"||t.dtype=="F32","Unsupported dtype");
        const auto& shape=item.at("shape");require(shape.is_array()&&shape.size()<=5,"Invalid tensor rank");
        for(const auto& v:shape){auto n=number(v,1,1000000);require(t.elements<=uint64_t(std::numeric_limits<int64_t>::max())/n,"Tensor shape overflow");t.elements*=n;t.shape.push_back(n);}
        const auto& offsets=item.at("data_offsets");require(offsets.is_array()&&offsets.size()==2,"Invalid tensor offsets");
        t.first=number(offsets[0],0,source.size-8-count);t.last=number(offsets[1],t.first,source.size-8-count);
        auto size=t.dtype=="F32"?4u:2u;require(t.elements<=(source.size-8-count)/size&&t.last-t.first==t.elements*size,"Tensor byte/shape mismatch");
        checkpoint.tensors.push_back(std::move(t));require(checkpoint.tensors.size()<=10000,"Tensor count outside budget");
    }
    require(!checkpoint.tensors.empty(),"Empty checkpoint");auto sorted=checkpoint.tensors;
    std::sort(sorted.begin(),sorted.end(),[](const Tensor& a,const Tensor& b){return a.first<b.first;});uint64_t previous=0;
    for(const auto& t:sorted){require(t.first==previous,"Tensor ranges overlap or leave unreviewed bytes");previous=t.last;}
    require(previous==source.size-8-count,"Unexpected checkpoint trailing data");return checkpoint;
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
    std::vector<std::string> owned;
public:
    fs::path stage,final;
    Transaction(const fs::path& root,const std::string& name,std::vector<std::string> files={"ltx098-dit.gguf","conversion.json"}) : owned(std::move(files)),final(root/fs::u8path(name)) {
        require(!owned.empty()&&owned.size()<=64,"Invalid transaction file list");
        for(const auto& file:owned)require(file!="."&&file!=".."&&fs::u8path(file).filename()==fs::u8path(file)&&
            !file.empty()&&file.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")==std::string::npos,"Unsafe transaction file name");
        require(!entry_exists(final),"Output directory already exists");
        auto tick=std::chrono::steady_clock::now().time_since_epoch().count();
        for(unsigned i=0;i<100;++i) {auto candidate=root/fs::u8path(".ltx098-prepare-"+std::to_string(tick)+"-"+std::to_string(i));
            std::error_code ec;if(fs::create_directory(candidate,ec)){stage=candidate;return;}}
        throw std::runtime_error("Cannot create exclusive staging directory");
    }
    ~Transaction() {
        if(!committed&&!stage.empty()) {
            // Only known files within this freshly created directory; never recursively delete.
            for(const auto& name:owned) {std::error_code ec;fs::remove(stage/name,ec);}
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
}

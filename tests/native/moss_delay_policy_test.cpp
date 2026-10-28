#include "../../native/moss_delay/policy.hpp"
#include "../../native/moss_delay/wave.hpp"
#include "llama.h"
#include <iostream>
#include <functional>

// Host-only fatal assertion sink. No tensor/backend/model APIs are implemented or simulated.
extern "C" GGML_NORETURN void ggml_abort(const char*,int,const char*,...) { std::abort(); }

extern std::vector<llama_token> common_tokenize(const llama_vocab*,const std::string&,bool,bool);
extern std::string common_token_to_piece(const llama_vocab*,llama_token,bool);
#define LOG(...) ((void)0)
#define LOG_ERR(...) ((void)0)
#include "moss-primitives.inc"
#undef LOG
#undef LOG_ERR

static int checks;
static void check(bool ok) {if(!ok)throw std::runtime_error("MOSS native assertion failed");++checks;}
static void rejects(const std::function<void()>& action) {try{action();}catch(const std::exception&){++checks;return;}throw std::runtime_error("Invalid MOSS input accepted");}
int main() {
    using namespace lma_moss;
    check(moss_delay_self_test()); // Execute the pinned upstream sampler, scheduling and de-delay tests.
    parameters(4,512,375,1.5,1,50,1.7,.8,25,1,42);++checks;
    for(int threads:{0,33})rejects([=]{parameters(threads,512,375,1.5,1,50,1.7,.8,25,1,42);});
    for(int tokens:{0,2049})rejects([=]{parameters(4,tokens,375,1.5,1,50,1.7,.8,25,1,42);});
    for(int frames:{63,1501})rejects([=]{parameters(4,512,frames,1.5,1,50,1.7,.8,25,1,42);});
    for(float temp:{-1.f,3.1f,std::numeric_limits<float>::quiet_NaN()})rejects([=]{parameters(4,512,375,temp,1,50,1.7,.8,25,1,42);});
    for(float p:{0.f,1.1f,std::numeric_limits<float>::infinity()})rejects([=]{parameters(4,512,375,1.5,1,50,1.7,p,25,1,42);});
    for(int k:{0,1025})rejects([=]{parameters(4,512,375,1.5,1,k,1.7,.8,25,1,42);});
    for(float r:{.9f,2.1f})rejects([=]{parameters(4,512,375,1.5,1,50,1.7,.8,25,r,42);});
    for(int64_t seed:{int64_t(-1),int64_t(2147483648LL)})rejects([=]{parameters(4,512,375,1.5,1,50,1.7,.8,25,1,seed);});
    context(512,512,375,40960);++checks;rejects([]{context(513,512,375,40960);});rejects([]{context(512,512,375,800);});rejects([]{context(4096,4096,375,40960);});
    for(const char* value:{"auto","en","zh","fa","hu","cs","da","el"}){language(value);++checks;}rejects([]{language("made_up_language");});
    std::vector<int32_t> rows(3*32);for(size_t i=0;i<rows.size();++i)rows[i]=int32_t(i);
    auto codes=encoder_codes(rows.data(),3,2);check(codes.size()==64);for(size_t i=0;i<codes.size();++i)check(codes[i]==int32_t(i));
    rejects([&]{encoder_codes(rows.data(),2,3);});rejects([&]{encoder_codes(rows.data(),0,0);});rejects([&]{encoder_codes(nullptr,3,2);});rows[33]=1024;rejects([&]{encoder_codes(rows.data(),3,2);});
    check(save_wav16("reference-structural-fixture.wav",std::vector<float>(24000,0),24000));
    check(lma_moss::reference_wave("reference-structural-fixture.wav").size()==24000);
    check(save_wav16("too-long-reference.wav",std::vector<float>(240001,0),24000));
    rejects([]{lma_moss::reference_wave("too-long-reference.wav");});
    {std::ofstream file("oversize-reference.wav",std::ios::binary);std::vector<char> bytes(1024*1024+1,0);file.write(bytes.data(),bytes.size());}
    rejects([]{lma_moss::reference_wave("oversize-reference.wav");});
    std::cout<<"{\"passed\":"<<checks<<",\"upstream_delay_self_test\":true,\"model_inference\":false}"<<std::endl;
}

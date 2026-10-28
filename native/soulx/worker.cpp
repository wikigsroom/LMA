// SPDX-License-Identifier: MIT
// One owned native process; all model data remains in the selected user bundle.
#include "contract.hpp"
#include "../../research/soulx_reference/reference.hpp"
#include "../../research/soulx_acoustic/acoustic.hpp"
#include "../../research/soulx_language/language.hpp"
#include <chrono>
#include <cstdio>
#include <csignal>
#include <atomic>
#ifdef _WIN32
#include <io.h>
#else
#include <sys/prctl.h>
#include <unistd.h>
#endif

namespace sx = lma::soulx;
using namespace lma_soulx_worker;
static FILE* events=nullptr;
static_assert(std::atomic<bool>::is_always_lock_free,"SoulX cancellation requires a signal-safe lock-free flag");
static std::atomic<bool> cancelled{false};
static void cancel_signal(int) { cancelled.store(true,std::memory_order_relaxed); }
static void check() { require(!cancelled.load(std::memory_order_relaxed),"SoulX task cancelled"); }
static void event(const json& value) { if(events) { auto line=value.dump(); std::fprintf(events,"%s\n",line.c_str()); std::fflush(events); } }
static int execute(int argc,char** argv) {
    try {
#ifdef _WIN32
        events=_fdopen(_dup(_fileno(stdout)),"w"); require(events && freopen("NUL","w",stdout) && freopen("NUL","w",stderr),"Cannot isolate SoulX diagnostics");
#else
        events=fdopen(dup(STDOUT_FILENO),"w"); require(events && freopen("/dev/null","w",stdout) && freopen("/dev/null","w",stderr),"Cannot isolate SoulX diagnostics");
        pid_t parent=getppid(); require(prctl(PR_SET_PDEATHSIG,SIGKILL)==0 && parent!=1 && getppid()==parent,"Cannot bind SoulX worker lifetime");
#endif
        std::signal(SIGTERM,cancel_signal); std::signal(SIGINT,cancel_signal);
        if(argc==2 && std::string(argv[1])=="--info") { event({{"schema","lma.engine/1"},{"engine","soulx_native"},{"pipeline","soulx_podcast_cpu_v1"},{"backend","cpu"},{"bundled_model_data",false},{"device_validated",false},{"required_model_components",14}}); return 0; }
        require(argc==2,"Pass a private SoulX request file"); auto r=json::parse(read(fs::u8path(argv[1]),256*1024));
        require(r.is_object() && r.size()==7 && r.at("schema")=="lma.engine-request/1" && r.at("type")=="speech.synthesize" && r.at("pipeline")=="soulx_podcast_cpu_v1","Unsupported SoulX worker request");
        Config p(r.at("parameters")); auto input=inputs(r.at("input")); std::string workspace=r.at("workspace"),output=r.at("output");
        require(!workspace.empty() && !output.empty() && workspace.find('\0')==std::string::npos && output.find('\0')==std::string::npos,"Invalid private SoulX paths");
        auto root=fs::u8path(workspace),destination=fs::u8path(output),models=root/"models"; require(fs::is_directory(root) && !fs::exists(destination),"Missing SoulX workspace or existing output");
        using Clock=std::chrono::steady_clock; auto start=Clock::now(); auto ms=[](Clock::time_point point){return std::chrono::duration<double,std::milli>(Clock::now()-point).count();};
        auto stop=[] { return cancelled.load(std::memory_order_relaxed); }; int reference_speaker=0;
        auto progress=[&](const std::string& stage,int done,int total) {
            check(); json data={{"event","progress"},{"stage",stage},{"step",done},{"steps",total}};
            if(stage=="language_decode") data={{"event","stage"},{"stage",stage}}; // decode counts and batch sizes are not a completion fraction
            if(reference_speaker) data["speaker"]=reference_speaker; event(data); check();
        };
        std::vector<sx::PreparedReference> references; std::vector<lg::Reference> prompts; json reference_receipts=json::array(); size_t reference_runs=0,reference_loads=0;
        auto mark=Clock::now();
        for(size_t i=0;i<input.transcripts.size();++i) {
            check(); reference_speaker=static_cast<int>(i)+1; event({{"event","stage"},{"stage","reading_reference_audio"},{"speaker",i+1}});
            auto pcm=reference_wave(root/"inputs"/("reference_s"+std::to_string(i+1)+".wav")); sx::OrtStats stats;
            auto ref=sx::prepare_reference({models},pcm,p.threads,stats,stop,progress); check(); require(stats.session_loads==2 && stats.session_unloads==2 && stats.max_live_sessions==1,"SoulX reference lifetime mismatch");
            lg::Tokens codes; for(auto c:ref.tokens) codes.push_back(static_cast<int32_t>(c)); prompts.push_back({input.transcripts[i],std::move(codes)});
            reference_receipts.push_back({{"speaker",i+1},{"samples",ref.source_samples},{"semanticCodes",ref.tokens.size()},{"graphRuns",stats.graph_runs},{"modelLoads",stats.session_loads},{"modelUnloads",stats.session_unloads}});
            reference_runs+=stats.graph_runs; reference_loads+=stats.session_loads; references.push_back(std::move(ref));
        }
        reference_speaker=0; double reference_ms=ms(mark); lg::Stats language_stats; std::vector<lg::Generated> generated; mark=Clock::now();
        {
            lg::Options options; options.context=p.context; options.threads=p.threads; options.batch=128;
            lg::Model model(models/"language.gguf",options,language_stats,stop,progress);
            generated=model.generate(prompts,input.turns,p.sampling,p.window,static_cast<uint64_t>(p.seed));
        }
        check(); require(language_stats.model_loads==1 && language_stats.model_unloads==1 && generated.size()==input.turns.size(),"SoulX language lifetime/result mismatch");
        double language_ms=ms(mark); size_t total_codes=0;
        for(const auto& turn:generated) { require(!turn.semantic.empty() && turn.semantic.size()<=static_cast<size_t>(p.sampling.maximum),"Empty or oversized SoulX generated utterance"); total_codes+=turn.semantic.size(); }
        auto pauses=(generated.size()-1)*static_cast<size_t>(p.pause_ms)*24; require(total_codes<=24000 && total_codes*960+pauses<=static_cast<size_t>(p.seconds)*24000,"SoulX generated audio exceeds requested total duration");
        Wave wave(root/"audio.part.wav",p.seconds); json turns=json::array(); size_t acoustic_runs=0,acoustic_loads=0; mark=Clock::now();
        for(size_t i=0;i<generated.size();++i) {
            check(); const auto& turn=generated[i]; const auto& ref=references.at(static_cast<size_t>(turn.speaker));
            event({{"event","stage"},{"stage","synthesizing_utterance"},{"turn",i+1},{"turns",generated.size()},{"speaker",turn.speaker+1}});
            sx::AcousticInput feed; feed.tokens=ref.tokens; feed.tokens.insert(feed.tokens.end(),turn.semantic.begin(),turn.semantic.end()); feed.prompt_tokens=ref.tokens.size(); feed.prompt_mel=ref.prompt_mel; feed.speaker=ref.speaker;
            sx::AcousticParams params; params.steps=p.steps; params.threads=p.threads; params.cfg=p.cfg; params.seed=static_cast<int64_t>((static_cast<uint64_t>(p.seed)+i)%2147483648ULL); sx::AcousticStats stats;
            auto pcm=sx::synthesize_acoustic({models},feed,params,stats,stop,progress); check(); require(pcm.size()==turn.semantic.size()*960 && stats.session_loads==4 && stats.session_unloads==4 && stats.max_live_sessions==1,"SoulX acoustic lifetime/output mismatch");
            wave.append(pcm); if(i+1<generated.size()) wave.silence(static_cast<size_t>(p.pause_ms)*24);
            turns.push_back({{"speaker",turn.speaker+1},{"semanticCodes",turn.semantic.size()},{"samples",pcm.size()},{"eos",turn.eos},{"historyDelimiterInserted",turn.history_delimiter_inserted},{"inputTokens",turn.input_tokens},{"graphRuns",stats.graph_runs},{"modelLoads",stats.session_loads},{"modelUnloads",stats.session_unloads},{"acousticSeed",params.seed}});
            acoustic_runs+=stats.graph_runs; acoustic_loads+=stats.session_loads;
        }
        check(); double acoustic_ms=ms(mark); event({{"event","stage"},{"stage","saving_audio"}}); wave.commit(destination); auto duration=double(wave.samples())/24000; double total_ms=ms(start);
        event({{"event","execution"},{"details",{{"pipeline","soulx_podcast_cpu_v1"},{"backend","cpu"},{"effectiveParameters",r.at("parameters")},{"sampleRate",24000},{"channels",1},{"outputSamples",wave.samples()},{"audioDurationSeconds",duration},{"peakBeforePcm",wave.peak},{"clippedSamples",wave.clipped},{"references",reference_receipts},{"turns",turns},{"referenceGraphRuns",reference_runs},{"acousticGraphRuns",acoustic_runs},{"ortModelLoads",reference_loads+acoustic_loads},{"ortModelUnloads",reference_loads+acoustic_loads},{"maxConcurrentOrtModels",1},{"languageModelLoads",language_stats.model_loads},{"languageModelUnloads",language_stats.model_unloads},{"languageDecodeCalls",language_stats.decode_calls},{"generatedSemanticCodes",total_codes},{"rasResets",language_stats.ras_resets},{"historyResets",language_stats.history_resets},{"referenceMs",reference_ms},{"languageMs",language_ms},{"acousticMs",acoustic_ms},{"pipelineMs",total_ms},{"pipelineRTF",total_ms/1000/duration},{"stageLoading","sequential"},{"stopReason","per_utterance_eos_or_explicit_limit"}}}});
        event({{"event","complete"},{"output",output}}); return 0;
    } catch(const std::exception& error) { event({{"event","error"},{"message",error.what()}}); return 1; }
}
#ifdef _WIN32
int wmain(int argc,wchar_t** argv) { return wide_main(argc,argv,execute); }
#else
int main(int argc,char** argv) { return execute(argc,argv); }
#endif

#pragma once
#include <chrono>
#include <string>
#include <vector>
#if defined(__linux__) || defined(__ANDROID__)
#include <sys/resource.h>
#endif
namespace lma_metrics {
using Clock=std::chrono::steady_clock;
inline Clock::time_point started=Clock::now(), stage_started=started;
inline std::string current_stage;
inline nlohmann::json stages=nlohmann::json::array();
inline bool ended=false;
inline long long milliseconds(Clock::time_point since){return std::chrono::duration_cast<std::chrono::milliseconds>(Clock::now()-since).count();}
inline void end_stage(){
 if(!current_stage.empty() && stages.size()<64)stages.push_back({{"stage",current_stage},{"elapsedMs",milliseconds(stage_started)}});
 current_stage.clear();
}
inline void stage(const std::string& value){
 if(ended)return;end_stage();current_stage=value.substr(0,80);stage_started=Clock::now();
}
inline nlohmann::json finish(){
 if(!ended){end_stage();ended=true;}
 nlohmann::json r={{"schema","lma.worker-observations/1"},{"elapsedMs",milliseconds(started)},
  {"stages",stages},{"memoryScope","worker_process_peak_rss_not_model_peak_or_whole_app"},
  {"qualityAssessed",false}};
#ifdef __ANDROID__
 r["platform"]="android";
#elif defined(_WIN32)
 r["platform"]="windows_host";
#else
 r["platform"]="other_host";
#endif
#if defined(__linux__) || defined(__ANDROID__)
 struct rusage usage{};
 if(getrusage(RUSAGE_SELF,&usage)==0 && usage.ru_maxrss>0){
  r["peakResidentBytes"]=static_cast<unsigned long long>(usage.ru_maxrss)*1024;
  r["memorySource"]="getrusage_RUSAGE_SELF_linux_kib";
 }else{r["peakResidentBytes"]=nullptr;r["memorySource"]="unavailable";}
#else
 r["peakResidentBytes"]=nullptr;r["memorySource"]="unavailable_on_this_platform";
#endif
 return r;
}
}

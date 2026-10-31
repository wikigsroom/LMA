#include "../../native/speech_extra/f5_frontend.hpp"
#include <iostream>
int main() {
 int count=0; auto check=[&](bool value){ if(!value)throw std::runtime_error("Frontend contract failed"); ++count; };
 check(lma_f5::tone3("nǚ")=="nv3"); check(lma_f5::tone3("lǜ")=="lv4"); check(lma_f5::tone3("ma")=="ma");
 for(const auto& invalid:std::vector<std::string>{"\xc0\x80","\xed\xa0\x80","\xf4\x90\x80\x80","\xe0\x80\x80","\xf0\x80\x80\x80","\xf0\x90"}) {
  bool rejected=false;try{lma_f5::chars(invalid);}catch(const std::exception&){rejected=true;}check(rejected);
 }
 lma_f5::dictionary["重"]={"zhong4"};lma_f5::dictionary["重庆"]={"chong2","qing4"};
 std::unordered_map<std::string,int32_t> words{{" ",0},{"chong2",1},{"qing4",2},{"zhong4",3},{".",4},{"a",5}};
 check(lma_f5::tokenize(words,"重庆。")==std::vector<int32_t>({0,1,0,2,4}));
 check(lma_f5::tokenize(words,"重a")==std::vector<int32_t>({0,3,5}));
 bool rejected=false;try{lma_f5::tokenize(words,"未知");}catch(const std::exception&){rejected=true;}check(rejected);
 check(lma_worker::integer(lma_worker::json{{"steps",999}},"steps",32,1,64)==64);
 lma_metrics::stage("loading");lma_metrics::stage("sampling");auto measured=lma_metrics::finish();
 check(measured["stages"].size()==2);check(measured["elapsedMs"].get<long long>()>=0);
 check(measured["memoryScope"]=="worker_process_peak_rss_not_model_peak_or_whole_app");check(measured["qualityAssessed"]==false);
 check(lma_metrics::finish()["stages"].size()==2);
 std::cout << "{\"passed\":" << count << ",\"model_inference\":false}\n";
}

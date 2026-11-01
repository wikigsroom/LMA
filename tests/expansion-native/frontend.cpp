#include "../../native/speech_extra/f5_frontend.hpp"
#include <iostream>
#include <chrono>
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
 namespace fs=std::filesystem;
 auto temp=fs::temp_directory_path()/(std::string("lma-selected-staging-")+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
 check(fs::create_directory(temp));auto models=temp/"models",views=temp/"views";fs::create_directory(models);fs::create_directory(views);
 auto source=temp/"selected.bin",other=temp/"other.bin",file=models/"model.gguf";
 {std::ofstream(source)<<"selected";std::ofstream(other)<<"other";}fs::create_hard_link(source,file);
 auto expect_rejected=[&](auto action){bool invalid=false;try{action();}catch(const std::exception&){invalid=true;}check(invalid);};
 lma_worker::json command={{"workspace",models.string()},{"components",{{"model",file.string()}}},{"componentSources",{{"model",source.string()}}}};
 check(lma_worker::component(command,"model")==file.string());
 auto legacy=command;legacy.erase("componentSources");check(lma_worker::component(legacy,"model")==file.string());
 auto wrong=command;wrong["componentSources"]["model"]=other.string();expect_rejected([&]{lma_worker::component(wrong,"model");});
 auto escaped=command;escaped["components"]["model"]=source.string();expect_rejected([&]{lma_worker::component(escaped,"model");});
 auto missing=command;missing["componentSources"]["model"]=(temp/"missing").string();expect_rejected([&]{lma_worker::component(missing,"model");});
 auto view_file=views/"00_front.png";fs::create_hard_link(source,view_file);
 lma_worker::json view_command={{"viewsDirectory",views.string()},{"viewSources",{{"00_front.png",source.string()}}}};
 check(lma_worker::view(view_command,"00_front.png")==view_file.string());
 auto wrong_view=view_command;wrong_view["viewSources"]["00_front.png"]=other.string();expect_rejected([&]{lma_worker::view(wrong_view,"00_front.png");});
 std::error_code symlink_error;auto link=models/"linked.gguf";fs::create_symlink(source,link,symlink_error);
 bool symbolic_link_checked=!symlink_error;
 if(symbolic_link_checked){auto linked=command;linked["components"]["model"]=link.string();check(lma_worker::component(linked,"model")==link.string());
  linked.erase("componentSources");expect_rejected([&]{lma_worker::component(linked,"model");});fs::remove(link);}
 fs::remove(view_file);fs::remove(file);fs::remove(source);fs::remove(other);fs::remove(models);fs::remove(views);fs::remove(temp);
 std::cout << "{\"passed\":" << count << ",\"symbolic_link_checked\":" << (symbolic_link_checked?"true":"false") << ",\"model_inference\":false}\n";
}

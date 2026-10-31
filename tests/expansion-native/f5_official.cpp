#include "../../native/speech_extra/f5_official.hpp"
#include <iostream>
int main(int argc,char** argv){
    try {
        lma_worker::require(argc==2,"Select a frontend resource");lma_f5_official::load(argv[1]);
        std::string line;while(std::getline(std::cin,line)){
            auto request=nlohmann::json::parse(line);nlohmann::json result;
            try {
                auto text=request.at("text").get<std::string>();auto& f=*lma_f5_official::selected;
                result={{"segments",f.segment(text)},{"tokens",f.tokens(text)}};
                if(request.contains("vocab"))result["ids"]=f.tokenize(request.at("vocab").get<std::unordered_map<std::string,int32_t>>(),text);
            }catch(const std::exception&){result={{"rejected",true}};}
            std::cout<<result.dump()<<std::endl;
        }
        return 0;
    }catch(const std::exception&){return 2;}
}

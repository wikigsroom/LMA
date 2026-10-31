#pragma once
// Tokenizer-only build: no tensor/backend, file downloader or logging runtime.
#include <string>
#define LOG_ERROR(...) ((void)0)
#define LOG_VERBOSE(...) ((void)0)
inline std::string escape_newlines(const std::string& value){return value;}
inline bool ends_with(const std::string& value,const std::string& suffix){return value.size()>=suffix.size()&&value.compare(value.size()-suffix.size(),suffix.size(),suffix)==0;}
inline std::string trim(const std::string& value){auto begin=value.find_first_not_of(" \t\n\r\f\v");if(begin==std::string::npos)return "";return value.substr(begin,value.find_last_not_of(" \t\n\r\f\v")-begin+1);}

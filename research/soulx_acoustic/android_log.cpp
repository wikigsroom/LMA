// SPDX-License-Identifier: MIT
// Match the existing private worker policy: no ORT messages go to Logcat.
#if defined(__ANDROID__)
#include <cstdarg>
extern "C" int __android_log_print(int,const char*,const char*,...){return 0;}
extern "C" int __android_log_vprint(int,const char*,const char*,va_list){return 0;}
extern "C" int __android_log_write(int,const char*,const char*){return 0;}
#endif

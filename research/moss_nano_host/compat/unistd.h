// SPDX-License-Identifier: MIT
#pragma once
#include "../../sd_host/platform.hpp"
#include <cstdio>
#include <cstring>
#include <io.h>

#define STDOUT_FILENO 1
#define dup _dup
#define fdopen _fdopen
#define fileno _fileno
#define fsync _commit

inline FILE* lma_nano_fopen(const wchar_t* path, const char* mode) {
    if (std::strcmp(mode, "wb") != 0) return nullptr;
    return _wfopen(path, L"wb");
}
inline FILE* lma_nano_fopen(const char* path, const char* mode) { return std::fopen(path, mode); }
inline FILE* lma_nano_freopen(const char* path, const char* mode, FILE* stream) {
    return std::freopen(std::strcmp(path, "/dev/null") == 0 ? "NUL" : path, mode, stream);
}
#define fopen lma_nano_fopen
#define freopen lma_nano_freopen

// SPDX-License-Identifier: MIT
// Windows-only parent-lifetime port for testing unchanged Android worker code.
#pragma once
#ifndef _WIN32
#error This developer compatibility layer is only for native Windows
#endif
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#include <climits>
#include <new>

using pid_t = int;
#ifndef SIGKILL
#define SIGKILL 9
#endif
#define PR_SET_PDEATHSIG 1

inline pid_t getppid() {
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snapshot == INVALID_HANDLE_VALUE) return 0;
    PROCESSENTRY32W item{}; item.dwSize = sizeof(item); DWORD parent = 0;
    if (Process32FirstW(snapshot, &item)) do {
        if (item.th32ProcessID == GetCurrentProcessId()) { parent = item.th32ParentProcessID; break; }
    } while (Process32NextW(snapshot, &item));
    CloseHandle(snapshot);
    return parent <= INT_MAX ? static_cast<pid_t>(parent) : 0;
}

inline DWORD WINAPI lma_sd_parent_watcher(void* handle) {
    HANDLE parent = static_cast<HANDLE>(handle);
    DWORD result = WaitForSingleObject(parent, INFINITE); CloseHandle(parent);
    if (result == WAIT_OBJECT_0) TerminateProcess(GetCurrentProcess(), 125);
    return 0;
}

inline int prctl(int operation, int signal) {
    if (operation != PR_SET_PDEATHSIG || signal != SIGKILL) return -1;
    pid_t parent_id = getppid(); if (parent_id <= 1) return -1;
    HANDLE parent = OpenProcess(SYNCHRONIZE, FALSE, static_cast<DWORD>(parent_id));
    if (!parent || WaitForSingleObject(parent, 0) != WAIT_TIMEOUT) { if (parent) CloseHandle(parent); return -1; }
    HANDLE thread = CreateThread(nullptr, 0, lma_sd_parent_watcher, parent, 0, nullptr);
    if (!thread) { CloseHandle(parent); return -1; }
    CloseHandle(thread); return 0;
}

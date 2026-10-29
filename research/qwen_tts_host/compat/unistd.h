// SPDX-License-Identifier: MIT
#pragma once
#include "../../moss_nano_host/compat/unistd.h"
#include <cstdlib>
inline int unsetenv(const char* name) { return _putenv_s(name, ""); }
inline int setenv(const char* name, const char* value, int overwrite) {
    return !overwrite && std::getenv(name) ? 0 : _putenv_s(name, value);
}

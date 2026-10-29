// SPDX-License-Identifier: MIT
// Signed-App stage lifetime; the owning Java task also kills and reaps each child.
#ifndef _WIN32
#include <sys/prctl.h>
#include <unistd.h>
#include <signal.h>
#include <cstdlib>
namespace {
struct ParentGuard {
    ParentGuard() {
        const auto parent = getppid();
        if (parent <= 1 || prctl(PR_SET_PDEATHSIG, SIGKILL) || getppid() != parent ||
            prctl(PR_SET_DUMPABLE, 0) || prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)) std::_Exit(125);
    }
} parent_guard;
}
#endif

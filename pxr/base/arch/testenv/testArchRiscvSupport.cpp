//
// Licensed under the terms set forth in the LICENSE.txt file available at
// https://openusd.org/license.
//

#include "pxr/pxr.h"
#include "pxr/base/arch/defines.h"
#include "pxr/base/arch/error.h"
#include "pxr/base/arch/math.h"
#include "pxr/base/arch/stackTrace.h"

#include <cerrno>

#if !defined(ARCH_OS_LINUX) || !defined(__riscv) || __riscv_xlen != 64
#error "testArchRiscvSupport requires Linux RV64"
#endif
#if !defined(ARCH_CPU_RISCV) || !defined(ARCH_BITS_64)
#error "RV64 must define ARCH_CPU_RISCV and ARCH_BITS_64"
#endif

PXR_NAMESPACE_USING_DIRECTIVE

static void TestCpuAndMath()
{
    ARCH_AXIOM(sizeof(void*) == 8);
    ARCH_AXIOM(ArchSign(-7) == -1);
    ARCH_AXIOM(ArchSign(0) == 0);
    ARCH_AXIOM(ArchSign(7) == 1);
    ARCH_AXIOM(ArchFloatToBitPattern(1.0f) == 0x3f800000u);
}

static void TestExecSuccess()
{
    char shell[] = "/bin/sh";
    char flag[] = "-c";
    char command[] = "exit 17";
    char* args[] = {shell, flag, command, nullptr};

    ARCH_AXIOM(ArchCrashHandlerSystemv(
        shell, args, 30, nullptr, nullptr) == 17);
}

static void TestExecMissing()
{
    char path[] = "/__openusd_missing_rv64_execve__";
    char* args[] = {path, nullptr};
    errno = 0;
    const int status = ArchCrashHandlerSystemv(
        path, args, 30, nullptr, nullptr);

    ARCH_AXIOM(status == 127);
    ARCH_AXIOM(errno == ENOENT);
}

int main()
{
    TestCpuAndMath();
    TestExecSuccess();
    TestExecMissing();
    return 0;
}

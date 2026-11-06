//
// Licensed under the terms set forth in the LICENSE.txt file available at
// https://openusd.org/license.
//

#include "pxr/pxr.h"
#include "pxr/base/arch/align.h"
#include "pxr/base/arch/defines.h"

#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <limits>
#include <unistd.h>

#ifndef ARCH_OS_LINUX
#error This cache-line boundary test is Linux-only.
#endif

static_assert(ARCH_CACHE_LINE_SIZE > 0,
              "The Linux cache-line fallback must be nonzero.");

#ifdef ARCH_TEST_KEY_MISSING
// Mimic a libc without this sysconf key, after unistd.h has been read.
#undef _SC_LEVEL1_DCACHE_LINESIZE
#elif !defined(_SC_LEVEL1_DCACHE_LINESIZE)
// Force the key-present path even on a libc that does not expose the key.
// The sysconf call below is intercepted, so the numeric key is never sent
// to libc.
#define _SC_LEVEL1_DCACHE_LINESIZE 190
#endif

static long _sysconfResult = 0;
static int _sysconfCalls = 0;

static long
_TestSysconf(int)
{
    ++_sysconfCalls;
    return _sysconfResult;
}

// Exercise the actual private production implementation, rather than a
// copy of its conditional logic.  Rename the second external symbol so
// linking against libarch does not duplicate Arch_ValidateAssumptions.
#define sysconf _TestSysconf
#define Arch_ValidateAssumptions Arch_ValidateAssumptionsForCacheLineTest
#include "pxr/base/arch/assumptions.cpp"
#undef Arch_ValidateAssumptions
#undef sysconf

PXR_NAMESPACE_USING_DIRECTIVE

static bool
_Check(long input, size_t expectedBytes, int expectedCalls)
{
    _sysconfResult = input;
    _sysconfCalls = 0;
    const size_t actual = Arch_ObtainCacheLineSize();

    if (actual != expectedBytes || _sysconfCalls != expectedCalls) {
        std::fprintf(stderr,
                     "cache-line size: got %zu, expected %zu; "
                     "sysconf calls: got %d, expected %d\n",
                     actual, expectedBytes,
                     _sysconfCalls, expectedCalls);
        return false;
    }
    return true;
}

int
main()
{
#ifdef ARCH_TEST_KEY_MISSING
    // A missing key must bypass sysconf, even if its substitute would
    // return a valid value.
    return _Check(128, ARCH_CACHE_LINE_SIZE, 0) ? 0 : 1;
#else
    // Positive results are preserved; zero and negative results fall back.
    return (_Check(128, 128, 1) &&
            _Check(0, ARCH_CACHE_LINE_SIZE, 1) &&
            _Check(-1, ARCH_CACHE_LINE_SIZE, 1)) ? 0 : 1;
#endif
}

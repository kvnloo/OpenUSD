//
// Licensed under the terms set forth in the LICENSE.txt file available at
// https://openusd.org/license.
//

// Compile the same production-function boundary control with the libc
// cache-line sysconf key deliberately absent.
#define ARCH_TEST_KEY_MISSING 1
#include "testArchCacheLineKeyPresent.cpp"

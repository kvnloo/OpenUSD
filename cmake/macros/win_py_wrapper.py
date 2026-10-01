#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#
# Usage:
#   win_py_wrapper.py file output.cmd

from __future__ import print_function
import sys

if len(sys.argv) != 3:
    print("Usage: %s file output.cmd" % sys.argv[0])
    sys.exit(1)

source, destination = sys.argv[1:]

with open(destination, 'w') as f:
    print('@python "%%~dp0%s" %%*' % source, file=f)

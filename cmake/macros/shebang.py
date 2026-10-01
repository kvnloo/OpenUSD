#
# Copyright 2017 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#
# Usage:
#   shebang.py shebang-str source.py dest.py

from __future__ import print_function
import sys

if len(sys.argv) != 4:
    print("Usage: %s shebang-str source.py dest.py" % sys.argv[0])
    sys.exit(1)

shebang, source, destination = sys.argv[1:]

if not shebang:
    print("Error: shebang-str must not be empty")
    sys.exit(1)

with open(source, 'r') as s:
    with open(destination, 'w') as d:
        for idx, line in enumerate(s):
            if idx == 0:
                d.write(line.replace('/pxrpythonsubst', shebang))
            else:
                d.write(line)

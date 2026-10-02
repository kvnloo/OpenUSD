#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Exercise pxr_python_bin helper dependencies without building USD libraries."""

import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import unittest


class PythonBinDependenciesTest(unittest.TestCase):
    def _CheckHelperDependency(self, helper, windowsWrapper=False):
        cmake = shutil.which("cmake")
        self.assertIsNotNone(cmake, "CMake is required for this build-system test")
        cmakeRoot = pathlib.Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            source = root / "source with spaces"
            build = root / "build with spaces"
            for relative in (
                "macros/Public.cmake", "macros/Private.cmake",
                "defaults/Version.cmake", "macros/shebang.py",
                "macros/win_py_wrapper.py",
            ):
                target = source / "cmake" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(cmakeRoot / relative, target)
            (source / "demo.py").write_text(
                '#!/pxrpythonsubst\nprint("hello")\n', encoding="utf-8")
            # WIN32 selects wrapper generation only. This does not execute a
            # Windows command script or claim a native Windows runtime test.
            project = '''cmake_minimum_required(VERSION 3.22)
project(PythonBinDependencies NONE)
list(APPEND CMAKE_MODULE_PATH
    "${PROJECT_SOURCE_DIR}/cmake/macros"
    "${PROJECT_SOURCE_DIR}/cmake/defaults")
include(Public)
add_custom_target(python_modules)
set(PYTHON_EXECUTABLE "{python}")
set(PXR_PYTHON_SHEBANG "/usr/bin/env python3")
set(WIN32 {windows})
pxr_python_bin(demo)
'''.replace("{python}", pathlib.Path(sys.executable).as_posix()).replace(
                "{windows}", "TRUE" if windowsWrapper else "FALSE")
            (source / "CMakeLists.txt").write_text(project, encoding="utf-8")

            def run(*arguments):
                result = subprocess.run(
                    [cmake, *arguments], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            run("-S", str(source), "-B", str(build))
            run("--build", str(build), "--target", "demo_script")
            output = build / ("demo.cmd" if windowsWrapper else "demo")
            original = output.read_text(encoding="utf-8")
            expected = ('@python "%~dp0demo" %*\n' if windowsWrapper else
                        '#!/usr/bin/env python3\nprint("hello")\n')
            self.assertEqual(original, expected)
            originalTime = output.stat().st_mtime_ns
            run("--build", str(build), "--target", "demo_script")
            self.assertEqual(output.stat().st_mtime_ns, originalTime)
            marker = "\nregenerated-by-updated-helper\n"
            # Ensure ordering even on filesystems with one-second timestamps.
            time.sleep(1.1)
            helperPath = source / "cmake/macros" / helper
            with helperPath.open("a", encoding="utf-8") as stream:
                stream.write(
                    '\nwith open(sys.argv[-1], "a") as output:\n'
                    '    output.write(%r)\n' % marker)
            run("--build", str(build), "--target", "demo_script")
            self.assertEqual(output.read_text(encoding="utf-8"), original + marker)
            rebuiltTime = output.stat().st_mtime_ns
            run("--build", str(build), "--target", "demo_script")
            self.assertEqual(output.stat().st_mtime_ns, rebuiltTime)

    def testShebangHelperChangeRebuildsScript(self):
        self._CheckHelperDependency("shebang.py")

    def testWrapperHelperChangeRebuildsCommandFile(self):
        self._CheckHelperDependency("win_py_wrapper.py", windowsWrapper=True)


if __name__ == "__main__":
    unittest.main()

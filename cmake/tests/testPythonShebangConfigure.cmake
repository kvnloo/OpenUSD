#
# Copyright 2026
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#
# Exercises the actual root CMake shebang configuration block in an isolated
# configure, without needing to build the rest of OpenUSD's dependencies.

cmake_minimum_required(VERSION 3.27)

get_filename_component(_root "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
file(READ "${_root}/CMakeLists.txt" _root_cmake)
string(FIND "${_root_cmake}" "set(PXR_PYTHON_SHEBANG " _start)
string(FIND "${_root_cmake}" "# CXXDefaults will set a variety of variables" _end)
if(_start EQUAL -1 OR _end LESS_EQUAL _start)
    message(FATAL_ERROR "Cannot locate the root CMake shebang configuration block")
endif()
math(EXPR _length "${_end} - ${_start}")
string(SUBSTRING "${_root_cmake}" ${_start} ${_length} _shebang_block)

set(_fixture "${CMAKE_CURRENT_BINARY_DIR}/testPythonShebangConfigure-fixture")
file(REMOVE_RECURSE "${_fixture}")
file(MAKE_DIRECTORY "${_fixture}")
file(WRITE "${_fixture}/CMakeLists.txt"
    "cmake_minimum_required(VERSION 3.27)\n"
    "project(testPythonShebangConfigure NONE)\n"
    "${_shebang_block}\n")

# _override: <UNSET> leaves the cache variable uninitialized; "" is an
# explicit empty cached override. _python is the default from Packages.cmake.
function(_check _name _enabled _override _python _expect_success _expected_cache)
    set(_build "${_fixture}/${_name}")
    set(_args
        -S "${_fixture}" -B "${_build}"
        "-DPXR_ENABLE_PYTHON_SUPPORT:BOOL=${_enabled}"
        "-DPYTHON_EXECUTABLE:FILEPATH=${_python}")
    if(NOT _override STREQUAL "<UNSET>")
        list(APPEND _args "-DPXR_PYTHON_SHEBANG:STRING=${_override}")
    endif()
    execute_process(
        COMMAND "${CMAKE_COMMAND}" ${_args}
        RESULT_VARIABLE _result
        OUTPUT_VARIABLE _stdout
        ERROR_VARIABLE _stderr)
    set(_log "${_stdout}\n${_stderr}")
    if(_expect_success)
        if(NOT _result STREQUAL "0")
            message(FATAL_ERROR "${_name} unexpectedly failed (${_result}):\n${_log}")
        endif()
        file(STRINGS "${_build}/CMakeCache.txt" _cached
            REGEX "^PXR_PYTHON_SHEBANG:STRING=")
        if(NOT _cached STREQUAL "PXR_PYTHON_SHEBANG:STRING=${_expected_cache}")
            message(FATAL_ERROR "${_name}: incorrect cache value: ${_cached}")
        endif()
    else()
        if(_result STREQUAL "0" OR
           NOT _log MATCHES "PXR_PYTHON_SHEBANG must not be empty")
            message(FATAL_ERROR "${_name} should reject an empty shebang:\n${_log}")
        endif()
    endif()
    message(STATUS "${_name}: PASS")
endfunction()

_check(enabled_empty ON "" "${CMAKE_COMMAND}" FALSE "")
_check(enabled_override ON "/custom/python3" "${CMAKE_COMMAND}" TRUE "/custom/python3")
_check(enabled_default ON "<UNSET>" "${CMAKE_COMMAND}" TRUE "${CMAKE_COMMAND}")
_check(enabled_missing_default ON "<UNSET>" "" FALSE "")
_check(disabled_empty OFF "" "" TRUE "")
_check(disabled_missing_default OFF "<UNSET>" "" TRUE "")

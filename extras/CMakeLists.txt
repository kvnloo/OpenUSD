if (${PXR_BUILD_EXEC})
    add_subdirectory(exec)
endif()
add_subdirectory(performance)
add_subdirectory(usd)
if (${PXR_BUILD_IMAGING})
    add_subdirectory(imaging)
endif()

# This downstream normalizer is pure Python and needs neither USD nor Qt.
if (PXR_BUILD_TESTS AND PXR_ENABLE_PYTHON_SUPPORT)
    add_test(NAME testUsdviewLabsPortableEvidence
        COMMAND "${PYTHON_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/usd/examples/usdviewPlugins/usdviewLabs/testenv/test_portable_evidence.py"
            -v
    )
    set_tests_properties(testUsdviewLabsPortableEvidence PROPERTIES
        LABELS "portable-evidence"
        TIMEOUT 30
    )
endif()

cmake_minimum_required(VERSION 3.22)
project(lma_moss_nano_host LANGUAGES C CXX)
if(NOT WIN32 OR NOT MSVC)
  message(FATAL_ERROR "Use native Windows MSVC without virtualization")
endif()
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_MSVC_RUNTIME_LIBRARY MultiThreaded)
set(SPM_ENABLE_SHARED OFF CACHE BOOL "" FORCE)
set(SPM_BUILD_TEST OFF CACHE BOOL "" FORCE)
set(SPM_ENABLE_TCMALLOC OFF CACHE BOOL "" FORCE)
set(SPM_DISABLE_EMBEDDED_DATA ON CACHE BOOL "" FORCE)
add_subdirectory("${ROOT}/build/native-src/sentencepiece" sentencepiece EXCLUDE_FROM_ALL)
add_library(lma_ort SHARED IMPORTED)
set_target_properties(lma_ort PROPERTIES IMPORTED_LOCATION "${RUNTIME}/onnxruntime.dll"
  IMPORTED_IMPLIB "${CMAKE_BINARY_DIR}/onnxruntime.lib")
add_executable(lma_moss_nano_host "${ROOT}/native/moss_nano/worker.cpp")
target_include_directories(lma_moss_nano_host PRIVATE "${ROOT}/research/moss_nano_host/compat"
  "${ROOT}/build/native-src/sentencepiece/src"
  "${ROOT}/build/native-src/onnxruntime-headers/include/onnxruntime/core/session"
  "${ROOT}/build/native-src/sd-cpp/thirdparty")
target_compile_definitions(lma_moss_nano_host PRIVATE LMA_MOSS_REVISION="${LMA_MOSS_REVISION}" _CRT_SECURE_NO_WARNINGS)
target_compile_options(lma_moss_nano_host PRIVATE /utf-8 /bigobj)
target_link_libraries(lma_moss_nano_host PRIVATE sentencepiece-static lma_ort)

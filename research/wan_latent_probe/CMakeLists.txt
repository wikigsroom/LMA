cmake_minimum_required(VERSION 3.22)
project(lma_wan_latent_probe LANGUAGES CXX)
get_filename_component(ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../.." ABSOLUTE)
set(SD "${ROOT}/build/native-src/sd-cpp")
set(WAN_LIB_ROOT "${ROOT}/build/sd-vulkan-host")
add_executable(lma_wan_latent_probe "${ROOT}/native/sd_worker.cpp" "${CMAKE_BINARY_DIR}/video_probe.cpp")
target_compile_features(lma_wan_latent_probe PRIVATE cxx_std_17)
target_compile_definitions(lma_wan_latent_probe PRIVATE LMA_SD_REVISION="${LMA_SD_REVISION}"
  LMA_SD_VULKAN=1 GGML_MAX_NAME=160 GGML_USE_CPU GGML_USE_VULKAN ONIG_STATIC UTF8PROC_STATIC
  _CRT_SECURE_NO_WARNINGS _SILENCE_CXX17_CODECVT_HEADER_DEPRECATION_WARNING)
target_compile_options(lma_wan_latent_probe PRIVATE /utf-8 /bigobj)
target_include_directories(lma_wan_latent_probe PRIVATE
  "${ROOT}/research/sd_host/compat" "${ROOT}/native" "${SD}/include" "${SD}/src"
  "${SD}/src/core" "${SD}/src/pipeline" "${SD}/ggml/include" "${SD}/ggml/src"
  "${SD}/thirdparty" "${SD}/thirdparty/oniguruma" "${SD}/thirdparty/utf8proc")
target_link_libraries(lma_wan_latent_probe PRIVATE
  "${WAN_LIB_ROOT}/sd-source/stable-diffusion.lib" "${WAN_LIB_ROOT}/sd-source/ggml/src/ggml.lib"
  "${WAN_LIB_ROOT}/sd-source/ggml/src/ggml-cpu.lib" "${WAN_LIB_ROOT}/sd-source/ggml/src/ggml-vulkan/ggml-vulkan.lib"
  "${WAN_LIB_ROOT}/sd-source/ggml/src/ggml-base.lib" "${WAN_LIB_ROOT}/vulkan-1.lib")

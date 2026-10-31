cmake_minimum_required(VERSION 3.20)
project(lma_multiview LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 17)
if(MSVC)
 add_compile_options(/utf-8 /bigobj)
endif()
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(GGML_NATIVE OFF CACHE BOOL "" FORCE)
set(GGML_OPENMP OFF CACHE BOOL "" FORCE)
set(GGML_CPU_KLEIDIAI OFF CACHE BOOL "" FORCE)
set(GGML_CUDA OFF CACHE BOOL "" FORCE)
set(GGML_VULKAN OFF CACHE BOOL "" FORCE)
add_compile_definitions(GGML_MAX_NAME=128)
get_filename_component(LMA_MV_SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/../../build/native-src/pixal3d-mv-cpp" ABSOLUTE)
add_subdirectory("${LMA_MV_SOURCE}/thirdparty/ggml" ggml EXCLUDE_FROM_ALL)
set(core trellis_model dit flow_runner ss_decoder mesh_glb dinov3 sparse shape_decoder dual_grid
 preprocess birefnet tri_bvh remesh_dc decimate_qem proj_grid pixal3d_cond pixal3d_cond_gpu
 naf naf_gpu transforms_json pixal3d_input image_preprocess model_manifest pixal3d_postprocess
 graph_dump deform_conv_cpu trellis_args)
set(sources "")
foreach(name IN LISTS core)
 list(APPEND sources "${LMA_MV_SOURCE}/src/${name}.cpp")
endforeach()
add_executable(lma-multiview worker.cpp ${sources}
 "${CMAKE_CURRENT_SOURCE_DIR}/../../build/multiview-generated/trellis_cli.cpp"
 "${CMAKE_CURRENT_SOURCE_DIR}/../../build/multiview-generated/uv_bake.cpp"
 "${LMA_MV_SOURCE}/thirdparty/xatlas/xatlas.cpp" "${LMA_MV_SOURCE}/thirdparty/meshoptimizer/simplifier.cpp")
target_include_directories(lma-multiview PRIVATE "${LMA_MV_SOURCE}/include" "${LMA_MV_SOURCE}/src"
 "${LMA_MV_SOURCE}/thirdparty/stb" "${LMA_MV_SOURCE}/thirdparty/xatlas"
 "${LMA_MV_SOURCE}/thirdparty/meshoptimizer" "${LMA_MV_SOURCE}/thirdparty/fqms" "${LMA_JSON_SOURCE}")
if(NOT MSVC)
 set_source_files_properties("${LMA_MV_SOURCE}/src/flow_runner.cpp" PROPERTIES COMPILE_OPTIONS "-ffp-contract=off")
endif()
target_link_libraries(lma-multiview PRIVATE ggml ggml-base ggml-cpu)
if(ANDROID)
 set_target_properties(lma-multiview PROPERTIES OUTPUT_NAME liblma-multiview.so)
 target_link_options(lma-multiview PRIVATE -Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384)
endif()

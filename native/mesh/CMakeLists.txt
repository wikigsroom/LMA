cmake_minimum_required(VERSION 3.20)
project(lma_mesh LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 17)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(GGML_NATIVE OFF CACHE BOOL "" FORCE)
set(GGML_OPENMP OFF CACHE BOOL "" FORCE)
set(GGML_CPU_KLEIDIAI OFF CACHE BOOL "" FORCE)
set(GGML_CUDA OFF CACHE BOOL "" FORCE)
set(GGML_VULKAN OFF CACHE BOOL "" FORCE)
add_compile_definitions(GGML_MAX_NAME=128)
add_subdirectory("${LMA_TRELLIS_SOURCE}/thirdparty/ggml" ggml EXCLUDE_FROM_ALL)
set(core trellis_debug trellis_sched trellis_model dit flow_runner ss_decoder mesh_glb dinov3 pixal3d naf
 sparse shape_decoder dual_grid preprocess uv_bake uv_overlap_cover birefnet tri_bvh remesh_dc decimate_qem
 mesh_shape quad_refinement quad_refinement_gates quad_refinement_io quad_components quad_topology
 quad_component_cover deform_conv_cpu trellis_cli trellis_args)
set(sources "")
foreach(name IN LISTS core)
  list(APPEND sources "${LMA_TRELLIS_SOURCE}/src/${name}.cpp")
endforeach()
add_executable(lma-mesh worker.cpp ${sources}
 "${LMA_TRELLIS_SOURCE}/thirdparty/xatlas/xatlas.cpp"
 "${LMA_TRELLIS_SOURCE}/thirdparty/meshoptimizer/simplifier.cpp")
target_include_directories(lma-mesh PRIVATE "${LMA_TRELLIS_SOURCE}/include" "${LMA_TRELLIS_SOURCE}/src"
 "${LMA_TRELLIS_SOURCE}/thirdparty/stb" "${LMA_TRELLIS_SOURCE}/thirdparty/xatlas"
 "${LMA_TRELLIS_SOURCE}/thirdparty/meshoptimizer" "${LMA_TRELLIS_SOURCE}/thirdparty/fqms" "${LMA_JSON_SOURCE}")
target_link_libraries(lma-mesh PRIVATE ggml ggml-base ggml-cpu)
if(ANDROID)
 set_target_properties(lma-mesh PROPERTIES OUTPUT_NAME liblma-mesh.so)
 target_link_options(lma-mesh PRIVATE -Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384 -Wl,--export-dynamic)
endif()

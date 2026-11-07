cmake_minimum_required(VERSION 3.20)
project(lma_chat_runtime LANGUAGES C CXX)
if(NOT ANDROID OR NOT LMA_LLAMA_SOURCE OR NOT LMA_BASE_RUNTIME)
  message(FATAL_ERROR "Pinned Android source and retained runtime are required")
endif()
add_subdirectory(${LMA_LLAMA_SOURCE} llama-source)
# Resolve C++ runtime helpers against the libraries actually retained in the APK.
# Linking against newly compiled dependencies can leave imports that an older
# publisher library does not export, despite unchanged llama/ggml function ABI.
get_target_property(chat_links llama-common LINK_LIBRARIES)
list(REMOVE_ITEM chat_links llama)
foreach(name llama ggml ggml-base)
  if(NOT EXISTS "${LMA_BASE_RUNTIME}/lib${name}.so")
    message(FATAL_ERROR "Missing retained dependency: ${name}")
  endif()
  list(APPEND chat_links "${LMA_BASE_RUNTIME}/lib${name}.so")
endforeach()
set_property(TARGET llama-common PROPERTY LINK_LIBRARIES "${chat_links}")
target_include_directories(llama-common PRIVATE
  "${LMA_LLAMA_SOURCE}/include" "${LMA_LLAMA_SOURCE}/ggml/include")

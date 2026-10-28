cmake_minimum_required(VERSION 3.22)
project(lma_qwen_tts LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
find_package(Threads REQUIRED)
add_subdirectory("${LMA_QWEN_SOURCE}/ggml" ggml EXCLUDE_FROM_ALL)
# Only the reviewed native library sources; no upstream CLI/JNI/converter/download utilities.
set(qwen_sources
  "${LMA_QWEN_SOURCE}/src/audio_tokenizer_encoder.cpp"
  "${LMA_QWEN_SOURCE}/src/common/audio_io.cpp"
  "${LMA_QWEN_SOURCE}/src/common/icl_prompt_io.cpp"
  "${LMA_QWEN_SOURCE}/src/common/speaker_embedding_io.cpp"
  "${LMA_QWEN_SOURCE}/src/coreml_code_predictor_stub.cpp"
  "${LMA_QWEN_SOURCE}/src/decoder/decoder_cache.cpp"
  "${LMA_QWEN_SOURCE}/src/decoder/decoder_graph.cpp"
  "${LMA_QWEN_SOURCE}/src/decoder/decoder_layers.cpp"
  "${LMA_QWEN_SOURCE}/src/decoder/decoder_loader.cpp"
  "${LMA_QWEN_SOURCE}/src/decoder/decoder_runtime.cpp"
  "${LMA_QWEN_SOURCE}/src/encoder/encoder_frontend.cpp"
  "${LMA_QWEN_SOURCE}/src/encoder/encoder_graph.cpp"
  "${LMA_QWEN_SOURCE}/src/encoder/encoder_loader.cpp"
  "${LMA_QWEN_SOURCE}/src/encoder/encoder_runtime.cpp"
  "${LMA_QWEN_SOURCE}/src/gguf_loader.cpp"
  "${LMA_QWEN_SOURCE}/src/pipeline/pipeline_models.cpp"
  "${LMA_QWEN_SOURCE}/src/pipeline/pipeline_runtime.cpp"
  "${LMA_QWEN_SOURCE}/src/pipeline/pipeline_synthesize.cpp"
  "${LMA_QWEN_SOURCE}/src/qwen3_tts.cpp"
  "${LMA_QWEN_SOURCE}/src/speech_tokenizer_encoder.cpp"
  "${LMA_QWEN_SOURCE}/src/text_tokenizer.cpp"
  "${LMA_QWEN_SOURCE}/src/tokenizer_unicode.cpp"
  "${LMA_QWEN_SOURCE}/src/tokenizer_unicode_data.cpp"
  "${LMA_QWEN_SOURCE}/src/transformer/transformer_cache.cpp"
  "${LMA_QWEN_SOURCE}/src/transformer/transformer_debug.cpp"
  "${LMA_QWEN_SOURCE}/src/transformer/transformer_embeddings.cpp"
  "${LMA_QWEN_SOURCE}/src/transformer/transformer_generate.cpp"
  "${LMA_QWEN_SOURCE}/src/transformer/transformer_graph_code_pred.cpp"
  "${LMA_QWEN_SOURCE}/src/transformer/transformer_graph_talker.cpp"
  "${LMA_QWEN_SOURCE}/src/transformer/transformer_loader.cpp"
  "${LMA_QWEN_SOURCE}/src/transformer/transformer_loader_metadata.cpp"
  "${LMA_QWEN_SOURCE}/src/transformer/transformer_loader_tensors.cpp"
  "${LMA_QWEN_SOURCE}/src/transformer/transformer_runtime.cpp"
  "${LMA_QWEN_SOURCE}/src/transformer/transformer_runtime_code_pred.cpp"
  "${LMA_QWEN_SOURCE}/src/tts_transformer.cpp"
)
add_library(qwen_tts_core STATIC ${qwen_sources})
target_include_directories(qwen_tts_core PUBLIC "${LMA_QWEN_SOURCE}/src" "${LMA_QWEN_SOURCE}/ggml/include")
target_link_libraries(qwen_tts_core PUBLIC ggml ggml-base ggml-cpu Threads::Threads)
add_executable(lma_qwen_worker worker.cpp)
target_compile_options(lma_qwen_worker PRIVATE -fexceptions)
target_include_directories(lma_qwen_worker PRIVATE "${LMA_JSON_SOURCE}")
target_compile_definitions(lma_qwen_worker PRIVATE LMA_QWEN_REVISION="${LMA_QWEN_REVISION}")
target_link_libraries(lma_qwen_worker PRIVATE qwen_tts_core)
target_link_options(lma_qwen_worker PRIVATE -Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384)
set_target_properties(lma_qwen_worker PROPERTIES OUTPUT_NAME "liblma-qwen-tts" SUFFIX ".so" SKIP_BUILD_RPATH TRUE)

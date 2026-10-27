# Native runtime provenance and notices

LMA independently implements its Android application and UI. It redistributes the CPU subset of the MIT-licensed llama.cpp runtime supplied by the [ServLlama 1.2.2 release](https://github.com/ArkaneFans/servllama/releases/tag/1.2.2).

- Asset: `llama-server-v0.4.1-android-arm64-v8a.zip`
- SHA256: `551e5be8494bd2ae9955992faaaca1a4f5cf29e3a97f90d2e04205eb460fcde6`
- Recorded llama.cpp revision: `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4`
- LMA includes 14 CPU libraries, recorded individually in `runtime-lock.json`. Optional OpenCL and Hexagon libraries are excluded.

`BUILD_INFO.json`, `SHA256SUMS` and `LLAMA_CPP_LICENSE` are the upstream provider's metadata. The toolchain image mentioned in that metadata was used by the provider. **No container, WSL, emulator or virtual machine was run in this LMA build.** Native compilation was performed upstream; LMA verifies and packages the prebuilt binaries and builds its Java / resources using native Windows SDK tools.

The primary engine license is in `LLAMA_CPP_LICENSE`. `notices/` contains accompanying third-party license texts from pinned upstream sources; `notices/sources.json` records their URLs. Standard LLVM runtime notices are included conservatively because the provider's ELF bundle statically includes its C++ runtime; a separate C++ runtime source revision is not recorded by the provider. Inclusion of a notice does not assert every optional upstream feature is enabled in LMA.

`tools/collect_notices.py` can refresh these notices from the recorded revisions. The build bundles them into `assets/licenses/` and the application's About page. `upstream/` contains selected source and documentation files used to check CLI flags and supported architectures; it is not a complete source checkout. Full source for the recorded engine revision is available from the [llama.cpp repository](https://github.com/ggml-org/llama.cpp/tree/b29c606e28a01b1bc8c1351026a0fa6e616bf6c4).

Model weights are not redistributed in the APK. Each catalogue entry links to its own model repository, whose model and base-model licenses govern the downloaded weights.

## Added development worker

0.3.0-dev adds a locally compiled ARM64 CPU sd.cpp worker, pinned with ggml in [engine-lock.json](engine-lock.json). Native Windows NDK 30.0.16248370 builds it; the temporary SUBST path alias is not virtualization. [Native sources](../native/CMakeLists.txt) replace embedded model vocabularies with externally installed user data. The 13 `sd-*` notice files come from the exact checkout and NDK, recorded in [sd-sources.json](notices/sd-sources.json). This proves compilation/packaging provenance, not phone inference or all selected-model support. Existing ServLlama binaries retain their original provenance. See [development status](../docs/DEVELOPMENT.en.md).

## MOSS Nano adapter

Pinned MOSS/SentencePiece/ORT headers and exact shared ORT bytes are recorded in [moss-nano-source-lock.json](moss-nano-source-lock.json). Seven upstream notice originals are collected from clean pinned sources. The signed worker uses external user-selected model data and shares one verified ORT file with sherpa. [中文](../docs/MOSS_NANO_ENGINE.md) · [English](../docs/MOSS_NANO_ENGINE.en.md).

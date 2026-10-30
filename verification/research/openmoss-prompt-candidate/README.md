# Unadopted MOSS prompt candidate / 未采用的提示候选

Exact original report, request, stdout/stderr, driver and candidate source are retained here. This experiment timed out after 1800 seconds at generation step 332/375; no WAV or complete execution record exists. No model parameter, seed, output limit or production binary was changed to obtain a passing result. The candidate was not adopted.

原始报告、请求、输出、驱动和候选源码按原字节保留。实际测试超时，没有完整产物，不作为修复通过，也不进入 APK。

`candidate-pipeline.cpp.txt` derives from `pwilkin/openmoss@bfb1f465e0a86fb5a52bbf93e67ceba4b7d0b4e1`, under [Apache-2.0](../../../third_party/notices/openmoss-LICENSE.txt), with LMA production guards and the single assistant-prefix candidate recorded in the original driver. Source is stored as text for audit, not compiled by the App. Model weights and compiled executables are excluded.

[中文诊断](../../../docs/MOSS_REFERENCE_DIAGNOSTICS.md) · [English diagnostics](../../../docs/MOSS_REFERENCE_DIAGNOSTICS.en.md)

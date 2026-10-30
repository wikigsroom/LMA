# v0.3.0 实现追溯矩阵

[English](IMPLEMENTATION_V030.en.md) · [machine-readable matrix](../catalogue/release-0.3.0-implementation.json) · [validation](../verification/program/status.json)

原提案保留为冻结需求记录。本矩阵追溯本版完整程序集成，不改写历史失败，不代表完整训练模型或手机质量验收；全部所选范围属于同一版本。

| ID | Production source / 生产源码 |
| --- | --- |
| F-01 | [HubCatalog](../app/src/main/java/com/lma/app/HubCatalog.java), [HubClient](../app/src/main/java/com/lma/app/HubClient.java), [RecipeCatalogue](../app/src/main/java/com/lma/app/core/RecipeCatalogue.java), [RecipeSuggestions](../app/src/main/java/com/lma/app/core/RecipeSuggestions.java) |
| F-02 | [BundleStore](../app/src/main/java/com/lma/app/core/BundleStore.java), [BundleTransfers](../app/src/main/java/com/lma/app/core/BundleTransfers.java), [BundleUpdates](../app/src/main/java/com/lma/app/core/BundleUpdates.java), [ComponentIntegrity](../app/src/main/java/com/lma/app/core/ComponentIntegrity.java) |
| F-03 | [ModelBundle](../app/src/main/java/com/lma/app/core/ModelBundle.java), [LocalEngines](../app/src/main/java/com/lma/app/LocalEngines.java), [TaskRequests](../app/src/main/java/com/lma/app/core/TaskRequests.java) |
| F-04 | [NativeWorker](../app/src/main/java/com/lma/app/NativeWorker.java), [NativeStages](../app/src/main/java/com/lma/app/NativeStages.java), [Ltx098Engine](../app/src/main/java/com/lma/app/Ltx098Engine.java), [MnnEngine](../app/src/main/java/com/lma/app/MnnEngine.java), [SdEngine](../app/src/main/java/com/lma/app/SdEngine.java), [SherpaEngine](../app/src/main/java/com/lma/app/SherpaEngine.java), [MossNanoEngine](../app/src/main/java/com/lma/app/MossNanoEngine.java), [QwenTtsEngine](../app/src/main/java/com/lma/app/QwenTtsEngine.java), [MossDelayEngine](../app/src/main/java/com/lma/app/MossDelayEngine.java), [OpenMossEngine](../app/src/main/java/com/lma/app/OpenMossEngine.java), [MossRqEngine](../app/src/main/java/com/lma/app/MossRqEngine.java), [SoulxEngine](../app/src/main/java/com/lma/app/SoulxEngine.java), [StableAudioEngine](../app/src/main/java/com/lma/app/StableAudioEngine.java) |
| F-05 | [ModelSettings](../app/src/main/java/com/lma/app/ModelSettings.java), [GgufMetadata](../app/src/main/java/com/lma/app/GgufMetadata.java), [ParameterSchema](../app/src/main/java/com/lma/app/core/ParameterSchema.java), [LtxPixArtSpec](../app/src/main/java/com/lma/app/core/LtxPixArtSpec.java) |
| F-06 | [LocalJobs](../app/src/main/java/com/lma/app/LocalJobs.java), [JobStore](../app/src/main/java/com/lma/app/core/JobStore.java), [ProcessControl](../app/src/main/java/com/lma/app/core/ProcessControl.java) |
| F-07 | [DeviceResourceProbe](../app/src/main/java/com/lma/app/DeviceResourceProbe.java), [ExecutionGate](../app/src/main/java/com/lma/app/core/ExecutionGate.java), [ResourceWatch](../app/src/main/java/com/lma/app/core/ResourceWatch.java) |
| F-08 | [LmaService](../app/src/main/java/com/lma/app/LmaService.java), [BootReceiver](../app/src/main/java/com/lma/app/BootReceiver.java), [JobStore](../app/src/main/java/com/lma/app/core/JobStore.java), [ArtifactStore](../app/src/main/java/com/lma/app/core/ArtifactStore.java) |
| F-09 | [ArtifactStore](../app/src/main/java/com/lma/app/core/ArtifactStore.java), [VideoEncoder](../app/src/main/java/com/lma/app/VideoEncoder.java), [TaskDrafts](../app/src/main/java/com/lma/app/core/TaskDrafts.java) |
| F-10 | [ApiHost](../app/src/main/java/com/lma/app/ApiHost.java), [LocalApi](../app/src/main/java/com/lma/app/core/LocalApi.java), [InputUploads](../app/src/main/java/com/lma/app/core/InputUploads.java), [AudioStreams](../app/src/main/java/com/lma/app/core/AudioStreams.java) |
| F-11 | [Store](../app/src/main/java/com/lma/app/Store.java), [BundleStore](../app/src/main/java/com/lma/app/core/BundleStore.java), [ModelSettings](../app/src/main/java/com/lma/app/ModelSettings.java) |
| F-12 | [ModelBundle](../app/src/main/java/com/lma/app/core/ModelBundle.java), [TaskRequests](../app/src/main/java/com/lma/app/core/TaskRequests.java) |

| Selection / 编号 | Model / 模型 | Recipe templates / 配方 |
| --- | --- | --- |
| 01 | Stable Diffusion 1.5 | `sd15_checkpoint_cpu_v1`, `sd15_split_cpu_v1` |
| 02 | LoRA loading and management | `sd15_lora_cpu_v1`, `sdxl_lora_cpu_v1` |
| 03 | SD-Turbo / LCM / LCM-LoRA | `sd21_turbo_checkpoint_cpu_v1`, `sd15_lcm_checkpoint_cpu_v1`, `sdxl_lcm_checkpoint_cpu_v1`, `sd15_lcm_lora_cpu_v1`, `sdxl_lcm_lora_cpu_v1` |
| 04 | Sana | `sana_sprint_06b_mnn_cpu_v1`, `sana_edit_mnn_cpu_v1` |
| 05 | SDXL | `sdxl_checkpoint_cpu_v1`, `sdxl_split_cpu_v1` |
| 06 | Z-Image-Turbo | `z_image_turbo_split_cpu_v1` |
| 07 | FLUX.2-klein-4B | `flux2_klein_4b_split_cpu_v1` |
| 08 | Qwen-Image-2.1 | `qwen_image_21_split_cpu_v1` |
| 09 | MOSS-TTS-Nano 100M | `moss_nano_cpu_v1` |
| 10 | Kokoro / Piper / Matcha | `kokoro_en_cpu_v1`, `piper_vits_en_cpu_v1`, `matcha_en_cpu_v1` |
| 11 | Qwen3-TTS 0.6B Base | `qwen3_tts_06b_base_cpu_v1` |
| 12 | Full MOSS family | `moss_delay_firstclass_cpu_v1`, `moss_local_v15_cpu_v1`, `moss_soundeffect_v2_cpu_v1`, `moss_tts_openmoss_cpu_v1`, `moss_tts_v15_openmoss_cpu_v1`, `moss_ttsd_openmoss_cpu_v1`, `moss_voicegen_openmoss_cpu_v1`, `moss_soundeffect_openmoss_cpu_v1`, `moss_local_v10_rq_cpu_v1`, `moss_realtime_rq_cpu_v1` |
| 13 | SoulX-Podcast 1.7B | `soulx_podcast_cpu_v1` |
| 14 | Stable Audio Open Small | `stable_audio_small_litert_v1` |
| 16 | Wan 2.1 T2V 1.3B Q4 | `wan21_13b_split_cpu_v1`, `wan21_13b_split_vulkan_v1` |
| 17 | LTX-Video 2B 0.9.8 distilled | `ltx098_pixart_multiscale_v1`, `ltx098_single_scale_google_q5_v1` |

MOSS 九个冻结子目标：MOSS-TTS 1.0、MOSS-TTS-v1.5、MOSS-TTS-Local-Transformer、MOSS-TTS-Local-Transformer-v1.5、MOSS-TTSD-v1.0、MOSS-VoiceGenerator、MOSS-SoundEffect、MOSS-SoundEffect-v2.0、MOSS-TTS-Realtime。

原有文本使用 `text_gguf_cpu_v1`。标签按输出能力、引擎、管线和组件标记，所有模型平级；38 个模板与 23 个模型包只是可选目录，不是预装权重。当前程序检查与有界夹具有新证据；模型质量及手机续航按新策略免于本版运行验证，仍保留未验证状态。

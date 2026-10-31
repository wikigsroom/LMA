# v0.3.8 implementation and validation inventory

[README](../README.en.md) · [Profiles](ADAPTER_PROFILES.en.md) · [Release](releases/v0.3.8.md) · [Evidence](../verification/releases/v0.3.8/status.json)

This release implements the frozen scope and P01–P06 bounded CPU profiles, without claiming arbitrary HF architecture support or full benchmark workflow reproduction. F01–F12, text, selections 01–14/16/17, nine MOSS targets, SD1.5/SDXL LoRA, community models and recommendations are preserved. The App delivers the foundation; users choose every model.

**62 recipes / 82 catalogue bundles / 18 extension engines plus text; 59 program suites / 14,973 assertions.** Recipe rows are peers, not rankings. Text GGUF service is separately preserved; the 62-entry table is the versioned extension recipe catalogue.

| ID | Recipe | Engine / pipeline | Task | Required roles |
| --- | --- | --- | --- | --- |
| R01 | `sd15_checkpoint_cpu_v1` · SD 1.5 · 完整 checkpoint | `sd_cpp` / `sd15` | image | model |
| R02 | `sd15_lora_cpu_v1` · SD 1.5 · LoRA | `sd_cpp` / `lora` | image | lora |
| R03 | `sdxl_checkpoint_cpu_v1` · SDXL · 完整 checkpoint | `sd_cpp` / `sdxl` | image | model |
| R04 | `sdxl_lora_cpu_v1` · SDXL · LoRA | `sd_cpp` / `lora` | image | lora |
| R05 | `sd15_split_cpu_v1` · SD 1.5 · 独立 diffusion + 编码器 + VAE | `sd_cpp` / `sd15` | image | diffusion, clip_l, vae |
| R06 | `sdxl_split_cpu_v1` · SDXL · 独立 diffusion + 编码器 + VAE | `sd_cpp` / `sdxl` | image | diffusion, clip_l, clip_g, vae |
| R07 | `sd21_turbo_checkpoint_cpu_v1` · SD-Turbo · SD 2.1 | `sd_cpp` / `sd21_turbo` | image | model |
| R08 | `sd15_lcm_checkpoint_cpu_v1` · LCM · SD 1.5 checkpoint | `sd_cpp` / `sd15_lcm` | image | model |
| R09 | `sdxl_lcm_checkpoint_cpu_v1` · LCM · SDXL checkpoint | `sd_cpp` / `sdxl_lcm` | image | model |
| R10 | `sd15_lcm_lora_cpu_v1` · SD 1.5 · LCM-LoRA | `sd_cpp` / `lora` | image | lora |
| R11 | `sdxl_lcm_lora_cpu_v1` · SDXL · LCM-LoRA | `sd_cpp` / `lora` | image | lora |
| R12 | `z_image_turbo_split_cpu_v1` · Z-Image-Turbo | `sd_cpp` / `z_image_turbo` | image | diffusion, llm, vae, qwen_merges |
| R13 | `flux2_klein_4b_split_cpu_v1` · FLUX.2-klein 4B · distilled | `sd_cpp` / `flux2_klein_4b` | image | diffusion, llm, vae, qwen_merges |
| R14 | `qwen_image_21_split_cpu_v1` · Qwen-Image 2.1 · 文生图 | `sd_cpp` / `qwen_image_21` | image | diffusion, llm, vae, qwen_merges |
| R15 | `wan21_13b_split_cpu_v1` · Wan 2.1 · T2V 1.3B | `sd_cpp` / `wan21_13b` | video | diffusion, t5, vae, umt5_tokenizer |
| R16 | `kokoro_en_cpu_v1` · Kokoro · 英语词表 | `sherpa_tts` / `kokoro` | audio | model, voices, tokens |
| R17 | `piper_vits_en_cpu_v1` · Piper VITS · 英语词表 | `sherpa_tts` / `piper_vits` | audio | model, tokens |
| R18 | `matcha_en_cpu_v1` · Matcha + vocoder · 英语词表 | `sherpa_tts` / `matcha` | audio | model, vocoder, tokens |
| R19 | `moss_nano_cpu_v1` · MOSS-TTS-Nano · ONNX + codec | `moss_nano_ort` / `moss_nano` | audio | manifest, tts_meta, codec_meta, text_tokenizer, tts_prefill, tts_decode, tts_local, codec_decode |
| R20 | `sana_sprint_06b_mnn_cpu_v1` · Sana-Sprint 0.6B · 文生图 | `mnn_diffusion` / `sana_sprint_06b_mnn_v1` | image | diffusion, diffusion_data, gemma0, gemma0_data, gemma1, gemma1_data, gemma2, gemma2_data, gemma3, gemma3_data, embeddings, encoder_config, tokenizer, vae |
| R21 | `sana_edit_mnn_cpu_v1` · Sana Edit · 本地图片卡通转换 | `mnn_diffusion` / `sana_edit_mnn_v1` | image | diffusion, diffusion_data, connector, connector_data, projector, projector_data, vae, vae_data, llm, llm_data, llm_config, tokenizer, meta_queries, vae_encoder, vae_encoder_data |
| R22 | `text_gguf_cpu_v1` · 文本 GGUF · CPU | `llama_text` / `text_gguf` | text | text_gguf |
| R23 | `qwen3_tts_06b_base_cpu_v1` · Qwen3-TTS · 12Hz 0.6B Base | `qwen_tts_native` / `qwen3_tts_06b_base` | audio | talker, audio_codec |
| R24 | `moss_delay_firstclass_cpu_v1` · MOSS Delay 8B · first-class 原生语音 | `moss_delay_native` / `moss_delay_firstclass_v1` | audio | backbone, audio_decoder |
| R25 | `moss_local_v15_cpu_v1` · MOSS Local-Transformer-v1.5 · 原生语音 | `openmoss_native` / `moss_local_v15_cpu_v1` | audio | backbone, extras |
| R26 | `moss_soundeffect_v2_cpu_v1` · MOSS SoundEffect-v2 · 原生音效 | `openmoss_native` / `moss_soundeffect_v2_cpu_v1` | audio | backbone, extras |
| R27 | `moss_tts_openmoss_cpu_v1` · MOSS-TTS · 原生语音 | `openmoss_native` / `moss_tts_openmoss_cpu_v1` | audio | backbone, extras |
| R28 | `moss_tts_v15_openmoss_cpu_v1` · MOSS-TTS-v1.5 · 原生语音 | `openmoss_native` / `moss_tts_v15_openmoss_cpu_v1` | audio | backbone, extras |
| R29 | `moss_ttsd_openmoss_cpu_v1` · MOSS-TTSD-v1.0 · 原生语音 | `openmoss_native` / `moss_ttsd_openmoss_cpu_v1` | audio | backbone, extras |
| R30 | `moss_voicegen_openmoss_cpu_v1` · MOSS-VoiceGenerator · 原生语音 | `openmoss_native` / `moss_voicegen_openmoss_cpu_v1` | audio | backbone, extras |
| R31 | `moss_soundeffect_openmoss_cpu_v1` · MOSS-SoundEffect · 原生环境音效 | `openmoss_native` / `moss_soundeffect_openmoss_cpu_v1` | audio | backbone, extras |
| R32 | `moss_local_v10_rq_cpu_v1` · MOSS-TTS-Local-Transformer（旧版） · 原生语音 | `moss_rq_native` / `moss_local_v10_rq_cpu_v1` | audio | model, codec, tokenizer |
| R33 | `moss_realtime_rq_cpu_v1` · MOSS-TTS-Realtime · 原生语音 | `moss_rq_native` / `moss_realtime_rq_cpu_v1` | audio | model, codec, tokenizer |
| R34 | `stable_audio_small_litert_v1` · Stable Audio Open Small · 本地短音频 | `stable_audio_litert` / `stable_audio_small_litert_v1` | audio | conditioner, diffusion_model, audio_decoder, tokenizer |
| R35 | `soulx_podcast_cpu_v1` · SoulX-Podcast 1.7B · 多说话人语音 / CPU | `soulx_native` / `soulx_podcast_cpu_v1` | audio | language, s3, s3_data, speaker, speaker_data, flow_encoder, flow_encoder_data, flow_estimator, flow_estimator_data, hift_f0, hift_f0_data, hift_spectrum, hift_spectrum_data, hift_source |
| R36 | `ltx098_single_scale_google_q5_v1` · 旧 LTX 2B 0.9.8 · 单尺度 Google T5 Q5 | `ltx098_native` / `ltx098_single_scale_google_q5` | video | diffusion_model, text_encoder, tokenizer_config, vae_graph_0, vae_data_0, vae_graph_1, vae_data_1, vae_graph_2, vae_data_2, vae_graph_3, vae_data_3, vae_graph_4, vae_data_4, vae_graph_5, vae_data_5, vae_graph_6, vae_data_6, vae_graph_7, vae_data_7, vae_graph_8, vae_data_8, vae_manifest |
| R37 | `ltx098_pixart_multiscale_v1` · 旧 LTX 2B 0.9.8 · PixArt 多尺度 | `ltx098_native` / `ltx098_pixart_multiscale_v1` | video | diffusion_model, vae_graph_0, vae_data_0, vae_graph_1, vae_data_1, vae_graph_2, vae_data_2, vae_graph_3, vae_data_3, vae_graph_4, vae_data_4, vae_graph_5, vae_data_5, vae_graph_6, vae_data_6, vae_graph_7, vae_data_7, vae_graph_8, vae_data_8, vae_manifest, text_config, text_index, text_shard_1, text_shard_2, tokenizer_config, tokenizer, upscaler |
| R38 | `wan21_13b_split_vulkan_v1` · Wan 2.1 1.3B · 本地 GPU 视频 | `wan_sd_cpp` / `wan21_13b` | video | diffusion, t5, vae, umt5_tokenizer |
| R39 | `melo_zh_onnx_cpu_expansion_v1` · MeloTTS Chinese · 自选配套组件 | `sherpa_tts` / `melo_zh` | audio | model, tokens, lexicon, rule_fst, rule_fst_2, rule_fst_3, rule_fst_4 |
| R40 | `f5_v1_safetensors_cpu_expansion_v1` · F5-TTS v1 Base · 自选配套组件 | `audio_cpp` / `f5_v1` | audio | model, vocoder, vocab, pinyin_chars, pinyin_phrases |
| R41 | `f5_v1_official_frontend_cpu_v1` · F5-TTS v1 · 官方兼容中文前端 | `audio_cpp` / `f5_v1` | audio | model, vocoder, vocab, frontend |
| R42 | `omnivoice_gguf_cpu_expansion_v1` · OmniVoice · 自选配套组件 | `audio_cpp` / `omnivoice` | audio | model |
| R43 | `omnivoice_safetensors_cpu_expansion_v1` · OmniVoice · 自选配套组件 | `audio_cpp` / `omnivoice` | audio | model, config, text_tokenizer, tokenizer_config, codec_config, codec_preprocessor, audio_codec |
| R44 | `trellis2_gguf_cpu_expansion_v1` · TRELLIS.2 · 自选配套组件 | `trellis_native` / `trellis2` | 3d | image_encoder, ss_decoder, shape_decoder, ss_flow, shape_flow |
| R45 | `pixal3d_gguf_cpu_expansion_v1` · Pixal3D · 自选配套组件 | `trellis_native` / `pixal3d` | 3d | image_encoder, ss_decoder, shape_decoder, ss_flow, shape_flow, naf |
| R46 | `pixal3d_mv_gguf_cpu_v1` · Pixal3D MV · 四视图自选配套组件 | `pixal_multiview` / `pixal3d_mv` | 3d | image_encoder, naf, ss_flow, ss_decoder, shape_flow, shape_decoder, shape_flow_hr |
| R47 | `triposg_onnx_cpu_v1` · TripoSG · 配套 FP32 ONNX | `rf_shape_ort` / `triposg` | 3d | config, image_encoder, flow, cache, query |
| R48 | `partcrafter_onnx_cpu_v1` · PartCrafter · 物体部件 · 配套 FP32 ONNX | `rf_shape_ort` / `partcrafter` | 3d | config, image_encoder, flow, cache, query |
| R49 | `partcrafter_scene_onnx_cpu_v1` · PartCrafter · 场景部件 · 配套 FP32 ONNX | `rf_shape_ort` / `partcrafter_scene` | 3d | config, image_encoder, flow, cache, query |
| R50 | `triposg_points_onnx_cpu_v1` · triposg · 点云 VAE 重建 | `rf_shape_ort` / `triposg_points` | 3d | config, encoder, cache, query |
| R51 | `partcrafter_points_onnx_cpu_v1` · partcrafter · 点云 VAE 重建 | `rf_shape_ort` / `partcrafter_points` | 3d | config, encoder, cache, query |
| R52 | `hunyuan3d_21_shape_onnx_cpu_v1` · Hunyuan3D 2.1 · 形状 · 配套 FP32 ONNX | `spatial_ort` / `hunyuan3d_21_shape` | 3d | config, image_encoder, flow, cache, query |
| R53 | `ultrashape_1_refine_onnx_cpu_v1` · UltraShape 1.0 · 粗网格精修 · 配套 FP32 ONNX | `spatial_ort` / `ultrashape_1_refine` | 3d | config, image_encoder, flow, cache, query |
| R54 | `hunyuan3d_21_paint_onnx_cpu_v1` · Hunyuan3D 2.1 Paint · 本地 PBR 贴图 | `spatial_ort` / `hunyuan3d_21_paint` | 3d | config, sampler, image_encoder, vae_encoder, flow, vae_decoder, upscale |
| R55 | `ultratex_flux1_onnx_cpu_v1` · UltraTex · FLUX.1 dev · 本地 PBR | `spatial_ort` / `ultratex_flux1` | 3d | config, tokenizer, clip_tokenizer, clip, text, vae_encoder, albedo_flow, mr_flow, albedo_decoder, mr_decoder |
| R56 | `ultratex_flux2_onnx_cpu_v1` · UltraTex · FLUX.2 / Klein · 本地 PBR | `spatial_ort` / `ultratex_flux2` | 3d | config, tokenizer, text, vae_encoder, albedo_flow, mr_flow, albedo_decoder, mr_decoder |
| R57 | `uniforge3d_onnx_cpu_v1` · UniForge3D · 四视图形状与 PBR | `spatial_ort` / `uniforge3d` | 3d | config, dino512, dino1024, structure_flow, structure_decoder, conditioner, shape512_adapter, shape1024_adapter, texture_adapter, shape512_flow, shape1024_flow, texture_flow, shape512_decoder, shape1024_decoder, texture_decoder |
| R58 | `supratex_onnx_cpu_v1` · SUPRA-Tex · 本地 Qwen 与材质补全 | `spatial_ort` / `supratex` | 3d | config, tokenizer, qwen_text, qwen_encode, qwen_decode, qwen_material, shape_encoder, material_encoder, shape_decoder, material_decoder, completion |
| R59 | `sam3d_objects_onnx_cpu_v1` · SAM 3D Objects · 单图本地重建 | `spatial_ort` / `sam3d_objects` | 3d | config, ss_conditioner, slat_conditioner, structure_flow, structure_decoder, slat_flow, mesh_decoder, depth_moge |
| R60 | `mv_sam3d_da3_onnx_cpu_v1` · MV-SAM3D + DA3 · 四视图本地重建 | `spatial_ort` / `mv_sam3d_da3` | 3d | config, ss_conditioner, slat_conditioner, structure_flow, structure_decoder, slat_flow, mesh_decoder, depth_anyview, depth_metric |
| R61 | `isnet_dis_onnx_cpu_v1` · DIS · 本地自动前景 | `vision_cpu` / `isnet_dis` | image | config, foreground |
| R62 | `vlm_parts_gguf_cpu_v1` · 视觉模型 · 本地部件识别 | `vision_cpu` / `vlm_parts` | text | model, mmproj |

Parameters, exact component declarations, source revisions and fixed component identities are in [recipe-templates.json](../app/src/main/assets/recipe-templates.json). Foundation/content/task/format/install tags remain independent. NSFW or Uncensored labels require recorded sources; an architecture name alone does not establish content status.

<a id="program-checks"></a>
## 程序检查 / Program checks

| ID | Suite | Assertions | Current record |
| --- | --- | --- | --- |
| T01 | `spatial` | 188 | [JSON](../verification/releases/v0.3.8/spatial.json) |
| T02 | `spatial-graphs` | 60 | [JSON](../verification/releases/v0.3.8/spatial-graphs.json) |
| T03 | `spatial-sparse` | 109 | [JSON](../verification/releases/v0.3.8/spatial-sparse.json) |
| T04 | `shape` | 161 | [JSON](../verification/releases/v0.3.8/shape.json) |
| T05 | `multiview` | 63 | [JSON](../verification/releases/v0.3.8/multiview.json) |
| T06 | `expansion` | 884 | [JSON](../verification/releases/v0.3.8/expansion.json) |
| T07 | `community` | 818 | [JSON](../verification/releases/v0.3.8/community.json) |
| T08 | `foundation` | 1,226 | [JSON](../verification/releases/v0.3.8/foundation.json) |
| T09 | `backend` | 138 | [JSON](../verification/releases/v0.3.8/backend.json) |
| T10 | `bundle-pause` | 22 | [JSON](../verification/releases/v0.3.8/bundle-pause.json) |
| T11 | `document-input` | 15 | [JSON](../verification/releases/v0.3.8/document-input.json) |
| T12 | `api` | 68 | [JSON](../verification/releases/v0.3.8/api.json) |
| T13 | `workbench` | 44 | [JSON](../verification/releases/v0.3.8/workbench.json) |
| T14 | `recovery` | 47 | [JSON](../verification/releases/v0.3.8/recovery.json) |
| T15 | `inputs` | 64 | [JSON](../verification/releases/v0.3.8/inputs.json) |
| T16 | `text` | 66 | [JSON](../verification/releases/v0.3.8/text.json) |
| T17 | `migration` | 69 | [JSON](../verification/releases/v0.3.8/migration.json) |
| T18 | `scheduler` | 151 | [JSON](../verification/releases/v0.3.8/scheduler.json) |
| T19 | `preparations` | 44 | [JSON](../verification/releases/v0.3.8/preparations.json) |
| T20 | `assemblies` | 47 | [JSON](../verification/releases/v0.3.8/assemblies.json) |
| T21 | `diffusion` | 197 | [JSON](../verification/releases/v0.3.8/diffusion.json) |
| T22 | `mnn` | 101 | [JSON](../verification/releases/v0.3.8/mnn.json) |
| T23 | `hub` | 80 | [JSON](../verification/releases/v0.3.8/hub.json) |
| T24 | `recipe-suggestions` | 73 | [JSON](../verification/releases/v0.3.8/recipe-suggestions.json) |
| T25 | `speech-voices` | 70 | [JSON](../verification/releases/v0.3.8/speech-voices.json) |
| T26 | `sana-sprint` | 448 | [JSON](../verification/releases/v0.3.8/sana-sprint.json) |
| T27 | `ui` | 782 | [JSON](../verification/releases/v0.3.8/ui.json) |
| T28 | `ltx-official` | 89 | [JSON](../verification/releases/v0.3.8/ltx-official.json) |
| T29 | `ltx-multiscale-app` | 280 | [JSON](../verification/releases/v0.3.8/ltx-multiscale-app.json) |
| T30 | `ltx-single-scale-app` | 127 | [JSON](../verification/releases/v0.3.8/ltx-single-scale-app.json) |
| T31 | `portable-sparse-models` | 97 | [JSON](../verification/releases/v0.3.8/portable-sparse-models.json) |
| T32 | `cascade` | 95 | [JSON](../verification/releases/v0.3.8/cascade.json) |
| T33 | `ultratex-attention` | 47 | [JSON](../verification/releases/v0.3.8/ultratex-attention.json) |
| T34 | `material` | 61 | [JSON](../verification/releases/v0.3.8/material.json) |
| T35 | `f5-frontend-tests` | 6,671 | [JSON](../verification/releases/v0.3.8/f5-frontend-tests.json) |
| T36 | `ultratex-tests` | 106 | [JSON](../verification/releases/v0.3.8/ultratex-tests.json) |
| T37 | `ultratex-flow-tests` | 107 | [JSON](../verification/releases/v0.3.8/ultratex-flow-tests.json) |
| T38 | `uniforge-tests` | 18 | [JSON](../verification/releases/v0.3.8/uniforge-tests.json) |
| T39 | `uniforge-component-tests` | 78 | [JSON](../verification/releases/v0.3.8/uniforge-component-tests.json) |
| T40 | `view-router-tests` | 48 | [JSON](../verification/releases/v0.3.8/view-router-tests.json) |
| T41 | `fdg-tests` | 72 | [JSON](../verification/releases/v0.3.8/fdg-tests.json) |
| T42 | `fdg-mesh-tests` | 80 | [JSON](../verification/releases/v0.3.8/fdg-mesh-tests.json) |
| T43 | `paint-tests` | 227 | [JSON](../verification/releases/v0.3.8/paint-tests.json) |
| T44 | `paint-export-tests` | 17 | [JSON](../verification/releases/v0.3.8/paint-export-tests.json) |
| T45 | `sam-tests` | 68 | [JSON](../verification/releases/v0.3.8/sam-tests.json) |
| T46 | `sam-component-tests` | 74 | [JSON](../verification/releases/v0.3.8/sam-component-tests.json) |
| T47 | `sam-conditioner-tests` | 42 | [JSON](../verification/releases/v0.3.8/sam-conditioner-tests.json) |
| T48 | `sam-export-tests` | 25 | [JSON](../verification/releases/v0.3.8/sam-export-tests.json) |
| T49 | `sam-math-tests` | 60 | [JSON](../verification/releases/v0.3.8/sam-math-tests.json) |
| T50 | `sam-pose-tests` | 32 | [JSON](../verification/releases/v0.3.8/sam-pose-tests.json) |
| T51 | `depth-component-tests` | 25 | [JSON](../verification/releases/v0.3.8/depth-component-tests.json) |
| T52 | `depth-postprocess-tests` | 78 | [JSON](../verification/releases/v0.3.8/depth-postprocess-tests.json) |
| T53 | `flexicubes-tests` | 139 | [JSON](../verification/releases/v0.3.8/flexicubes-tests.json) |
| T54 | `supra-tests` | 16 | [JSON](../verification/releases/v0.3.8/supra-tests.json) |
| T55 | `supra-component-tests` | 52 | [JSON](../verification/releases/v0.3.8/supra-component-tests.json) |
| T56 | `vision-tests` | 29 | [JSON](../verification/releases/v0.3.8/vision-tests.json) |
| T57 | `pointcloud-tests` | 35 | [JSON](../verification/releases/v0.3.8/pointcloud-tests.json) |
| T58 | `surface-tests` | 21 | [JSON](../verification/releases/v0.3.8/surface-tests.json) |
| T59 | `adaptation-audit-checks` | 22 | [JSON](../verification/releases/v0.3.8/adaptation-audit-checks.json) |

All counts are part of the total, not additional duplicate claims. Each record carries inputs/build identities or observations; [status.json](../verification/releases/v0.3.8/status.json) indexes 72 host/build records plus status, with separate physical-device and preserved-failure records. Packaging checks validate the APK, signing certificate, 41 native libraries and dependencies, API28+, 16 KiB alignment and Lint (zero errors / 16 existing warnings). [Media](MEDIA.md): ten flows, 57 screenshots, ten GIFs and ten MP4s. All owned browsers close after use.

No complete trained-model downloads, copies or runs were performed. Separate [physical acceptance](DEVICE_ACCEPTANCE.en.md) records 19 program checks and approximately 60 seconds of screen-off API health. Model quality, inference memory, Z20 capacity and inference endurance remain unmeasured. Program-only validation uses actual pinned source classes, formal meta construction, tiny random networks, native process execution, numerical comparisons, application contracts and explicit UI fixtures. It does not establish trained-model quality or phone feasibility.

The [current source audit](../research/portability/adaptation-current.json) has no required remaining scoped code ports. Complete public matched-export endpoints are unverified; strict offline export and local import are available. Full benchmark workflow reproduction is false. [Licenses](../THIRD_PARTY_NOTICES.md), including the bundled DISO CC BY-NC 4.0 noncommercial component, apply. Historical records in `verification/program/` and `verification/history/` retain original identities.

Physical program acceptance: [23 checks / 60-second screen-off health](DEVICE_ACCEPTANCE.en.md), [JSON](../verification/releases/v0.3.8/physical-device.json). This is additional to the 59 host suites; no inference or endurance claim.

## v0.3.8 recommendations / 推荐补充

14 optional choices: original text 3 + image 3 + video 2 + audio 3 + 3D 3. Registry/task/size/source validation and 34 additional UI checks preserve explicit downloads and All/Local management. [中文](RECOMMENDED_MODELS.md) / [English](RECOMMENDED_MODELS.en.md). Four additional actual-phone category checks bring the physical program total to 23; no complete trained model is run.

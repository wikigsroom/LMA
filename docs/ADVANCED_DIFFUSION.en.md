# Local foundation bindings for Z-Image, FLUX, Qwen-Image and Wan

[中文](ADVANCED_DIFFUSION.md) · [Diffusion basics](DIFFUSION_ENGINE.en.md) · [HF recipes](HF_RECIPES.en.md) · [Development](DEVELOPMENT.en.md)

Applies to internal **0.3.0-dev.13 / code 17**, not a complete Release. Component contracts, sampling plans, native parameters and an ARM64 CPU worker are integrated. **Android model outputs, quality, speed, memory and screen-off operation remain unverified.** Selections 06/07/08/16 and every other target retain the same complete v0.3.0 gates.

## User-controlled components

The App ships signed code, recipes and tags, without any weights or vocabulary below. In the HF file view, explicitly select a template and each matching file, possibly from different repositories. Every asset retains its revision, size and integrity identity. Review/register the manifest, then independently confirm download or folder import. Local manages settings, updates, rollback and deletion. Browsing, App upgrades and missing-component jobs never download assets implicitly.

| Independent template | Required user assets | Output/foundation tags |
| --- | --- | --- |
| `z_image_turbo_split_cpu_v1` | Z-Image-Turbo diffusion, matching Qwen3 4B encoder, FLUX.1 VAE, Qwen merges.txt | Image/text-to-image, sd_cpp, z_image_turbo, CPU |
| `flux2_klein_4b_split_cpu_v1` | Distilled klein 4B diffusion, matching Qwen3 4B, **FLUX.2 VAE**, Qwen merges.txt | Image/text-to-image, sd_cpp, flux2_klein_4b, CPU |
| `qwen_image_21_split_cpu_v1` | Qwen-Image 2.1 diffusion, matching Qwen3-VL 8B Instruct, **2.1-specific VAE**, Qwen merges.txt | Image/text-to-image, sd_cpp, qwen_image_21, CPU |
| `wan21_13b_split_cpu_v1` | Wan 2.1 T2V 1.3B diffusion, UMT5 XXL encoder, Wan 2.1 VAE, UMT5 tokenizer.json | Video/text-to-video, sd_cpp, wan21_13b, CPU |

Weight roles accept GGUF/Safetensors; vocabulary roles accept text/JSON respectively, up to 32 MiB. These split recipes reject all-in-one declarations, missing dependencies, conflicting architectures and unused extra components. Formats, names and a complete four-file list cannot prove tensor compatibility. Templates neither convert models, download automatically, install engines nor alter Recommended.

Qwen supports this text-to-image binding only: reference-image/mmproj handling, editing, older Qwen-Image and 2.1 Turbo fixed sigmas are not integrated. The FLUX recipe targets distilled klein 4B, without substituting base/9B/dev. Wan targets T2V 1.3B, without substituting I2V/VACE/14B/Wan 2.2; frozen acceptance still requires the selected Q4 assets. Z-Image targets Turbo; ordinary base weights do not establish distillation.

## Parameters and execution

| Pipeline | Effective task sampling | Geometry/video constraints |
| --- | --- | --- |
| Z-Image-Turbo | euler/discrete, CFG=1, 1–8 steps, negative conditioning disabled | Width/height aligned to 16 |
| Distilled FLUX.2-klein | euler/flux2, CFG=1, 1–4 steps, negative conditioning disabled | Width/height aligned to 16 |
| Qwen-Image 2.1 | euler/flux, normal CFG and negative conditioning | Width/height aligned to **32**; upstream resolution-aware schedule |
| Wan 2.1 T2V | euler/discrete, default CFG=6 and flowShift=3 | Dimensions aligned to 16; **4n+1** frames, 5–129; fps 1–60 |

Step limits, dimensions 64–2048, fps and flowShift ranges are current recipe/application guards, not official architectural maxima or measured phone budgets. Editable presets normalize values: Wan 18 frames becomes 17; Qwen width 1008 becomes 992. Settings remain per model. A separate `diffusionPlan` stores effective task values and reasons without overwriting the base model's saved profile.

All four routes bind `flowShift` to `sd_sample_params_t.flow_shift`. **0 means automatic**, mapped natively to upstream's INFINITY sentinel, rather than a literal zero shift. Nonzero values are bounded by 32. Z/FLUX/Qwen default to automatic; Wan defaults to 3. Persisted JSON contains finite numbers only. Native code independently checks sampler, scheduler, negative conditioning, dimensions and frame counts.

After loading, native routing checks tensor-family names: Z-Image, Flux.2 klein, Qwen Image 2.1 and Wan 2.x. **Family checks cannot prove Turbo training, 4B versus 9B, or Wan 1.3B/14B/2.2 identities sharing the same family.** Exact component provenance/revisions/hashes and real execution evidence remain necessary; a template cannot grant device-verified status.

Wan calls `generate_video()` for motion frames. Returned frame count/fps must equal the effective request before Android MediaCodec/MediaMuxer encodes MP4 on the same phone. Duplicate static frames do not complete a motion-video task. The generation library retains all returned frames; private RGB staging and MP4 also consume disk. The 512×288/17-frame preset does not establish whole-pipeline phone feasibility. Codec behavior, cancellation and playable artifacts still require device validation.

## Checks and evidence limits

- 174 diffusion assertions: 117 production-Java/actual-host-child protocol checks and 57 executions of the shared C++ policy. Coverage includes every missing dependency, conflicting/extra components, derived parameters, leased asset paths/vocabulary environment, tampered plans, sampling and geometry.
- Children write protocol JSON, never model images. The host Wan codec port deliberately rejects encoding; it cannot establish MP4 generation. No model tensors execute.
- Foundation 425 checks (233 recipe/integrity), UI 203, native Windows NDK ARM64 compilation and signed-package checks pass. Captures are explicit UI FIXTUREs, without Android installation evidence.
- Exact-target device outputs, quality, resource measurements, three load/unload cycles, screen-off/endurance, Android codecs and upgrades remain incomplete. MNN/audio/old-LTX and other mandatory pipelines remain in this same release scope; no reduced Release is created.

## Primary source mapping

Behavior was checked against pinned sd.cpp commit `be486498eadc29dc3cd234d944c2180ed42b1415`: [Z-Image](https://github.com/leejet/stable-diffusion.cpp/blob/be486498eadc29dc3cd234d944c2180ed42b1415/docs/z_image.md), [FLUX.2](https://github.com/leejet/stable-diffusion.cpp/blob/be486498eadc29dc3cd234d944c2180ed42b1415/docs/flux2.md), [Qwen 2.1](https://github.com/leejet/stable-diffusion.cpp/blob/be486498eadc29dc3cd234d944c2180ed42b1415/docs/qwen_image_2.1.md), [Wan](https://github.com/leejet/stable-diffusion.cpp/blob/be486498eadc29dc3cd234d944c2180ed42b1415/docs/wan.md). Sampling defaults and family names come from `src/model/integrations`; frame alignment comes from `src/pipeline/diffusion_engine.cpp`.

Each selected model/component retains its own license. In particular, the [Qwen-Image 2.1 model card](https://huggingface.co/Qwen/Qwen-Image-2.1) identifies Qwen Research License; older Qwen-Image Apache descriptions do not apply automatically. The App's code license does not grant rights to model weights.

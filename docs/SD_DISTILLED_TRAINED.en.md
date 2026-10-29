# SD-Turbo and the standalone LCM checkpoint: trained-weight validation

[中文](SD_DISTILLED_TRAINED.md) · [Diffusion foundation](DIFFUSION_ENGINE.en.md) · [Paired adapters / LCM-LoRA](SD_VARIANTS_TRAINED.en.md) · [Numbered work and full pending scope](releases/v0.3.0-dev.24-sd-distilled.md)

Follow-up: [small native LCM preparation](LCM_LOCAL_PREPARATION.en.md), with trained source preparation and small-component native output. The new C++ candidate fails its preset pixel maximum (8 > 5), remains unintegrated, and does not close quality, canonical pipeline or phone gates.

This follow-up executes independent SD-Turbo and LCM checkpoints on native Windows CPU using unchanged production C++, vocabulary code and Java binding. SD-Turbo completes the production HF composition/import/inference path. LCM investigation identifies a conversion omission, validates a fixed-guidance fold and produces actual native PNGs. These are scoped host observations and a developer derivation; quality, canonical image-pipeline equivalence, phone resources and endurance remain unaccepted. The APK stays **0.3.0-dev.24 / code28**, with unchanged production sources, APK inputs and bytes. This is not a reduced v0.3.0 release.

## 1. User selection, acquisition and management

The App delivers the foundation; users control model assets. Installation, upgrade, discovery and missing-component tasks start no model download. Developer reference UNet weights, the derived checkpoint, Python and the test coverage collection are not user prerequisites. Every product inference stage must execute on the same Android phone, without ROOT, external execution or hidden fallback.

1. Open `Green-Sky/SD-Turbo-GGUF` through Models → All/search, select the pinned `sd_turbo-f16-q8_0.gguf`, and choose **SD-Turbo · full checkpoint** in the existing component/recipe selector. Do not declare it as SD1.5, generic SD2 or SDXL.
2. Review revision, full file, licenses and dependencies. This checkpoint contains diffusion/text encoder/VAE weights but requires the external CLIP merges file. The two selected objects total **2,024,269,995 bytes**. This applies to this exact quantization; HF discovery does not establish universal execution compatibility.
3. Adding it to Local registers metadata only. Explicitly confirm download, or import a folder using the displayed `model/...` and `clip_merges/...` paths. Local retains separate pause/resume, settings, update/rollback and deletion controls.
4. Settings belong to each model, with editable presets and clamping. This recipe requires **1–4 steps, CFG1, Euler ancestral/discrete and an empty negative prompt**; this experiment uses 512×512. The application guards of2048 pixels/64threads do not promise model quality or Z20 resource fit.
5. Execution retains immutable settings/component leases. Caller mutation cannot change a queued request; active models cannot be deleted. Error/cancellation releases the actual child/private request; retry remains explicit.

Models remain peers, with separate task, dependency, architecture, backend, format and evidence tags. Recommended stays `m08 → m06 → m01`. Successful import/inference never grants an uncensored label; that requires separate attributed evidence. The [SD-Turbo JSON](../research/sd_distilled_trained/sd_turbo_q8_0.json) is a developer metadata reference; ordinary users use the existing HF selector.

The standalone LCM checkpoint and LCM-LoRA remain separate targets. No product repair or recommendation is claimed for the incomplete LCM conversion; an existing LCM template does not validate these particular weights. The reference F32 UNet is developer-only and is never automatically fetched for a user.

## 2. Immutable assets and licensing scope

| ID | Publisher / file | Bytes | Revision |
| --- | --- | ---: | --- |
| A01 | [Green-Sky SD-Turbo GGUF](https://huggingface.co/Green-Sky/SD-Turbo-GGUF), `sd_turbo-f16-q8_0.gguf` | 2,023,745,376 | `19a31586d02d64a73b4419bc193b3ecfaf38e1f0` |
| A02 | [Steward LCM DreamShaper GGUF](https://huggingface.co/Steward/lcm-dreamshaper-v7-gguf), `LCM_Dreamshaper_v7-f16.gguf` | 2,134,675,232 | `ae3fa73e105d5f848a4ef122e2ce14c92123bf1a` |
| A03 | [Original LCM DreamShaper](https://huggingface.co/SimianLuo/LCM_Dreamshaper_v7), `unet/diffusion_pytorch_model.safetensors` | 3,438,495,328 | `a85df6a8bd976cdd08b4fd8f3b73f229c9e54df5` |

The three developer objects total **7,596,915,936 bytes**; existing external CLIP merges add524,619 bytes. The [asset lock](../research/sd_distilled_trained/assets.json) records immutable URLs, whole SHA-256, attribution and license metadata. No original/derived weights or tokenizer payload enters Git, the APK or source attachments.

The SD-Turbo quantizer declares `other / stability-ai-community-license-agreement` and links the [original SD-Turbo license](https://huggingface.co/stabilityai/sd-turbo/blob/main/LICENSE.md). A quantizer declaration does not replace base terms. The LCM GGUF has no license metadata; the original UNet declares MIT, while DreamShaper/SD1.5/base-component obligations still need separate review. Complete license review remains open; availability is not a redistribution grant.

## 3. Missing LCM condition and fixed-guidance candidate

The original UNet has **687 tensors /859,602,884 F32 parameters**, including `time_embedding.cond_proj.weight` with shape `[320,256]` and81,920 nonzero values. The conversion maps only686 UNet tensors. All **859,520,964 mapped values** exactly match the original cast to their F16/F32 types, including the unchanged first time-MLP bias: zero mismatching tensors. The missing condition was neither retained nor pre-folded in this conversion.

SHA-pinned official time/guidance embedding functions produce the fixed guidance **8.5** condition. Folding before SiLU gives `b0' = b0 + W0 × Wcond × guidance_embedding(8.5−1)`. **Distilled guidance8.5 and sampler CFG1 are distinct values**; changing the current UI CFG to8.5 cannot repair the omitted branch.

The private candidate copies the entire GGUF and changes only a **5,120-byte bias region**, with4,987 actually different bytes. Other bytes and file length remain identical; originals are preserved. Candidate SHA-256 is `a307d7a72384ece75380ac91c0fe2d012dc9599c95224e1a5abe2a0bfaa6d298`. This2.13GB derivation is not bundled or implemented as product preparation. An explicit phone-side preparation/provenance/lifecycle path remains necessary; a small tensor overlay should be evaluated to avoid whole-checkpoint duplication.

The complete trained UNet runs **30 forwards**: five groups × six timesteps0/1/249/499/749/999, deterministic synthetic latents/text conditioning, reduced8×8/16×16 latent geometry and one CPU thread. Original-F32 folded/conditioned and converted-F16-cast folded/conditioned pairs both pass the predeclared `max≤2e−4 / RMSE≤5e−5 / cosine≥0.99999` gates. All six omitted-branch controls exceed the maximum-error gate.

| 对照 / Comparison | 最大绝对误差 / Max abs | 最大 RMSE | 最低 cosine |
| --- | ---: | ---: | ---: |
| `omitted-branch-vs-original` | 0.04063150287 | 0.01091605851 | 0.99988382767 |
| `f32-folded-vs-conditioned` | 8.165836334e-06 | 1.892911665e-06 | 0.999999999996 |
| `converted-conditioned-vs-original-f32` | 0.002236783504 | 0.000672562832 | 0.999999368979 |
| `converted-folded-vs-converted-conditioned` | 7.152557373e-06 | 1.755699476e-06 | 0.999999999996 |

The reference uses a SHA-pinned isolated diffusers0.42.1 source wheel and guidance functions from pinned0.22.0, with no global installation, model download or network attempts. This is a complete UNet comparison at reduced geometry, **not equivalence of the complete canonical512 image pipeline**. Actual native/official0.22.0 scheduler execution matches at1/2/5/7steps and differs at3/4/6/8steps. Four-step timesteps are `999/759/499/259` and `999/759/519/279`. This is a version observation, not proof the native scheduler is wrong or permission to relax acceptance; the intended full reference, boundary handling, RNG and sampler still require comparison.

## 4. Actual outputs, errors, cancellation and recovery

Production worker/external-vocabulary C++ remains unchanged, pinned sd.cpp `be486498…` /ggml `a5915eb0…`, CPU only. Windows replaces only parent-lifetime handling. SD-Turbo1/4steps and LCM checkpoint4steps use512×512, seed42, six threads, CFG1, no LoRA, empty negative prompt and the same fox/blue-teapot/wooden-table prompt.

| 任务 / Job | Steps | 含加载秒 / Seconds incl. load | 主机峰值 WS / MiB | PNG SHA 前12位 / Prefix |
| --- | ---: | ---: | ---: | --- |
| SD-Turbo / `one-step` | 1 | 103.128 | 1956.9 | `fcb9a5ae36e5` |
| SD-Turbo / `four-step` | 4 | 180.114 | 1957.0 | `5845daae68c1` |
| SD-Turbo / `recovery` | 4 | 189.637 | 1957.0 | `5845daae68c1` |
| LCM checkpoint / `converted-original` | 4 | 156.448 | 2054.9 | `7d25b2edc3d6` |
| LCM checkpoint / `fixed-guidance8p5` | 4 | 195.736 | 2055.9 | `3565db6b8185` |
| LCM checkpoint / `recovery` | 4 | 318.797 | 2055.2 | `3565db6b8185` |

The two suites run **ten native children /six PNGs**, including invalid-CFG rejection, actual sampler-step1 termination and recovery. SD-Turbo1/4steps differ; LCM original/folded outputs differ; each recovery reproduces its respective four-step PNG exactly. Windows termination timing is separate from Android cooperative cancellation; generating-stage entry is never labelled a sampler step.

Production Java completes **60 flow checks + 20 binding checks, one real HF composition, two full-object imports, five actual workers /three PNGs and zero network calls**. Coverage includes clamping/isolation, immutable requests, leases, pre-launch negative-prompt rejection, native errors, generating-stage-entry cancellation, recovery and ordinary restart. All three PNGs equal their matching direct native outputs byte-for-byte; Java cancellation makes no sampler-step claim.

This host test invokes production recipes/storage/settings/SdEngine directly; it does not execute Android Activity, LocalJobs Service or the local API. The existing Windows functional metadata port tests atomic replacement/ordinary restart and **omits metadata fsync**. It does not validate Android AtomicFile, power-loss durability, SAF, Service or screen-off execution. Production full model-file copy/sync/SHA verification still executes. Host elapsed times/working sets are non-exclusive observations, not Z20 measurements or benchmarks.

Visual review finds recognizable fox/blue vessel/wood in SD-Turbo1step, with a floating/deformed handle;4steps improve subject clarity but retain cropped spout/detail concerns. Both original and folded LCM images have conspicuously blurred fox faces and unreliable blue-teapot details. **Image quality is not accepted.** Numerical folding and pixel differences cannot replace prompt/subject/color/artifact review.

![Actual SD-Turbo host outputs](media/development/sd-distilled-sd-turbo-contact-sheet.png)

![LCM conversion and private fixed-guidance candidate](media/development/sd-distilled-lcm-checkpoint-contact-sheet.png)

![Actual PNG still slideshow; not a phone recording](media/development/sd-distilled-trained-slideshow.gif)

[MP4 still slideshow](media/development/sd-distilled-trained-slideshow.mp4) · [Original/media hashes](media/development/sd-distilled-trained-media.json). Four PNG originals are copied byte-for-byte. GIF4frames /MP4 88frames at10fps both last8.8seconds. These are labelled host-image slides; the previous68 UI fixtures/recordings keep their original scope.

## 5. Developer audit and remaining product work

Independent audit passes **89 retained capture files, ten direct native + five Java/native children, nine actual generated PNGs,30 UNet arrays, four complete originals /two full imported objects and one derived checkpoint**. It recomputes array errors, byte-compares the derivation outside the exact bias region and rehashes whole objects; all eight incorrect-evidence controls are rejected. Public records cover [assets](../verification/development/sd-distilled-assets.json), [native execution](../verification/development/sd-distilled-native.json), [LCM numerical analysis](../verification/development/sd-distilled-lcm-analysis.json), [Java binding](../verification/development/sd-turbo-app-host.json) and [independent audit](../verification/development/sd-distilled-capture-audit.json), with shared [development status](../verification/development/status.json). Complete target/quality/Android/Release flags remain unaccepted.

```powershell
python tools/fetch_sd_distilled_trained.py --download
python tools/replay_sd_turbo_native.py --execute
python tools/test_sd_turbo_app_host.py
python tools/check_sd_distilled_evidence.py
python tools/export_development.py
python tools/check_repository.py --development
```

These are developer commands requiring native tools, explicitly acquired complete weights/existing CLIP merges and corresponding experiment inputs. Acquisition verifies only by default; `--download` permits explicit developer retrieval. SD-Turbo replay retains earlier captures and never downloads. Java imports whole files again and compares actual native outputs. The full audit also requires retained LCM captures,30 raw arrays, reference sources/wheel and the derived candidate; missing experiment data cannot be replaced by passing declarations.

[Ten original experiment snapshots](../research/sd_distilled_trained/experiments/README.md) preserve execution bytes/historical paths. LCM coordination waits/reference inputs require the developer layout; this is not an installable phone repair. Required product work includes explicit phone preparation/small bias assets/provenance, versioned full sampler comparison, quality/resources and actual Android/endurance validation. LCM-LoRA cannot substitute for the standalone checkpoint, and no developer candidate may become an APK-bundled model.

The single next release still includes F01–F12, existing text, selections01–14/16/17 and every frozen subtarget; see [full numbered pending scope](releases/v0.3.0-dev.24-sd-distilled.md). No Android phone is currently available. Three load/unload cycles per model,15-minute screen-off, one-hour API, upgrade and A1–A11/R01–R05 remain open. No complete Release is created. No Docker/WSL/VM/emulator or browser UI tabs were used.

# Local Wan video

dev.40 adds per-model 128–1024-pixel spatial tiles and experimental temporal decoding, with existing-installation and legacy-job compatibility. Defaults remain128 / temporal off. Five full-geometry experiments and the unchanged official CPU VAE retain the later artifacts. [Settings, resource observations and quality diagnosis](WAN_DECODER.en.md).

[中文](WAN_VIDEO.md) · [English README](../README.en.md) · [Complete release scope](MULTIMODAL_RELEASE_PLAN.en.md)

LMA adds an optional Wan 2.1 T2V 1.3B Q4 model alongside text, image and audio peers. Its tags identify video/text-to-video and the Vulkan diffusion / CPU text and VAE foundation. App updates supply the runtime only. Users explicitly choose, download or import all four components; browsing, installation and upgrades never fetch weights.

The route reuses model management, independent settings, immutable jobs, cancellation, artifacts and provenance. It adds no ComfyUI canvas, user nodes, plugins or external inference provider. Existing CPU recipes, user assets and saved jobs retain their identities.

## 1. User flow

1. Open **Models → All → Video** and choose **Wan 2.1 · 1.3B Q4 · 本地 GPU 视频**. Recommended keeps its original three entries and order.
2. Review all four files, approximately **4.74 GB**, publishers and licenses. Download begins only after your explicit action. Exact complete content hashes can reuse existing objects without implicitly installing a peer. Alternatively select files through HF search and the matching recipe, or explicitly import complete local files.
3. Manage the installation and paused transfers in **Local**. Models, independent settings and generated results have separate lifecycles; deleting a model does not automatically delete results.
4. Edit resolution, steps, frame count/rate, CFG, seed, threads and flow shift in that model's settings. Editable presets accept custom values and clamp values above declared ceilings. Execution preparation also applies Wan geometry and `4n+1` frame constraints.
5. Use the model, enter a prompt, acknowledge unmeasured resources and submit. Each job freezes model identity, complete component hashes and submitted settings. Later edits do not change queued jobs.
6. The shared task page exposes generation/encoding progress, cancellation, explicit errors, retries and results. Completed MP4s retain effective parameters, component provenance and actual backend observations. Native services own background work; screen-off endurance has no physical-phone acceptance in this checkpoint.

Recipe defaults are **512×288, 17 frames, 8 fps, 20 steps, CFG 6, Euler/discrete, flow shift 3 and VAE tiling**. These editable defaults do not guarantee performance or memory fit on a Nubia Z20. Development checks can explicitly choose 256×256 / 5 frames / 4 steps; small test outputs do not establish default quality.

## 2. Complete components

| Role | Pinned file | Complete bytes |
|---|---|---:|
| Diffusion | off-grid-ai/Wan2.1-T2V-1.3B-GGUF · Wan2.1-T2V-1.3B-Q4_K_S.gguf | 816,061,024 |
| Text encoder | off-grid-ai/Video-Companions-GGUF · umt5-xxl-encoder-Q4_K_M.gguf | 3,655,145,312 |
| VAE | Same companion repository · wan_2.1_vae.safetensors | 253,815,318 |
| Tokenizer | google/umt5-xxl · tokenizer.json | 16,853,013 |

Total: **4,741,874,667 bytes**. Immutable revisions, complete SHA256, canonical HF URLs and Apache-2.0 declarations are in the [asset lock](../research/wan_trained/assets.json), [optional catalogue descriptor](../research/wan_trained/catalogue-bundle.json) and [attribution](../research/wan_trained/NOTICE). Assets never enter Git or APKs. Filename hints assist selection; they do not prove architecture, content labels or phone compatibility. The 1.3B recipe excludes 14B names and never silently chooses between quantizations.

## 3. Execution on the same phone

`wan_sd_cpp` builds pinned sd.cpp/ggml: CPU UMT5 tokenization/encoding, `Vulkan0` diffusion and CPU VAE. Java passes actual generated RGB frames to that phone's Android MediaCodec/MediaMuxer for MP4 encoding. The route requires no ROOT or Termux and uses no RPC, off-device decoder or external media composition.

The Vulkan worker has a distinct identity from the existing `sd_cpp` CPU worker and rejects backend mismatches. Missing Vulkan produces an explicit local failure with no automatic CPU fallback. Results require observation of a completed GPU matrix operation in a non-host Vulkan buffer. A detected device name alone is insufficient. Actual backend observations are retained with result provenance.

Parameter ceilings are not a device resource budget. GPU drivers, memory, heat, latency and Android encoding require separate acceptance. No LMA Z20 device evidence exists, so this does not establish long-video or continuous background usability.

## 4. Reproduction and evidence boundaries

Run inside the repository with native Windows tools. No Docker, WSL, virtual machine or emulator is used.

```text
python tools/fetch_wan_trained.py
python tools/fetch_wan_trained.py --download --jobs 2
python tools/build_sd_vulkan.py --android --jobs 2
python tools/test_wan_trained.py
python tools/test_wan_app_host.py
python tools/render_wan_trained.py
node tools/capture_workbench.cjs wan
```

The first command verifies existing local files; only the second explicitly downloads. Inference uses no network. Operators may explicitly select a download mirror; receipts retain that transport origin and still require exact full-file hashes. Tests never fetch assets automatically.

Native checks use real prompts, parameter changes, actual sampler cancellation, errors and recovery, and require completed Vulkan computation and moving frames. Production Java checks cover complete offline import, object reuse, independent settings, leases, immutable jobs, actual children, results and restart/deletion. The Windows test-only encoder uses native FFmpeg and is explicitly **not Android codec evidence**. The APK retains the production Android encoder.

UI screenshots and recordings use production HTML with a labelled simulated bridge; they are neither phone captures nor inference evidence. Actual model frames/video are separate artifacts with original outputs and failures retained. Host execution, ARM64 compilation, independent numerics, quality, phone resources and formal Release are separate gates.

This remains work inside the single complete v0.3.0 scope. A descriptor or host video does not close target16. All frozen targets, original LCM/Sana/LTX failures and phone/release gates remain required.


## 5. 实际产物 / Actual artifacts

[实际默认配置视频 / Default host video](media/development/wan-trained/default.mp4) · [帧比较 / Actual frames](media/development/wan-trained/default-frames.png) · [页面录制 / UI recording](media/development/wan/wan-ui.mp4) · [完整编号交付 / Numbered delivery](releases/v0.3.0-dev.39.md)

![Actual Wan host output; not Android footage or generation timing](media/development/wan-trained/default.gif)

默认配置为一次明确标记的完整主机 smoke；小配置七场景及生产 Java 业务另外校验。Default output is a labelled complete host smoke; small-configuration scenario checks and production Java lifecycle checks are separate. Quality and phone acceptance remain pending.

Later frames of the actual default example show visible block artifacts. This is not a quality pass. All original frames and this issue are retained; numerical comparison and video quality fixes remain required inside the same complete v0.3.0 scope.


验证 / Validation: **22 suites /3,057 checks** =2,801 shared controls +117 tokenizer +39 complete native Wan +100 production Java. Signed development APK:61,325,834 bytes;35 native files;Lint0 errors /17 warnings. Actual host MP4 input frames match direct native output byte-for-byte. These checks do not accept video quality, physical Android or the complete Release.

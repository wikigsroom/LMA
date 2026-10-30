# Wan per-model decoder controls and quality comparison

[中文](WAN_DECODER.md) · [Complete video workflow](WAN_VIDEO.en.md) · [dev.40 delivery and full remaining scope](releases/v0.3.0-dev.40.md)

dev.40 connects per-model Wan decoder settings to native execution. The APK still supplies only the foundation; assets are explicitly selected, downloaded/imported and managed by users. The full v0.3.0 scope remains unchanged. Windows observations do not establish Android or complete Release acceptance.

## 1. User workflow

1. Choose the optional Wan 2.1 T2V 1.3B profile in All/video or a matching HF recipe, inspect all four components, and explicitly download/import. Browsing, settings and submission never initiate another implicit download.
2. In Local, edit that model's settings. **VAE spatial tile size** applies when spatial tiling is enabled. **VAE temporal decoding (experimental)** is independent. Other pipelines do not silently inherit it.
3. Tile size accepts **128–1024 pixels, aligned to 64**. An entered 999 becomes 960; a value above 1024 becomes 1024. Native execution separately rejects invalid direct requests. This ceiling is an application guard, not a claimed training limit.
4. Saving affects that model's future requests. Submitted jobs freeze complete parameters and component identities; later edits cannot change them. Per-model settings survive restart.
5. Temporal mode uses one latent time frame per chunk. It does **not guarantee less memory or corrected quality**.

Defaults remain **128 / temporal off**, preserving the previous memory policy. Engine schema augmentation exposes new controls for existing installations without rewriting user manifests, weights or frozen jobs. Legacy requests missing these fields retain the original native behavior; regression requires the exact corresponding dev.39 RGB SHA.

Shared native progress now forwards stage changes, the first completed step and terminal progress promptly while retaining throttling for intermediate updates. Actual Java/native cancellation exposed the missing-step bug; the production fix adds fast-child regressions without relaxing cancellation conditions.

## 2. Actual quality diagnosis

All five experiments use complete assets, 512×288, 17 frames, 8fps, 20 steps, CFG6 and seed42. Values below are native Windows observations, without measured GPU memory or phone resources; they are not a controlled performance benchmark. Quality is assessed from raw generated RGB, before MP4 composition.

| ID | Explicit decoder/sampling configuration | Observed time | Windows peak working set | Finding |
|---|---|---:|---:|---|
| Q01 | Original dev.39, 128 spatial tiles, temporal off, flow3 | 1012.16 s | 4,973,056,000 B | Later block artifacts; original retained |
| Q02 | Spatial/temporal off, flow3 | 440.46 s | 11,291,410,432 B | Artifacts persist |
| Q03 | Spatial off, upstream four-latent-frame temporal chunks, flow3 | 406.92 s | 13,261,283,328 B | Same RGB SHA as Q02 |
| Q04 | Explicit 512 tiles / one-latent-frame temporal chunks, flow3 | 317.46 s | 12,558,258,176 B | Same RGB SHA as Q02; not model defaults |
| Q05 | Q04 with flow8 only | 312.57 s | 12,561,133,568 B | Different output; artifacts persist |

These measurements do not justify increasing default memory demand on a Nubia Z20. The original full Q01 output and failed quality observations remain intact. Smaller test geometry or showing only the first frame cannot establish a fix.

A separate diagnostic captures the actual denoised tensor immediately before VAE decoding. It intentionally returns the worker's generation error and produces **no completed video**. The unchanged [official Wan VAE](https://github.com/Wan-Video/Wan2.1/blob/9737cba9c1c3c4d04b33fcad41c111989865d315/wan/modules/vae.py) then decodes that tensor with the same complete weights, strict loading and CPU F32. Against Q02, every frame/channel differs by at most **one 8-bit level**, with mean absolute byte error about **0.4951**. It reproduces the later artifacts. Decoder tiling and MP4 composition do not explain this sample. This does not identify whether sampling implementation, quantization, component pairing or model behavior at this resolution is responsible; full generator numerics and quality remain unresolved.

![Same actual latent: C++ above, official CPU VAE below; both quality unaccepted](media/development/wan-quality/vae-comparison.png)

[Original failed-quality GIF](media/development/wan-quality/legacy-default.gif) · [Original MP4](media/development/wan-quality/legacy-default.mp4) · [Complete diagnosis](../verification/development/wan-quality.json)

## 3. Reproduction and evidence scope

`tools/probe_wan_quality.py` explicitly runs full-geometry experiments without downloads. `tools/build_wan_latent_probe.py` adds one diagnostic seam to a build-only copy; pinned upstream sources stay pristine. The diagnostic is neither registered nor packaged. `tools/probe_wan_latents.py` provides `--capture` and `--decode`, requiring explicitly prepared pinned official sources, isolated Python dependencies and matching weights. Normalization comes from the original wrapper; shapes, strict weights and output identities are checked.

Seven original reports are archived byte-for-byte in [research evidence](../verification/research/wan-quality/), retaining compilation identities, parameters, output hashes, logs and observed resources. Current aggregation does not relabel earlier experiments as current APK inference checks. Complete RGB/latent/process logs remain in ignored development directories. Weights, dependency caches and reference assets enter neither Git nor APK.

Actual native checks cover exact legacy output, invalid tile rejection, changed prompts/steps, sampler cancellation and recovery. Production Java checks cover explicit import, persistent settings, immutable jobs, real model children and two MP4s whose encoder inputs match native RGB exactly. Windows FFmpeg is an explicit host test port; same-phone Android MediaCodec, endurance, resource fit and quality still require their own acceptance.

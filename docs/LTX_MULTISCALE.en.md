# Old LTX 0.9.8: original PixArt T5 and multiscale

[中文](LTX_MULTISCALE.md) · [Implementation](IMPLEMENTATION_V030.en.md) · [Program validation](PROGRAM_VALIDATION.en.md)

v0.3.0 adds the original PixArt F32 T5 and multiscale program route for selection 17. The existing Google T5 Q5 single-scale route retains its own identity, settings and history. Validation is program-only: no complete trained model, quality acceptance or phone resource measurements.

## Explicit user asset acquisition

1. Explicitly import/download the pinned `ltx098_source_r8984fa2` source bundle.
2. Run `ltx098_dit_vae_v1` locally on user-owned source weights. The APK supplies programs and architecture, without model data or automatic retrieval.
3. Choose `ltx098_pixart_generation_v1` to associate the 20 prepared DiT/VAE components with `ltx098_runtime_pixart_multiscale_v1`, preserving source identities and reusing data.
4. Review and explicitly download/import the seven remaining dependencies: T5 config, shard index, two original F32 shards, tokenizer config, SentencePiece file and learned spatial upsampler. The download action remains unavailable when non-downloadable prepared components are missing.
5. After all 27 components pass validation, save per-model settings in Local and submit a video task. Preflight explains missing assets and unknown resources; there is no silent model substitution or off-device execution.

Runtime assets total **25,616,311,982 bytes: about 23.86 GiB / 25.62 GB**. The original T5 shards alone occupy about 17.74 GiB. Source and preparation temporaries need additional storage. Direct mapping avoids another converted T5 copy; it does not establish sufficient RAM or Z20 suitability.

## Pinned identities

| Source | Revision | Purpose |
| --- | --- | --- |
| PixArt-alpha/PixArt-XL-2-1024-MS | `b89adadeccd9ead2adcb9fa2825d3fabec48d404` | Original T5 config, index, two F32 safetensors and tokenizer resources |
| Lightricks/LTX-Video | `8984fa25007f376c1a299016d0957a37a2f797bb` | Old distilled source and 505,024,432-byte spatial upsampler |

Exact sizes, SHA256 values and header identities are in the [metadata lock](../third_party/ltx098-official/identity.json), [bundle catalogue](../catalogue/model-bundles.json) and [dedicated validation spec](../app/src/main/java/com/lma/app/core/LtxPixArtSpec.java). This work retrieved only bounded headers, small configs and tokenizer metadata, not complete weights. LTX-Video Open Weights 0.x and PixArt OpenRAIL++ terms remain separate from LMA's MIT license.

## Sequential stages on the phone

| Stage | Behavior |
| --- | --- |
| 1 | First dimensions are requested dimensions × 0.6666666, floored to a multiple of 32; initialize deterministic noise |
| 2 | CPU directly maps both original F32 T5 shards, with original SentencePiece, extra tokens, EOS and attention masking |
| 3 | Vulkan DiT: seven steps at sigma 1, .9937, .9875, .9812, .975, .9094, .725; final step targets zero |
| 4 | Unpatchify into 128-channel latents |
| 5 | One CPU ORT upsampler session: VAE channel denormalization → learned spatial 2× upsample → normalization → channel AdaIN with unbiased standard deviation; close the session |
| 6 | Renoise at .9094 and prepare separate VAE decoding noise |
| 7 | Vulkan DiT: three refinement steps at .9094, .725, .4219; final step targets zero |
| 8 | Unpatchify refined latents |
| 9 | Nine-stage CPU VAE with timestep .05 and decode noise .025; release stages sequentially |
| 10 | Clamp decoded values to [-1,1] before align_corners=false bilinear resizing; Android MediaCodec encodes AVC MP4 |

CFG=1, STG=0, direct prompt encoding. Optional prompt enhancement models are not downloaded implicitly. LMA's deterministic random stream does not promise PyTorch/upstream same-seed byte identity. Output width/height: 128–256 in multiples of 32; frames: 9–33 with 8n+1 alignment; fps 1–60; threads 1–8; exactly ten steps. These are supported application-profile bounds, not theoretical model limits.

The 22,474-byte ONNX resource contains architecture and structural constants only. All 72 learned tensors reference the user's original upsampler file as external data. APK validation regenerates the graph and checks exact bytes, references and absence of embedded learned values. Tasks lease components; failures/cancellation wait for owned children before workspace cleanup, without publishing partial artifacts.

## Program evidence

- 89 bounded checks cover original T5 layout/tokenization, random tiny T5 reference comparison, random small upsampler comparison, AdaIN, the unchanged upstream scheduler, noise and resizing. No complete trained weights.
- 280 production Java engine/queue assertions cover ten sequential stages, snapshots, failures, missing/duplicate receipts, cancellation, encoding errors and cleanup. Neural stages use explicit fixture ports; production descriptor validation rejects fixture files.
- The independent legacy single-scale route retains 127 program assertions, without merging numerical/quality outcomes.
- ARM64/API28 compilation, 16 KiB alignment, final APK inspection, 21 new page interactions, four screenshots, GIF and MP4. Recordings visibly identify the desktop UI fixture and close their browser.

[Current records](../verification/program/status.json) remain separate from historical failures. Following the user's instruction, this work does not continue complete-model, ASR, phone inference or prolonged screen-off tests. Quality, speed, resources and device acceptance remain unverified.

# Old LTX F32 operation staging

[中文](LTX098_STAGING.md) · [Original precision diagnosis](LTX098_PRECISION.en.md) · [Full chain](LTX098_PIPELINE.en.md) · [Numbered handoff and full pending scope](releases/v0.3.0-dev.23-ltx-staging.md) · [Complete same-version scope](MULTIMODAL_RELEASE_PLAN.en.md)

This source follow-up implements explicit F32 grouped RMS reduction and original GeGLU operation order, with actual trained host A/B/A chains. The candidate's unchanged original float/RGB gates report **FAIL**. Reference forwards, external weights and thresholds remain unchanged. The existing native baseline retains its earlier 157/163 passing checks and six failures; promotion and all required regression remain pending.

App updates deliver the foundation; users choose/download/import every model and dependency. These offline developer executables are unregistered and unpackaged. The signed package remains `0.3.0-dev.23 / code 27`, public v0.2.0 stays available, and complete v0.3.0, Android inference, quality/resources and endurance remain open.

## Operation staging

1. GeGLU computes the F32 cubic term before multiplying its coefficient, then retains each original F32 add/tanh/product stage. The former coefficient-first multiplication has different rounding.
2. RMS squares in F32 and sums eight lanes/four streams in groups of sixteen. Mean, epsilon, reciprocal square root and the two products retain F32 rounding. The scalar C++ implementation reproduces the reviewed width 4096 without x86 instructions; other widths and Android compilation/numerics need their own checks.
3. Dense projections and attention retain the previous isolated F64 accumulations. Stage tensors remain F32. All 219 trained T5 tensors, 4,762,310,656 parameters, external GGUF, tokenizer results and equations stay fixed.

The grouping was checked against [PyTorch v2.14.0 CPU sum](https://github.com/pytorch/pytorch/blob/v2.14.0/aten/src/ATen/native/cpu/SumKernel.cpp). Preserved trained intermediates produce 48 mean tensors/2,544 bit-identical values and 24 bit-identical activation-order comparisons: 72 local comparisons. Mean analysis simulates grouping in NumPy; activation-order analysis uses Torch. These are separate from actual native full-model or phone acceptance.

## Actual host results

Each of four new T5 candidates ran three trained A/B/A jobs, 12 total, with real load/unload and identical repeated A bytes. Higher precision does not automatically match the original F32 reference; every result remains visible.

| Candidate | A caption max abs | B caption max abs | Actual trained jobs |
| --- | --- | --- | --- |
| F64 RMS + F64 GeGLU | 1.66893005371e-05 | 1.19209289551e-06 | 3 / bitwise A/B/A |
| F64 RMS + ordered F32 GeGLU | 1.01029872894e-05 | 1.43051147461e-06 | 3 / bitwise A/B/A |
| Baseline RMS + ordered F32 GeGLU | 4.94718551636e-06 | 1.19209289551e-06 | 3 / bitwise A/B/A |
| Staged F32 RMS + ordered F32 GeGLU | 2.38418579102e-06 | 1.19209289551e-06 | 3 / bitwise A/B/A |

The final candidate then feeds native embeddings into three independent DiT/decode chains with fixed real prompts/seed: 256×256, 33 frames, 24 fps, eight steps, single-scale Google/community Q5 T5. Each chain runs native seeded noise, layout restoration, the complete nine-graph trained VAE, RGB packing and host FFmpeg. No reference tensor feeds a native generation stage.

| Job | Latent max abs | Latent relative RMSE | Decoded max abs | Decoded relative RMSE | RGB max / mean | Gates |
| --- | --- | --- | --- | --- | --- | --- |
| A | 0.00260734558105 | 0.000125466615603 | 0.00119844079018 | 5.84066037162e-05 | 1 / 0.00196622598051 | PASS |
| B | 0.0127477049828 | 0.000665280217877 | 0.0156812220812 | 0.000527671740951 | 2 / 0.00814295296717 | FAIL |
| A repeat | 0.00260734558105 | 0.000125466615603 | 0.00119844079018 | 5.84066037162e-05 | 1 / 0.00196622598051 | PASS |

Frozen gates: max absolute error ≤ 0.003, relative RMSE ≤ 0.0003, cosine ≥ 0.99999; RGB max ≤ 2 and mean ≤ 0.02. Caption, token latent, NCTHW latent, decoded float and RGB are checked separately. Repeated A latents, decoded arrays and every RGB frame match bitwise.

A reviewer field-name error occurred after the first sampling child completed. Recovery verifies its binary, model, request, log and 11 files and records reuse. The recovery invocation executes **14** new native children; together with that retained sampler this gives 15 sampling/decode-stage children plus the final candidate's three T5 runs. Three actual trained VAE children each load/unload nine graphs. Resource data is host child observation; GPU memory is unmeasured.

![Measured actual-host numeric errors](media/development/ltx098-staging-errors.png)

![Actual host frames: baseline / candidate / original forward](media/development/ltx098-staging-frames.png)

[Actual host video](media/development/ltx098-staging-comparison.mp4) · [GIF](media/development/ltx098-staging-comparison.gif). Media is explicitly HOST ONLY. Numerical agreement establishes neither semantic/motion quality nor Android usability. Original unquantized Google/PixArt identities, official multiscale defaults and prompt enhancement remain unaccepted.

## Independent sampler diagnosis

Five separate native eight-step case-B diagnostics use the exact same original reference caption, noise and trained weights to distinguish conditioning drift from sampler error. Reference tensors deliberately condition these diagnostics; they never count as the native-T5 full-model chains above. Each actual native child retains eight latent traces, final output, request, log, executable identity and host resource samples.

The pinned CPU backend converts the right-side F32 activation to F16 through `vec_dot_type=F16` for an F16 weight matrix, despite the existing accumulation policy. An isolated candidate explicitly casts both operands to F32 before `ggml_mul_mat`. A second CPU-only candidate adds staged F32 grouped reduction to DiT Q/K and block RMS. Source weight files, equations and gates are fixed. The [pinned GGML CPU source](https://github.com/ggml-org/ggml/blob/a5915eb0e47adef21c3f25b889a008925ea838c2/src/ggml-cpu/ggml-cpu.c) matches the locked local code.

| Sampler diagnostic | Latent max abs | Relative RMSE | Cosine | Native seconds | Latent gates |
| --- | --- | --- | --- | --- | --- |
| Original CPU | 0.788247942924 | 0.0505370007584 | 0.998722860265 | 109.441 | FAIL |
| Original Vulkan | 0.00779688358307 | 0.000416970937671 | 0.999999913106 | 9.502 | FAIL |
| Explicit F32 CPU | 0.00511467456818 | 0.000285841148193 | 0.999999959164 | 133.567 | FAIL |
| Explicit F32 Vulkan | 0.00779688358307 | 0.000416970937671 | 0.999999913106 | 560.564 | FAIL |
| Explicit F32 + staged RMS CPU | 0.00590533018112 | 0.000333848676232 | 0.999999944295 | 574.886 | FAIL |

Seconds include native child loading and host I/O; they are not directly comparable inference benchmarks. During disk contention in the final CPU RMS diagnostic, a separate sequential read of the same fixed weights improved caching. All 3,849,516,416 bytes were rehashed against the fixed SHA256 identity. That read changed no model/program and is not counted as model execution.

Explicit inputs reduce the CPU conversion error without closing full-model gates. The Vulkan result matches its original diagnostic; CPU improvement cannot be assumed for other backends. Host working-set/private-memory samples establish neither peak VRAM, Android memory use nor performance promises.

The five public records under `verification/development/` are `ltx098-context-reference-{cpu,vulkan}.json`, `ltx098-compute-f32-reference-{cpu,vulkan}.json` and `ltx098-compute-f32-rms-reference-cpu.json`. All retain `diagnostic_only=true`; model, video, App, Android and Release acceptance remain separate and incomplete.

## Reproduction and evidence

Use native Windows, reviewed MSVC/CMake/Ninja and existing offline developer assets. Experiment code stays in `research/ltx098_text_accuracy/`, `ltx098_text_order/`, and `ltx098_text_f32/`. Records bind sources, compilation dependencies, binaries, output identities, measurements and actual child resources. Weights, raw intermediate arrays and caches remain ignored under `build/`.

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONIOENCODING='utf-8'
$env:TEMP="$PWD/build/tmp"
$env:TMP="$PWD/build/tmp"
# Existing pinned developer assets/reference; no implicit acquisition.
python tools/analyze_ltx098_staging.py <preserved-trained-intermediate-directory>
python tools/experiment_ltx098_text_accuracy.py --reference <original-reference> --activation-f64
python tools/experiment_ltx098_text_order.py --reference <original-reference>
python tools/experiment_ltx098_text_staging.py --reference <original-reference> --normalization baseline
python tools/experiment_ltx098_text_f32.py --reference <original-reference>
# Native host FFmpeg must be on PATH for the complete developer chain.
python tools/test_ltx098_accuracy_trajectory.py --variant f32 --reference <original-reference>
python tools/diagnose_ltx098_sampling_context.py --reference <original-reference> --case 1 --context reference --backend cpu
python tools/diagnose_ltx098_sampling_context.py --reference <original-reference> --case 1 --context reference --backend vulkan
python tools/diagnose_ltx098_compute_precision.py --reference <original-reference> --case 1 --context reference --backend cpu
python tools/diagnose_ltx098_compute_precision.py --reference <original-reference> --case 1 --context reference --backend vulkan
python tools/diagnose_ltx098_compute_precision.py --reference <original-reference> --case 1 --context reference --backend cpu --staged-rms
python tools/export_development.py
python tools/render_ltx098_staging.py --reference <original-reference>
python tools/check_repository.py --development
```


`--initial-sampling` explicitly recovers a completed first stage. `--review` revalidates a complete saved A/B/A and records zero newly executed children. Public records comprise `verification/development/ltx098-staging-analysis.json`, four `ltx098-accuracy-*.json` candidates and `ltx098-accuracy-trajectory-f32.json`. Repository auditing recomputes gate flags and checks provenance; the plot/GIF/MP4 have a separate source-hash media receipt.

Repairing the remaining text/sampler numerical failures, production promotion, required native regression and Android candidate compilation come next, followed by user-controlled T5 acquisition, same-phone encoding, quality/resources and endurance. F-01–F-12, existing text and 01–14/16/17 remain one complete release; see the [full pending table](releases/v0.3.0-dev.23-ltx-staging.md).

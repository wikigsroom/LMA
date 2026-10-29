# Old LTX text precision investigation

[中文](LTX098_PRECISION.md) · [Complete prompt pipeline](LTX098_PIPELINE.en.md) · [Numbered handoff](releases/v0.3.0-dev.21-ltx-precision.md) · [Full scope in this version](MULTIMODAL_RELEASE_PLAN.md)

The old LTX 0.9.8 original-forward pipeline comparison still records **157 passed checks and six failed float gates out of 163**. This update adds reproducible intermediate diagnostics and isolated precision candidates. It preserves the accepted model source, original reference forwards, frozen gates and APK. Diagnostic comparison counts do not establish new model acceptance.

## Actual evidence

| No. | Item | Scope |
| --- | --- | --- |
| D-01 | 314 trained intermediate comparisons | Embedding, 13 observations in each of 24 blocks, final normalization; native and original Transformers outputs |
| D-02 | 628 hashed raw tensors | All byte sizes and SHA values verified; all 314 maximum-error and relative-RMSE values recomputed; arrays remain in ignored `build/` |
| D-03 | 120 matched-input operator comparisons | Two RMS norms, GeGLU, SDPA and eager attention per block; original Torch operators consume the exact captured native inputs |
| D-04 | Baseline identities | Instrumented native final embedding is byte-identical to the existing native output; original final embedding is byte-identical to the existing independent reference |

The capture uses prompt A's 53 tokens, all 219 trained tensors and the complete 24-block Google/community Q5 T5. Original Transformers selects `sdpa`. Hooks only save outputs, without replacing return values or rewriting equations. Existing reference hooks still page original block parameters.

The final embedding maximum error is `2.3752450942993164e-5`, with relative RMSE `1.5835138112703526e-6`, exactly matching the previous failed pipeline's text stage. Small text differences can grow along the full video trajectory; text-level accuracy cannot replace complete-chain comparison.

![Host text roundoff measurements; no App or phone acceptance](media/development/ltx098-text-roundoff.png)

The left panel compares native and original forward intermediates, including propagated differences. The right supplies identical native inputs to individual original operators. The logarithmic y axis is relative RMSE across each complete tensor, with 24 measured points. It is not a video-quality or phone-performance chart.

| Local matched-input comparison | Largest absolute error across 24 blocks |
| --- | --- |
| Attention input RMS norm | `7.152557373046875e-7` |
| FFN input RMS norm | `9.5367431640625e-7` |
| GeGLU | `7.62939453125e-6` |
| Attention mix versus original SDPA | `1.049041748046875e-5` |
| Attention mix versus original eager operator | `1.1444091796875e-5` |

These measurements do not identify one operator as the sole cause. Eager is an additional local diagnostic; it does not replace SDPA in the complete original oracle. They also do not establish unquantized Google or PixArt weight identity, official multi-scale defaults, semantic quality or motion acceptance.

## Isolated precision candidates

`research/ltx098_text_precision/` contains developer candidates, without App registration or APK packaging. Attention scores, stable softmax and value mixing use F64 intermediates before returning F32. Optional dense projections accumulate in F64, still consuming the same externally stored Q5 weights cast one matrix at a time to F32. Tokenization, weights, equations and complete-chain thresholds remain unchanged. A separate implementation identifier distinguishes candidates from the accepted encoder.

`tools/experiment_ltx098_text_precision.py` verifies existing trained assets and independent references, builds with native Windows tools and executes three complete real-prompt T5 jobs in A/B/A order. It records errors, resource observations, build dependencies, executable and output identities. Repeated A outputs must match byte for byte. **Completing text candidates does not establish complete video parity or Android compilation/execution.**

Both candidates completed three real trained T5 jobs, six total. Each A/B/A sequence is byte-reproducible. The comparison uses the same external quantized weights and original forwards, not unquantized-weight acceptance.

| Implementation | A embedding maximum error | B embedding maximum error | A/B/A bytes |
| --- | --- | --- | --- |
| Existing F32 baseline | `2.3752450942993164e-5` | `1.430511474609375e-6` | Identical |
| F64 attention candidate | `6.794929504394531e-6` | `3.814697265625e-6` | Identical |
| F64 attention + dense candidate | `2.86102294921875e-6` | `1.1920928955078125e-6` | Identical |

Attention alone increases B's maximum error; it does not improve every case. The combined candidate improves both measured embeddings, but its actual eight-step Vulkan A trajectory still fails the frozen gate:

| Partial A trajectory | Final latent maximum error | Relative RMSE | Original gate result |
| --- | --- | --- | --- |
| F64 attention | `0.003952622413635254` | `0.00018860916780748471` | Above `0.003`; failed |
| F64 attention + dense | `0.0038292407989501953` | `0.00018156580439107774` | Above `0.003`; failed |

Both probes verify the independent original eight-step oracle, original noise, candidate captions, complete trained DiT/Vulkan and per-step file identities. Public records explicitly reuse this round's actual captures. Review commands do not execute inference again and retain exit 1 after saving evidence. Candidate VAE, B video and video A/B/A were not executed. These partial results cannot close the six existing complete-chain failures.

Candidate evidence: [attention](../verification/development/ltx098-text-precision-attention.json) / [combined](../verification/development/ltx098-text-precision-linear.json); partial trajectories: [attention](../verification/development/ltx098-precision-sampling-attention.json) / [combined](../verification/development/ltx098-precision-sampling-linear.json).

## Reproduction and public scope

First prepare pinned local assets, native builds, real-prompt jobs and independent references using the [pipeline guide](LTX098_PIPELINE.en.md). These commands do not download models. Replace `CAPTURE` with the emitted capture directory below `build/`, and `REFERENCE` with the existing `original-reference` directory. Raw arrays are not committed.

```powershell
python -B tools/diagnose_ltx098_text.py build/ltx098-pipeline-probe/red-42
python -B tools/analyze_ltx098_text.py CAPTURE
python -B tools/review_ltx098_text_diagnosis.py CAPTURE
python -B tools/export_development.py
python -B tools/plot_ltx098_text_diagnosis.py
python -B tools/experiment_ltx098_text_precision.py --reference REFERENCE
python -B tools/experiment_ltx098_text_precision.py --reference REFERENCE --linear-f64
python -B tools/compare_ltx098_precision_sampling.py --variant attention --reference REFERENCE
python -B tools/compare_ltx098_precision_sampling.py --variant linear --reference REFERENCE
python -B tools/check_repository.py --development
```

Each raw capture/candidate uses a fresh directory, preserving old jobs, encoder and media. Public [intermediates](../verification/development/ltx098-text-diagnosis.json), [matched-input metrics](../verification/development/ltx098-text-operators.json), [recomputed evidence](../verification/development/ltx098-text-diagnosis-review.json) and [chart provenance](media/development/ltx098-text-roundoff.json) contain measurements and identities, without model weights or raw activations.

Retaining intermediates changes diagnostic memory. Candidate/check timings depend on host caches and concurrent audits and are not production benchmarks. Windows working sets are not VRAM, system or phone memory. No Android execution, long-input/all-language coverage, quality or endurance is established.

App updates still deliver only foundation code; users explicitly choose, download, import and manage every model asset. This update adds no external inference path, automatic model retrieval, ComfyUI user nodes or APK. `ltx098_t5_intermediate_diagnostic_executed=true` and `ltx098_t5_roundoff_repair_accepted=false` distinguish execution from accepted repair. Every frozen v0.3.0 target remains required in the same complete release.

# Old LTX 0.9.8: modulation-order diagnosis

[中文](LTX098_MODULATION.md) · [Previous staging experiments](LTX098_STAGING.en.md) · [Full scope](MULTIMODAL_RELEASE_PLAN.en.md)

A definite floating-point operation-order discrepancy is corrected in an isolated candidate, but **the complete sampler numerical gates still fail**. This is source work within the same v0.3.0. The candidate is unregistered and unpackaged, without new Android, video-quality or background acceptance.

## Observation and implementation

The publisher uses `x * (1 + scale) + shift` twice per Transformer block and at the output. The original isolated native implementation used `(x + x * scale) + shift`. They are algebraically equivalent but round differently in F32. The candidate preserves the publisher's staging and explicit F32 matmul operands. Original sources, weights, references and thresholds remain intact.

Two actual original trained forwards observe prompt B at steps 0 and 7. Each loads all 715 tensors /1,923,385,472 parameters using module paging and passively captures normalized values, scale, shift and the observed downstream inputs at 57 sites. The 456 arrays are retained. No original forward function is replaced. Both original forward/sampling outputs match the frozen trajectories bit for bit.

| Original step | Sites | Publisher staging exact | Reassociated differing elements /37,355,520 | Maximum absolute error |
| --- | --- | --- | --- | --- |
| 0 | 57 | 57 /57 | 9,520,543 | 1.9073486328125e-6 |
| 7 | 57 | 57 /57 | 9,388,623 | 1.9073486328125e-6 |

An independent retained-file audit recomputes 114 modulation sites and 16 native sampling steps, verifies 478 raw files and reproduces every reported metric. Original captions/latents are diagnostic inputs; these observations do not establish complete native model acceptance.

## Actual native sampling

Both new runs use the converted exact old `ltxv-2b-0.9.8-distilled` DiT, Vulkan, four CPU threads, eight steps and the original B geometry/noise. Both execute all 28 trained DiT layers:

| B conditioning | Final maximum absolute error | Relative RMSE | Cosine | Original gates |
| --- | --- | --- | --- | --- |
| Original reference caption, diagnostic only | 0.00445225834846 | 0.000286313719571 | 0.999999959027 | FAIL: maximum error |
| Retained actual native F32 T5 caption | 0.0124872624874 | 0.000660452306871 | 0.999999781991 | FAIL: maximum error and RMSE |

Thresholds remain maximum error ≤0.003, relative RMSE ≤0.0003 and cosine ≥0.99999. The preceding reference-caption Vulkan result was 0.00779688358307 maximum error. Local improvement does not close the full-chain failure. Native T5 conditioning still includes quantized-encoder differences and downstream sensitivity; reference-conditioned improvement cannot establish a repaired T5 pipeline.

The two native runs took about 9.35 /9.75 seconds, with observed host peak working sets around 1.22 GB and sampled peak private bytes around 4.36 GB. Loading/cache/system activity affect timing. GPU memory was not measured; these are not phone resource or performance claims. No new VAE/RGB/video run was executed for these failed latent conditions. Previous full-chain failure evidence is retained.

![Measured host modulation and sampling errors; final gates fail](media/development/ltx098-modulation-errors.png)

## Sources and reproduction

- [Isolated modulation implementation](../research/ltx098_modulation/modulation.inc), [builder](../tools/build_ltx098_modulation.py), [sampler test](../tools/test_ltx098_modulation.py).
- [Passive original-forward observation](../tools/analyze_ltx098_modulation.py), [independent retained-array audit](../tools/check_ltx098_modulation_evidence.py).
- [Step 0](../verification/development/ltx098-modulation-step0.json), [step 7](../verification/development/ltx098-modulation-step7.json), [reference-conditioned sampler](../verification/development/ltx098-modulation-reference-vulkan.json), [native-T5-conditioned sampler](../verification/development/ltx098-modulation-f32-vulkan.json), [recomputation receipt](../verification/development/ltx098-modulation-capture-audit.json).

After explicitly acquiring developer assets and creating the frozen references as described in the [pipeline guide](LTX098_PIPELINE.en.md):

```powershell
python tools/analyze_ltx098_modulation.py --reference build/ltx098-pipeline-tests/run-s3z3urrv/original-reference --case 1 --step 0
python tools/analyze_ltx098_modulation.py --reference build/ltx098-pipeline-tests/run-s3z3urrv/original-reference --case 1 --step 7
python tools/test_ltx098_modulation.py --reference build/ltx098-pipeline-tests/run-s3z3urrv/original-reference --case 1 --context reference --backend vulkan
python tools/test_ltx098_modulation.py --reference build/ltx098-pipeline-tests/run-s3z3urrv/original-reference --case 1 --context f32 --backend vulkan
python tools/check_ltx098_modulation_evidence.py
```

These commands do not download assets. The reference directory identifies this retained run; reproductions must use their own identically verified original reference. Weights and raw arrays remain ignored under `build/`, outside Git/APKs/user devices. Numerical repair, production integration, explicit user asset control and full same-phone Android acceptance remain required. Every other frozen target, including both SD1.5/SDXL LoRA pairings, remains in the same complete release.

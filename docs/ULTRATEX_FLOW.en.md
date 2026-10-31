# UltraTex flow component conversion

[中文](ULTRATEX_FLOW.md) · [Complete work list](REMAINING_ADAPTATION.en.md) · [Local materials](LOCAL_MATERIALS.en.md)

**This is a network component converter. UltraTex is not yet a complete application recipe.** It implements the actual FLUX.1 dev / FLUX.2 flow exports, LoRA, foreground compaction and positional IDs. It registers neither a runnable model nor a download candidate. Local text encoding, matched VAE, UltraTex conditions, sampling and application orchestration remain required.

| ID | Implemented | Boundary |
| --- | --- | --- |
| U01 | Pinned FLUX.1 dev | Actual double / single blocks, modulation, RoPE, pooled text, distilled guidance and BSA; no substitute architecture |
| U02 | Pinned FLUX.2 | Guidance and Klein without guidance; ordinary joint reference sequence used in training, not the different causal KV-cache path |
| U03 | Dynamic foreground | Target / normals pruned separately, original positions and single reference preserved; returns prediction plus original target indices; batch 1–2 |
| U04 | LoRA | Publisher FLUX.1 processor factors and fixed FLUX.2 PEFT format; validate every target, shape, factor and finite value before modifying weights |
| U05 | Exact rotary tables | Original FLUX.1 FP64 trig converted to FP32 for integer IDs 0–8191, avoiding Android ORT's unsupported double Cos; exact publisher comparisons; tables stay with selected model assets |
| U06 | Local CPU / ORT | Existing compiled BSA, FP32 / BF16 attention; no Triton, CUDA installer or downloaded executable plugin |
| U07 | Offline conversion | Explicit local safetensors, strict base weights, source / SHA256 receipt and missing stages; refuse an existing destination before loading models |

Source is pinned to `yiboz2001/UltraTex@a726678f3f3631fe2c5e3d1fb4597114784c7a8b`; [the lock](../third_party/ultratex-flow-source-lock.json) hashes eight files. Only reviewed definitions execute. No upstream training/inference module, caption cache, installer or download helper is imported. Apache / SLA notices are already provided; individual weight licences also apply.

## Conversion

The developer tool needs native Python, CPU PyTorch, ONNX, einops, safetensors and pinned sources. If sources are absent, the existing `tools/fetch_spatial_sources.py` retrieves fixed source revisions without model weights.

```powershell
python tools/export_ultratex_flow.py --family flux1 `
  --config E:/models/ultratex/flux1-parameters.json `
  --weights E:/models/ultratex/flux1-base.safetensors `
  --lora E:/models/ultratex/flux1-lora.safetensors `
  --output E:/models/ultratex/flow-export-new
```

The JSON config supplies the exact publisher `FluxParams` / `Flux2Params` constructor parameters matching the selected base weights. Use `--family flux2` for its matching architecture and PEFT factors. LoRA is optional. `--lora-scale` defaults to 1, bounded to -4…4. Attention preserves BF16 probability casts by default; `--float-attention` explicitly uses FP32. Full conversion can require substantial desktop memory; verification uses small random architectures only.

Output contains `flow.onnx`, external tensor data if needed, and `export-receipt.json`. The receipt declares `complete_adapter=false` and `app_recipe_registered=false`; **no misleading complete `lma-bundle.json` is generated**. Local input paths / filenames are omitted; roles, sizes, hashes and source identity remain.

FLUX.1 position inputs are int64 in 0–8191; FLUX.2 retains float32 source positions. Masks are shared-across-batch int64 0/1 vectors; at least one target foreground token is required. Float inputs must be finite. Output indices support future same-phone target restoration. A bare ONNX component is not complete task preflight: its caller must enforce this contract. Existing BSA work limits and disclosed deterministic tie ordering apply.

## Program evidence and remaining work

101 checks execute actual random publisher double / single networks, dynamic ONNX and production native C++ ORT / BSA. Cases cover varying sequence lengths / batches, removal of background attention, original IDs / reference influence, FP32 / BF16, exact publisher rotary values, actual unmerged FLUX.1 processors, atomic invalid-factor rejection, both real conversion CLIs and preserving prior exports. Zero complete trained models, phones or virtualized environments were used.

[Records](../verification/adaptation/ultratex-flows.json) · [Test entrypoint](../tools/test_ultratex_flows.py)

A complete workflow still needs same-phone CLIP / T5 or Qwen3 tokenization and encoding, corresponding tile VAE / BN and material decoders, canonical geometry conditions / token packing, Euler / CFG and black-background restoration, separate albedo / MR passes and the application asset / parameter / child-process / PBR orchestration. All remain in the original delivery scope; a passing network export does not complete UltraTex.

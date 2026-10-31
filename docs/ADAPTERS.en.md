# Peer LoRA models and explicit pairing

> v0.3.2 adds four speech families and single-image 3D. See the [expansion guide](SPEECH_3D_EXPANSION.en.md) for formats, components, workflows, API, builds and program checks. Existing capabilities remain; older checkpoints below retain their original context.

[中文](ADAPTERS.md) · [Asset-control audit](ASSET_CONTROL_AUDIT.en.md) · [Development](DEVELOPMENT.en.md) · [Full scope](MULTIMODAL_RELEASE_PLAN.en.md)

[Native LCM preparation follow-up](LCM_LOCAL_PREPARATION.en.md): the new program derives a source/base-bound component but is not an App module yet; direct two-file host experiments do not establish product recipe support. The new C++ candidate fails its preset pixel maximum (8 > 5) and remains rejected.

Standalone LCM checkpoints and LCM-LoRA remain separate targets. [New host analysis](SD_DISTILLED_TRAINED.en.md) identifies a dropped guidance condition in one conversion and retains numerical/native-image fold candidates; neither adapter execution nor this derivation establishes complete product checkpoint support.

Applies to internal **0.3.0-dev.12 / code 16**. Pairing, storage and task code is integrated; **there is no LMA Android LoRA-generation evidence**. Real SD 1.5/SDXL weights, quality and lifecycle acceptance for selection 02 remain mandatory in the same complete v0.3.0.

## User flow

1. Explicitly select and separately download/import the base bundle and LoRA bundle. Details disclose each bundle's files, sizes and licenses. This checkpoint adds no checked LoRA download candidate.
2. Bases and adapters are peers in the image-filtered library. Adapters also show LoRA / requires base model. Preserve Recommended `m08 → m06 → m01`.
3. Choose Pair on an installed adapter, then explicitly select an installed compatible base. With no match, install a base through the library yourself; pairing never selects/downloads missing assets. Alternatively select adapters in the base model's task form.
4. Enter a prompt and select at most eight matching adapters with editable strengths. Each adapter has independent saved settings; task edits leave those settings intact. Over-limit input clamps to that adapter's declared bounds, within the native absolute range `-4…4`.
5. Submission freezes the base ID, ordered adapter IDs, effective strengths and adjustments. Later settings changes leave queued snapshots intact.
6. Execution holds base/adapter references together, protecting assets and settings. Completion, errors, cancellation and partial-acquisition failure release them. Assets explicitly deleted while queued cause a local execution failure, never a download.

All loading, sampling and output processing execute on the same phone. App updates carry foundation code without LoRA/base weights or model-specific vocabularies. LoRAs are optional model assets, not executable plugins.

## Manifest and API

Reuse `lma.model-bundle/1` and add a data-only `adapter` declaration. The [Chinese guide's JSON fragment](ADAPTERS.md) uses `lma.adapter/1`, `kind: lora`, `sd_cpp / cpu`, image output, `pipeline: lora` and one `sd15` base architecture/pipeline. For SDXL use `sdxl` consistently. An optional `baseModelIds` list narrows compatibility to specific model IDs.

Exactly one component has role `lora` and format `safetensors` or `gguf`, with the actual file size and SHA256. Adapter settings contain only numeric `scale`, explicit minimum/maximum within `-4…4`, and editable presets. Adapters cannot be bases. Reject unknown adapter versions or command fields.

`basePipelines` constrains pairing. Dev.12 dedicated LCM-LoRA templates add `"sampling":"lcm"`; pairing with an ordinary matching base freezes LCM sampler/scheduler, CFG=1 and the 1–8 step guard for this task while retaining saved base settings. Negative prompts are rejected. Pairing declarations/names alone do not enable LCM. See [diffusion](DIFFUSION_ENGINE.en.md); official [SD1.5](https://huggingface.co/latent-consistency/lcm-lora-sdv1-5) and [SDXL](https://huggingface.co/latent-consistency/lcm-lora-sdxl) weights target different bases.

Add optional `adapters` to an existing authenticated `POST /v1/jobs` image request:

```json
{
  "bundleId": "your_installed_sd15_bundle",
  "type": "image.generate",
  "input": {"prompt": "A cabin in morning mist."},
  "parameters": {},
  "adapters": [{"bundleId": "your_installed_lora_bundle", "scale": 0.75}],
  "allowUnmeasured": true
}
```

Replace example IDs with actual installed bundles. Omitting scale freezes the saved adapter value. Reject duplicate/self dependencies, more than eight adapters, non-finite numbers, path/unknown fields and adapters on non-image tasks. Clients cannot supply native paths. Output provenance retains complete adapter manifests, effective strengths and task parameters.

## Evidence and limits

[AdapterSpec](../app/src/main/java/com/lma/app/core/AdapterSpec.java), [ModelSelection](../app/src/main/java/com/lma/app/core/ModelSelection.java), [BundleStore](../app/src/main/java/com/lma/app/core/BundleStore.java), [LocalJobs](../app/src/main/java/com/lma/app/LocalJobs.java) and [SdEngine](../app/src/main/java/com/lma/app/SdEngine.java) resolve verified object paths from the complete lease group into the packaged worker's `loras` array.

45 added host checks use arbitrary fixture bytes for both architecture declarations, rejection/bounds, frozen snapshots, atomic references and no implicit transfers. They do not parse real adapter weights or generate images. The checkpoint passes 130 foundation and 97 UI assertions; screenshots/video/GIF are visibly labeled UI FIXTURE.

Actual compatibility still depends on tensor names/shapes, training bases, quantized application mode, runtime version and available memory. Declared compatibility is not inspected-weight evidence. Admission adds a conservative four-times-file-size adapter RAM guard, not a measured peak. Pinned real recipes, effect comparisons, the full HF multi-component selector, Android loading/cancellation/release and endurance remain unfinished.

[Trained SD1.5/SDXL style and LCM-LoRA validation](SD_VARIANTS_TRAINED.en.md) adds complete learned weights through unchanged production C++/Java on the host: zero/base equality, enabled/combined effects, a diagnostic changing only LCM scale, incompatible families, leases, independent parameters and cancellation/error/recovery. Zero LCM scale is a native developer diagnostic that the App rejects. Low-step outputs still have quality problems. Learned-weight effects do not establish quality, arbitrary HF compatibility or Android acceptance; the original45 fixture checks remain separately scoped.

# Diffusion foundation: SDXL, SD-Turbo and LCM

[中文](DIFFUSION_ENGINE.md) · [HF components](HF_RECIPES.en.md) · [LoRA](ADAPTERS.en.md) · [Development status](DEVELOPMENT.en.md)

New actual host follow-up: [SD-Turbo and standalone LCM checkpoint](SD_DISTILLED_TRAINED.en.md). SD-Turbo completes HF/import/native checks. The LCM conversion omits a condition branch; a fixed-guidance candidate passes complete-UNet numerical checks and actual PNG controls, with quality, canonical pipeline, product preparation and Android still unaccepted.

Applies to internal **0.3.0-dev.13 / code 17**. This describes implemented bindings, recipes, native Windows compilation and scoped checks. Android model output, image quality, memory and screen-off behavior remain unverified. Selections 01/02/03/05 and every other selected target remain in the same complete v0.3.0.

## User selection and components

The App delivers signed runtime code, data recipes and tags. Users select/download/import weights, LoRA, CLIP encoders, VAE and vocabularies. Installation, upgrades, browsing and incomplete jobs do not fetch assets. No weights are bundled, and installing all recipes is never required.

1. Open a repository through All/search, choose the component-recipe entry, then explicitly select its architecture/recipe.
2. Bind matching required files, including across repositories. Each file retains its pinned commit, size and integrity identity. Review every dependency and total transfer size.
3. Register the manifest, then separately confirm its download or import a folder. Local manages pause/resume, settings, versions and deletion.
4. Use a complete model or explicitly pair a LoRA with a compatible installed base. Missing bases never download automatically.
5. Fill the prompt and task settings, explicitly permit an unmeasured attempt and submit to the shared phone queue. Resource/model/engine failures remain local.

| Recipe | User-selected components | Output/dependency labels |
| --- | --- | --- |
| Complete SD1.5/SDXL checkpoint | `model`, optional matching `vae`, disclosed `clip_merges` | Image/text-to-image, sd_cpp/CPU/architecture |
| Split SD1.5 | `diffusion`, `clip_l`, `vae`, `clip_merges` | Image; complete component set required |
| Split SDXL | `diffusion`, `clip_l`, `clip_g`, `vae`, `clip_merges` | Image; both CLIP encoders required |
| SD-Turbo | Complete SD2.1 Turbo checkpoint including encoders/VAE, optional VAE, `clip_merges` | Image/distilled sampling, `sd21_turbo` |
| SD1.5/SDXL LCM checkpoint | Complete matching LCM checkpoint, optional VAE, `clip_merges` | Image/distilled sampling, `sd15_lcm`/`sdxl_lcm` |
| SD1.5/SDXL LCM-LoRA | Separate `lora` plus explicitly selected ordinary matching base | Peer image adapter/distilled sampling/requires base |

Weight roles accept GGUF/Safetensors. Extensions/declarations do not establish tensor compatibility. A complete checkpoint must actually contain the required encoders/VAE; split recipes require each component. SDXL may use a matching replacement VAE. After loading, the native worker checks SD1.x/SD2.x/SDXL architecture and rejects other families or inpaint variants for these text-to-image routes. This check cannot prove training/distillation method or quality; actual weight provenance still matters.

Text/image/video/audio capability tags, installation, device evidence and Uncensored content labels remain independent. All models are peers, and Recommended m08 → m06 → m01 is preserved. Production diffusion recipes remain prompt-only; importing media does not enable image editing or image-to-image generation.

## Task sampling policy

| Source | Native sampler/scheduler | Step guard | CFG |
| --- | --- | --- | --- |
| Ordinary SD/SDXL plus style LoRA | Selected model recipe | Independent model settings | Independent model settings |
| LCM checkpoint or one declared LCM-LoRA | `lcm` / `lcm` | 1–8 | 1, disabled |
| SD-Turbo | `euler_a` / `discrete` | 1–4 | 1, disabled |

These are application recipe guards, not universal training maxima. sd.cpp expresses disabled classifier-free guidance as CFG=1; numerical conventions from other libraries do not transfer directly. Low-step recipes reject negative prompts. The UI disables that input; the API returns an error.

Selecting LCM-LoRA displays the effective policy and clamps excessive task steps; deselection restores the previous form values. Saved base-model steps/CFG remain independent. Select at most one consistency accelerator; an LCM checkpoint does not take another LCM-LoRA. Its scale must be positive. Other declared compatible style LoRAs may be selected within the eight-adapter limit.

The optional restricted adapter declaration `"sampling":"lcm"` extends the existing `lma.adapter/1` pairing rules. Only this declaration enables acceleration; a model name cannot enable it. Unknown policies, mismatched architectures, missing components or missing ordered leases fail explicitly.

## API, snapshots and native boundary

Clients use the normal `POST /v1/jobs` request with installed base/adapter IDs, a prompt, task parameters and explicit unmeasured consent; see the [complete JSON example](DIFFUSION_ENGINE.md#api快照与原生边界) and [API guide](API.en.md).

The server freezes `diffusionPlan`: `lma.diffusion-plan/1`, profile, effective parameters and adjustment reasons. Requested parameters stay separate so forced LCM values neither overwrite ordinary model settings nor break retry against an older recipe schema. Clients cannot submit this derived field. Retry removes the old plan and validates again. Before starting, the binding recomputes the plan from held immutable base/adapter leases and rejects differences. Numeric JSON representation is normalized before persistence to avoid spurious `1.0` versus `1` mismatches.

The worker receives verified private component paths and explicit adapter order. CLIP merges remains managed user data outside the APK. Java and C++ independently constrain the low-step policy; C++ also checks the loaded tensor architecture. Tokenization, encoding, sampling, VAE decoding and PNG output all execute on the same Android phone, without off-device fallback.

## Development evidence and remaining acceptance

- [Diffusion receipt](../verification/development/diffusion.json): 174 checks, comprising 117 production Java planning/binding/actual-host-child protocol assertions and 57 executions of the shared C++ policy. Child output is protocol JSON bytes, never an image or model result.
- Foundation: 425 checks, including 233 recipe/integrity assertions. UI: 203. Twenty signed data recipes register without downloading.
- Native Windows Android ARM64 compilation, APK signing, 19 native files, API28/16KiB alignment and Lint checks pass; no Android execution evidence exists.
- Complete pinned model sources/licenses, SD1.5/SDXL LoRA effects, LCM/Turbo quality/speed/RAM, loading/release, screen-off/upgrades and every other target remain mandatory for the same v0.3.0. No new Release.

Implementation: [SdSpec](../app/src/main/java/com/lma/app/core/SdSpec.java), [SdEngine](../app/src/main/java/com/lma/app/SdEngine.java), [C++ policy](../native/sd_policy.hpp), [worker](../native/sd_worker.cpp). Reviewed upstream sources: [pinned sd.cpp LCM guide](https://github.com/leejet/stable-diffusion.cpp/blob/be486498eadc29dc3cd234d944c2180ed42b1415/docs/lcm.md), [SD/component guide](https://github.com/leejet/stable-diffusion.cpp/blob/be486498eadc29dc3cd234d944c2180ed42b1415/docs/sd.md), [official SD-Turbo](https://huggingface.co/stabilityai/sd-turbo), [LCM-LoRA SD1.5](https://huggingface.co/latent-consistency/lcm-lora-sdv1-5), [LCM-LoRA SDXL](https://huggingface.co/latent-consistency/lcm-lora-sdxl). Upstream support is separate from LMA device evidence.


See [advanced bindings](ADVANCED_DIFFUSION.en.md) for four additional image/video routes, complete components, flowShift and geometry. The same diffusion receipt also covers these routes.


## dev.24 progress and actual trained assets

[Trained SD1.5 validation](SD15_TRAINED.en.md) adds host PNGs, sampler cancellation/recovery and the external-vocabulary workflow. Callbacks follow loading/generating; local operation steps are not all diffusion steps. Android compilation, UI fixtures, host model execution and phone acceptance remain separate; other families and LoRAs need independent acceptance.

[Complete SDXL and paired style/LCM-LoRA measurements](SD_VARIANTS_TRAINED.en.md) use complete learned files, external vocabulary and unchanged production code for zero/enabled scale, LCM weight-effect, actual-sampler cancellation/recovery and full production Java import. Actual PNGs, time and observed host memory remain separately scoped. Low-step samples fail quality acceptance; separate SD-Turbo/LCM checkpoints still require complete acceptance. Host outputs do not close Android, phone/endurance or full Release gates.

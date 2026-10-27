"""Generate data-only component recipes for engines already shipped in the App. No asset fetches."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build():
    bundles = json.loads((ROOT / "catalogue/model-bundles.json").read_text(encoding="utf-8"))["bundles"]
    sd = next(b for b in bundles if b["pipeline"] == "sd15")
    templates = []
    for arch, caption in (("sd15", "SD 1.5"), ("sdxl", "SDXL")):
        definition = {k: copy.deepcopy(sd[k]) for k in ("engine", "backend", "tasks", "capabilities", "parameters")}
        definition.update(architecture=arch, pipeline=arch)
        if arch == "sdxl":
            for dim in ("width", "height"):
                definition["parameters"]["fields"][dim]["default"] = 1024
        templates.append({"id": arch + "_checkpoint_cpu_v1", "name": caption + " · 完整 checkpoint", "primaryRole": "model", "definition": definition,
                          "requirements": [{"role": "model", "label": "完整 checkpoint（含编码器 / VAE）", "formats": ["gguf", "safetensors"], "required": True}],
                          "fixedComponents": [copy.deepcopy(next(c for c in sd["components"] if c["role"] == "clip_merges"))],
                          "help": "只适用于完整 checkpoint。独立 diffusion 权重需要另一套完整组件配方；张量架构、量化兼容与资源尚需验证。"})
        scale = {"type": "number", "label": "LoRA 强度", "default": 1, "minimum": -4, "maximum": 4, "presets": [0.5, 0.75, 1], "limitSource": "application_guard"}
        definition = dict(engine="sd_cpp", backend="cpu", architecture=arch, pipeline="lora", tasks=["image"], capabilities=["image_adapter"],
                          adapter={"schema": "lma.adapter/1", "kind": "lora", "baseArchitectures": [arch], "basePipelines": [arch]}, parameters={"version": 1, "fields": {"scale": scale}})
        templates.append({"id": arch + "_lora_cpu_v1", "name": caption + " · LoRA", "primaryRole": "lora", "definition": definition,
                          "requirements": [{"role": "lora", "label": "与基础架构匹配的 LoRA", "formats": ["safetensors", "gguf"], "required": True}], "fixedComponents": [],
                          "help": "LoRA 不能单独生成；完成安装后需明确选择已安装的兼容基础模型。此配方不自动适配 LCM-LoRA。"})
    for pipeline, caption, roles in (("kokoro", "Kokoro · 英语词表", ("model", "voices", "tokens")), ("piper_vits", "Piper VITS · 英语词表", ("model", "tokens")), ("matcha", "Matcha + vocoder · 英语词表", ("model", "vocoder", "tokens"))):
        source = next(b for b in bundles if b["pipeline"] == pipeline)
        definition = {k: copy.deepcopy(source[k]) for k in ("engine", "backend", "architecture", "pipeline", "tasks", "capabilities", "parameters")}
        speaker = definition["parameters"]["fields"]["speaker"]
        speaker.update(maximum=65535, limitSource="application_guard"); speaker["presets"] = [0]
        formats = {"model": ["onnx"], "vocoder": ["onnx"], "voices": ["bin"], "tokens": ["text"]}
        templates.append({"id": pipeline + "_en_cpu_v1", "name": caption, "primaryRole": "model", "definition": definition,
                          "requirements": [{"role": role, "label": role, "formats": formats[role], "required": True} for role in roles],
                          "fixedComponents": [copy.deepcopy(c) for c in source["components"] if c["role"] == "lexicon"],
                          "help": "请选择此架构对应的 sherpa-onnx 导出模型、配套 tokens 与其他组件。此模板使用下方明确列出的英语 lexicon，不提供语音克隆或自动转换。音色实际范围由模型加载后核对。"})
    return {"schema": "lma.recipe-catalogue/1", "templates": templates}


if __name__ == "__main__":
    target = ROOT / "app/src/main/assets/recipe-templates.json"
    target.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Generated 7 data-only component recipes; no weights or tokenizer data.")

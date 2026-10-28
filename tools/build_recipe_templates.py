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
                          adapter={"schema": "lma.adapter/1", "kind": "lora", "baseArchitectures": [arch], "basePipelines": [arch, arch + "_lcm"]}, parameters={"version": 1, "fields": {"scale": scale}})
        templates.append({"id": arch + "_lora_cpu_v1", "name": caption + " · LoRA", "primaryRole": "lora", "definition": definition,
                          "requirements": [{"role": "lora", "label": "与基础架构匹配的 LoRA", "formats": ["safetensors", "gguf"], "required": True}], "fixedComponents": [],
                          "help": "LoRA 不能单独生成；完成安装后需明确选择已安装的兼容基础模型。此配方不自动适配 LCM-LoRA。"})
    # These are data recipes, never a model installation list. Each file remains a user choice.
    checkpoint = {t["definition"]["architecture"]: t for t in templates if t["primaryRole"] == "model"}
    for arch in ("sd15", "sdxl"):
        base = checkpoint[arch]
        base["requirements"].append(dict(role="vae", label="可选：匹配架构的替代 VAE", formats=["safetensors", "gguf"], required=False))
        split = copy.deepcopy(base)
        split.update(id=arch + "_split_cpu_v1", name=("SD 1.5" if arch == "sd15" else "SDXL") + " · 独立 diffusion + 编码器 + VAE", primaryRole="diffusion")
        split["requirements"] = [dict(role=role, label=role, formats=["gguf", "safetensors"], required=True) for role in (["diffusion", "clip_l", "vae"] if arch == "sd15" else ["diffusion", "clip_l", "clip_g", "vae"])]
        split["help"] = "选择同一架构配套的 diffusion、完整 CLIP 编码器和 VAE；SDXL 必须同时提供 CLIP-L 与 CLIP-G。全部组件核验后才能运行，词表作为已披露依赖由用户下载。"
        templates.append(split)
    for pipeline, arch, caption in (("sd21_turbo", "sd21", "SD-Turbo · SD 2.1"), ("sd15_lcm", "sd15", "LCM · SD 1.5 checkpoint"), ("sdxl_lcm", "sdxl", "LCM · SDXL checkpoint")):
        t = copy.deepcopy(checkpoint["sd15" if arch == "sd21" else arch]); t.update(id=pipeline + "_checkpoint_cpu_v1", name=caption)
        d = t["definition"]; d.update(pipeline=pipeline, architecture=arch, capabilities=["text_to_image", "distilled_sampling"])
        f = d["parameters"]["fields"]; lcm = pipeline.endswith("_lcm")
        f["steps"].update(default=4 if lcm else 1, maximum=8 if lcm else 4, presets=[1, 2, 4, 8] if lcm else [1, 2, 4], limitSource="application_sampling_policy")
        f["cfg"].update(default=1, minimum=1, maximum=1, presets=[1], limitSource="application_sampling_policy")
        f["sampler"].update(default="lcm" if lcm else "euler_a", values=["lcm"] if lcm else ["euler_a"])
        f["scheduler"] = dict(type="enum", label="调度器", default="lcm" if lcm else "discrete", values=["lcm"] if lcm else ["discrete"])
        t["help"] = "只选择该蒸馏架构的完整 checkpoint。低步数配方关闭 CFG，不接受负面提示词；LCM checkpoint 不再叠加 LCM-LoRA。采样上限是应用配方约束，实际图像与手机资源仍待验证。"
        templates.append(t)
    for arch in ("sd15", "sdxl"):
        t = copy.deepcopy(next(t for t in templates if t["id"] == arch + "_lora_cpu_v1"))
        t.update(id=arch + "_lcm_lora_cpu_v1", name=("SD 1.5" if arch == "sd15" else "SDXL") + " · LCM-LoRA")
        t["definition"]["adapter"].update(sampling="lcm", basePipelines=[arch])
        t["definition"]["capabilities"].append("distilled_sampling")
        t["definition"]["parameters"]["fields"]["scale"].update(minimum=0.1, maximum=2, presets=[0.5, 0.75, 1])
        t["help"] = "与对应架构的普通基础模型显式配对；一次只选一个 LCM 加速来源。任务自动固定 LCM 采样 / 调度、CFG=1 与 1–8 步保护范围，保存的基础模型设置保留；不支持负面提示词。"
        templates.append(t)
    for pipeline, arch, caption, encoder, vae, tokenizer, steps, cfg, schedule in (
        ("z_image_turbo", "z_image", "Z-Image-Turbo", "Qwen3 4B（匹配 Z-Image）", "FLUX.1 VAE", "qwen_merges", 8, 1, "discrete"),
        ("flux2_klein_4b", "flux2_klein", "FLUX.2-klein 4B · distilled", "Qwen3 4B（匹配 klein）", "FLUX.2 VAE（非 FLUX.1）", "qwen_merges", 4, 1, "flux2"),
        ("qwen_image_21", "qwen_image_21", "Qwen-Image 2.1 · 文生图", "Qwen3-VL 8B Instruct（匹配 2.1）", "Qwen-Image 2.1 VAE（非旧版）", "qwen_merges", 20, 6, "flux"),
        ("wan21_13b", "wan21", "Wan 2.1 · T2V 1.3B", "UMT5 XXL encoder（匹配 Wan 2.1）", "Wan 2.1 VAE", "umt5_tokenizer", 20, 6, "discrete")):
        video = pipeline == "wan21_13b"; distilled = pipeline in ("z_image_turbo", "flux2_klein_4b")
        d = copy.deepcopy(checkpoint["sd15"]["definition"])
        d.update(architecture=arch, pipeline=pipeline, tasks=["video" if video else "image"], capabilities=["text_to_video" if video else "text_to_image"] + (["distilled_sampling"] if distilled else []))
        f = d["parameters"]["fields"]
        for dim in ("width", "height"):
            f[dim].update(default=(512 if dim == "width" else 288) if video else 1024, multipleOf=32 if pipeline == "qwen_image_21" else 16, limitSource="pipeline_alignment_and_application_guard")
        f["steps"].update(default=steps, maximum=steps if distilled else 200, presets=[1, 2, 4, 8] if steps == 8 else [1, 2, 4] if distilled else [8, 12, 20, 30], limitSource="application_sampling_policy" if distilled else "application_guard")
        f["cfg"].update(default=cfg, minimum=1 if distilled else 0, maximum=1 if distilled else 30, presets=[1] if distilled else [1, 3, 6, 9])
        f["sampler"].update(default="euler", values=["euler"])
        f["scheduler"] = dict(type="enum", label="调度器", default=schedule, values=[schedule])
        f["flowShift"] = dict(type="number", label="流匹配偏移（0 自动）", default=3 if video else 0, minimum=0, maximum=32, presets=[0, 1, 3, 5], limitSource="application_guard")
        if video:
            f["frames"] = dict(type="integer", label="视频帧数（4n+1）", default=17, minimum=5, maximum=129, multipleOf=4, alignmentOrigin=1, presets=[5, 9, 17, 33, 65], limitSource="pipeline_alignment_and_application_guard")
            f["fps"] = dict(type="integer", label="每秒帧数", default=8, minimum=1, maximum=60, presets=[8, 12, 16, 24], limitSource="application_guard")
        requirements = [dict(role=role, label=label, formats=formats, required=True) for role, label, formats in (
            ("diffusion", "仅选择 " + caption + " diffusion 权重", ["gguf", "safetensors"]),
            ("t5" if video else "llm", encoder, ["gguf", "safetensors"]),
            ("vae", vae, ["gguf", "safetensors"]),
            (tokenizer, "匹配 UMT5 tokenizer.json" if video else "匹配 Qwen merges.txt", ["json"] if video else ["text"]))]
        help_text = "独立组件须与指定模型版本匹配；目录登记不下载。全部分词、编码、生成、解码在本机执行，CPU 速度和高内存需求尚未通过真机验证。"
        if distilled: help_text += "此蒸馏配方关闭 CFG / 负面提示词；不是 base 模型通用配方。"
        if pipeline == "qwen_image_21": help_text += "仅文生图，不包含图像编辑、旧版 Qwen 或 2.1 Turbo；遵守各组件许可，主模型为 Qwen Research License。"
        if video: help_text += "仅 T2V 1.3B，非 14B / I2V / VACE；帧数按 4n+1 归位，生成帧在手机编码 MP4。原生生成会持有全部帧，低分辨率预设不代表手机资源已验证。"
        templates.append(dict(id=pipeline + "_split_cpu_v1", name=caption, primaryRole="diffusion", definition=d, requirements=requirements, fixedComponents=[], help=help_text))
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
    fields = {}
    for key, label, default, low, high, presets in (
        ("threads", "CPU 线程", 2, 1, 16, [1, 2, 4]), ("speaker", "音色编号", 0, 0, 127, [0]),
        ("maxFrames", "音频 token 帧上限", 375, 1, 1500, [125, 250, 375, 750]),
        ("maxInputTokens", "文本 token 预算", 1024, 1, 2048, [256, 512, 1024]),
        ("seed", "随机种子", 1234, 0, 2147483647, [1234])):
        fields[key] = dict(type="integer", label=label, default=default, minimum=low, maximum=high, presets=presets, limitSource="application_guard")
    roles = [("manifest", "含音色提示的 browser manifest", "json"), ("tts_meta", "TTS ONNX metadata", "json"), ("codec_meta", "codec ONNX metadata", "json"),
        ("text_tokenizer", "配套 SentencePiece tokenizer.model", "sentencepiece"), ("tts_prefill", "prefill ONNX", "onnx"), ("tts_decode", "decode_step ONNX", "onnx"),
        ("tts_local", "local_fixed_sampled_frame ONNX", "onnx"), ("codec_decode", "codec decode_full ONNX", "onnx")]
    requirements = [dict(role=role, label=label, formats=[fmt], required=True) for role, label, fmt in roles]
    for group in ("tts", "codec"):
        for index in range(1, 5): requirements.append(dict(role=f"{group}_data_{index}", label=f"{group} 外置权重 .data {index}（按图依赖选择）", formats=["onnx_data"], required=False))
    templates.append(dict(id="moss_nano_cpu_v1", name="MOSS-TTS-Nano · ONNX + codec", primaryRole="tts_prefill",
        definition=dict(engine="moss_nano_ort", backend="cpu", architecture="moss_tts_nano", pipeline="moss_nano", tasks=["audio"], capabilities=["text_to_speech"], parameters=dict(version=1, fields=fields)),
        requirements=requirements, fixedComponents=[],
        help="仅接受匹配的 Nano browser ONNX 导出与 decode_full codec；不是其他 MOSS 架构。须自行选择图引用的全部 .data，缺少数据会在本机报错。所有词表和音色均需用户下载；不提供参考音频克隆。音色编号按已下载 manifest 回填，数值上限为应用保护值，手机效果与内存待实测。"))
    text_fields = {}
    for key, label, default, low, high, presets, kind in (
        ("threads", "CPU 线程", 4, 1, 256, [1, 2, 4, 8], "integer"),
        ("context", "上下文长度", 2048, 2, 131072, [512, 1024, 2048, 4096, 8192], "integer"),
        ("maxTokens", "单次输出上限", 512, 1, 131071, [128, 256, 512, 1024], "integer"),
        ("temperature", "采样温度", 0.7, 0, 2, [0, 0.3, 0.7, 1], "number")):
        text_fields[key] = dict(type=kind, label=label, default=default, minimum=low, maximum=high, presets=presets, limitSource="application_guard")
    text_fields["maxTokens"]["maximumFrom"] = dict(field="context", offset=-1)
    text_fields["reasoning"] = dict(type="enum", label="思考模式", default="off", values=["off", "auto", "on"])
    text_fields["systemPrompt"] = dict(type="string", label="系统提示词", default="你是一个有帮助的本地助手。请优先使用用户的语言，准确、清楚地回答。", maxLength=4000)
    templates.append(dict(id="text_gguf_cpu_v1", name="文本 GGUF · CPU", primaryRole="text_gguf",
        definition=dict(engine="llama_text", backend="cpu", architecture="gguf", pipeline="text_gguf", tasks=["text"], capabilities=["text_generation"], parameters=dict(version=1, fields=text_fields)),
        requirements=[dict(role="text_gguf", label="完整文本 GGUF（含 tokenizer）", formats=["gguf"], required=True)], fixedComponents=[],
        help="仅适用于现有 llama.cpp 引擎支持的完整文本 GGUF，不接受拆分权重、视觉 / 音频组件或自定义代码。下载后读取实际上下文上限，未知时采用应用保护值；CPU 内存和真实手机输出仍需验证。登记不下载，原有精选与已下载文本模型保留。"))
    return {"schema": "lma.recipe-catalogue/1", "templates": templates}


if __name__ == "__main__":
    target = ROOT / "app/src/main/assets/recipe-templates.json"
    result = build()
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(result['templates'])} data-only component recipes; no weights or tokenizer data.")

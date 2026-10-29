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
    sana_fields = {}
    for key, label, default, low, high, presets in (
        ("width", "宽度（32 对齐）", 512, 256, 2048, [256, 512, 1024]), ("height", "高度（32 对齐）", 512, 256, 2048, [256, 512, 1024]),
        ("steps", "采样步数", 10, 1, 50, [4, 10, 20]), ("threads", "CPU 线程", 4, 1, 32, [1, 2, 4]),
        ("maxInputTokens", "编码文本 token 预算", 512, 1, 1792, [256, 512, 1024, 1792]), ("seed", "随机种子（-1 随机）", -1, -1, 2147483647, [-1, 42])):
        sana_fields[key] = dict(type="integer", label=label, default=default, minimum=low, maximum=high, presets=presets, limitSource="application_guard")
        if key in ("width", "height"): sana_fields[key]["multipleOf"] = 32
    sana_fields["useCfg"] = dict(type="boolean", label="启用 CFG（双批次编码 / 采样）", default=False)
    sana_fields["cfg"] = dict(type="number", label="启用 CFG 时的引导强度", default=4, minimum=0, maximum=30, presets=[1, 4, 6], limitSource="application_guard")
    sana_roles = [("diffusion", "transformer.mnn", "mnn"), ("diffusion_data", "transformer.mnn.weight", "mnn_data"),
        ("connector", "connector.mnn", "mnn"), ("connector_data", "connector.mnn.weight", "mnn_data"),
        ("projector", "projector.mnn", "mnn"), ("projector_data", "projector.mnn.weight", "mnn_data"),
        ("vae", "vae_decoder.mnn", "mnn"), ("vae_data", "vae_decoder.mnn.weight", "mnn_data"),
        ("llm", "llm/llm.mnn", "mnn"), ("llm_data", "llm/llm.mnn.weight", "mnn_data"),
        ("llm_config", "llm/llm_config.json", "json"), ("tokenizer", "llm/tokenizer.txt", "text"), ("meta_queries", "llm/meta_queries.mnn", "mnn")]
    templates.append(dict(id="sana_mnn_cpu_v1", name="Sana mobile · Qwen3 + MNN", primaryRole="diffusion",
        definition=dict(engine="mnn_diffusion", backend="cpu", architecture="sana_mobile", pipeline="sana_mnn_v1", tasks=["image"], capabilities=["text_to_image"], parameters=dict(version=1, fields=sana_fields)),
        requirements=[dict(role=r, label=n, formats=[f], required=True) for r,n,f in sana_roles], fixedComponents=[],
        help="仅匹配 MNN-Sana-Edit-V2 的 Qwen3-0.6B 移动管线；本配方仅文生图，不接受原版 Sana 或 LoRA。13 个组件全部由用户选择，MNN 图与 .weight 必须成套。编码器配置只提取已验证的架构 / embedding 字段，不执行任意路径 / 缓存 / 联网配置。负面提示词需启用 CFG；启用后增加编码和采样开销。当前只有 CPU 编译与主机协议验证，无手机生图 / 性能证据。"))
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
    qwen_fields = {}
    for key, label, default, low, high, presets, kind in (
        ("threads", "CPU 线程", 4, 1, 32, [2, 4, 8], "integer"),
        ("maxInputTokens", "输入 token 预算（含格式）", 512, 1, 2048, [256, 512, 1024, 2048], "integer"),
        ("maxAudioTokens", "音频帧上限（约 12.5 帧 / 秒）", 375, 1, 1500, [125, 375, 750, 1500], "integer"),
        ("temperature", "采样温度", .9, 0, 2, [0, .5, .9, 1], "number"),
        ("topP", "Top P", 1, .01, 1, [.8, .9, 1], "number"),
        ("topK", "Top K", 50, 1, 1024, [20, 50, 100], "integer"),
        ("repetitionPenalty", "重复惩罚", 1.05, 1, 2, [1, 1.05, 1.1], "number"),
        ("seed", "随机种子（-1 自动）", -1, -1, 2147483647, [-1, 42, 1234], "integer")):
        qwen_fields[key] = dict(type=kind, label=label, default=default, minimum=low, maximum=high, presets=presets, limitSource="application_guard")
    qwen_fields["language"] = dict(type="enum", label="语言", default="auto", values=["auto", "en", "zh", "ja", "ko", "de", "fr", "ru", "pt", "es", "it"])
    templates.append(dict(id="qwen3_tts_06b_base_cpu_v1", name="Qwen3-TTS · 12Hz 0.6B Base", primaryRole="talker",
        definition=dict(engine="qwen_tts_native", backend="cpu", architecture="qwen3_tts_06b", pipeline="qwen3_tts_06b_base", tasks=["audio"], capabilities=["text_to_speech"], parameters=dict(version=1, fields=qwen_fields)),
        requirements=[dict(role="talker", label="0.6B Base Talker（含分词 / Code Predictor / speaker encoder）", formats=["gguf"], required=True, provides=["text_tokenizer", "code_predictor", "speaker_assets"]), dict(role="audio_codec", label="配套 Qwen3 12Hz 音频 codec", formats=["gguf"], required=True)], fixedComponents=[],
        help="仅匹配 Danmoreng/qwen3-tts.cpp 转换布局的 0.6B Base 和 12Hz codec；不能用 CustomVoice、VoiceDesign、1.7B 或通用文本 GGUF 替代。模型、内嵌词表和说话人编码器均由用户选择下载。可选导入 24 kHz 单声道 1–30 秒 WAV，当前提供 speaker-embedding 参考；未提供 ICL 文本、命名音色或指令音色设计。CPU 编译不代表手机输出、质量或实时性已验证。"))
    moss_fields = {
        "threads": dict(type="integer", label="CPU 线程", default=4, minimum=1, maximum=32, presets=[2,4,8], limitSource="application_guard"),
        "maxInputTokens": dict(type="integer", label="格式化输入上限（含参考音频）", default=512, minimum=1, maximum=2048, presets=[256,512,1024,2048], limitSource="application_guard"),
        "maxNewTokens": dict(type="integer", label="生成步数上限（含 Delay 排空）", default=375, minimum=64, maximum=1500, presets=[128,375,750,1500], limitSource="application_guard"),
        "seed": dict(type="integer", label="随机种子（-1 自动）", default=-1, minimum=-1, maximum=2147483647, presets=[-1,0,42], limitSource="native_seed_range"),
        "audioRepetitionPenalty": dict(type="number", label="音频重复惩罚", default=1, minimum=1, maximum=2, presets=[1,1.05,1.1], limitSource="application_guard"),
        "language": dict(type="enum", label="语言提示", default="auto", values=["auto","zh","en","de","es","fr","ja","it","hu","ko","ru","fa","ar","pl","pt","cs","da","sv","el","tr"]),
    }
    for prefix, caption, temperature, top_p, top_k in [("text","文本",1.5,1,50),("audio","音频",1.7,.8,25)]:
        moss_fields[prefix+"Temperature"]=dict(type="number", label=caption+"温度", default=temperature, minimum=0, maximum=3, presets=[0,1,temperature], limitSource="application_guard")
        moss_fields[prefix+"TopP"]=dict(type="number", label=caption+" Top P", default=top_p, minimum=.01, maximum=1, presets=[.8,.9,1], limitSource="application_guard")
        moss_fields[prefix+"TopK"]=dict(type="integer", label=caption+" Top K", default=top_k, minimum=1, maximum=1024, presets=[1,25,50], limitSource="application_guard")
    templates.append(dict(id="moss_delay_firstclass_cpu_v1", name="MOSS Delay 8B · first-class 原生语音", primaryRole="backbone",
        definition=dict(engine="moss_delay_native", backend="cpu", architecture="moss_delay_8b_v1", pipeline="moss_delay_firstclass_v1", tasks=["audio"], capabilities=["text_to_speech"], parameters=dict(version=1,fields=moss_fields)),
        requirements=[dict(role="backbone", label="first-class MOSS Delay 8B（含 BPE / 32 路 embedding 和输出头）", formats=["gguf"], required=True, provides=["text_tokenizer"]),dict(role="audio_decoder", label="配套 24 kHz / 32 路原生解码器", formats=["gguf"], required=True),dict(role="audio_encoder", label="可选：同版原生编码器（参考音频必需）", formats=["gguf"], required=False)], fixedComponents=[],
        help="仅匹配固定 OpenMOSS/llama.cpp first-class 转换布局；普通 MOSS-TTS-GGUF / 仅 Qwen3 backbone / Nano / Local / Realtime / v2 codec 不适用。用户明确选择主模型和解码器；仅需参考音频时再选择编码器。参考 WAV 为 24 kHz 单声道 1–10 秒，生成与 codec 分阶段释放。8B 内存需求高，尚无手机输出、速度或后台验收；此路由不表示完整 MOSS 九子目标已支持。"))
    open_common = {
        "threads": dict(type="integer", label="CPU 线程", default=4, minimum=1, maximum=32, presets=[2,4,8], limitSource="application_guard"),
        "seed": dict(type="integer", label="随机种子（-1 自动）", default=-1, minimum=-1, maximum=2147483647, presets=[-1,0,42], limitSource="native_seed_range"),
    }
    local_fields=copy.deepcopy(open_common)
    for key,label,kind,value,low,high,presets in [
        ("maxInputTokens","格式化输入上限（含参考）","integer",512,1,2048,[256,512,1024,2048]),
        ("maxNewTokens","生成帧数上限（每帧 80 ms）","integer",250,1,750,[125,250,375,750]),
        ("textTemperature","继续 / 停止头温度","number",1,0,3,[0,1,1.5]),
        ("audioTemperature","音频温度","number",1.7,0,3,[0,1,1.7]),
        ("audioTopP","音频 Top P","number",.8,.01,1,[.8,.9,1]),
        ("audioTopK","音频 Top K","integer",25,1,1024,[1,25,50]),
        ("audioRepetitionPenalty","音频重复惩罚","number",1,1,2,[1,1.05,1.1]),
    ]: local_fields[key]=dict(type=kind,label=label,default=value,minimum=low,maximum=high,presets=presets,limitSource="application_guard")
    sound_fields=copy.deepcopy(open_common)
    for key,label,kind,value,low,high,presets in [
        ("seconds","音效时长（latent 始终生成完整 30 秒）","number",5,1,30,[1,5,10,30]),
        ("steps","去噪步数","integer",50,1,100,[10,25,50,100]),
        ("cfgScale","CFG 强度","number",4,1,10,[1,4,7]),
        ("sigmaShift","Sigma shift","number",5,1,10,[1,3,5,10]),
    ]: sound_fields[key]=dict(type=kind,label=label,default=value,minimum=low,maximum=high,presets=presets,limitSource="application_guard")
    for sound,fields in [(False,local_fields),(True,sound_fields)]:
        templates.append(dict(id="moss_soundeffect_v2_cpu_v1" if sound else "moss_local_v15_cpu_v1",
            name="MOSS SoundEffect-v2 · 原生音效" if sound else "MOSS Local-Transformer-v1.5 · 原生语音", primaryRole="backbone",
            definition=dict(engine="openmoss_native",backend="cpu",architecture="moss_soundeffect_v2" if sound else "moss_local_v15",pipeline="moss_soundeffect_v2_cpu_v1" if sound else "moss_local_v15_cpu_v1",tasks=["audio"],capabilities=["text_to_audio","negative_prompt"] if sound else ["text_to_speech"],parameters=dict(version=1,fields=fields)),
            requirements=[dict(role="backbone",label="同次 openmoss 转换的 Qwen3 主干（含 BPE）",formats=["gguf"],required=True,provides=["text_tokenizer"]),dict(role="extras",label="配套 DiT / VAE extras" if sound else "配套 Local Transformer / v2 codec extras",formats=["gguf"],required=True,provides=["audio_decoder"] if sound else ["audio_encoder","audio_decoder"])],fixedComponents=[],
            help=("仅匹配固定 pwilkin/openmoss 转换布局，必须选择同次转换的主干和 extras；不能混用 first-class、Nano 或其他 MOSS 版本。模型及 codec 均为用户资产。CPU 路线同时驻留主干与 extras，需要高内存设备；不表示 Z20 已可运行。" + ("SoundEffect-v2 使用 30 秒 latent 去噪后裁剪，缩短输出不同比降低生成内存；支持负面提示词，不是语音克隆或整曲音乐。" if sound else "仅针对 Local-Transformer-v1.5，12 路 codec / 48 kHz 双声道；可选导入同格式 1–10 秒参考 WAV。暂不提供参考转写续说、多说话人或其他 Local 版本。") + "尚无 LMA Android 输出、质量、速度或后台验收。")))
    for ident,arch,name,layout in [
        ("moss_tts_openmoss_cpu_v1","moss_tts","MOSS-TTS","32 路 / 8B"),
        ("moss_tts_v15_openmoss_cpu_v1","moss_tts_v15","MOSS-TTS-v1.5","32 路 / 8B"),
        ("moss_ttsd_openmoss_cpu_v1","moss_ttsd","MOSS-TTSD-v1.0","16 路 / 8B"),
        ("moss_voicegen_openmoss_cpu_v1","moss_voicegenerator","MOSS-VoiceGenerator","16 路 / 1.7B"),
    ]:
        fields=copy.deepcopy(local_fields);fields['maxInputTokens']['default']=1024
        fields['maxNewTokens'].update(default=375,maximum=1500,presets=[125,375,750,1500],label="生成步数上限（含 delay flush；每音频帧 80 ms）")
        fields['voiceInstruction']=dict(type="string",label="声音描述（必填）" if arch=='moss_voicegenerator' else "声音描述（可选）",default="",maxLength=1000)
        fields['language']=dict(type="string",label="语言提示（留空为 None）",default="",maxLength=64)
        dialogue=arch=='moss_ttsd';voice=arch=='moss_voicegenerator'
        detail="文本须含 [S1]、[S2]；可选成对导入对应的 24 kHz 单声道参考 WAV，保持说话人映射。" if dialogue else "必填声音描述，不接受参考音频；按描述设计声音。" if voice else "可选一个 24 kHz 单声道参考 WAV；v1.0 与 v1.5 结构相同不能仅凭几何确认权重来源。"
        templates.append(dict(id=ident,name=name+" · 原生语音",primaryRole="backbone",
            definition=dict(engine="openmoss_native",backend="cpu",architecture=arch,pipeline=ident,tasks=["audio"],capabilities=["text_to_speech"]+(["multi_speaker_tts"] if dialogue else ["voice_design"] if voice else []),parameters=dict(version=1,fields=fields)),
            requirements=[dict(role="backbone",label="匹配的 Qwen3 主干（含 BPE）",formats=["gguf"],required=True,provides=["text_tokenizer"]),dict(role="extras",label="同次转换的 delay 头 / v1 codec extras",formats=["gguf"],required=True,provides=["audio_encoder","audio_decoder"])],fixedComponents=[],
            help=f"仅匹配固定 pwilkin/openmoss 转换布局（{layout}），输出 24 kHz 单声道。主干和 extras 需用户显式选择、同次转换；不能混用 first-class / Nano / Local / SoundEffect 文件。{detail}参考仅支持 1–10 秒、≤1 MiB 的 PCM16 / float32 WAV，不自动重采样。CPU 同时驻留全部组件，8B 主干与大 codec 需要高内存设备；未证明 Z20 可运行。模型、BPE、codec 均不附带；参数随模型保存。没有 LMA Android 输出、质量、速度或后台验收。"))
    effect=copy.deepcopy(local_fields)
    for key,value in {"maxInputTokens":1024,"maxNewTokens":375,"audioTemperature":1.5,"audioTopP":.6,"audioTopK":50,"audioRepetitionPenalty":1.2}.items():effect[key]['default']=value
    effect['maxNewTokens'].update(label="生成步数上限（含 delay 收尾，不承诺精确时长）",maximum=1500,presets=[125,375,750,1500])
    templates.append(dict(id="moss_soundeffect_openmoss_cpu_v1",name="MOSS-SoundEffect · 原生环境音效",primaryRole="backbone",
        definition=dict(engine="openmoss_native",backend="cpu",architecture="moss_soundeffect",pipeline="moss_soundeffect_openmoss_cpu_v1",tasks=["audio"],capabilities=["text_to_audio","environment_sound_conditioning"],parameters=dict(version=1,fields=effect)),
        requirements=[dict(role="backbone",label="旧 SoundEffect Qwen3-8B 主干（含 BPE）",formats=["gguf"],required=True,provides=["text_tokenizer"]),dict(role="extras",label="同次转换的 16 路 delay 头 / v1 codec extras",formats=["gguf"],required=True,provides=["audio_decoder"])],fixedComponents=[],
        help="旧 MOSS-SoundEffect，16 路 delay / 24 kHz 单声道。按官方处理器将提示词绑定到 Ambient Sound，Text 为 None；不支持负面提示词、声音指令或参考音频。仅匹配固定 pwilkin/openmoss 转换布局，同次转换的主干与 extras，不能混用 SoundEffect-v2 / TTSD / VoiceGenerator。8B 与 codec 同时驻留 CPU 内存，未证明 Z20 可运行。用户自行选择组件；无附带权重、词表或自动下载；尚无 LMA Android 推理或后台验收。"))
    for rt in (False,True):
        ident="moss_realtime_rq_cpu_v1" if rt else "moss_local_v10_rq_cpu_v1"
        fields=copy.deepcopy(open_common)
        for key,label,kind,value,low,high,presets in [
            ("maxInputTokens","格式化输入上限（含参考与余下文本）","integer",1024,1,2048,[512,1024,2048]),
            ("maxNewTokens","生成步数上限（每帧 80 ms，含停止步）","integer",375,1,750,[125,375,750]),
            ("audioTemperature","音频温度","number",.8 if rt else 1.7,0,3,[0,.8,1.7]),
            ("audioTopP","音频 Top P","number",.6 if rt else .8,.01,1,[.6,.8,1]),
            ("audioTopK","音频 Top K","integer",30 if rt else 25,1,1024,[1,25,30,50]),
            ("audioRepetitionPenalty","音频重复惩罚","number",1.1,1,2,[1,1.1,1.2])]:
            fields[key]=dict(type=kind,label=label,default=value,minimum=low,maximum=high,presets=presets,limitSource="application_guard")
        if rt:fields["streamAudio"]=dict(type="boolean",label="流式试听",default=False,help="逐帧输出并保留完整 WAV；试听与最终文件使用相同固定增益，不做整段响度调整。速度取决于设备，应用退到后台后仍继续生成。")
        if not rt:
            for key,label,kind,value,low,high in [("textTemperature","继续 / 停止头温度","number",1.5,0,3),("textTopP","继续 / 停止头 Top P","number",1,.01,1),("textTopK","继续 / 停止头 Top K","integer",50,1,1024)]:fields[key]=dict(type=kind,label=label,default=value,minimum=low,maximum=high,limitSource="application_guard")
            fields['voiceInstruction']=dict(type="string",label="声音描述（可选）",default="",maxLength=1000)
            fields['language']=dict(type="string",label="语言提示（可选）",default="",maxLength=64)
        templates.append(dict(id=ident,name=("MOSS-TTS-Realtime" if rt else "MOSS-TTS-Local-Transformer（旧版）")+" · 原生语音",primaryRole="model",
            definition=dict(engine="moss_rq_native",backend="cpu",architecture="moss_tts_realtime" if rt else "moss_tts_local_v10",pipeline=ident,tasks=["audio"],capabilities=["text_to_speech","single_text_to_wav"]+(["incremental_audio_output"] if rt else []),parameters=dict(version=1,fields=fields)),
            requirements=[dict(role="model",label="匹配的 "+("moss-tts-rt / 16 路" if rt else "moss-tts-local / 32 路旧 Local")+" GGUF",formats=["gguf"],required=True),dict(role="codec",label="v1 MOSS-Audio-Tokenizer GGUF（24 kHz / 32 路）",formats=["gguf"],required=True,provides=["audio_encoder","audio_decoder"]),dict(role="tokenizer",label="与此版本匹配的 moss-tokenizer BPE GGUF",formats=["gguf"],required=True,provides=["text_tokenizer"])],fixedComponents=[],
            help="仅匹配固定 mudler/moss-tts.cpp 转换格式；模型 / codec / BPE 由用户显式选择，不能混用 openmoss、Nano、first-class 或 Local-v1.5。"+("Realtime 使用独立的 4 层 RoPE 深度 Transformer / 16 路编码，逐步注入文本；可在本地模型设置中选择流式试听，逐帧输出 PCM 并保留完整 WAV，使用相同固定增益。当前仍一次提交完整文本，不提供增量文本会话。" if rt else "旧 Local 使用 4 层 Qwen3 深度 Transformer、输入及逐通道输出 MLP / 32 路编码，区别于 v1.5 的单层 GPT-J；支持可选声音描述及语言提示。")+"输出 24 kHz 单声道；可选 1–10 秒、≤1 MiB 同格式 PCM16 / float32 参考 WAV，不自动重采样。1.7B 主干与大 codec 同时驻留内存，需要高内存设备；未证明 Z20 可运行。无附带权重或词表；尚无 LMA Android 推理、质量、速度或后台验收。"))
    fields={}
    for key,label,value,low,high,presets,source in [
        ("threads","CPU 线程",4,1,32,[2,4,8],"application_guard"),
        ("seed","种子（-1 自动）",-1,-1,2147483647,[-1,42],"application_guard"),
        ("seconds","输出秒数（裁切；固定长度生成与解码）",5,1,11,[3,5,8,11],"model_duration_limit"),
        ("steps","扩散步数",8,1,32,[4,8,16,32],"application_guard"),
        ("maxInputTokens","有效提示词上限（含 EOS）",64,1,64,[32,64],"export_conditioning_limit")]:
        fields[key]=dict(type="integer",label=label,default=value,minimum=low,maximum=high,presets=presets,limitSource=source)
    templates.append(dict(id="stable_audio_small_litert_v1",name="Stable Audio Open Small · 本地短音频",primaryRole="diffusion_model",
        definition=dict(engine="stable_audio_litert",backend="cpu",architecture="stable_audio_open_small",pipeline="stable_audio_small_litert_v1",tasks=["audio"],capabilities=["text_to_audio","short_audio","english_prompts","fixed_latent_length"],parameters=dict(version=1,fields=fields)),
        requirements=[dict(role=role,label=label,formats=[fmt],required=True,provides=provides) for role,label,fmt,provides in [
            ("conditioner","匹配 Arm 导出的 T5-base / 时长条件编码器（128 输入 / 64 有效 token）","tflite",["text_encoder"]),
            ("diffusion_model","同版 SAO Small DiT（64×256 latent）","tflite",[]),
            ("audio_decoder","同版音频解码器（44.1 kHz 立体声 / 524288 帧）","tflite",[]),
            ("tokenizer","T5-base 配套 spiece.model（32000 pieces）","sentencepiece",["text_tokenizer"])]],fixedComponents=[],
        help="仅匹配固定 Arm-Examples audiogen TFLite 导出，不是任意 Stable Audio checkpoint。四份组件由用户逐一选择，安装 / 浏览 / 缺件均不自动下载。手机 LiteRT CPU 依次编码、扩散、解码；英文提示词最多 64 token（含 EOS），超过报错，不静默截断。输出 1–11 秒、44.1 kHz 立体声 PCM16；短时长仍执行固定 256 latent / 524288 解码帧，不能据此降低内存估算。无负面提示词、CFG、参考音频、语音克隆或图像 LoRA。官方权重受 Stability AI Community 条款及访问限制约束，模型许可与 App 许可独立。8 步是上游默认；线程 / 32 步属于应用保护。上游建议 8 GB RAM，未证明 Z20 可运行；LMA 尚无完整模型音质、速度或 Android 验收。"))
    from soulx_recipe import recipe as soulx_recipe
    templates.append(soulx_recipe())
    return {"schema": "lma.recipe-catalogue/1", "templates": templates}


if __name__ == "__main__":
    target = ROOT / "app/src/main/assets/recipe-templates.json"
    result = build()
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(result['templates'])} data-only component recipes; no weights or tokenizer data.")

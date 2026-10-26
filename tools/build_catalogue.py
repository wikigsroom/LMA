"""Create LMA's curated download catalogue from the checked research data."""
import json
from pathlib import Path
from evidence import current

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "catalogue"
SELECTION = ["M08", "M06", "M01", "M05", "M04", "M03", "M09", "M11", "M12", "M13", "M14", "M16", "M10", "M15"]
DETAILS = {
    "M01": ("Dolphin 3 · Qwen 0.5B Uncensored", "Qwen", "light", ["轻量", "中英", "0.5B"], "体积小，适合第一次验证本地运行；复杂任务能力有限。"),
    "M03": ("Qwen 3.5 · 0.8B Abliterated", "Qwen", "experimental", ["中文", "新架构", "0.8B"], "较新的轻量路线；请检查回复稳定性，先使用短上下文。"),
    "M04": ("Dolphin 3 · Llama 1B Uncensored", "Llama", "light", ["英文", "轻量", "1B"], "成熟 Llama 架构，适合英文短对话与轻量任务。"),
    "M05": ("Gemma 3 · 1B Abliterated", "Gemma", "light", ["多语言", "轻量", "1B"], "小体积文本模型，适合作为另一种回答风格的对照。"),
    "M06": ("LFM 2.5 · 1.2B Uncensored", "LFM", "balanced", ["中文", "高效", "1.2B"], "侧重内存与效率的轻量候选，适合与 Qwen 进行比较。"),
    "M08": ("Qwen 3 · 1.7B Abliterated", "Qwen", "balanced", ["中文", "推荐", "1.7B"], "中文对话的首轮候选；在老款手机上先用 2048 上下文。"),
    "M09": ("Qwen 3.5 · 2B Abliterated", "Qwen", "experimental", ["中文", "新架构", "2B"], "运行内存可能明显高于权重体积；建议 8GB 设备谨慎比较。"),
    "M10": ("LFM 2.5 · 2.6B Uncensored", "LFM", "quality", ["思考模型", "2.6B"], "这个版本会先输出思考；建议增加输出长度，避免只有思考而没有正文。"),
    "M11": ("Dolphin 3 · Qwen 3B Uncensored", "Qwen", "quality", ["中文", "3B"], "8GB 手机可比较的质量路线；建议使用短上下文并观察持续速度。"),
    "M12": ("Dolphin 3 · Llama 3B Uncensored", "Llama", "quality", ["英文", "3B"], "偏英文的较大模型，对内存和等待时间要求更高。"),
    "M13": ("Llama 3.2 · 3B Uncensored", "Llama", "quality", ["英文", "3B"], "开放式聊天候选，文件略大；加载是否稳定取决于可用内存。"),
    "M14": ("Qwen 3 · 4B Instruct 2507 Abliterated", "Qwen", "quality", ["中文", "4B"], "Huihui 去拒答权重版本，建议 8GB 以上设备从短上下文开始。"),
    "M15": ("Qwen 3.5 · 4B Uncensored", "Qwen", "experimental", ["中文", "新架构", "4B"], "对老款手机的内存与持续速度要求较高，请按实际表现决定是否保留。"),
    "M16": ("Gemma 3 · 4B Abliterated v2", "Gemma", "quality", ["多语言", "4B"], "多语言纯文本对照；此版本不下载视觉投影文件。"),
}


def main():
    source = json.loads((RESEARCH / "research-source.json").read_text(encoding="utf-8"))
    index = {m["id"]: m for m in source["models"]}
    audit = json.loads((RESEARCH / "verified-models.json").read_text(encoding="utf-8"))
    verified = {m["id"]: m for m in audit["models"] if m.get("ok")}
    uncensored = json.loads((RESEARCH / "uncensored-evidence.json").read_text(encoding="utf-8"))
    current(uncensored["input_fingerprint"])
    declarations = {m["id"]: m for m in uncensored["models"]}
    models = []
    for model_id in SELECTION:
        m = index[model_id]
        checked = verified[model_id.lower()]
        declaration = declarations[model_id.lower()]
        assert declaration["qualified"] is True and declaration["basis"] == "publisher-declared-uncensored", "The preserved curated labels require an explicit publisher claim"
        assert (declaration["gguf_repository"], declaration["gguf_revision"], declaration["weight_sha256"]) == (checked["repository"], checked["revision"], checked["sha256"]), "Uncensored evidence must match the exact download"
        name, family, tier, tags, description = DETAILS[model_id]
        models.append({"id": model_id.lower(), "researchId": model_id, "name": name, "family": family,
                       "tier": tier, "tags": tags, "description": description, "quant": "Q4_K_M",
                       "bytes": checked["bytes"], "sizeIsApproximate": False,
                       "url": checked["pinned_url"], "sha256": checked["sha256"], "revision": checked["revision"],
                       "sourceUrl": "https://huggingface.co/" + checked["repository"], "filename": checked["filename"],
                       "catalogueCheckedAt": audit["checked_at"],
                       "uncensored": {"declared": True, "basis": declaration["basis"], "method": declaration["method"],
                                      "summary": declaration["summary"], "evidenceUrl": declaration["author_card_url"],
                                      "upstreamUrl": "https://huggingface.co/" + declaration["author_repository"], "refusalRateTested": False},
                       "recommended": model_id in ("M08", "M06", "M01"), "deviceTested": False})
    output = {"version": 4, "updated": "2026-10-27", "scope": "local-models-with-uncensored-tags", "discovery": "huggingface-hub-paginated", "models": models}
    path = ROOT / "app/src/main/assets/models.json"; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"catalogue_models": len(models), "known_publisher_hashes": sum(bool(m["sha256"]) for m in models)}))


if __name__ == "__main__":
    main()

"""Read actual GGUF architecture metadata and compare it with the pinned engine source."""
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import struct
from audit_catalogue import request

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "b29c606e28a01b1bc8c1351026a0fa6e616bf6c4"


def main():
    url = "https://api.github.com/repos/ggml-org/llama.cpp/contents/src/llama-arch.cpp?ref=" + COMMIT
    _, _, raw, _ = request(url)
    source_bytes = base64.b64decode(json.loads(raw)["content"])
    source = source_bytes.decode("utf-8")
    cache = ROOT / "build/catalogue-audit"; cache.mkdir(parents=True, exist_ok=True)
    (cache / "llama-arch.cpp").write_bytes(source_bytes)
    native = (ROOT / "app/src/main/jniLibs/arm64-v8a/libllama.so").read_bytes()
    models = json.loads((ROOT / "app/src/main/assets/models.json").read_text(encoding="utf-8"))["models"]
    def probe(model):
        address = model["url"].replace("https://huggingface.co/", "https://hf-mirror.com/")
        _, _, raw, _ = request(address, {"Range": "bytes=0-255", "Accept-Encoding": "identity"}, limit=256)
        assert raw[:4] == b"GGUF"
        size = struct.unpack_from("<Q", raw, 24)[0]; offset = 32
        key = raw[offset:offset + size].decode(); offset += size
        kind = struct.unpack_from("<I", raw, offset)[0]; offset += 4
        assert key == "general.architecture" and kind == 8
        size = struct.unpack_from("<Q", raw, offset)[0]; offset += 8
        architecture = raw[offset:offset + size].decode()
        return {"id": model["id"], "architecture": architecture, "pinned_url": model["url"],
                "present_in_pinned_upstream_architecture_map": bool(re.search(r'LLM_ARCH_\w+\s*,\s*"' + re.escape(architecture) + '"', source)),
                "architecture_string_present_in_packaged_library": architecture.encode() + b"\0" in native}
    with ThreadPoolExecutor(max_workers=3) as pool: rows = list(pool.map(probe, models))
    assert all(row["present_in_pinned_upstream_architecture_map"] and row["architecture_string_present_in_packaged_library"] for row in rows)
    record = {"checked_at": datetime.now(timezone.utc).isoformat(), "upstream_commit": COMMIT, "upstream_source_url": url,
              "upstream_source_sha256": hashlib.sha256(source_bytes).hexdigest(), "prefix_bytes_per_model": 256,
              "model_load_tested": False, "models": rows}
    (ROOT / "catalogue/architecture-check.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"architectures": sorted(set(r["architecture"] for r in rows)), "models_checked": len(rows), "model_load_tested": False}))


if __name__ == "__main__": main()

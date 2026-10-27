"""Collect pinned source notices for the compiled Nano worker and register its shared ORT dependency."""
import hashlib
import json
from pathlib import Path
from evidence import current
from fetch_moss_nano import validate_sources
from native_payload import engine_files

ROOT = Path(__file__).resolve().parents[1]


def main():
    lock = json.loads((ROOT / "third_party/moss-nano-source-lock.json").read_text(encoding="utf-8"))
    receipt = json.loads((ROOT / "build/moss-nano-build-info.json").read_text(encoding="utf-8"))
    current(receipt["source_inputs"])
    if validate_sources(lock) != receipt["sources"]: raise RuntimeError("Source notices differ from the compiled engine")
    output = ROOT / "third_party/notices"; records = []
    for source in lock["sources"]:
        for item in source["notices"]:
            data = (ROOT / "build/native-src" / source["name"] / item["path"]).read_bytes()
            if hashlib.sha256(data).hexdigest() != item["sha256"] or Path(item["output"]).name != item["output"]: raise RuntimeError("Pinned source notice changed")
            (output / item["output"]).write_bytes(data)
            records.append({"file": item["output"], "sha256": item["sha256"], "source": source["url"] + "/blob/" + source["revision"] + "/" + item["path"]})
    notices = {r["file"]: r["sha256"] for r in records}
    for name in ("sd-nlohmann-json-LICENSE.txt", "sd-NDK-LLVM-NOTICE.txt"):
        notices[name] = hashlib.sha256((output / name).read_bytes()).hexdigest()
    engine = {k: receipt[k] for k in ("engine", "file", "source_revision", "abi", "backend", "ndk", "sha256", "bytes", "android_api_notes", "dependencies")}
    engine["notices"] = notices
    path = ROOT / "third_party/engine-lock.json"; engines = json.loads(path.read_text(encoding="utf-8"))
    engines["engines"] = [e for e in engines["engines"] if e["engine"] != engine["engine"]] + [engine]
    engine_files(engines["engines"])
    path.write_text(json.dumps(engines, indent=2) + "\n", encoding="utf-8")
    (output / "moss-sources.json").write_text(json.dumps({"sources": receipt["sources"], "files": records, "model_assets": False}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"collected_notices": len(records), "engine": engine["engine"], "shared_onnxruntime": True}))


if __name__ == "__main__": main()

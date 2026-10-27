"""Resolve shared native dependencies without allowing conflicting bytes or worker aliases."""
from pathlib import PurePosixPath


def engine_files(engines):
    workers, ids = set(), set()
    for engine in engines:
        if engine["file"] in workers or engine["engine"] in ids: raise RuntimeError("Duplicate native worker or engine")
        workers.add(engine["file"]); ids.add(engine["engine"])
    files = {}
    for engine in engines:
        for item in [engine] + engine.get("dependencies", []):
            name = item["file"]
            if not name or PurePosixPath(name).name != name or "\\" in name or ":" in name: raise RuntimeError("Invalid native dependency name")
            if item is not engine and name in workers: raise RuntimeError("A dependency cannot alias a worker")
            identity = {k: item.get(k, [28] if k == "android_api_notes" else None) for k in ("sha256", "bytes", "android_api_notes")}
            if name in files:
                previous = {k: files[name].get(k, [28] if k == "android_api_notes" else None) for k in identity}
                if identity != previous: raise RuntimeError("Native engines require conflicting shared dependencies: " + name)
            else: files[name] = item
    return list(files.values())

"""Inspect live HF metadata and real GGUF byte ranges without downloading weights."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/catalogue-audit"


def request(url, headers=None, limit=8 * 1024 * 1024):
    request = urllib.request.Request(url, headers={"User-Agent": "LMA-catalogue-audit/0.1", **(headers or {})})
    with urllib.request.urlopen(request, timeout=35) as response:
        data = response.read(limit)
        return response.status, dict(response.headers), data, response.url


def inspect(model, origin):
    result = {"id": model["id"], "name": model["name"], "url": model["url"], "metadata_origin": origin}
    try:
        path = urllib.parse.urlparse(model["url"]).path.strip("/").split("/")
        repository = "/".join(path[:2]); filename = "/".join(path[4:])
        revision = model.get("revision", "")
        metadata_url = origin + "/api/models/" + repository + ("/revision/" + revision if revision else "") + "?blobs=true"
        _, _, data, _ = request(metadata_url)
        info = json.loads(data)
        (OUT / (model["id"] + "-metadata.json")).write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        file = next((item for item in info["siblings"] if item["rfilename"] == filename), None)
        if file is None: raise ValueError("Selected filename is missing from the repository revision: " + filename)
        lfs = file.get("lfs", {})
        result.update(repository=repository, filename=filename, revision=info["sha"], bytes=lfs.get("size", file.get("size")), sha256=lfs.get("sha256", ""),
                      previous_sha256=model.get("sha256", ""), sha_matches=not model.get("sha256") or lfs.get("sha256") == model["sha256"])
        pinned = "https://huggingface.co/" + repository + "/resolve/" + info["sha"] + "/" + urllib.parse.quote(filename)
        result["pinned_url"] = pinned
        code, headers, prefix, _ = request(pinned.replace("https://huggingface.co", origin), {"Range": "bytes=0-63", "Accept-Encoding": "identity"}, limit=64)
        result.update(range_status=code, content_range=headers.get("Content-Range", headers.get("content-range", "")), prefix_hex=prefix[:24].hex(), gguf_header=prefix[:4] == b"GGUF")
        if prefix[:4] == b"GGUF" and len(prefix) >= 24:
            import struct
            result["gguf_version"], result["tensor_count"], result["metadata_count"] = struct.unpack_from("<IQQ", prefix, 4)
        result["total_size_matches_range"] = result["content_range"] == "bytes 0-63/" + str(result["bytes"])
        result["ok"] = result["gguf_header"] and result["sha_matches"] and bool(result.get("sha256")) and result["total_size_matches_range"] and result.get("gguf_version") == 3 and result.get("tensor_count", 0) > 0
    except Exception as error:
        result["error"] = str(error) or repr(error); result["ok"] = False
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", nargs="*")
    parser.add_argument("--origin", choices=["https://huggingface.co", "https://hf-mirror.com"], default="https://huggingface.co")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    models = json.loads((ROOT / "app/src/main/assets/models.json").read_text(encoding="utf-8"))["models"]
    if args.ids: models = [m for m in models if m["id"] in args.ids]
    results = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(inspect, m, args.origin): m for m in models}
        for future in as_completed(futures):
            result = future.result(); results.append(result)
            print(json.dumps(result, ensure_ascii=True), flush=True)
    record = {"checked_at": datetime.now(timezone.utc).isoformat(), "weight_files_downloaded": False, "range_bytes_per_model": 64,
              "models": sorted(results, key=lambda r: r["id"]), "passed": sum(r["ok"] for r in results), "total": len(results)}
    suffix = "mirror" if "hf-mirror" in args.origin else "primary"
    (OUT / (suffix + ("-results.json" if not args.ids else "-subset-results.json"))).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": record["passed"], "total": record["total"]}))


if __name__ == "__main__":
    main()

"""Collect native dependency license notices from pinned upstream sources."""
import json
import base64
from pathlib import Path
import re
import urllib.request
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "third_party/notices"
CACHE = ROOT / "third_party/cache/notices"
COMMIT = "b29c606e28a01b1bc8c1351026a0fa6e616bf6c4"
BASE = "https://raw.githubusercontent.com/ggml-org/llama.cpp/" + COMMIT + "/"


def fetch(url, name):
    path = CACHE / name
    if not path.exists():
        if url.startswith("https://raw.githubusercontent.com/"):
            relative = url.split("raw.githubusercontent.com/", 1)[1].split("/", 3)
            owner, repository, ref, resource = relative
            api = "https://api.github.com/repos/" + owner + "/" + repository + "/contents/" + urllib.parse.quote(resource) + "?ref=" + urllib.parse.quote(ref)
            request = urllib.request.Request(api, headers={"User-Agent": "LMA-build/0.1"})
            with urllib.request.urlopen(request, timeout=30) as response: record = json.load(response)
            if record.get("encoding") != "base64":
                request = urllib.request.Request(record["git_url"], headers={"User-Agent": "LMA-build/0.1"})
                with urllib.request.urlopen(request, timeout=30) as response: record = json.load(response)
            path.write_bytes(base64.b64decode(record["content"]))
        else:
            request = urllib.request.Request(url, headers={"User-Agent": "LMA-build/0.1"})
            with urllib.request.urlopen(request, timeout=30) as response: path.write_bytes(response.read())
    return path.read_text(encoding="utf-8", errors="replace")


def main():
    OUT.mkdir(parents=True, exist_ok=True); CACHE.mkdir(parents=True, exist_ok=True)
    sources = []
    for name, relative in [
        ("cpp-httplib-LICENSE.txt", "vendor/cpp-httplib/LICENSE"),
        ("rotate-bits-LICENSE.txt", "vendor/hash/rotate-bits/LICENSE.md"),
        ("sha256-LICENSE.txt", "vendor/hash/sha256/LICENSE"),
        ("xxhash-LICENSE.txt", "vendor/hash/xxhash/LICENSE"),
    ]:
        url = BASE + relative
        (OUT / name).write_text(fetch(url, name), encoding="utf-8")
        sources.append({"file": name, "url": url})
    for name, relative in [
        ("stb-image-LICENSE.txt", "vendor/stb/stb_image.h"),
        ("miniaudio-LICENSE.txt", "vendor/miniaudio/miniaudio.h"),
        ("subprocess-LICENSE.txt", "vendor/sheredom/subprocess.h"),
    ]:
        url = BASE + relative
        header = fetch(url, name + ".source")
        blocks = re.findall(r"/\*.*?\*/", header, re.DOTALL)
        notices = [b for b in blocks if "Permission is hereby granted" in b or "This is free and unencumbered software" in b]
        if not notices: raise ValueError("License block not found: " + relative)
        (OUT / name).write_text("\n\n".join(notices) + "\n", encoding="utf-8")
        sources.append({"file": name, "url": url})
    name = "nlohmann-json-LICENSE.txt"
    header = fetch(BASE + "vendor/nlohmann/json.hpp", "json.hpp")
    version = re.search(r"version\s+([0-9]+\.[0-9]+\.[0-9]+)", header[:2000]).group(1)
    url = "https://raw.githubusercontent.com/nlohmann/json/v" + version + "/LICENSE.MIT"
    (OUT / name).write_text(fetch(url, name), encoding="utf-8")
    sources.append({"file": name, "url": url, "vendor_header_version": version})
    for component in ["libcxx", "libcxxabi", "libunwind"]:
        name = component + "-LICENSE.txt"
        url = "https://raw.githubusercontent.com/llvm/llvm-project/llvmorg-21.1.0/" + component + "/LICENSE.TXT"
        (OUT / name).write_text(fetch(url, name), encoding="utf-8")
        sources.append({"file": name, "url": url, "note": "Standard LLVM runtime license text; provider does not record a separate C++ runtime commit"})
    (OUT / "sources.json").write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"dependency_notices": len(sources)}))


if __name__ == "__main__":
    main()

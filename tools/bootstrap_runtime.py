"""Fetch the pinned Android llama-server bundle without a virtualized toolchain."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "third_party" / "cache"
LIBS = ROOT / "app" / "src" / "main" / "jniLibs" / "arm64-v8a"
RELEASE_API = "https://api.github.com/repos/ArkaneFans/servllama/releases/tags/1.2.2"
ASSET_NAME = "llama-server-v0.4.1-android-arm64-v8a.zip"
PINNED_SHA256 = "551e5be8494bd2ae9955992faaaca1a4f5cf29e3a97f90d2e04205eb460fcde6"
CPU_LIBS = {"libllama-server.so", "libllama-server-impl.so", "libllama.so", "libllama-common.so", "libggml.so", "libggml-base.so", "libmtmd.so"}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "LMA-Android-build/0.1"})
    with urllib.request.urlopen(req, timeout=45) as response:
        return response.read()


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    release_file = CACHE / "runtime-release.json"
    if release_file.exists():
        release = json.loads(release_file.read_text(encoding="utf-8"))
    else:
        release = json.loads(fetch(RELEASE_API))
        release_file.write_text(json.dumps(release, ensure_ascii=False, indent=2), encoding="utf-8")
    asset = next(a for a in release["assets"] if a["name"] == ASSET_NAME)
    archive = CACHE / ASSET_NAME
    if not archive.exists():
        print("Downloading pinned Android runtime bundle", flush=True)
        archive.write_bytes(fetch(asset["browser_download_url"]))
    payload = archive.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != PINNED_SHA256:
        raise ValueError("Archive differs from the pinned LMA runtime")
    expected = asset.get("digest")
    if expected and expected != "sha256:" + digest:
        raise ValueError("Runtime release digest mismatch")
    if len(payload) != asset["size"]:
        raise ValueError("Runtime release size mismatch")
    LIBS.mkdir(parents=True, exist_ok=True)
    files = []
    entries = []
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            if entry.is_dir():
                continue
            if entry.filename.endswith(".tar.gz"):
                with tarfile.open(fileobj=io.BytesIO(bundle.read(entry)), mode="r:gz") as nested:
                    for member in nested.getmembers():
                        if member.isfile():
                            entries.append((member.name, nested.extractfile(member).read()))
            else:
                entries.append((entry.filename, bundle.read(entry)))
    for path, content in entries:
        name = Path(path).name
        if name.endswith(".so") and name.startswith("lib"):
            if name not in CPU_LIBS and not name.startswith("libggml-cpu-android_arm"):
                # LMA currently ships the CPU backend only. Keep optional GPU/DSP
                # modules out of the APK instead of probing unsupported drivers.
                if (LIBS / name).is_file(): (LIBS / name).unlink()
                continue
            if not content.startswith(b"\x7fELF"):
                raise ValueError(f"Not an ELF native library: {name}")
            (LIBS / name).write_bytes(content)
            files.append({"name": name, "size": len(content), "sha256": hashlib.sha256(content).hexdigest()})
        elif name in ("BUILD_INFO.json", "SHA256SUMS", "LLAMA_CPP_LICENSE"):
            (ROOT / "third_party" / name).write_bytes(content)
    if not any(f["name"] == "libllama-server.so" for f in files):
        raise ValueError("Bundle does not contain packaged llama-server")
    record = {"runtime": "llama.cpp", "version": "v0.4.1", "provider": "ArkaneFans/servllama 1.2.2 release native bundle",
              "asset_url": asset["browser_download_url"], "asset_sha256": digest,
              "publisher_digest_verified": bool(expected), "backend": "CPU only", "files": files,
              "downloaded_model_weights": False, "executed_android_code_on_host": False}
    (ROOT / "third_party" / "runtime-lock.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"runtime_files": len(files), "archive_bytes": len(payload), "sha256": digest, "publisher_digest_verified": bool(expected)}))
    for item in files:
        print(item["name"], item["size"])


if __name__ == "__main__":
    main()

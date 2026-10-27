"""Fetch pinned code-only Android TTS libraries and matching public C headers; no models."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", choices=("https", "ssh"), default="https")
    args = parser.parse_args()
    lock = json.loads((ROOT / "third_party/tts-source-lock.json").read_text(encoding="utf-8"))
    source = ROOT / "build/native-src/sherpa-onnx"
    source.mkdir(parents=True, exist_ok=True)
    if not (source / ".git").is_dir():
        if any(source.iterdir()):
            raise RuntimeError("TTS source cache is nonempty and is not a Git checkout")
        subprocess.run(["git", "init"], cwd=source, check=True, capture_output=True)
        remote = lock["source_url"] + ".git" if args.transport == "https" else "git@github.com:k2-fsa/sherpa-onnx.git"
        subprocess.run(["git", "remote", "add", "origin", remote], cwd=source, check=True)
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=source, text=True).strip():
        raise RuntimeError("TTS source cache has local changes; refusing to overwrite")
    revision = lock["source_revision"]
    if subprocess.run(["git", "cat-file", "-e", revision + "^{commit}"], cwd=source, capture_output=True).returncode:
        subprocess.run(["git", "fetch", "--depth", "1", "origin", revision], cwd=source, check=True, timeout=180)
    subprocess.run(["git", "checkout", "--detach", revision], cwd=source, check=True, capture_output=True)
    archive = ROOT / "build/native-deps/sherpa-onnx-v2.0.1-android.tar.bz2"
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.is_file():
        part = archive.with_suffix(".part")
        request = urllib.request.Request(lock["archive"]["url"], headers={"User-Agent": "LMA-native-bootstrap"})
        with urllib.request.urlopen(request, timeout=40) as response, part.open("wb") as stream:
            while data := response.read(1024 * 1024): stream.write(data)
        if part.stat().st_size != lock["archive"]["bytes"] or hashlib.sha256(part.read_bytes()).hexdigest() != lock["archive"]["sha256"]:
            raise RuntimeError("Upstream TTS code archive hash mismatch")
        part.replace(archive)
    if archive.stat().st_size != lock["archive"]["bytes"] or hashlib.sha256(archive.read_bytes()).hexdigest() != lock["archive"]["sha256"]:
        raise RuntimeError("TTS code archive changed; refusing extraction")
    target = ROOT / "build/native-deps/sherpa-onnx-v2.0.1"
    target.mkdir(exist_ok=True)
    wanted = {"jniLibs/arm64-v8a/" + d["file"] for d in lock["dependencies"]}
    with tarfile.open(archive) as tar:
        members = [m for m in tar.getmembers() if m.name.removeprefix("./") in wanted]
        if {m.name.removeprefix("./") for m in members} != wanted or len(members) != len(wanted) or not all(m.isfile() for m in members):
            raise RuntimeError("TTS archive does not contain the exact reviewed native libraries")
        tar.extractall(target, members=members, filter="data")
    for dependency in lock["dependencies"]:
        path = target / "jniLibs/arm64-v8a" / dependency["file"]
        if path.stat().st_size != dependency["bytes"] or hashlib.sha256(path.read_bytes()).hexdigest() != dependency["sha256"]:
            raise RuntimeError("TTS dependency hash mismatch")
    print(json.dumps({"source_revision": revision, "code_only": True, "model_assets_downloaded": False}))


if __name__ == "__main__":
    main()

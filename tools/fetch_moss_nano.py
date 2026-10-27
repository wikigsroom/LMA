"""Fetch pinned code-only sources for the Android MOSS Nano adapter. No model repositories."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def validate_sources(lock):
    for source in lock["sources"]:
        path = ROOT / "build/native-src" / source["name"]
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
        if revision != source["revision"] or subprocess.check_output(["git", "status", "--porcelain"], cwd=path, text=True).strip():
            raise RuntimeError("Native source cache is not the clean pinned revision: " + source["name"])
        for file, digest in source["reviewed_files"].items():
            if hashlib.sha256((path / file).read_bytes()).hexdigest() != digest:
                raise RuntimeError("Reviewed native source changed: " + file)
    return {s["name"]: s["revision"] for s in lock["sources"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", choices=("https", "ssh"), default="https")
    args = parser.parse_args()
    lock = json.loads((ROOT / "third_party/moss-nano-source-lock.json").read_text(encoding="utf-8"))
    for source in lock["sources"]:
        path = ROOT / "build/native-src" / source["name"]
        path.mkdir(parents=True, exist_ok=True)
        if not (path / ".git").is_dir():
            if any(path.iterdir()): raise RuntimeError("Nonempty native cache is not a checkout")
            subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
            remote = source["url"] + ".git" if args.transport == "https" else source["url"].replace("https://github.com/", "git@github.com:") + ".git"
            subprocess.run(["git", "remote", "add", "origin", remote], cwd=path, check=True, capture_output=True)
        if subprocess.check_output(["git", "status", "--porcelain"], cwd=path, text=True).strip():
            raise RuntimeError("Refusing to overwrite changed native sources")
        revision = source["revision"]
        if subprocess.run(["git", "cat-file", "-e", revision + "^{commit}"], cwd=path, capture_output=True).returncode:
            subprocess.run(["git", "fetch", "--depth", "1", "origin", revision], cwd=path, check=True, timeout=180)
        if source["sparse"]:
            subprocess.run(["git", "sparse-checkout", "set", "--no-cone", *source["sparse"]], cwd=path, check=True, capture_output=True)
        subprocess.run(["git", "checkout", "--detach", revision], cwd=path, check=True, capture_output=True)
    print(json.dumps({"sources": validate_sources(lock), "production_model_assets_downloaded": False}))


if __name__ == "__main__": main()

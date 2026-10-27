"""Fetch exact public upstream code into the project-local ignored native build cache."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def run(args, cwd):
    subprocess.run(args, cwd=cwd, check=True, timeout=180)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", choices=("https", "ssh"), default="https")
    args = parser.parse_args()
    engine = json.loads((ROOT / "third_party/engine-lock.json").read_text(encoding="utf-8"))["engines"][0]
    target = ROOT / "build/native-src/sd-cpp"
    target.mkdir(parents=True, exist_ok=True)
    if not (target / ".git").is_dir():
        if any(target.iterdir()):
            raise RuntimeError("Source cache is nonempty and is not a Git repository; preserve and inspect it")
        run(["git", "init"], target)
        remote = "https://github.com/leejet/stable-diffusion.cpp.git" if args.transport == "https" else "git@github.com:leejet/stable-diffusion.cpp.git"
        run(["git", "remote", "add", "origin", remote], target)
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=target, text=True).strip():
        raise RuntimeError("Pinned source cache has local changes; refusing to overwrite them")
    revision = engine["source_revision"]
    if subprocess.run(["git", "cat-file", "-e", revision + "^{commit}"], cwd=target, capture_output=True).returncode:
        run(["git", "fetch", "--depth", "1", "origin", revision], target)
    run(["git", "checkout", "--detach", revision], target)
    options = ["-c", "url.git@github.com:.insteadOf=https://github.com/"] if args.transport == "ssh" else []
    run(["git", *options, "submodule", "update", "--init", "--depth", "1", "ggml"], target)
    actual = subprocess.check_output(["git", "-C", "ggml", "rev-parse", "HEAD"], cwd=target, text=True).strip()
    if actual != engine["ggml_revision"]:
        raise RuntimeError("ggml submodule differs from the reviewed source revision")
    print(json.dumps({"source_revision": revision, "ggml_revision": actual, "model_assets_downloaded": False}))


if __name__ == "__main__":
    main()

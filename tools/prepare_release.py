"""Prepare a versioned, hash-checked release directory; never publishes anything."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
from evidence import version, current

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    release = version()
    if "-dev" in release:
        raise RuntimeError("Development builds are not complete Release candidates. Program-only validation does not waive missing implementation; see docs/PROGRAM_VALIDATION.md")
    tag = "v" + release
    dist = ROOT / "dist"
    output = dist / "releases" / tag
    output.mkdir(parents=True, exist_ok=True)
    build = json.loads((dist / "build-info.json").read_text(encoding="utf-8"))
    validation = json.loads((dist / "validation.json").read_text(encoding="utf-8"))
    current(build["input_fingerprint"])
    assert build["version"] == validation["version"] == release
    apk = dist / build["apk"]
    assert sha(apk) == build["sha256"] == validation["sha256"]
    source = dist / ("LMA-" + release + "-source.zip")
    assert (dist / (source.name + ".sha256")).read_text().split()[0] == sha(source)
    media = json.loads((ROOT / "docs/media/manifest.json").read_text(encoding="utf-8"))
    current(media["input_fingerprint"])
    for item in media["files"]:
        path = ROOT / "docs/media" / item["file"]
        assert path.stat().st_size == item["bytes"] and sha(path) == item["sha256"]
    notes = ROOT / "docs/releases" / (tag + ".md")
    assert notes.is_file() and release in notes.read_text(encoding="utf-8")
    files = [apk, dist / (apk.name + ".sha256"), source, dist / (source.name + ".sha256"),
             dist / "validation.json", dist / "build-info.json"]
    names = []
    for path in files:
        shutil.copy2(path, output / path.name)
        names.append(path.name)
    renamed = {"docs/media/lma-walkthrough.mp4": "LMA-" + release + "-demo.mp4",
               "docs/media/lma-walkthrough.gif": "LMA-" + release + "-demo.gif",
               "docs/media/lma-api-theme.gif": "LMA-" + release + "-api-theme.gif",
               "docs/media/lma-hf-local.gif": "LMA-" + release + "-hf-local.gif",
               "docs/media/lma-model-settings.gif": "LMA-" + release + "-model-settings.gif",
               notes.relative_to(ROOT).as_posix(): "RELEASE_NOTES.md"}
    for original, name in renamed.items():
        shutil.copy2(ROOT / original, output / name)
        names.append(name)
    verification_name = "LMA-" + release + "-verification.zip"
    with zipfile.ZipFile(output / verification_name, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((ROOT / "verification").glob("*")):
            if path.is_file():
                archive.write(path, "verification/" + path.name)
        archive.write(ROOT / "docs/media/manifest.json", "media-manifest.json")
    names.append(verification_name)
    names.sort()
    (output / "SHA256SUMS").write_text("".join(sha(output / name) + "  " + name + "\n" for name in names), encoding="utf-8")
    names.append("SHA256SUMS")
    assets = [{"name": name, "bytes": (output / name).stat().st_size, "sha256": sha(output / name)} for name in names]
    manifest = {"repository": "wikigsroom/LMA", "version": release, "tag": tag,
                "title": "LMA " + tag + " · Local Models & HF / 本地模型工作台",
                "prerelease": True, "notes": "docs/releases/" + tag + ".md", "assets": assets,
                "apk_sha256": build["sha256"], "physical_device_tested": False,
                "phone_inference_tested": False, "background_endurance_tested": False,
                "media_uses_simulated_native_state": True,
                "signing_material_included": False, "model_weights_included": False}
    (output / "release-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"tag": tag, "directory": output.relative_to(ROOT).as_posix(), "assets": len(assets) + 1,
                      "bytes": sum(a["bytes"] for a in assets) + (output / "release-manifest.json").stat().st_size,
                      "prerelease": True, "published": False}, ensure_ascii=True))


if __name__ == "__main__":
    main()

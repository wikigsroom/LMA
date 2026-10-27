"""Check public files, local documentation links, evidence and prepared release bytes."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
from urllib.parse import unquote, urlsplit
import zipfile
from evidence import version, current, build_inputs

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--published", action="store_true", help="Verify immutable source ZIP against its published tag after later documentation/tool updates")
    parser.add_argument("--development", action="store_true", help="Check a development checkpoint; never claims Release or phone readiness")
    args = parser.parse_args()
    run = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT, capture_output=True, check=True)
    names = sorted(set(run.stdout.decode("utf-8").strip("\0").split("\0")))
    assert names and all(names)
    protected_parts = {"signing", "build", "dist", ".git", "node_modules", "__pycache__", ".gradle", ".idea", ".vscode"}
    protected_suffixes = {".p12", ".jks", ".keystore", ".pem", ".key", ".gguf", ".part", ".idsig", ".apk", ".pyc"}
    secrets = [re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
               re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
               re.compile(rb"\blma_[a-f0-9]{48}\b")]
    for name in names:
        p = Path(name)
        assert not set(p.parts) & protected_parts, "Private/generated path staged: " + name
        assert p.suffix not in protected_suffixes and not p.name.startswith(".env"), "Private artifact: " + name
        assert p.parts[:2] != ("third_party", "cache") and "jniLibs" not in p.parts, "Re-fetchable native bytes staged: " + name
        data = (ROOT / p).read_bytes()
        assert len(data) < 25 * 1024 * 1024, "Oversized repository file: " + name
        assert not any(pattern.search(data) for pattern in secrets), "Possible secret in public file: " + name
    documents = [ROOT / name for name in names if name.endswith(".md") and (
        len(Path(name).parts) == 1 or name.startswith(("docs/", "verification/", ".github/")) or name == "third_party/README.md")]
    links = 0
    for document in documents:
        text = document.read_text(encoding="utf-8")
        targets = re.findall(r"!?\[[^\]]*\]\(([^)\n]+)\)", text)
        targets += re.findall(r'<img\b[^>]*\bsrc="([^"]+)"', text)
        for raw in targets:
            target = raw.strip().strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith("#"):
                continue
            target = unquote(parsed.path)
            if not target:
                continue
            resolved = (document.parent / target).resolve()
            assert resolved.is_relative_to(ROOT.resolve()) and resolved.exists(), "Broken local link: " + str(document.relative_to(ROOT)) + " -> " + target
            links += 1
    release = version()
    if args.development:
        assert not args.published and "-dev" in release
        directory = ROOT / "verification/development"
        status = json.loads((directory / "status.json").read_text(encoding="utf-8"))
        assert status["version"] == release and not status["release_ready"] and not status["all_selected_models_supported"]
        assert status["physical_device_tests"] == 0 and not status["model_inference_tested"]
        records = {name: json.loads((directory / name).read_text(encoding="utf-8")) for name in status["sources"]}
        for record in records.values(): current(record["input_fingerprint"])
        assert records["build-info.json"]["input_fingerprint"] == build_inputs()
        assert records["build-info.json"]["sha256"] == records["package.json"]["sha256"]
        assert records["foundation.json"]["passed"] >= 217 and records["foundation.json"]["recipe_integrity_assertions"] >= 87 and records["foundation.json"]["adapter_contract_assertions"] >= 45 and records["backend.json"]["passed"] >= 85 and records["hub.json"]["passed"] >= 74
        assert records["tts.json"]["passed"] >= 62 and records["tts.json"]["actual_host_child_processes"] and not records["tts.json"]["model_inference"]
        assert records["moss-nano.json"]["passed"] >= 190 and records["moss-nano.json"]["native_parser"]["native_host_execution"] and records["moss-nano.json"]["java_contracts"]["actual_host_hardlinks"] and not records["moss-nano.json"]["model_inference"]
        assert records["api.json"]["passed"] >= 67 and records["api.json"]["actual_socket_io"] and not records["api.json"]["physical_device"]
        assert records["ui.json"]["passed"] >= 112 and not records["ui.json"]["errors"] and records["lint.json"]["errors"] == 0
        media = json.loads((ROOT / "docs/media/development/manifest.json").read_text(encoding="utf-8"))
        current(media["input_fingerprint"])
        assert not media["android_device"] and not media["model_inference"] and media["browser_closed"] and not media["browser_errors"]
        for item in media["files"]:
            data = (ROOT / "docs/media/development" / item["file"]).read_bytes()
            assert len(data) == item["bytes"] and digest(data) == item["sha256"]
        result = {"development_only": True, "release_ready": False, "public_files": len(names), "documents": len(documents), "local_links": links, "version": release, "passed": True}
        (ROOT / "build/repository-check-development.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result)); return
    build = json.loads((ROOT / "dist/build-info.json").read_text(encoding="utf-8"))
    assert build["input_fingerprint"] == build_inputs() and build["version"] == release
    records = sorted((ROOT / "verification").glob("*.json"))
    assert len(records) >= 13
    for path in records:
        record = json.loads(path.read_text(encoding="utf-8"))
        if "input_fingerprint" in record:
            current(record["input_fingerprint"])
    validation = json.loads((ROOT / "verification/validation.json").read_text(encoding="utf-8"))
    assert validation["sha256"] == build["sha256"] and validation["version"] == release
    assert validation["physical_device_tests"] == 0 and not validation["phone_inference_tested"]
    media = json.loads((ROOT / "docs/media/manifest.json").read_text(encoding="utf-8"))
    current(media["input_fingerprint"])
    assert not media["android_device"] and not media["model_inference"] and not media["browser_errors"] and media["browser_closed"]
    for item in media["files"]:
        data = (ROOT / "docs/media" / item["file"]).read_bytes()
        assert len(data) == item["bytes"] and digest(data) == item["sha256"]
    source = ROOT / "dist" / ("LMA-" + release + "-source.zip")
    if args.published:
        snapshot = subprocess.run(["git", "archive", "--format=tar", "v" + release], cwd=ROOT, capture_output=True, check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(snapshot), mode="r:") as repository:
            expected_source = {member.name: repository.extractfile(member).read() for member in repository.getmembers() if member.isfile()}
    else:
        expected_source = {name: (ROOT / name).read_bytes() for name in names}
    with zipfile.ZipFile(source) as archive:
        members = archive.namelist()
        assert len(members) == len(set(members)) and archive.testzip() is None
        for name, data in expected_source.items():
            assert archive.read("LMA/" + name) == data, "Source ZIP differs from " + ("published tag: " if args.published else "current source: ") + name
        assert len([n for n in members if "/jniLibs/" in n and n.endswith(".so")]) == 14
        assert not any("/signing/" in n or "/cache/" in n or "/.git/" in n or "/node_modules/" in n for n in members)
    output = ROOT / "dist/releases" / ("v" + release)
    manifest = json.loads((output / "release-manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == release and manifest["repository"] == "wikigsroom/LMA" and manifest["prerelease"]
    for item in manifest["assets"]:
        data = (output / item["name"]).read_bytes()
        assert len(data) == item["bytes"] and digest(data) == item["sha256"]
    for line in (output / "SHA256SUMS").read_text().splitlines():
        expected, name = line.split("  ", 1)
        assert digest((output / name).read_bytes()) == expected
    result = {"public_files": len(names), "documents": len(documents), "local_links": links,
              "evidence_records": len(records), "screenshots": len(media["screenshots"]),
              "release_assets": len(manifest["assets"]) + 1, "source_matches_current_public_files": not args.published,
              "source_matches_published_tag": args.published,
              "private_files_excluded": True, "version": release, "passed": True}
    (ROOT / "build/repository-check.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()

"""Publish prepared assets with an authenticated GitHub CLI; default is read-only preview."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from evidence import version

ROOT = Path(__file__).resolve().parents[1]


def run(args, *, optional=False, timeout=120):
    result = subprocess.run([str(a) for a in args], cwd=ROOT, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=timeout)
    if result.returncode and not optional:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Command failed")
    return result


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gh", default=shutil.which("gh"), help="Existing authenticated GitHub CLI executable")
    parser.add_argument("--publish", action="store_true", help="Create/upload/publish the GitHub prerelease")
    args = parser.parse_args()
    release = version()
    directory = ROOT / "dist/releases" / ("v" + release)
    manifest_path = directory / "release-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["version"] == release and manifest["tag"] == "v" + release
    assert manifest["repository"] == "wikigsroom/LMA" and manifest["prerelease"] is True
    assets = list(manifest["assets"])
    assets.append({"name": manifest_path.name, "bytes": manifest_path.stat().st_size, "sha256": sha(manifest_path)})
    for asset in assets:
        assert Path(asset["name"]).name == asset["name"]
        path = directory / asset["name"]
        assert path.stat().st_size == asset["bytes"] and sha(path) == asset["sha256"]
    if not args.publish:
        print(json.dumps({"repository": manifest["repository"], "tag": manifest["tag"], "assets": len(assets),
                          "prerelease": True, "action": "preview only; use --publish after commit/tag push"}))
        return
    if not args.gh or not Path(args.gh).is_file():
        raise RuntimeError("Install/authenticate GitHub CLI, then provide --gh if not on PATH")
    assert not run(["git", "status", "--porcelain"]).stdout.strip(), "Commit the reviewed repository before publishing"
    run([sys.executable, ROOT / "tools/check_repository.py"])
    head = run(["git", "rev-parse", "HEAD"]).stdout.strip()
    tag = manifest["tag"]
    assert run(["git", "rev-list", "-n", "1", tag]).stdout.strip() == head, "Release tag must point to the reviewed HEAD"
    tag_object = run(["git", "rev-parse", "refs/tags/" + tag]).stdout.strip()
    refs = run(["git", "ls-remote", "--tags", "origin", "refs/tags/" + tag, "refs/tags/" + tag + "^{}"]).stdout
    remote_refs = dict(line.split()[::-1] for line in refs.splitlines())
    assert remote_refs.get("refs/tags/" + tag) == tag_object, "Push the exact reviewed tag first"
    repo = manifest["repository"]
    base = "repos/" + repo + "/releases"

    def gh(*command, optional=False, timeout=120):
        return run([args.gh, *command], optional=optional, timeout=timeout)

    def api(endpoint, optional=False):
        response = gh("api", endpoint, optional=optional)
        if response.returncode:
            if "404" in response.stderr:
                return None
            raise RuntimeError(response.stderr.strip())
        return json.loads(response.stdout)

    permissions = api("repos/" + repo).get("permissions", {})
    assert permissions.get("push"), "Authenticated account lacks repository write permission"
    remote = api(base + "/tags/" + tag, optional=True)
    if remote is None:
        gh("release", "create", tag, "--repo", repo, "--verify-tag", "--title", manifest["title"],
           "--notes-file", ROOT / manifest["notes"], "--draft", "--prerelease")
        remote = api(base + "/tags/" + tag)
    assert remote["prerelease"] is True, "Refuse to repurpose an existing stable release"
    known = {asset["name"]: asset for asset in remote["assets"]}
    for asset in assets:
        present = known.get(asset["name"])
        if present:
            assert present["state"] == "uploaded" and present["size"] == asset["bytes"], "Existing asset differs: " + asset["name"]
            assert present.get("digest") == "sha256:" + asset["sha256"], "Existing asset hash differs; use a new version: " + asset["name"]
        else:
            assert remote["draft"], "Published releases are immutable in this workflow; use a new version"
            print("Uploading " + asset["name"], flush=True)
            gh("release", "upload", tag, directory / asset["name"], "--repo", repo, timeout=300)
    remote = api(base + "/tags/" + tag)
    uploaded = {asset["name"]: asset for asset in remote["assets"]}
    assert set(uploaded) == {asset["name"] for asset in assets}, "Unexpected or missing release assets"
    for asset in assets:
        actual = uploaded[asset["name"]]
        assert actual["state"] == "uploaded" and actual["size"] == asset["bytes"]
        assert actual.get("digest") == "sha256:" + asset["sha256"], "Server digest mismatch: " + asset["name"]
    if remote["draft"]:
        print("All uploaded hashes match; publishing prerelease", flush=True)
        gh("release", "edit", tag, "--repo", repo, "--draft=false", "--prerelease")
    remote = api(base + "/tags/" + tag)
    assert not remote["draft"] and remote["prerelease"]
    receipt = {"repository": repo, "tag": tag, "commit": head, "url": remote["html_url"], "id": remote["id"],
               "published_at": remote["published_at"], "prerelease": True, "draft": False,
               "assets": assets, "all_server_digests_verified": True, "physical_device_tested": False}
    (directory / "publish-receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"url": receipt["url"], "assets": len(assets), "prerelease": True, "published": True}))


if __name__ == "__main__":
    main()

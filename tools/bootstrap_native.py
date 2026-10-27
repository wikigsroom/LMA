"""Fetch the pinned Windows NDK inside this project; no SDK mutation or virtualization."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NDK = {
    "version": "30.0.16248370",
    "directory": "android-ndk-r30",
    "filename": "android-ndk-r30-windows.zip",
    "bytes": 727980788,
    "sha1": "9bf167a1985fa7d4a036186b78f702eab9179408",
    "source": "https://developer.android.com/ndk/downloads",
    "urls": [
        "https://googledownloads.cn/android/repository/android-ndk-r30-windows.zip",
        "https://dl.google.com/android/repository/android-ndk-r30-windows.zip",
    ],
}
CMAKE = {"filename": "cmake-3.31.6-windows.zip", "bytes": 20491843, "sha1": "1efbef168291afc5d6ae449b1a016f8bf034b0fc", "source": "https://googledownloads.cn/android/repository/repository2-3.xml"}


def digest(path, kind="sha256"):
    checksum = hashlib.new(kind)
    with path.open("rb") as stream:
        while data := stream.read(1024 * 1024):
            checksum.update(data)
    return checksum.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", choices=NDK["urls"], default=NDK["urls"][0])
    args = parser.parse_args()
    directory = ROOT / "build/toolchain"
    directory.mkdir(parents=True, exist_ok=True)
    archive = directory / NDK["filename"]
    partial = archive.with_suffix(".part")
    if not archive.exists():
        offset = partial.stat().st_size if partial.exists() else 0
        request = urllib.request.Request(args.url, headers={"User-Agent": "LMA-native-build", "Accept-Encoding": "identity", **({"Range": f"bytes={offset}-"} if offset else {})})
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status == 200:
                offset = 0
            elif response.status != 206 or not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-"):
                raise RuntimeError("NDK download returned an invalid range")
            last = offset
            with partial.open("ab" if offset else "wb") as stream:
                total = offset
                while data := response.read(1024 * 1024):
                    stream.write(data)
                    total += len(data)
                    if total > NDK["bytes"]:
                        raise RuntimeError("NDK download exceeds its pinned size")
                    if total - last >= 32 * 1024 * 1024:
                        print(f"NDK download {total}/{NDK['bytes']} bytes", flush=True)
                        last = total
        if partial.stat().st_size != NDK["bytes"]:
            raise RuntimeError("NDK download incomplete; rerun to resume")
        if digest(partial, "sha1") != NDK["sha1"]:
            partial.unlink()
            raise RuntimeError("NDK official SHA1 mismatch; rejected")
        partial.replace(archive)
    if archive.stat().st_size != NDK["bytes"] or digest(archive, "sha1") != NDK["sha1"]:
        raise RuntimeError("Cached NDK does not match Google's pinned checksum")
    ndk = directory / NDK["directory"]
    receipt = directory / "ndk-receipt.json"
    if not (ndk / "source.properties").is_file():
        print("Extract verified Windows NDK", flush=True)
        with zipfile.ZipFile(archive) as package:
            for item in package.infolist():
                parts = PurePosixPath(item.filename).parts
                if not parts or parts[0] != NDK["directory"] or ".." in parts or "\\" in item.filename:
                    raise RuntimeError("NDK archive contains an unexpected path")
            package.extractall(directory)
    record = {**NDK, "sha256": digest(archive), "path": ndk.relative_to(ROOT).as_posix(), "virtualization_used": False}
    receipt.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    cmake_archive = directory / CMAKE["filename"]
    if not cmake_archive.exists():
        with urllib.request.urlopen("https://googledownloads.cn/android/repository/" + CMAKE["filename"], timeout=30) as response, cmake_archive.with_suffix(".part").open("wb") as stream:
            while data := response.read(1024 * 1024):
                stream.write(data)
        cmake_archive.with_suffix(".part").replace(cmake_archive)
    if cmake_archive.stat().st_size != CMAKE["bytes"] or digest(cmake_archive, "sha1") != CMAKE["sha1"]:
        raise RuntimeError("CMake official checksum mismatch")
    cmake_directory = directory / "cmake-3.31.6"
    if not (cmake_directory / "bin/cmake.exe").is_file():
        cmake_directory.mkdir(exist_ok=True)
        with zipfile.ZipFile(cmake_archive) as package:
            for item in package.infolist():
                parts = PurePosixPath(item.filename).parts
                if ".." in parts or "\\" in item.filename or item.filename.startswith("/"):
                    raise RuntimeError("CMake archive contains an unexpected path")
            package.extractall(cmake_directory)
    (directory / "cmake-receipt.json").write_text(json.dumps({**CMAKE, "sha256": digest(cmake_archive), "path": cmake_directory.relative_to(ROOT).as_posix()}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()

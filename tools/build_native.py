"""Compile pinned Android workers with Windows NDK tools, keeping all files in this project."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SD_REVISION = "be486498eadc29dc3cd234d944c2180ed42b1415"
GGML_REVISION = "a5915eb0e47adef21c3f25b889a008925ea838c2"


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT / "build/native-src/sd-cpp"), *args], cwd=ROOT, text=True).strip()


def logged(args, cwd, logfile):
    result = subprocess.run(args, cwd=cwd, capture_output=True)
    output = result.stdout + result.stderr
    with logfile.open("ab") as stream:
        stream.write(output)
    lines = output.decode("utf-8", errors="replace").splitlines()
    print("\n".join(lines[-20:]), flush=True)
    if result.returncode:
        raise RuntimeError(f"Native command failed ({result.returncode}); inspect {logfile}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    if os.name != "nt":
        raise RuntimeError("This build path requires native Windows tools")
    if args.jobs < 1 or args.jobs > 16:
        raise ValueError("Use 1 to 16 compiler jobs")
    if git("rev-parse", "HEAD") != SD_REVISION or git("-C", "ggml", "rev-parse", "HEAD") != GGML_REVISION:
        raise RuntimeError("Native source revision does not match the pinned build")
    if git("status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("Pinned upstream source has local modifications")
    # Some Windows CMake/LLVM probe parsers crash on non-ASCII paths. This temporary
    # filesystem alias points to this exact directory; no files leave the project.
    drive = next((letter + ":" for letter in "RSTUVWXYZ" if not Path(letter + ":/").exists()), None)
    if drive is None:
        raise RuntimeError("No unused drive letter is available for a temporary build path alias")
    subprocess.run(["subst", drive, str(ROOT)], check=True, capture_output=True)
    try:
        alias = drive + "/"
        cmake = alias + "build/toolchain/cmake-3.31.6/bin/cmake.exe"
        ninja = alias + "build/toolchain/cmake-3.31.6/bin/ninja.exe"
        ndk = alias + "build/toolchain/android-ndk-r30"
        output = alias + "build/native-arm64-cpu-r30"
        log = ROOT / "build/native-build.log"
        log.write_bytes(b"")
        configure = [cmake, "-S", alias + "native", "-B", output, "-G", "Ninja", "-DCMAKE_MAKE_PROGRAM=" + ninja,
                     "-DCMAKE_TOOLCHAIN_FILE=" + ndk + "/build/cmake/android.toolchain.cmake", "-DANDROID_ABI=arm64-v8a", "-DANDROID_PLATFORM=android-28",
                     "-DANDROID_STL=c++_static", "-DCMAKE_BUILD_TYPE=Release", "-DLMA_SD_SOURCE=" + alias + "build/native-src/sd-cpp", "-DLMA_SD_REVISION=" + SD_REVISION]
        logged(configure, alias, log)
        logged([cmake, "--build", output, "--target", "lma_sd_worker", "-j", str(args.jobs)], alias, log)
        binary = ROOT / "build/native-arm64-cpu-r30/liblma-sd.so"
        if not binary.is_file():
            raise RuntimeError("Native worker was not produced")
        llvm = ndk + "/toolchains/llvm/prebuilt/windows-x86_64/bin/"
        logged([llvm + "llvm-strip.exe", "--strip-unneeded", str(binary.relative_to(ROOT)).replace("\\", "/")], alias, log)
        data = binary.read_bytes()
        if data[:5] != b"\x7fELF\x02" or struct.unpack_from("<H", data, 18)[0] != 183:
            raise RuntimeError("Worker is not an Android ARM64 ELF")
        phoff = struct.unpack_from("<Q", data, 32)[0]
        phsize, phcount = struct.unpack_from("<HH", data, 54)
        alignments = [struct.unpack_from("<Q", data, phoff + i * phsize + 48)[0] for i in range(phcount) if struct.unpack_from("<I", data, phoff + i * phsize)[0] == 1]
        if not alignments or min(alignments) < 16384:
            raise RuntimeError("Worker does not meet the 16 KiB page alignment requirement")
        record = {"schema": "lma.native-build/1", "engine": "sd_cpp", "source_revision": SD_REVISION, "ggml_revision": GGML_REVISION,
                  "abi": "arm64-v8a", "min_sdk": 28, "ndk": "30.0.16248370", "backend": "cpu", "file": "liblma-sd.so",
                  "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "elf_load_alignment": alignments,
                  "vocabularies": "external_user_selected_components", "physical_device_tests": 0, "model_inference_tested": False,
                  "virtualization_used": False, "source_inputs": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT / "native").glob("*")) if p.is_file()}}
        target = ROOT / "app/src/main/jniLibs/arm64-v8a/liblma-sd.so"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(binary, target)
        (ROOT / "build/native-build-info.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(record), flush=True)
    finally:
        subprocess.run(["subst", drive, "/D"], check=True, capture_output=True)


if __name__ == "__main__":
    main()

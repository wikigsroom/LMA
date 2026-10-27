"""Build the Android ARM64 MOSS Nano host loop with native Windows NDK tools."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from evidence import fingerprint
from fetch_moss_nano import validate_sources
from verify_package import elf_info

ROOT = Path(__file__).resolve().parents[1]


def main():
    if os.name != "nt": raise RuntimeError("Use the native Windows toolchain")
    lock = json.loads((ROOT / "third_party/moss-nano-source-lock.json").read_text(encoding="utf-8"))
    sources = validate_sources(lock)
    if hashlib.sha256((ROOT / "build/native-src/sd-cpp/thirdparty/json.hpp").read_bytes()).hexdigest() != lock["json_header_sha256"]:
        raise RuntimeError("Pinned JSON header changed")
    dependency = lock["shared_dependency"]
    library = ROOT / "app/src/main/jniLibs/arm64-v8a" / dependency["file"]
    data = library.read_bytes(); dep_info = elf_info(data)
    if len(data) != dependency["bytes"] or hashlib.sha256(data).hexdigest() != dependency["sha256"] or dep_info["android_api_notes"] != dependency["android_api_notes"] or not dep_info["16k_elf_aligned"]:
        raise RuntimeError("Shared ONNX Runtime differs from the reviewed TTS dependency")
    if lock["onnxruntime_version"].encode() + b"\0" not in data: raise RuntimeError("Review the ONNX Runtime header/binary version pairing")
    ndk_bin = ROOT / "build/toolchain/android-ndk-r30/toolchains/llvm/prebuilt/windows-x86_64/bin"
    imports = subprocess.check_output([str(ndk_bin / "llvm-nm.exe"), "-D", "--undefined-only", str(library)], text=True)
    log_imports = {line.split()[-1] for line in imports.splitlines() if "__android_log_" in line}
    if not log_imports.issubset({"__android_log_print", "__android_log_vprint", "__android_log_write"}): raise RuntimeError("Review new ONNX Runtime diagnostic imports")
    inputs = fingerprint("native/moss_nano", "tools/build_moss_nano.py", "tools/fetch_moss_nano.py", "third_party/moss-nano-source-lock.json")
    drive = next((c + ":" for c in "RSTUVWXYZ" if not Path(c + ":/").exists()), None)
    if not drive: raise RuntimeError("No unused temporary path alias")
    subprocess.run(["subst", drive, str(ROOT)], check=True, capture_output=True)
    try:
        alias = drive + "/"; ndk = alias + "build/toolchain/android-ndk-r30"; cmake = alias + "build/toolchain/cmake-3.31.6/bin/cmake.exe"; output = alias + "build/moss-nano-arm64-cpu-r30"
        commands = [[cmake, "-S", alias + "native/moss_nano", "-B", output, "-G", "Ninja", "-DCMAKE_MAKE_PROGRAM=" + alias + "build/toolchain/cmake-3.31.6/bin/ninja.exe",
            "-DCMAKE_TOOLCHAIN_FILE=" + ndk + "/build/cmake/android.toolchain.cmake", "-DANDROID_ABI=arm64-v8a", "-DANDROID_PLATFORM=android-28", "-DANDROID_STL=c++_static", "-DCMAKE_BUILD_TYPE=Release",
            "-DLMA_SENTENCEPIECE_SOURCE=" + alias + "build/native-src/sentencepiece", "-DLMA_ORT_SOURCE=" + alias + "build/native-src/onnxruntime-headers", "-DLMA_ORT_LIBRARY=" + alias + "app/src/main/jniLibs/arm64-v8a/libonnxruntime.so",
            "-DLMA_SD_SOURCE=" + alias + "build/native-src/sd-cpp", "-DLMA_MOSS_REVISION=" + sources["moss-nano"]],
            [cmake, "--build", output, "--target", "lma_moss_nano_worker", "-j", "4"],
            [ndk + "/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-strip.exe", "--strip-unneeded", output + "/liblma-moss-nano.so"]]
        log = ROOT / "build/moss-nano-build.log"; log.write_bytes(b"")
        for command in commands:
            result = subprocess.run(command, cwd=alias, capture_output=True)
            with log.open("ab") as stream: stream.write(result.stdout + result.stderr)
            print("\n".join((result.stdout + result.stderr).decode("utf-8", errors="replace").splitlines()[-8:]), flush=True)
            if result.returncode: raise RuntimeError("MOSS Nano build failed; inspect build/moss-nano-build.log")
    finally:
        subprocess.run(["subst", drive, "/D"], check=True, capture_output=True)
    binary = ROOT / "build/moss-nano-arm64-cpu-r30/liblma-moss-nano.so"; data = binary.read_bytes(); info = elf_info(data)
    if not info["16k_elf_aligned"] or info["android_api_notes"] != [28] or info["interpreter"] != "/system/bin/linker64": raise RuntimeError("MOSS Nano worker ELF contract failed")
    exports = subprocess.check_output([str(ndk_bin / "llvm-nm.exe"), "-D", "--defined-only", str(binary)], text=True)
    if not log_imports.issubset({line.split()[-1] for line in exports.splitlines()}): raise RuntimeError("Missing process-local diagnostic interception")
    shutil.copy2(binary, library.parent / binary.name)
    receipt = {"schema": "lma.native-build/1", "engine": "moss_nano_ort", "file": binary.name, "source_revision": sources["moss-nano"], "sources": sources, "version": "nano-onnx-1",
        "abi": "arm64-v8a", "backend": "cpu", "ndk": "30.0.16248370", "min_sdk": 28, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "elf_load_alignment": info["load_segment_alignment"],
        "android_api_notes": [28], "dependencies": [dependency], "onnxruntime": lock["onnxruntime_version"], "source_inputs": inputs,
        "vocabularies": "external_user_selected_components", "physical_device_tests": 0, "model_inference_tested": False, "virtualization_used": False,
        "third_party_diagnostics": "private_stdout_stderr_and_process_local_liblog_interposition", "reviewed_log_imports": sorted(log_imports), "android_log_binding_tested": False}
    (ROOT / "build/moss-nano-build-info.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in receipt.items() if k not in ("source_inputs", "dependencies")}))


if __name__ == "__main__": main()

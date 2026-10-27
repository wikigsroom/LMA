"""Compile the actual Android ARM64 TTS worker with native Windows NDK tools."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from evidence import fingerprint
from verify_package import elf_info

ROOT = Path(__file__).resolve().parents[1]


def main():
    if os.name != "nt": raise RuntimeError("This path uses the native Windows NDK")
    lock = json.loads((ROOT / "third_party/tts-source-lock.json").read_text(encoding="utf-8"))
    source = ROOT / "build/native-src/sherpa-onnx"
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    if revision != lock["source_revision"] or subprocess.check_output(["git", "status", "--porcelain"], cwd=source, text=True).strip():
        raise RuntimeError("TTS source is not the clean pinned revision")
    header = source / "sherpa-onnx/c-api/c-api.h"
    if hashlib.sha256(header.read_bytes()).hexdigest() != lock["header_sha256"]: raise RuntimeError("TTS C ABI header changed")
    if hashlib.sha256((ROOT / "build/native-src/sd-cpp/thirdparty/json.hpp").read_bytes()).hexdigest() != lock["json_header_sha256"]: raise RuntimeError("Pinned JSON header changed")
    deps = ROOT / "build/native-deps/sherpa-onnx-v2.0.1/jniLibs/arm64-v8a"
    nm = ROOT / "build/toolchain/android-ndk-r30/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-nm.exe"
    log_imports = set()
    for dep in lock["dependencies"]:
        data = (deps / dep["file"]).read_bytes()
        info = elf_info(data)
        if len(data) != dep["bytes"] or hashlib.sha256(data).hexdigest() != dep["sha256"] or info["android_api_notes"] != dep["android_api_notes"] or not info["16k_elf_aligned"]:
            raise RuntimeError("TTS dependency does not match the reviewed binary")
        symbols = subprocess.check_output([str(nm), "-D", "--undefined-only", str(deps / dep["file"])], text=True)
        log_imports.update(line.split()[-1] for line in symbols.splitlines() if "__android_log_" in line)
    if log_imports != {"__android_log_print", "__android_log_vprint", "__android_log_write"}: raise RuntimeError("Review new upstream liblog imports before packaging")
    inputs = fingerprint("native/tts", "tools/build_tts.py", "tools/fetch_tts.py", "third_party/tts-source-lock.json")
    drive = next((c + ":" for c in "RSTUVWXYZ" if not Path(c + ":/").exists()), None)
    if not drive: raise RuntimeError("No unused temporary build path alias")
    subprocess.run(["subst", drive, str(ROOT)], check=True, capture_output=True)
    try:
        alias = drive + "/"
        ndk = alias + "build/toolchain/android-ndk-r30"
        cmake = alias + "build/toolchain/cmake-3.31.6/bin/cmake.exe"
        output = alias + "build/tts-arm64-cpu-r30"
        commands = [[cmake, "-S", alias + "native/tts", "-B", output, "-G", "Ninja", "-DCMAKE_MAKE_PROGRAM=" + alias + "build/toolchain/cmake-3.31.6/bin/ninja.exe",
                     "-DCMAKE_TOOLCHAIN_FILE=" + ndk + "/build/cmake/android.toolchain.cmake", "-DANDROID_ABI=arm64-v8a", "-DANDROID_PLATFORM=android-28", "-DANDROID_STL=c++_static",
                     "-DCMAKE_BUILD_TYPE=Release", "-DLMA_SHERPA_SOURCE=" + alias + "build/native-src/sherpa-onnx", "-DLMA_SHERPA_LIBS=" + alias + "build/native-deps/sherpa-onnx-v2.0.1/jniLibs/arm64-v8a",
                     "-DLMA_SD_SOURCE=" + alias + "build/native-src/sd-cpp", "-DLMA_SHERPA_REVISION=" + revision],
                    [cmake, "--build", output, "-j", "4"],
                    [ndk + "/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-strip.exe", "--strip-unneeded", output + "/liblma-tts.so"]]
        log = ROOT / "build/tts-build.log"; log.write_bytes(b"")
        for command in commands:
            result = subprocess.run(command, cwd=alias, capture_output=True)
            with log.open("ab") as stream: stream.write(result.stdout + result.stderr)
            print("\n".join((result.stdout + result.stderr).decode("utf-8", errors="replace").splitlines()[-8:]), flush=True)
            if result.returncode: raise RuntimeError("TTS native build failed; inspect build/tts-build.log")
    finally:
        subprocess.run(["subst", drive, "/D"], check=True, capture_output=True)
    binary = ROOT / "build/tts-arm64-cpu-r30/liblma-tts.so"
    data = binary.read_bytes(); info = elf_info(data)
    if not info["16k_elf_aligned"] or info["android_api_notes"] != [28] or info["interpreter"] != "/system/bin/linker64": raise RuntimeError("TTS worker ELF contract failed")
    exports = subprocess.check_output([str(nm), "-D", "--defined-only", str(binary)], text=True)
    if not log_imports.issubset({line.split()[-1] for line in exports.splitlines()}): raise RuntimeError("Worker does not export the required process-local log interception symbols")
    libs = ROOT / "app/src/main/jniLibs/arm64-v8a"
    for dep in lock["dependencies"]: shutil.copy2(deps / dep["file"], libs / dep["file"])
    shutil.copy2(binary, libs / binary.name)
    receipt = {"schema": "lma.native-build/1", "engine": "sherpa_tts", "file": binary.name, "source_revision": revision, "version": lock["version"],
               "abi": "arm64-v8a", "backend": "cpu", "ndk": "30.0.16248370", "min_sdk": 28, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
               "elf_load_alignment": info["load_segment_alignment"], "android_api_notes": [28], "dependencies": lock["dependencies"],
               "vocabularies": "external_user_selected_components", "physical_device_tests": 0, "model_inference_tested": False, "virtualization_used": False,
               "source_inputs": inputs, "third_party_diagnostics": "private_stdout_stderr_and_process_local_liblog_interposition", "reviewed_log_imports": sorted(log_imports), "android_log_binding_tested": False}
    (ROOT / "build/tts-build-info.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in receipt.items() if k not in ("source_inputs", "dependencies")}))


if __name__ == "__main__":
    main()

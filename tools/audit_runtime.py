"""Check launcher options and CPU discovery against the exact distributed engine commit.

This is static evidence: it never executes the Android ARM64 engine on the host.
"""
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from audit_catalogue import request
from evidence import fingerprint

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/runtime-source-audit"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    commit = json.loads((ROOT / "third_party/BUILD_INFO.json").read_text(encoding="utf-8"))["llamaCppCommit"]
    resources = ["common/arg.cpp", "ggml/src/ggml-backend-reg.cpp", "tools/server/server-http.cpp"]
    sources, provenance = {}, []
    for name in resources:
        url = "https://api.github.com/repos/ggml-org/llama.cpp/contents/" + name + "?ref=" + commit
        _, _, response, _ = request(url)
        raw = base64.b64decode(json.loads(response)["content"])
        (OUT / name.replace("/", "__")).write_bytes(raw)
        sources[name] = raw.decode("utf-8")
        provenance.append({"path": name, "url": url, "sha256": hashlib.sha256(raw).hexdigest()})
    engine = (ROOT / "app/src/main/java/com/lma/app/EngineHost.java").read_text(encoding="utf-8")
    flags = sorted(set(re.findall(r'(?:add\(command,|command\.add\()\s*"(-[^\"]+)"', engine)))
    assert len(flags) >= 15, "No complete production launcher command found"
    common = (ROOT / "app/src/main/jniLibs/arm64-v8a/libllama-common.so").read_bytes()
    for flag in flags:
        assert '"' + flag + '"' in sources["common/arg.cpp"], "Unknown engine option: " + flag
        assert flag.encode() + b"\0" in common, "Packaged engine does not contain the expected option: " + flag
    assert '.set_env("LLAMA_API_KEY")' in sources["common/arg.cpp"]
    assert 'builder.environment().put("LLAMA_API_KEY"' in engine
    assert '"Bearer "' in sources["tools/server/server-http.cpp"] and 'middleware_validate_api_key' in sources["tools/server/server-http.cpp"]
    registry = sources["ggml/src/ggml-backend-reg.cpp"]
    assert 'readlink("/proc/self/exe"' in registry and 'search_paths.push_back(get_executable_path())' in registry
    assert '"ggml_backend_score"' in registry and 'if (s > best_score)' in registry
    kernels = sorted((ROOT / "app/src/main/jniLibs/arm64-v8a").glob("libggml-cpu-*.so"))
    assert any(p.name == "libggml-cpu-android_armv8.0_1.so" for p in kernels)
    for kernel in kernels: assert b"ggml_backend_score\0" in kernel.read_bytes(), "Missing CPU feature score entry: " + kernel.name
    result = {"checked_at": datetime.now(timezone.utc).isoformat(), "upstream_commit": commit, "sources": provenance,
              "production_launcher_options": flags, "api_key_environment_matches": True,
              "cpu_discovery_in_executable_directory": True, "cpu_feature_score_exports": [p.name for p in kernels],
              "android_execution_tested": False, "input_fingerprint": fingerprint("app/src/main/java/com/lma/app/EngineHost.java", "app/src/main/jniLibs/arm64-v8a", "third_party/BUILD_INFO.json", "tools/audit_runtime.py")}
    (ROOT / "third_party/runtime-audit.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"launcher_options_checked": len(flags), "cpu_kernels_checked": len(kernels), "api_key_environment_matches": True, "android_execution_tested": False}))


if __name__ == "__main__": main()

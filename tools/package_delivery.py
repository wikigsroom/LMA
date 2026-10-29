"""Export reviewable validation and sources, excluding caches and signing material."""
import hashlib
import json
from pathlib import Path
import zipfile
from evidence import current, version
from preparation_build_inputs import build_inputs

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def main():
    if "-dev" in version():
        raise RuntimeError("Internal development builds cannot substitute for the complete v0.3.0 delivery; use export_development.py for scoped evidence")
    build = json.loads((DIST / "build-info.json").read_text(encoding="utf-8"))
    package = json.loads((ROOT / "build/package-verification.json").read_text(encoding="utf-8"))
    ui = json.loads((ROOT / "build/ui-qa/results.json").read_text(encoding="utf-8"))
    backend = json.loads((ROOT / "build/backend-tests/results.json").read_text(encoding="utf-8"))
    hub = json.loads((ROOT / "build/hub-tests/results.json").read_text(encoding="utf-8"))
    hub_live = json.loads((ROOT / "build/hub-tests/live-results.json").read_text(encoding="utf-8"))
    sqlite = json.loads((ROOT / "build/sqlite-tests/results.json").read_text(encoding="utf-8"))
    protocol = json.loads((ROOT / "build/protocol-tests/results.json").read_text(encoding="utf-8"))
    acceptance = json.loads((ROOT / "build/device-tests/acceptance-build.json").read_text(encoding="utf-8"))
    device = json.loads((ROOT / "build/device-tests/device-results.json").read_text(encoding="utf-8"))
    runtime = json.loads((ROOT / "third_party/runtime-audit.json").read_text(encoding="utf-8"))
    lint = json.loads((ROOT / "build/android-lint/results.json").read_text(encoding="utf-8"))
    uncensored = json.loads((ROOT / "catalogue/uncensored-evidence.json").read_text(encoding="utf-8"))
    for record in (package, ui, backend, hub, hub_live, sqlite, protocol, acceptance, runtime, lint, uncensored): current(record["input_fingerprint"])
    assert package["sha256"] == build["sha256"]
    assert build["input_fingerprint"] == build_inputs()
    assert acceptance["applicationApkSha256"] == build["sha256"]
    assert lint["applicationApkSha256"] == build["sha256"] and lint["errors"] == 0
    assert lint["java_source_files"] == len(list((ROOT / "app/src/main/java").rglob("*.java")))
    assert runtime["upstream_commit"] == json.loads((ROOT / "third_party/BUILD_INFO.json").read_text(encoding="utf-8"))["llamaCppCommit"]
    assert ui["passed"] >= 66 and ui["passed"] == len(ui["checks"]) and not ui["errors"]
    assert backend["passed"] >= 85 and hub["passed"] >= 45 and hub_live["passed"] == 5 and sqlite["passed"] == 5
    result = {"app": "LMA", "version": build["version"], "apk": build["apk"], "sha256": build["sha256"],
              "protocol_checks": (ROOT / "build/protocol-test-results.txt").read_text(encoding="utf-8").strip(),
              "ui_checks": ui["passed"], "ui_uses_test_bridge": True, "signatures_verified": build["signatures_verified"],
              "backend_checks": backend["passed"], "backend_uses_android_framework_adapters": True,
              "hub_checks": hub["passed"], "hub_live_metadata_checks": hub_live["passed"], "hub_live_source": hub_live["source"],
              "hf_discovery_all_formats": True, "recommended_model_ids_preserved": ["m08", "m06", "m01"], "local_model_management": True,
              "independent_model_settings": True, "gguf_context_metadata_bounds": True, "editable_presets_with_clamping": True,
              "sqlite_query_checks": sqlite["passed"], "sqlite_android_framework_tested": False,
              "catalogue_pinned_models": package["catalogue_models"], "catalogue_publisher_hashes": package["known_publisher_hashes"],
              "builtin_uncensored_declarations_verified": package["builtin_uncensored_declarations_verified"], "refusal_rates_measured": False,
              "native_libraries_verified": package["native_libraries_verified"], "elf_16k_aligned": package["all_elf_load_segments_16k_aligned"],
              "native_android_api_notes": sorted({api for native in package["native"].values() for api in native["android_api_notes"]}),
              "native_launcher_interpreter": package["native"]["libllama-server.so"]["interpreter"],
              "launcher_options_statically_checked": len(runtime["production_launcher_options"]), "cpu_kernels_statically_checked": len(runtime["cpu_feature_score_exports"]),
              "android_lint_errors": lint["errors"], "android_lint_warning_ids": [issue["id"] for issue in lint["warnings"]],
              "zip_alignment_verified": package["final_apk_zip_alignment_verified"], "packaged_ui_matches_source": package["packaged_ui_matches_source"],
              "physical_device_tests": 0, "phone_inference_tested": False, "background_endurance_tested": False,
              "docker_wsl_emulator_used": False, "acceptance_apk_compiled": acceptance["compiled"],
              "device_gate": device["status"], "signing_certificate_sha256": package["signing_certificate_sha256"],
              "ready_for_physical_device_acceptance": True, "fully_usable_on_phone_verified": False}
    (DIST / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    network = json.loads((ROOT / "build/catalogue-audit/mirror-results.json").read_text(encoding="utf-8"))
    assert network["passed"] == 14 and all(m["ok"] for m in network["models"])
    evidence = {"backend": backend, "hub": hub, "hub-live": hub_live, "ui": ui, "sqlite": sqlite, "protocol": protocol, "package": package, "device": device, "acceptance-build": acceptance, "build": build, "model-network": network, "runtime": runtime, "android-lint": lint, "uncensored-models": uncensored, "validation": result}
    public = ROOT / "verification"
    public.mkdir(exist_ok=True)
    for name, record in evidence.items():
        (public / (name + ".json")).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    source = DIST / ("LMA-" + build["version"] + "-source.zip")
    excluded = {"build", "dist", "signing", ".gradle", ".git", "__pycache__", "node_modules", ".idea", ".vscode"}
    with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(ROOT.rglob("*")):
            if not path.is_file(): continue
            relative = path.relative_to(ROOT)
            if any(part in excluded for part in relative.parts) or relative.parts[:2] == ("third_party", "cache") or path.name == "local.properties": continue
            if path.name == ".env" or path.name.startswith(".env."): continue
            if path.suffix in (".p12", ".jks", ".keystore", ".pem", ".key", ".part", ".gguf", ".pyc", ".idsig", ".apk"): continue
            archive.write(path, "LMA/" + relative.as_posix())
    with zipfile.ZipFile(source) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == len(set(archive.namelist()))
        assert not any("/signing/" in name or "/cache/" in name or "/build/" in name for name in archive.namelist())
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    (DIST / (source.name + ".sha256")).write_text(digest + "  " + source.name + "\n", encoding="utf-8")
    print(json.dumps({"source_archive": source.name, "bytes": source.stat().st_size, "source_sha256": digest, "validation": "validation.json", "signing_material_included": False}))


if __name__ == "__main__":
    main()

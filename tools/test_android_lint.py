"""Run the SDK's standalone Android Lint on every production Java and resource file.

Uses an explicit project descriptor for the native SDK build; never invokes
Gradle, an emulator or virtualization. Warnings remain in the exported report.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
from evidence import build_inputs, fingerprint

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/android-lint"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", default=os.environ.get("ANDROID_SDK_ROOT", str(Path(os.environ.get("LOCALAPPDATA", "C:/Users/carzy/AppData/Local")) / "Android/Sdk")))
    args = parser.parse_args()
    sdk = Path(args.sdk).resolve()
    lint = sdk / "cmdline-tools/latest/bin/lint.bat"
    if not lint.is_file():
        raise RuntimeError("Install Android SDK command-line tools, or choose their SDK with --sdk")
    build = json.loads((ROOT / "dist/build-info.json").read_text(encoding="utf-8"))
    assert build["input_fingerprint"] == build_inputs(), "Rebuild the application before checking it with Lint"
    assert (ROOT / "build/classes/com/lma/app/MainActivity.class").is_file(), "Compiled application classes are missing"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cache").mkdir(exist_ok=True)
    (OUT / "results.json").unlink(missing_ok=True)
    sources = sorted((ROOT / "app/src/main/java").rglob("*.java"))
    resources = sorted(p for p in (ROOT / "app/src/main/res").rglob("*") if p.is_file())
    assert len(sources) >= 12 and len(resources) >= 3, "Production source files are missing"
    project = ET.Element("project", android="true")
    ET.SubElement(project, "root", dir=ROOT.as_posix())
    ET.SubElement(project, "sdk", dir=sdk.as_posix())
    ET.SubElement(project, "cache", dir=(OUT / "cache").as_posix())
    module = ET.SubElement(project, "module", {"name": "app", "android": "true", "library": "false", "compile-sdk-version": "35", "javaLanguage": "1.8"})
    ET.SubElement(module, "manifest", file=(ROOT / "app/src/main/AndroidManifest.xml").as_posix())
    for source in sources:
        ET.SubElement(module, "src", file=source.as_posix())
    for resource in resources:
        ET.SubElement(module, "resource", file=resource.as_posix())
    ET.SubElement(module, "classes", dir=(ROOT / "build/classes").as_posix())
    descriptor = OUT / "project.xml"
    ET.ElementTree(project).write(descriptor, encoding="utf-8", xml_declaration=True)
    xml = OUT / "report.xml"
    text = OUT / "report.txt"
    xml.unlink(missing_ok=True)
    text.unlink(missing_ok=True)
    process = subprocess.run([str(lint), "--offline", "--project", str(descriptor.relative_to(ROOT)), "--exitcode", "--xml", str(xml.relative_to(ROOT)), "--text", str(text.relative_to(ROOT))], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    (OUT / "console.txt").write_text(process.stdout + process.stderr, encoding="utf-8")
    if not xml.is_file():
        raise RuntimeError("Lint did not produce a report: " + process.stdout + process.stderr)
    report = ET.parse(xml).getroot()
    issues = []
    for issue in report.findall("issue"):
        location = issue.find("location")
        issues.append({"id": issue.attrib["id"], "severity": issue.attrib["severity"], "message": issue.attrib["message"], "location": location.attrib if location is not None else {}})
    errors = [issue for issue in issues if issue["severity"] in ("Error", "Fatal")]
    warnings = [issue for issue in issues if issue["severity"] == "Warning"]
    if errors or process.returncode:
        print(text.read_text(encoding="utf-8"), flush=True)
        raise RuntimeError("Android Lint failed; see build/android-lint/report.txt")
    result = {"tool": report.attrib.get("by"), "default_checks": True, "offline": True,
              "java_source_files": len(sources), "resource_files": len(resources), "min_sdk": build["min_sdk"], "compile_sdk": 35,
              "errors": len(errors), "warnings": warnings, "issues": issues, "android_execution_tested": False,
              "applicationApkSha256": build["sha256"], "input_fingerprint": fingerprint("app/src/main/java", "app/src/main/res", "app/src/main/AndroidManifest.xml", "tools/test_android_lint.py")}
    (OUT / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"tool": result["tool"], "java_source_files": len(sources), "errors": len(errors), "warnings": len(warnings), "android_execution_tested": False}))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()

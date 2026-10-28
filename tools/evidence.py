"""Fingerprint verification inputs so stale passing reports cannot ship a new build."""
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ANDROID = "{http://schemas.android.com/apk/res/android}"


def version():
    return ET.parse(ROOT / "app/src/main/AndroidManifest.xml").getroot().attrib[ANDROID + "versionName"]


def fingerprint(*names):
    files = set()
    for name in names:
        path = ROOT / name
        files.update(p for p in path.rglob("*") if p.is_file()) if path.is_dir() else files.add(path)
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}


def current(record):
    assert record, "Missing verification input fingerprints"
    for name, expected in record.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, "Stale verification evidence: " + name


def build_inputs():
    return fingerprint("app/src/main", "native", "tools/build_moss_rq.py", "tools/moss_rq_pipeline.py", "tools/fetch_moss_rq.py", "tools/collect_moss_rq_notices.py", "third_party/moss-rq-source-lock.json", "tools/build_openmoss.py", "tools/openmoss_pipeline.py", "tools/fetch_openmoss.py", "tools/collect_openmoss_notices.py", "third_party/openmoss-source-lock.json", "tools/build.py", "tools/build_native.py", "tools/build_tts.py", "tools/fetch_tts.py", "tools/collect_tts_notices.py", "tools/build_mnn.py", "tools/fetch_mnn.py", "tools/collect_mnn_notices.py", "third_party/mnn-source-lock.json", "tools/build_moss_delay.py", "tools/fetch_moss_delay.py", "tools/collect_moss_delay_notices.py", "third_party/moss-delay-source-lock.json", "tools/build_qwen_tts.py", "tools/fetch_qwen_tts.py", "tools/collect_qwen_tts_notices.py", "third_party/qwen-tts-source-lock.json", "tools/build_moss_nano.py", "tools/fetch_moss_nano.py", "tools/collect_moss_nano_notices.py", "tools/native_payload.py", "third_party/moss-nano-source-lock.json", "third_party/tts-source-lock.json", "third_party/tts-notice-sources.json", "tools/bootstrap_native.py", "tools/fetch_native.py", "tools/collect_native_notices.py", "tools/package_native.py", "tools/build_catalogue.py", "tools/build_bundle_catalogue.py", "tools/build_recipe_templates.py", "tools/evidence.py", "catalogue/verified-models.json", "catalogue/model-bundles.json", "catalogue/bundle-evidence.json", "catalogue/uncensored-policy.json", "catalogue/uncensored-evidence.json", "tools/audit_uncensored.py", "third_party/runtime-lock.json", "third_party/BUILD_INFO.json", "third_party/engine-lock.json", "third_party/notices")

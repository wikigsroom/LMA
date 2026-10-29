"""APK inputs include signed asset-preparation programs and model-free graphs."""
from evidence import build_inputs as foundation_inputs, fingerprint


def build_inputs():
    return foundation_inputs() | fingerprint(
        "tools/preparation_build_inputs.py", "tools/package_preparations.py",
        "research/local_prepare", "research/ltx098_prepare", "research/ltx098_vae_prepare",
        "tools/build_ltx098_prepare.py", "tools/build_ltx098_vae_prepare.py",
        "tools/prepare_ltx098_vae_templates.py", "third_party/ltx098-source-lock.json",
        "third_party/ltx098-text-source-lock.json", "third_party/ltx098-vae-source-lock.json",
        "catalogue/asset-preparations.json")

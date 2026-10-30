"""APK inputs include signed asset-preparation programs and model-free graphs."""
from evidence import build_inputs as foundation_inputs, fingerprint


def build_inputs():
    return foundation_inputs() | fingerprint(
        "tools/preparation_build_inputs.py", "tools/package_preparations.py",
        "research/local_prepare", "research/lcm_prepare", "tools/build_lcm_prepare.py", "tools/generate_lcm_condition_contract.py", "research/ltx098_prepare", "research/ltx098_vae_prepare",
        "tools/build_ltx098_prepare.py", "tools/build_ltx098_vae_prepare.py",
        "tools/prepare_ltx098_vae_templates.py", "third_party/ltx098-source-lock.json",
        "third_party/ltx098-text-source-lock.json", "third_party/ltx098-vae-source-lock.json",
        "research/sd_variants_trained/assets.json", "research/sd_distilled_trained/assets.json", "verification/development/sd-variants-assets.json", "verification/development/sd-distilled-assets.json", "catalogue/asset-preparations.json", "catalogue/model-assemblies.json", "catalogue/model-bundles.json", "tools/build_bundle_catalogue.py")

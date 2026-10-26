"""Verify each built-in model's publisher claim and its pinned GGUF attribution.

Publisher declarations are evidence of model selection, not measured refusal rates.
Reads model cards as data only; never runs their example commands.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from audit_catalogue import request
from evidence import fingerprint

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/uncensored-review"


def body(text):
    return text.split("---", 2)[2] if text.startswith("---") else text


def normalized_text(text):
    class TextOnly(HTMLParser):
        def __init__(self): super().__init__(); self.parts = []
        def handle_data(self, data): self.parts.append(data)
    parser = TextOnly(); parser.feed(body(text))
    return re.sub(r"\s+", " ", "".join(parser.parts))


def inspect(policy, checked, origin, cached=None):
    repo = policy["author_repository"]
    if cached is None:
        _, _, raw, _ = request(origin + "/api/models/" + repo)
        revision = json.loads(raw)["sha"]
        _, _, author, _ = request(origin + "/" + repo + "/resolve/" + revision + "/README.md")
        _, _, quant, _ = request(origin + "/" + checked["repository"] + "/resolve/" + checked["revision"] + "/README.md")
    else:
        assert cached["author_repository"] == repo
        revision = cached["author_revision"]
        author = (OUT / (checked["id"] + "-author.md")).read_bytes()
        quant = (OUT / (checked["id"] + "-gguf.md")).read_bytes()
        assert hashlib.sha256(author).hexdigest() == cached["author_card_sha256"]
        assert hashlib.sha256(quant).hexdigest() == cached["gguf_card_sha256"]
    assert re.fullmatch(r"[0-9a-f]{40}", revision)
    author_text = normalized_text(author.decode("utf-8"))
    assert policy["claim_phrase"].casefold() in author_text.casefold(), "Missing publisher claim: " + repo
    for marker in policy.get("method_markers", []):
        assert marker.casefold() in author_text.casefold(), "Missing method description: " + repo
    quant_text = quant.decode("utf-8")
    attribution = "repository-reference"
    if repo.casefold() == checked["repository"].casefold():
        assert policy["claim_phrase"].casefold() in normalized_text(quant_text).casefold(), "Pinned publisher claim missing: " + repo
        attribution = "same-repository"
    elif repo.casefold() not in quant_text.casefold():
        matched = False
        for alias in policy.get("author_aliases", []):
            if alias.casefold() not in quant_text.casefold(): continue
            _, _, alias_raw, _ = request(origin + "/api/models/" + alias)
            assert json.loads(alias_raw)["id"].casefold() == repo.casefold(), "Unverified publisher rename"
            matched = True; attribution = "verified-publisher-rename"; break
        if not matched:
            # One publisher's GGUF card has erroneous base_model front matter.
            # Require its explicit model title and uncensored statement instead.
            assert repo.split("/")[0] == checked["repository"].split("/")[0]
            assert policy.get("gguf_binding_phrases"), "Missing original-model attribution: " + repo
            quant_body = re.sub(r"\s+", " ", body(quant_text))
            for phrase in policy["gguf_binding_phrases"]:
                assert phrase.casefold() in quant_body.casefold(), "GGUF publisher text does not match"
            attribution = "same-publisher-explicit-model-card"
    (OUT / (checked["id"] + "-author.md")).write_bytes(author)
    (OUT / (checked["id"] + "-gguf.md")).write_bytes(quant)
    return {"id": checked["id"], "qualified": True, "basis": "publisher-declared-uncensored",
            "method": policy["method"], "summary": policy["summary"], "claim_excerpt": policy["claim_phrase"],
            "author_repository": repo, "author_revision": revision, "author_card_sha256": hashlib.sha256(author).hexdigest(),
            "author_card_url": "https://huggingface.co/" + repo + "/blob/" + revision + "/README.md",
            "gguf_repository": checked["repository"], "gguf_revision": checked["revision"],
            "gguf_card_sha256": hashlib.sha256(quant).hexdigest(), "gguf_attribution": attribution,
            "weight_sha256": checked["sha256"], "filename": checked["filename"], "refusal_rate_tested": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", choices=["https://huggingface.co", "https://hf-mirror.com"], default="https://hf-mirror.com")
    parser.add_argument("--cached-cards", action="store_true", help="Reuse this review's downloaded cards and recorded SHA256 values")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    policies = json.loads((ROOT / "catalogue/uncensored-policy.json").read_text(encoding="utf-8"))["models"]
    verified = {m["id"]: m for m in json.loads((ROOT / "catalogue/verified-models.json").read_text(encoding="utf-8"))["models"]}
    cached = {m["id"]: m for m in json.loads((OUT / "cards.json").read_text(encoding="utf-8"))} if args.cached_cards else {}
    assert len({p["id"] for p in policies}) == len(policies)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda p: inspect(p, verified[p["id"]], args.origin, cached.get(p["id"])), policies))
    record = {"checked_at": datetime.now(timezone.utc).isoformat(), "retrieval_origin": args.origin,
              "scope": "Built-in models only; custom imports are not automatically classified",
              "cached_cards_checked_by_sha256": args.cached_cards,
              "refusal_rates_measured": False, "models": sorted(results, key=lambda m: m["id"]),
              "input_fingerprint": fingerprint("catalogue/uncensored-policy.json", "catalogue/verified-models.json", "tools/audit_uncensored.py")}
    (ROOT / "catalogue/uncensored-evidence.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"publisher_claims_verified": len(results), "pinned_gguf_attributions_verified": len(results), "refusal_rates_measured": False}))


if __name__ == "__main__": main()

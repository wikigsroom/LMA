"""Collect the actual pinned sd.cpp source notices. Never collect tokenizer/model data."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "build/native-src/sd-cpp"
OUT = ROOT / "third_party/notices"


def main():
    receipt = json.loads((ROOT / "build/native-build-info.json").read_text(encoding="utf-8"))
    revision = subprocess.check_output(["git", "-C", str(SOURCE), "rev-parse", "HEAD"], text=True).strip()
    if revision != receipt["source_revision"]:
        raise RuntimeError("Notice source does not match the compiled worker")
    records = []
    def save(name, text, source):
        name = "sd-" + name + ".txt"
        data = text.encode("utf-8")
        (OUT / name).write_bytes(data)
        records.append({"file": name, "sha256": hashlib.sha256(data).hexdigest(), "source": source})
    for name, relative in (("LICENSE", "LICENSE"), ("ggml-LICENSE", "ggml/LICENSE"), ("oniguruma-COPYING", "thirdparty/oniguruma/COPYING"), ("utf8proc-LICENSE", "thirdparty/utf8proc/LICENSE.md"), ("darts-clone-LICENSE", "thirdparty/LICENSE.darts_clone.txt")):
        save(name, (SOURCE / relative).read_text(encoding="utf-8"), relative)
    for name in ("stb_image.h", "stb_image_write.h", "stb_image_resize.h", "miniz.h", "zip.c", "zip.h"):
        text = (SOURCE / "thirdparty" / name).read_text(encoding="utf-8")
        blocks = re.findall(r"/\*.*?\*/", text, re.DOTALL)
        selected = [block for block in blocks if any(phrase in block for phrase in ("Permission is hereby granted", "This is free and unencumbered software", 'THE SOFTWARE IS PROVIDED "AS IS"'))]
        # The resize header's public-domain notice is a single line at its start.
        if name == "stb_image_resize.h":
            selected.insert(0, text.splitlines()[0])
        if not selected:
            raise RuntimeError("No notice found in " + name)
        save(name + "-NOTICE", "\n\n".join(selected) + "\n", "thirdparty/" + name)
    # Same MIT terms, with the copyright declaration from the actual 3.11.2 header.
    header = (SOURCE / "thirdparty/json.hpp").read_text(encoding="utf-8")
    declaration = re.search(r"SPDX-FileCopyrightText: ([^\r\n]+)", header).group(1)
    mit = (OUT / "nlohmann-json-LICENSE.txt").read_text(encoding="utf-8")
    mit = re.sub(r"Copyright \(c\) [^\r\n]+", "Copyright (c) " + declaration, mit, count=1)
    save("nlohmann-json-LICENSE", mit, "thirdparty/json.hpp SPDX declaration; MIT license terms")
    relative = "build/toolchain/android-ndk-r30/toolchains/llvm/prebuilt/windows-x86_64/NOTICE"
    save("NDK-LLVM-NOTICE", (ROOT / relative).read_text(encoding="utf-8"), relative)
    (OUT / "sd-sources.json").write_text(json.dumps({"revision": revision, "files": records}, indent=2) + "\n", encoding="utf-8")
    # A changed native binary requires explicit review of this lock diff before commit.
    engine = {k: receipt[k] for k in ("engine", "file", "source_revision", "ggml_revision", "abi", "backend", "ndk", "sha256", "bytes")}
    engine["notices"] = {r["file"]: r["sha256"] for r in records}
    (ROOT / "third_party/engine-lock.json").write_text(json.dumps({"schema": "lma.engine-lock/1", "engines": [engine]}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"collected_native_notices": len(records), "source_revision": revision}))


if __name__ == "__main__":
    main()

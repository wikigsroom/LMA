"""Collect exact upstream TTS dependency notices into the signed APK and reviewed engine lock."""
import base64
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request
import zipfile
from evidence import current

ROOT=Path(__file__).resolve().parents[1]


def main():
    manifest=json.loads((ROOT/"third_party/tts-notice-sources.json").read_text(encoding="utf-8"))
    receipt=json.loads((ROOT/"build/tts-build-info.json").read_text(encoding="utf-8"))
    current(receipt["source_inputs"])
    if receipt["source_revision"] != manifest["source_revision"]: raise RuntimeError("Notice sources differ from compiled TTS ABI")
    cache=ROOT/"third_party/cache/tts-notices";cache.mkdir(parents=True,exist_ok=True)
    output=ROOT/"third_party/notices"
    def fetch(item):
        target=cache/item["sha256"]
        if not target.exists():
            request=urllib.request.Request(item["url"],headers={"User-Agent":"LMA-notice-bootstrap"})
            with urllib.request.urlopen(request,timeout=40) as response: data=response.read(64*1024*1024+1)
            if len(data)>64*1024*1024: raise RuntimeError("Unexpected notice source size")
            if item.get("encoding")=="github-base64": data=base64.b64decode(json.loads(data)["content"])
            if hashlib.sha256(data).hexdigest()!=item["sha256"]: raise RuntimeError("Notice source hash mismatch")
            target.write_bytes(data)
        data=target.read_bytes()
        if hashlib.sha256(data).hexdigest()!=item["sha256"]: raise RuntimeError("Cached notice source changed")
        return data
    records=[]
    def save(item,data,source):
        name=item["output"]
        if Path(name).name!=name or not name.startswith("tts-") or hashlib.sha256(data).hexdigest()!=item["sha256"]: raise RuntimeError("Invalid notice output")
        (output/name).write_bytes(data)
        records.append({"file":name,"sha256":item["sha256"],"source":source})
    for archive in manifest["archives"]:
        data=fetch(archive)
        if archive["format"]=="zip":
            with zipfile.ZipFile(io.BytesIO(data)) as source:
                for item in archive["members"]: save(item,source.read(item["path"]),archive["url"]+"#"+item["path"])
        else:
            with tarfile.open(fileobj=io.BytesIO(data)) as source:
                for item in archive["members"]:
                    member=source.getmember(item["path"])
                    if not member.isfile() or member.size>4*1024*1024: raise RuntimeError("Invalid notice archive member")
                    save(item,source.extractfile(member).read(),archive["url"]+"#"+item["path"])
    for item in manifest["raw"]: save(item,fetch(item),item["url"])
    notices={r["file"]:r["sha256"] for r in records}
    for name in ("sd-nlohmann-json-LICENSE.txt","sd-NDK-LLVM-NOTICE.txt"):
        notices[name]=hashlib.sha256((output/name).read_bytes()).hexdigest()
    engine={k:receipt[k] for k in ("engine","file","source_revision","abi","backend","ndk","sha256","bytes","android_api_notes","dependencies")}
    engine["notices"]=notices
    path=ROOT/"third_party/engine-lock.json";lock=json.loads(path.read_text(encoding="utf-8"))
    lock["engines"]=[e for e in lock["engines"] if e["engine"]!="sherpa_tts"]+[engine]
    path.write_text(json.dumps(lock,indent=2)+"\n",encoding="utf-8")
    (output/"tts-sources.json").write_text(json.dumps({"source_revision":receipt["source_revision"],"files":records,"prebuilt_provenance":True,"model_assets":False},indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"collected_tts_notices":len(records),"engine":"sherpa_tts","source_revision":receipt["source_revision"]}))


if __name__=="__main__":main()

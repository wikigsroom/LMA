"""Check a physical Android phone; optional actual download/inference and screen-off API run.

No emulator, root, Docker or WSL. Instrumentation ends BEFORE background endurance.
The API key is captured in memory and is excluded from every report and console log.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from evidence import current

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/device-tests"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial")
    parser.add_argument("--run", action="store_true", help="Install acceptance APK and exercise Android UI/SQLite/service")
    parser.add_argument("--install", action="store_true", help="Install/upgrade the main APK, retaining application data")
    parser.add_argument("--model", choices=["m01", "m08", "m06"], help="Actually download, hash, load and infer with this model")
    parser.add_argument("--minutes", type=int, default=15, help="Screen-off endurance after instrumentation exits; 0 skips")
    args = parser.parse_args()
    if args.model and not args.run: parser.error("--model requires --run")
    if not 0 <= args.minutes <= 1440: parser.error("--minutes must be 0..1440")
    sdk = Path(os.environ.get("ANDROID_SDK_ROOT", str(Path(os.environ["LOCALAPPDATA"]) / "Android/Sdk")))
    adb = str(sdk / "platform-tools/adb.exe")
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "physical_device_tests": 0, "phone_inference_tested": False, "background_endurance_tested": False, "emulator_used": False}
    key, forwarding, serial = "", "", ""
    def save(): (OUT / "device-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    def command(*values, timeout=30):
        r = subprocess.run([adb] + (["-s", serial] if serial else []) + list(values), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        if r.returncode: raise RuntimeError("ADB command failed: " + (r.stderr or r.stdout)[:1000])
        return r.stdout.strip()
    try:
        devices = [line.split()[0] for line in command("devices").splitlines()[1:] if re.search(r"\sdevice$", line)]
        if not devices:
            report["status"] = "awaiting_physical_device"; save(); print(json.dumps(report)); return 2
        if args.serial:
            if args.serial not in devices: raise RuntimeError("Selected physical device is not authorized or connected")
            serial = args.serial
        elif len(devices) == 1: serial = devices[0]
        else: raise RuntimeError("Multiple devices; select --serial")
        if serial.startswith("emulator-") or command("shell", "getprop", "ro.kernel.qemu") == "1": raise RuntimeError("Emulators are excluded by this project")
        abi = command("shell", "getprop", "ro.product.cpu.abilist"); api = int(command("shell", "getprop", "ro.build.version.sdk"))
        if "arm64-v8a" not in abi or api < 28: raise RuntimeError("LMA requires a physical ARM64 Android 9+ device")
        report["device"] = {"model": command("shell", "getprop", "ro.product.model"), "api": api, "abis": abi}
        report["status"] = "physical_device_available"
        build = json.loads((ROOT / "dist/build-info.json").read_text(encoding="utf-8")); report["apk_sha256"] = build["sha256"]
        if args.install: command("install", "-r", str(ROOT / "dist" / build["apk"]), timeout=180)
        if not args.run: save(); print(json.dumps(report, ensure_ascii=True)); return 0
        acceptance = json.loads((OUT / "acceptance-build.json").read_text(encoding="utf-8")); current(acceptance["input_fingerprint"])
        if acceptance["applicationApkSha256"] != build["sha256"]: raise RuntimeError("Rebuild the acceptance APK against the current application")
        import hashlib
        if hashlib.sha256((ROOT / acceptance["apk"]).read_bytes()).hexdigest() != acceptance["sha256"]: raise RuntimeError("Acceptance APK hash mismatch")
        command("install", "-r", str(ROOT / acceptance["apk"]), timeout=180)
        if api >= 33: command("shell", "pm", "grant", "com.lma.app", "android.permission.POST_NOTIFICATIONS")
        instrument = ["shell", "am", "instrument", "-w"]
        if args.model: instrument += ["-e", "model", args.model]
        raw = command(*(instrument + ["com.lma.app.acceptance/com.lma.app.DeviceAcceptance"]), timeout=2800)
        match = re.search(r"INSTRUMENTATION_RESULT: lma_result=(\{[^\r\n]+\})", raw)
        if not match: raise RuntimeError("Instrumentation did not return structured results")
        result = json.loads(match.group(1)); key = result.pop("apiKey", "")
        report["instrumentation"] = result
        if result.get("status") != "passed": raise RuntimeError(result.get("error", "Android acceptance failed"))
        report["physical_device_tests"] = len(result["checks"])
        report["phone_inference_tested"] = bool(args.model)
        # The app runs normally after this launch; no attached instrumentation can
        # keep its process alive during the following background survival test.
        if args.model:
            command("shell", "am", "start", "-n", "com.lma.app/.MainActivity")
            forwarding = command("forward", "tcp:0", "tcp:" + str(result["port"]))
            origin = "http://127.0.0.1:" + forwarding
            def request(path, data=None, api_key=None):
                headers = {"Authorization": "Bearer " + (key if api_key is None else api_key)}
                if data is not None: headers["Content-Type"] = "application/json"
                return urllib.request.urlopen(urllib.request.Request(origin + path, data=None if data is None else json.dumps(data).encode(), headers=headers), timeout=310)
            deadline = time.monotonic() + 330
            while True:
                try:
                    with request("/v1/models") as r: models = json.load(r)
                    if not any(m["id"] == args.model for m in models["data"]): raise RuntimeError("Unexpected native model alias")
                    break
                except (OSError, urllib.error.URLError):
                    if time.monotonic() >= deadline: raise RuntimeError("Native API did not recover after instrumentation detached")
                    time.sleep(1)
            try:
                with request("/v1/models", api_key="incorrect") as r: r.read(100)
                raise RuntimeError("Native API accepted an incorrect key")
            except urllib.error.HTTPError as error:
                if error.code != 401: raise
            report["external_api_auth_tested"] = True
            if args.minutes:
                command("shell", "input", "keyevent", "3"); command("shell", "input", "keyevent", "223")
                power = command("shell", "dumpsys", "power")
                if not re.search(r"mWakefulness=(?:Asleep|Dozing)|Display Power: state=OFF", power): raise RuntimeError("Could not confirm screen-off state")
                started = time.monotonic(); deadline = started + args.minutes * 60; samples = []
                while time.monotonic() < deadline:
                    at = time.monotonic(); first = None; chars = 0; finished = False
                    payload = {"model": args.model, "messages": [{"role": "user", "content": "请详细介绍手机本地语言模型的工作原理，并给出具体使用步骤。"}], "stream": True, "max_tokens": 512, "stream_options": {"include_usage": True}}
                    with request("/v1/chat/completions", payload) as response:
                        for line in response:
                            if not line.startswith(b"data:"): continue
                            data = line[5:].strip()
                            if data == b"[DONE]": finished = True; break
                            chunk = json.loads(data)
                            if "error" in chunk: raise RuntimeError("Native SSE returned an error")
                            for choice in chunk.get("choices", []):
                                delta = choice.get("delta", {}); text = delta.get("content") or delta.get("reasoning_content") or ""
                                if text and first is None: first = time.monotonic() - at
                                chars += len(text)
                    if not finished or not chars: raise RuntimeError("Screen-off API reply did not finish with generated content")
                    power = command("shell", "dumpsys", "power")
                    if not re.search(r"mWakefulness=(?:Asleep|Dozing)|Display Power: state=OFF", power): raise RuntimeError("Phone woke during screen-off endurance")
                    samples.append({"first_delta_seconds": first, "seconds": time.monotonic() - at, "characters": chars})
                    print(json.dumps({"completed_screen_off_requests": len(samples), "elapsed_seconds": round(time.monotonic() - started)}), flush=True)
                report["background_endurance_tested"] = True; report["background_elapsed_seconds"] = time.monotonic() - started; report["screen_off_requests"] = samples
        report["status"] = "passed"; save(); print(json.dumps({k: v for k, v in report.items() if k != "screen_off_requests"}, ensure_ascii=True)); return 0
    except Exception as error:
        message = str(error).replace(key, "[hidden]") if key else str(error)
        report["status"] = "failed"; report["error"] = message; save(); print(json.dumps(report, ensure_ascii=True)); return 1
    finally:
        if forwarding:
            try: command("forward", "--remove", "tcp:" + forwarding)
            except Exception: pass


if __name__ == "__main__": sys.exit(main())

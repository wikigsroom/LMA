# Physical Android acceptance

[中文](DEVICE_ACCEPTANCE.md) · [Documentation](README.md)

No physical Android device was available. The acceptance APK is compiled, not executed. The runner accepts only authorized ADB **physical ARM64 Android 9+ devices**, rejects emulators, and uses no ROOT, Docker, WSL, or virtual machine.

## Build and preflight

```powershell
python tools/build.py
python tools/build_acceptance.py
python tools/device_check.py
```

`build/device-tests/LMA-acceptance.apk` is a separate same-signed instrumentation tool, unnecessary for ordinary users. Preserve local signing material for upgrades; private keys are never included in public sources. No authorized device records `awaiting_physical_device` and exits with code 2 rather than launching an emulator.

## Android framework checks

Connect and authorize USB debugging, unlock the phone, and stop important active work before running:

```powershell
python tools/device_check.py --install --run
```

The runner updates the app without clearing its data, installs acceptance instrumentation, and exercises the actual offline WebView/bridge, catalogue, native-executable permissions, SQLite interruption recovery, and foreground settings commands. Authorized ADB grants notification permission on Android 13+ for the test.

SQLite checks create and remove a temporary session and restore the previous selection. Instrumentation restarts the target app; do not run it during important downloads or generation.

## Full model and screen-off requests

```powershell
python tools/device_check.py --install --run --model m01 --minutes 15
```

This downloads the real approximately 398 MB Dolphin Qwen 0.5B weight on the phone, or reuses and rehashes an existing file, then loads the packaged ARM engine and generates/persists through actual ChatRunner. The test chat and downloaded model remain in the app.

After instrumentation ends, the runner opens LMA normally, waits for model/API restoration, and uses a temporary ADB forward to test authentication and a wrong-key rejection. It then goes Home, turns the screen off, and sends real streaming requests from the host. Instrumentation is detached during this phase to avoid changing process priority. Each round requires nonempty output, successful completion, and a still-off screen.

This verifies screen-off FGS/API behavior with ADB attached. USB power and ADB affect power policy, so it is not equivalent to unplugged battery/vendor extreme-saving operation; it also does not validate password-lock interaction. Authorized wireless ADB can provide another comparison. The tool does not enable wireless debugging by itself.

Use `--model m06` for LFM 1.2B or `--model m08` for Qwen 1.7B. `--minutes 60` is an hour, with a maximum of 1440 minutes; the final request can extend wall-clock duration. `--minutes 0` skips endurance and never marks it as passed. Use `--serial` to select among authorized devices.

The API key exists only in trusted process memory, not console/report files. Temporary forwarding is removed in `finally`. The model continues serving after the test according to app settings; stop it in LMA or the notification.

## Results and additional scenarios

Results go to `build/device-tests/device-results.json`. Framework execution, actual inference, and endurance have separate fields. Compilation never substitutes for execution.

Manually verify actual WLAN from another device, SAF providers, notification Stop/wake-lock release, download network transitions, reboot restoration, all candidate models, and vendor power policy. Record power source, cooling, OS, weight SHA256, threads, context, temperature, duration, and failure rate. Update both validation languages and release notes when evidence changes.

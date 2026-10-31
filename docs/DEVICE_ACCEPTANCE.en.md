# Physical Android program acceptance · v0.3.7

[中文](DEVICE_ACCEPTANCE.md) · [Release notes](releases/v0.3.7.md) · [Evidence](../verification/releases/v0.3.7/physical-device.json)

Wireless ADB connected an actual phone, reporting **motorola edge plus / burton, Android 12 / API31, SM8250 and approximately 11.4 GiB system-visible RAM**. This is not an X30, Snapdragon 8 Gen 1 or Nubia Z20 acceptance result. The PC installs, controls and forwards requests; application services execute on the same Android phone without ROOT.

## 1. Problems fixed

| ID | Observed problem | Result |
| --- | --- | --- |
| D01 | An unprepared legacy LTX entry triggered execution validation during v0.3.6 catalogue snapshot construction, aborting device and model-card state | Each entry retains `inputSchemaError`; the rest of the catalogue and device state render. Execution still requires real matching assets |
| D02 | The acceptance APK compressed `resources.arsc`, which Android 12 rejected | Preserve its stored compression and alignment; independent instrumentation installs |
| D03 | An older ADB failed to export media to an absolute path containing Chinese characters | Export relative to the repository working directory |

The patch is **0.3.7 / code57**, signed with the original identity. It preserves application data and user-selected assets. Published v0.3.6 files and historical failures remain unchanged.

## 2. Actual coverage

**19 physical program checks** cover complete zero-model state and 82 bundles, real memory, native bridge/cards, recommended order `m08 → m06 → m01`, All/Local and four other pages, executable permissions, Android SQLite interruption recovery, service commands, zero-model API startup and recovery after instrumentation detaches, 401 authentication / 403 browser-origin rejection, engine and data endpoints, and 409 missing-weight rejection without downloading models.

With instrumentation detached, the application survives approximately **60 seconds with the display off**, serving **seven authenticated health requests** while the real foreground service remains present. This is a short program survival check. It establishes no model inference, continuous token generation or endurance result.

Keys remain in the trusted runner's memory and are removed before writing reports. Public records exclude serial numbers, network endpoints, pairing credentials and personal logs. No complete trained models were downloaded, copied or run.

## 3. Reproduce

Use native Windows SDK/JDK/Python, with an authorized, unlocked physical ARM64 Android 9+ device. No emulator, Docker, WSL or VM. Wireless pairing and connection use separate ports; consult the [official ADB documentation](https://developer.android.com/tools/adb#wireless-android11-command-line).

```powershell
python tools/build_acceptance.py
python tools/device_check.py --serial DEVICE_IP:CONNECT_PORT --install --run --program-api --minutes 1
# Unlock manually after the screen-off check, then capture without locking again.
python tools/device_check.py --serial DEVICE_IP:CONNECT_PORT --run --program-api --minutes 0 --capture-media
```

Do not pass `--model`: that historical option downloads and runs trained weights and is outside this validation policy. Zero-model API acceptance stops if existing installed models are found and preserves those files. Installation upgrades in place; it never clears app data. Users enter their own lock-screen credentials.

## 4. Actual media

[Phone screenshot](media/device/v0.3.7/01-recommended.png) · [Screen recording](media/device/v0.3.7/physical-walkthrough.mp4) · [GIF](media/device/v0.3.7/physical-walkthrough.gif) · [Identity manifest](media/device/v0.3.7/manifest.json)

Only LMA screen content is published. Personal launcher, lock screens, credentials and other applications are excluded. Physical media is separate from the labelled desktop **UI FIXTURE** recordings under `docs/media/development/`. Playback timing is not generation performance.

## 5. Unmeasured scope

| ID | Not established | Treatment |
| --- | --- | --- |
| U01 | Full text/image/video/audio/3D inference, quality, tokens/s, peak memory or temperature | Omitted under the user's program-only policy |
| U02 | Long screen-off inference, vendor power management, reboot/force-stop model recovery | Only short no-model API survival is recorded |
| U03 | X30, Nubia Z20 or other devices | Evidence applies to this reported phone only |
| U04 | Arbitrary HF architectures, every upstream CUDA workflow or verified complete public 3D exports | Preserve the bounded 62-recipe / 82-bundle / 18-extension-plus-text scope and acquisition limits |

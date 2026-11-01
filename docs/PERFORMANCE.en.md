# v0.3.12 installed-model idle measurement

Final APK: snapshot p50 **275.88 ms**, p95 **286.75 ms**; maximum observed main-thread gap **27 ms**, **zero gaps over 100 ms**. Eight program/performance checks passed with all five existing models preserved and no active generation. Model discovery uses a cached lightweight publication snapshot; it does not scan/load weights on each request. [Current evidence](../verification/releases/v0.3.12/ui-performance.json) · [Device report and limits](DEVICE_BENCHMARK_V0312.en.md). These measurements are not FPS, peak native-worker RAM or thermal endurance. The historical before/after analysis follows.

# Idle UI performance and fixes · v0.3.9

[中文](PERFORMANCE.md) · [Release](releases/v0.3.9.md) · [Numbers and identities](../verification/releases/v0.3.9/ui-performance.json)

Without a loaded model, v0.3.8 still built the full 82-bundle catalogue on Android's main thread on each state update. It repeatedly validated immutable manifests, resolved the same parameter schema, and serialized roughly 954 KB of state. Input and scrolling waited behind this work. The frontend also rebuilt model views, refreshed hidden pages and replaced unchanged recommendation counters. These costs belong to application code; they do not require inference.

Earlier safeguards included 60 ms broadcast debounce, model-card/chat signatures and notification throttling. Debounce did not reduce individual snapshot cost or move it off the main thread; view generation and counter changes happened before the signature check. Functional checks did not measure snapshot latency or main-thread gaps. That verification gap is addressed here. Source inspection found no fixed idle timer continuously rebuilding the catalogue: the affected paths are startup and state broadcasts.

## 1. Same phone, same diagnostic program

The phone reports motorola edge plus / burton, Android 12 / API31, SM8250 and about 11.4 GiB system-visible RAM. The untouched stable v0.3.8 was measured before upgrading in place with the original signer. Neither installed complete weights nor inference were used. Existing uninstalled local/transfer records are preserved and do not count as installed weights. These are not X30 or Nubia Z20 results.

| 测量 / Measurement | v0.3.8 | v0.3.9 |
| --- | ---: | ---: |
| 状态序列化 p50 / Snapshot serialization p50 | 4061.09 ms | 229.85 ms |
| 模型目录 p50 / Bundle catalogue p50 | 3853.89 ms | 184.08 ms |
| 主线程最长间隔 / Maximum main-thread gap | 4228.00 ms | 24.00 ms |
| 超过 100 ms 的间隔 / Gaps over 100 ms | 1.00 | 0.00 |
| 12 次更新的视图生成 / Model-view builds over 12 updates | 72.00 | 12.00 |
| 12 次更新的页面修改 / DOM mutations over 12 updates | 699.00 | 118.00 |
| 前端更新平均 / Mean receive execution | 4.95 ms | 1.31 ms |

Snapshot numbers include complete JSON serialization, with seven warm samples; catalogue numbers use five samples. A main-thread callback is scheduled every 16 ms while the test thread emits eight ordinary state broadcasts 300 ms apart. Callback gaps **are not FPS or input-latency measurements**. The frontend receives the same state twelve times on Recommended / All tasks; synchronous execution, public view calls and DOM changes are counted. Both versions retain all 82 bundles and 14 recommendation cards. The linked record binds numbers to APK digests and unchanged diagnostic sources. Optimized snapshot work runs in the background; its roughly 230 ms duration is not a 230 ms input pause.

## 2. Changes

| ID | Implementation | Correctness preserved |
| --- | --- | --- |
| P01 | One background snapshot worker, debounce, at most one pending refresh | Main thread delivers results; stopped/destroyed views reject stale work and resume with fresh state |
| P02 | Reuse validated immutable ModelBundle definitions; resolve each bundle schema once per snapshot | Defensive JSON copies; fresh file/receipt/install/config/version/lease checks; execution validates again |
| P03 | Build shared frontend model views once per received state | Invalidate on every new state; preserve full catalogue, recommendation prefix, NSFW tags and independent parameters |
| P04 | Refresh model/chat/server pages when visible; retain unchanged counter/theme/runtime nodes | Entering a page renders it; task acknowledgements and saved parameter callbacks continue |
| P05 | Hash each distinct signed native file once per startup, reusing shared dependency results in that constructor | Every new process still verifies each distinct file and compares every manifest entry; no persistent verification bypass |
| P06 | Add cache-isolation, one-schema-per-snapshot, repeated UI update and physical performance regression checks | No weight caching, integrity removal, trained-model download or inference |

## 3. Reproduce

Use native host tools, no VM or emulator, and an authorized, unlocked ARM64 Android 12+ phone (this diagnostic reads the API31 SoC field; the app still supports Android 9+). Build the diagnostic APK with `tools/build_acceptance.py`; run `tools/profile_device.py --serial DEVICE --label optimized`; export with `tools/performance_evidence.py`. The exporter binds the historical stable APK and current APK identities. Public records contain no raw state, API keys, private model contents, debugging endpoints or passwords. This specialty requires no installed weights and never clears user data.

## 4. Limits

This is a warm program benchmark on one phone. Cold-start time, battery drain, prolonged background activity, sustained FPS, other devices, complete-model speed/peak RAM and quality remain unmeasured. Full state serialization still costs roughly 1 MB; background coalescing and view reuse remove the measured multi-second main-thread block, without promising zero jank on every device. Complete trained-model runs are excluded by the user's validation policy.

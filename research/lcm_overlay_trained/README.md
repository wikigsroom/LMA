# Retained strict-observer diagnostic / 严格采集器诊断归档

`strict_probe_snapshot.py` preserves the exact ignored execution source from
`build/sd-distilled-asset-probe/probe_lcm_overlay.py`. It is an archival experiment,
not a product entry point or a portable replay command. Its historical coordination
paths and the original source fingerprint are retained in the private receipt.

The unchanged native worker completed a trained four-step LCM image using the
complete original checkpoint plus a 5,216-byte single-bias GGUF. The PNG matched
the earlier full patched checkpoint byte for byte. The strict host observer still
rejected this capture because multi-file loading emitted one empty stdout line.
That failed observation is retained, rather than rewritten as an original pass.

The current `tools/test_lcm_overlay_trained.py` independently parses every raw
stdout line, tolerates only whitespace-only lines, retains the original observer
error list and checks actual sampler output, controls, cancellation and recovery.
Production `NativeWorker` already skips non-JSON diagnostics. Product routing and
source-bound overlay validation are separate unfinished work; this does not enable
model-plus-diffusion recipes in the APK.

该归档保留一次严格采集失败：原生进程成功、图像与整份修正版完全一致，但加载两个
文件时额外输出一个空行。后续采集仅允许纯空白行，并保留原始日志及原始错误列表。
这里不含模型、条件参数、词表或其他权重；输出权重仅留在被忽略的开发缓存内。
没有 Android 真机、App 生产流程、画质或完整 Release 的通过声明。

# Captured experiment sources / 实测实验源码

These ten files preserve the exact bytes used by the retained developer
experiments. They are **not Android programs, App plugins or user model data**.
No learned weights or vocabulary are included. Original experiment hashes are
checked against these snapshots by `tools/check_sd_distilled_evidence.py`.

The original execution location was `build/sd-distilled-asset-probe/`; relative
paths and old coordination waits intentionally retain that historical context.
Do not execute all snapshots directly from this archive directory. The public
`tools/replay_sd_turbo_native.py --execute` stages the exact SD-Turbo source in
its original ignored location, preserves earlier captures and never downloads.
Complete weights and external merges must already have been explicitly acquired.

The LCM snapshots document bounded header inspection, full original/converted
parameter comparison, missing condition projection, fixed-guidance bias folding,
thirty complete reduced-geometry UNet forwards, native PNGs, and actual scheduler
version comparison. Their private receipts/reference inputs and coordination
paths require the documented developer experiment layout. This archive does
not provide a one-command Android conversion or a product LCM repair. Original
upstream Python sources and the reference wheel are SHA-locked separately;
they are fetched/checked as developer references, not installed in the App.

十份源码保留实测时的原始字节与历史路径，供复核来源；LCM 的历史协调等待不构成新用户
前置步骤。它们既不是手机运行组件，也不是用户需要执行的模型准备方案。生产接入、
完整官方图像管线数值对照、画质、资源与 Android 验收仍分别待完成。

See [中文指南](../../../docs/SD_DISTILLED_TRAINED.md) /
[English guide](../../../docs/SD_DISTILLED_TRAINED.en.md).

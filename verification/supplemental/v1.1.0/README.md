# v1.1.0 supplemental client audit / 客户端补充程序复核

[中文说明](../../../docs/DSH_CLIENT_AUDIT.md) · [English](../../../docs/DSH_CLIENT_AUDIT.en.md) · [Results / 结果](client-code.json)

`client-code.json` records 79 checks with the real DSH 1.4.76 static runtime and LMA production Java HTTP/protocol code. Synthetic native SSE replaces inference; no DSH tools, subagents, Android UI, trained models or phone operations run during these checks. Client APK/code and intermediate requests stay private under ignored build output.

本目录单列发布后的程序证据。原正式版本的67组／15,394项程序断言、21项选择性m15真机工具检查、APK／源码附件及媒体不改写。手机被其他任务占用期间，按用户要求只做代码复核；DSH App本身完整工具／子代理实机验收仍待完成。

The installed APK was checked against stable v1.1.0 before phone interaction stopped. Supplemental program evidence does not change the published APK or establish DSH App acceptance. Reproduce with `python tools/test_dsh_client.py --apk <legitimately-obtained-matching-apk>`; no automatic download or ADB is used.

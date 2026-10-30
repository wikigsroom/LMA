# 本地模型导入、暂停与恢复

[English](MODEL_TRANSFERS.en.md) · [完整版本范围](MULTIMODAL_RELEASE_PLAN.md) · [本轮编号记录](releases/v0.3.0-dev.42.md)

用户在「全部 / 搜索」选择模型，在「本地」管理资产。安装、升级、浏览不会开始下载；APK 只交付共用基座。生文、生图、生视频、生音频按任务和依赖标签区分，模型平级；推荐 m08→m06→m01 保留。

## 操作逻辑

1. 查看完整组件、许可证、磁盘需求及运行状态，再点击下载或逐个选择文件导入。不会因文件名相似替换权重。
2. 暂停会持久保存状态、断开 HTTP，dev.42 还关闭正在读取的本地文件流，释放传输队列，让下一项用户已选择的工作继续。
3. HTTP 继续下载校验 Range、总长度和响应区间。文档提供者的普通输入流不保证随机定位，因此显式重新选择本地文件后，未完成组件从头复制；完整且已验证的其他组件保留。**本地导入重新开始不等同于 HTTP 字节续传。**
4. 每个组件满足固定大小和完整 SHA-256 后才接纳，全部组件齐全才安装。部分文件不算已安装模型，用户暂停不显示为传输失败。
5. 关闭基座停止活动读取，未完成工作持久暂停。恢复 App 不自动传输，用户显式继续或重新选择文件。原始文件、已装版本、逐模型设置独立保留。

本次修复调用关闭实际输入，但所有 Android 文档提供者的响应尚未验证。大模型复制吞吐、Android 文件选择器及全部目标生命周期仍待验收。已有文件完整 SHA 接入、流式复制和 Android 文件选择器分别记账；原 MOSS 13.43 GB 主机复制 900 秒超时没有因此通过。

## 实现与验证

共用 `BundleTransfers` 先禁止后续读取，再取出并关闭活动输入。登记新流与暂停共享任务锁，关闭在任务锁之外执行，退出的旧操作只移除自己的流引用。完整 SHA 接纳与组件租约仍强制执行。

真实阻塞输入夹具首先复现旧问题：暂停后下一项导入无法运行。[原始失败](../verification/research/bundle-pause-issue/first-run.json)保留原代码、用例、驱动与输出。修复后 13 项检查通过，覆盖阻塞读取释放、队列继续、暂停持久化、显式重新导入完整字节 / SHA、关闭活动流及关闭后队列不打开输入。这 13 项也进入共用基座 692 项检查；API 68 项通过。它们是原生 Windows 上的生产 Java 检查，无网络请求、模型推理或 Android 执行。

```powershell
python tools/test_bundle_pause.py
python tools/test_foundation.py
python tools/test_api.py
```

[当前暂停检查](../verification/development/bundle-pause.json) · [基座](../verification/development/foundation.json) · [API](../verification/development/api.json)

没有新增页面控件；[恢复管理截图 / GIF / MP4](media/development/recovery/manifest.json)按当前版本重录，明示模拟桥接，不作为 Android 导入证据。

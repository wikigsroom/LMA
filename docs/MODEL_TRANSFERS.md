# 本地模型导入、暂停与恢复

[English](MODEL_TRANSFERS.en.md) · [完整版本范围](MULTIMODAL_RELEASE_PLAN.md) · [本轮编号记录](releases/v0.3.0-dev.44.md) · [程序验证规则](PROGRAM_VALIDATION.md)

用户在「全部 / 搜索」选择模型，在「本地」管理资产。安装、升级、浏览不会开始下载；APK 只交付共用基座。生文、生图、生视频、生音频按任务和依赖标签区分，模型平级；推荐 m08→m06→m01 保留。

## 操作逻辑

1. 查看完整组件、许可证、磁盘需求及运行状态，再点击下载或逐个选择文件导入。不会因文件名相似替换权重。
2. 暂停会持久保存状态、断开 HTTP，并取消等待打开的文档 / 关闭正在读取的流，释放传输队列，让下一项用户已选择的工作继续。dev.44 覆盖模型包、原有文本模型与媒体素材；关闭基座也取消等待打开的输入。
3. HTTP 继续下载校验 Range、总长度和响应区间。文档提供者的普通输入流不保证随机定位，因此显式重新选择本地文件后，未完成组件从头复制；完整且已验证的其他组件保留。**本地导入重新开始不等同于 HTTP 字节续传。**
4. 每个组件满足固定大小和完整 SHA-256 后才接纳，全部组件齐全才安装。部分文件不算已安装模型，用户暂停不显示为传输失败。
5. 关闭基座停止活动读取，未完成工作持久暂停。恢复 App 不自动传输，用户显式继续或重新选择文件。原始文件、已装版本、逐模型设置独立保留。

系统文件提供者通过取消信号接收打开取消请求，具体提供者可能延迟响应；迟到的句柄不会发布为有效输入。程序检查使用小型数据和明确标记的主机接口，Android 文件提供者与大模型吞吐未实测。根据新规则，不再为验证复制完整模型；原 MOSS 13.43 GB 主机复制超时仍为历史失败。

## 实现与验证

共用 `InputHandle` 在调用提供者前登记输入来源；`DocumentInput` 使用系统 `CancellationSignal` 打开 `AssetFileDescriptor`。取消覆盖等待打开和读取两阶段，迟到资源立即释放；回调 / 关闭在管理锁之外执行，旧操作不会关闭新任务。完整 SHA 接纳、磁盘保留量和组件租约继续强制执行。

真实阻塞夹具先后复现[读取阶段旧问题](../verification/research/bundle-pause-issue/first-run.json)和[打开阶段本轮问题](../verification/research/input-opening-issue/first-run.json)，保留原代码、用例、驱动和失败输出。当前 22 项模型包检查覆盖打开 / 读取 × 暂停 / 关闭；后端 138 项包含文本与媒体导入 8 组 / 40 项取消和恢复检查；实际 `DocumentInput` 源码另做 6 组 / 15 项检查，包括空句柄、创建流失败、提前取消和迟到资源。基座 701 项、API 68 项通过。以上是原生 Windows 上生产程序与明确 Android 接口替身的检查，不是完整模型或 Android 真机运行。

```powershell
python tools/test_bundle_pause.py
python tools/test_document_input.py
python tools/test_backend.py
python tools/test_foundation.py
python tools/test_api.py
```

[当前程序证据](../verification/program/status.json) · [历史 dev.43 记录](../verification/development/status.json)

没有新增页面控件；[恢复管理截图 / GIF / MP4](media/development/recovery/manifest.json)保留 dev.42 原始页面夹具与身份，核对相关页面源码不变；本轮另外运行当前页面回归，不把旧录制或主机夹具作为 Android 导入证据。

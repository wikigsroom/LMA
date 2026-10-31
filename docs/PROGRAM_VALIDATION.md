# 仅程序验证策略

[English](PROGRAM_VALIDATION.en.md) · [v0.3.1](releases/v0.3.1.md) · [policy JSON](proposals/program-validation-policy.json)

用户于 2026-10-31 明确要求后续只做程序验证，不再走完整模型运行验证。该要求覆盖旧文档的完整训练模型、ASR、真机推理及长时耐久门槛；不豁免缺失的程序功能，不拆分原先冻结范围。

v0.3.1 延续 F-01–F-12、文本、01–14 / 16 / 17 的完整程序集成，在同一基座增加 44 个社区 checkpoint 配方与内容来源标记。详见[当前实现](IMPLEMENTATION_V031.md)、[社区来源 / 使用说明](COMMUNITY_MODELS.md)和[当前矩阵](../catalogue/release-0.3.1-implementation.json)。

| 项目 | 当前结果 |
| --- | --- |
| 程序检查 | 24 组 / **4,438 项**，当前源码指纹核对 |
| 新社区来源 / 生产 Java | 814 项，覆盖全部 44 个可选配方、标签、独立参数与任务规划 |
| 完整页面 | **564 项**；另有两条当前录制流程，社区 34 项 / 工作台 8 项 |
| 安装包 | ARM64、API28、35 原生库、依赖完整、16 KiB ELF / ZIP 对齐、原签名 |
| Android Lint | 0 错误，16 个原有警告 |
| 当前媒体 | 10 张截图、2 GIF、2 MP4；明确显示 UI FIXTURE |
| 研究数据 | 27 个来源仓库、45 个必要文件头与有界 API / 模型卡元数据；不是完整模型 |
| 完整模型下载 / 复制 / 执行 | 全部为 0 |
| 真机 / 效果 / 耐久 | 本轮按用户要求不执行，不声称通过 |

[29 份当前记录](../verification/program/status.json)绑定本版源码和 APK。v0.3.0 的 29 个程序文件[原样归档](../verification/history/v0.3.0-program-archive.json)，与原提交 Git blob 对照；旧两条录制位于 `docs/media/history/v0.3.0/`。dev.45 / dev.44 / dev.42 和先前完整模型失败记录保留原身份，不变成当前通过。

程序检查通过明确的桌面 Android / 媒体 / 神经阶段替身调用生产校验、参数、存储、调度、进程管理、下载与接口代码。Android Service、SAF、MediaCodec 的真实系统执行以编译和包检查覆盖，未在设备执行。有界随机神经小图只校验计算结构，不是训练模型生成。

`release_ready` 表示符合本策略的程序发行要求，不表示努比亚 Z20 或其他手机已经跑通某个 checkpoint。文件头检查不能证明模型效果、峰值内存、预测语义或驱动表现；这些边界写入来源说明。

主要复核入口：`tools/test_backend.py` → `tools/test_community.py`、`node tests/ui-smoke.cjs`、`tools/build.py` → `tools/verify_package.py` → `tools/test_android_lint.py`、两条 `capture_workbench.cjs community / release-workbench` 录制。其他原有受影响套件也必须保持当前；完整列表和指纹见状态记录。最后运行 `tools/release_scope.py`、`tools/program_evidence.py --export`、`tools/package_delivery.py`、`tools/check_repository.py` 和 `tools/prepare_release.py`。

不得通过改写指纹、放宽门槛、删除历史失败或把仅登记条目标成已适配来制造通过。不得使用 `--trained`、下载完整训练模型、调度 Docker / WSL / 虚拟机 / 模拟器；浏览器须在 finally 中关闭。APK 不包含权重或个人凭据，下载和模型更新由用户明确选择。

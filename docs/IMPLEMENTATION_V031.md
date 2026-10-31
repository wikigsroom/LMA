# v0.3.1 程序实现与本轮增量

[English](IMPLEMENTATION_V031.en.md) · [社区完整指南](COMMUNITY_MODELS.md) · [当前实现矩阵](../catalogue/release-0.3.1-implementation.json)

同一 App 延续完整 F-01–F-12 基座、既有文本和 01–14 / 16 / 17。保留 38 套模板、12 个扩展引擎系列。各原有路线详见冻结的[基座实现](IMPLEMENTATION_V030.md)；本版源码身份与程序验证以 v0.3.1 矩阵及记录为准。

| 编号 | 本轮增量 | 生产实现 |
| --- | --- | --- |
| 01 | 14 系列 / 44 个可选 checkpoint | `community_catalogue.py`、精确 Range 文件头与 API 证据、不可变 ID、合并为 67 项的目录 |
| 02 | 独立内容来源 | `ContentMetadata`、`ModelBundle.tags`、`HubClient`、`RecipeCatalogue` 将标记保留到自选 HF 配方 |
| 03 | 全部 / 搜索 / 本地闭环 | `community.js`、内容 / 来源筛选、来源 / 许可 / 组件复核与原有明确下载流程 |
| 04 | 本机执行 | 沿用 SD1.5 / SDXL CPU、Wan 2.1 T2V 1.3B Vulkan；不引入外部推理、ROOT、自动权重下载或用户插件 |
| 05 | 可审查交付 | 原签名、程序检查、双语文档、当前截图 / GIF / MP4、v0.3.0 原样证据归档 |

新增配方已进入程序流程并检查来源文件结构，不代表完整模型或真机验收。更新的视频架构和视频 LoRA 明确列为不适用当前配方，具体调研见社区指南；原先选定的基座目标没有顺延或删除。

# LMA 界面与交互 / Interface and interaction

**当前规范：UI10 云母分区 / Current specification: UI10 Mica Bento (2026-11-03).**

以不透明蓝灰分区、钴蓝选中和薄荷操作构建 Android 本地模型工作台。默认暗色，完整支持明亮与系统跟随；保留 Logo21、标语04、模型平级、本机推理、用户主动下载和每模型参数。五个入口为模型库、对话、任务、服务、设置。

Use opaque blue-gray sections, cobalt selection and mint actions. Default to dark, fully specify light/System, and preserve Logo21/Slogan04, equal model peers, same-phone inference, explicit downloads and per-model settings. The five destinations are Models, Chat, Tasks, Server and Settings.

| 内容 / Topic | 中文 | English |
| --- | --- | --- |
| 风格、明暗配色、字体、材质与性能 / Style and themes | [设计总规范](design/MICA_BENTO.md) | [Design](design/MICA_BENTO.en.md) |
| 模型卡、参数、对话、任务、媒体、API 与弹层 / Components | [30 类组件](design/COMPONENTS.md) | [Component contracts](design/COMPONENTS.en.md) |
| 窄屏、宽屏、横屏、键盘、折叠与大字 / Adaptive layout | [适配及验收](design/RESPONSIVE.md) | [Adaptation and acceptance](design/RESPONSIVE.en.md) |
| 机器可读值与决策 / Values and decision | [tokens.json](design/tokens.json) | [decision.json](design/decision.json) |

v1.0.0 已接入新 UI；参考 CSS 不直接加载，运行资产由 tokens 编译。[实现和真机演示](MICA_V100.md)／[English](MICA_V100.en.md)。原始 20 套方案、包和已发布 APK 保留身份。历史浅色／四入口说明已迁至[旧设计档案](history/DESIGN-initial.md)，不得继续按其过时导航和默认主题实施。

v1.0.0 implements this specification. [Current implementation and phone media](MICA_V100.en.md). Reference CSS is not directly loaded; runtime tokens are generated. Original concepts, archives and the published APK retain their identity. The superseded light/four-destination brief is preserved in the [historical archive](history/DESIGN-initial.md).

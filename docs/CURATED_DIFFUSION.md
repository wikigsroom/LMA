# 生图模型选择、依赖与任务闭环

[English](CURATED_DIFFUSION.en.md) · [使用手册](USER_GUIDE.md) · [本轮实现及完整待办](releases/v0.3.0-dev.32.md)

**0.3.0-dev.32 / code 36** 将六套已有完整训练主机记录的资产方案加入“模型 → 全部”，补齐通用 LoRA 基础模型查看入口。App 安装与升级只增加基座代码和清单；没有权重、分词数据或自动下载。它是内部开发检查点，完整 v0.3.0 的所有要求继续保留。

## 1. 可选清单

六项与其他模型平级，使用“生图”、架构、引擎和 LoRA / 基础模型依赖标签；推荐仍为 **m08 → m06 → m01**。HF 全部 / 搜索与自定义配方继续可用。这不是“所有 HF 模型均可在 Android 运行”的声明。

| 编号 | 全部列表中的方案 | 该包完整下载字节数 | 额外依赖 |
|---|---|---:|---|
| C01 | [SDXL Base 1.0 Q4_0 / genai-archive](https://huggingface.co/genai-archive/stable-diffusion-xl-base-1.0-gguf) | 2,598,564,107 | 完整 checkpoint 与 CLIP merges 已逐项列出 |
| C02 | [PixelArtRedmond SD 1.5](https://huggingface.co/artificialguybr/pixelartredmond-1-5v-pixel-art-loras-for-sd-1-5) | 27,216,848 | 单独选择 SD 1.5 基础模型；提示词可用 `pixel art, PixArFK` |
| C03 | [Pixel Art XL / nerijs](https://huggingface.co/nerijs/pixel-art-xl) | 170,543,052 | 单独选择 SDXL 基础模型；作者未要求专用触发词 |
| C04 | [LCM-LoRA SD 1.5](https://huggingface.co/latent-consistency/lcm-lora-sdv1-5) | 134,621,556 | 单独选择 SD 1.5 基础模型，使用明确的 LCM 任务策略 |
| C05 | [LCM-LoRA SDXL](https://huggingface.co/latent-consistency/lcm-lora-sdxl) | 393,855,224 | 单独选择 SDXL 基础模型，使用明确的 LCM 任务策略 |
| C06 | [SD-Turbo Q8_0 / Green-Sky](https://huggingface.co/Green-Sky/SD-Turbo-GGUF) | 2,024,269,995 | 完整 checkpoint 与 CLIP merges 已逐项列出 |

字节数是所选包的文件总量，**LoRA 行不包含另选基础模型**。已经通过完整哈希校验的同一对象可复用；剩余传输由详情页显示。文件大小不是运行峰值内存；这六项的手机峰值资源均保持未知，不据此承诺努比亚 Z20 可用。

## 2. 用户操作

1. 打开“模型 → 全部”，选择“生图”，查看模型详情、许可、完整组件、所需空间及可复用文件。此操作只看清单。
2. 选择基础模型或独立 SD-Turbo 时，点击“下载所选模型包”，或从完整文件夹导入。下载仅包含明确列出的组件。
3. 选择 LoRA 时，详情列出当前库中声明兼容的基础模型，以及“尚未安装 / 传输未完成 / 已安装 / 使用中”状态。点击“查看基础模型”，检查该基础包的完整内容；可用“返回 LoRA”回到原选择。**LoRA 下载不连带下载基础模型。** 基础模型也需你明确点击下载或导入。
4. 在“本地”管理已下载模型与未完成传输。LoRA 已装但基础模型未装时，“选择基础模型”会阻止提交，并提供直接查看入口。兼容基础模型安装后可配对；不同架构、配方、后端或受限模型标识不会混入选择。
5. 从本地模型设置保存该模型的默认参数。任务表单允许编辑 LoRA 强度，超限回填各自上限；本次修改不改变已保存默认值。普通风格 LoRA 和 LCM-LoRA 的范围分别来自其模型描述。
6. 填写提示词、检查参数并明确提交。任务冻结基础包、LoRA、各自强度与采样参数，进入共用本地队列。LCM-LoRA 使用 1–8 步、CFG 1、空负面提示词；SD-Turbo 使用 1–4 步、CFG 1、空负面提示词及 Euler ancestral。基础模型的保存设置保留。
7. 沿用任务详情、取消 / 明确重试、资源保护与结果库。生成、解码和媒体处理均在同一手机；缺资产不会触发下载或转到其他设备执行。本轮界面录像只演示到排队，实际训练图像见已有独立主机证据。

## 3. 升级、资产与许可

六套方案采用新的不可变包 / 模型标识（见[实际清单](../catalogue/model-bundles.json)）。之前导入的研究清单保持原样；不会用新增描述覆盖同名旧包，也不会迁移覆盖旧设置或改写旧任务。新 SD 1.5 LoRA 明确兼容 App 已有基础模型 `sd15_ss_q4_0_r031b5f5`，同时保留旧导入标识；新 SDXL LoRA 同时允许本轮 SDXL 基础包和旧研究包。实际配对仍由生产 Java / 原生接口验证。

发布者的许可标记分别为：SDXL 量化仓库 CreativeML OpenRAIL-M，原始 SDXL 为 Open RAIL++；PixelArtRedmond 为 bespoke LoRA 条款；Pixel Art XL 为 CreativeML OpenRAIL-M；两套 LCM-LoRA 为 Open RAIL++；SD-Turbo 量化仓库为 Stability AI Community License Agreement。参见表中各发布者模型卡及[SDXL / LoRA 许可记录](SD_VARIANTS_TRAINED.md)、[SD-Turbo 许可记录](SD_DISTILLED_TRAINED.md)。这些分别记录的作者声明不替代逐组件 / 上游条款审核，也不构成统一再分发许可；原始模型数据不进入 APK、Git 或源码附件。

2026-10-30 复核了可访问的公开模型卡。固定 revision API 的本机直连超时；本轮没有重新下载训练权重或把它说成新鲜的文件可用性检查。[逐组件清单证据](../catalogue/bundle-evidence.json)将完整固定 URL、revision、字节数与 SHA 绑定至原资产锁和原始主机记录，并记录这一限制。构建工具校验历史文件本身的 SHA，不把历史训练结论冒充本轮运行。

## 4. 验证与媒体边界

| 编号 | 本轮验证 | 意义与边界 |
|---|---|---|
| V01 | 55 项新增生产数据层主机检查 | 旧导入与 16 项清单共存、重开后设置保留、精确组件一致、零自动传输、两类 LoRA 正反配对 |
| V02 | 40 项当前界面检查 | 四种 LoRA 逐一走依赖查看、明确下载意图、安装状态夹具、配对、上限回填与冻结任务请求；不是实际下载或推理 |
| V03 | 原签名 arm64 APK 与当前回归记录 | Android 编译 / 包核验、源码业务控制和界面留证；不等于物理手机测试 |
| V04 | 历史完整训练记录独立保留 | [SDXL / 两类 LoRA / LCM-LoRA](SD_VARIANTS_TRAINED.md)、[SD-Turbo](SD_DISTILLED_TRAINED.md)；本轮未重跑模型数学 |

| LoRA 依赖（桌面界面夹具） | 配对任务（桌面界面夹具） |
|---|---|
| ![SDXL LoRA 依赖查看](media/development/curated/01-dependency-review.png) | ![配对与独立强度](media/development/curated/03-paired-task.png) |

[基础包详情](media/development/curated/02-base-review.png) · [任务队列](media/development/curated/04-queued-task.png) · [录屏 MP4](media/development/curated/curated-ui.mp4) · [GIF](media/development/curated/curated-ui.gif) · [媒体原始记录](media/development/curated/manifest.json)。全部明确标注 UI FIXTURE，执行后关闭浏览器，不下载或打包模型。

完整版本仍要求 F01–F12、既有生文及 01–14 / 16 / 17 全部冻结子目标、训练质量与资源、同机 Android 验收。原 LCM 像素 maximum 8 > 5 和旧 LTX 六项数值失败保持失败；参见[完整编号待办](releases/v0.3.0-dev.32.md)。

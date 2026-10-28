# HF 组件选择与本地配方

[English](HF_RECIPES.en.md) · [HF 发现](HF_MODELS.md) · [开发状态](DEVELOPMENT.md) · [资产边界核对](ASSET_CONTROL_AUDIT.md)

适用：**0.3.0-dev.16 / code 20，内部开发检查点，未发 Release**。App 提供代码与配方元数据，用户选择和管理模型资产。以下流程不表示任意 HF 权重均能在 Android 上运行；实际架构、语言、组件配套、许可和设备资源仍需核对。

## 用户操作

1. 在模型页进入“全部”或搜索 HF，打开仓库的“选择文件”。保留原有 GGUF 文本入口；点击“构建模型包 / LoRA 配方”进入组件选择。
2. 明确选择配方。当前提供二十九个签名 App 数据模板：文本 GGUF、MOSS Nano、Qwen3-TTS Base、MOSS Delay first-class、Local-v1.5 / SoundEffect-v2、MOSS-TTS / v1.5 / TTSD / VoiceGenerator、匹配的 Sana MNN 移动管线、Z-Image / FLUX / Qwen-Image / Wan 独立组件、SD1.5 / SDXL 完整及分离组件、两者普通 LoRA、SD-Turbo、两者 LCM checkpoint / LCM-LoRA，以及 Kokoro / Piper / Matcha 英语模板。具体组件和采样规则见[扩散指南](DIFFUSION_ENGINE.md)。模板不安装引擎，不转换权重，不证明手机已支持。
3. 按角色选择每个必需文件，例如 `model`、`voices`、`tokens`、`vocoder`。可在选择页输入其他 `作者/仓库`，使用分页寻找组件；已经选择的组件保留各自仓库和固定提交。文件扩展名只用于角色格式检查，不推断模型架构或语言。切换配方会清空草稿选择，关闭窗口或重启可能丢失未登记草稿。
4. 检查主文件、全部固定依赖、来源、版本、大小与校验类型。扩散模板披露 CLIP merges；分离 SDXL 必须包含 CLIP-L、CLIP-G 和 VAE。语音模板披露英语词表；其他语言仍需正确完整配方。LCM-LoRA 使用专用模板，不能把普通 LoRA 名称当成加速声明。
5. 点击“加入本地并查看下载计划”：只登记不可变清单，**不下载**。在详情中核对完整总量、已验证可复用文件、剩余传输及引擎状态，再单独点击下载。缺引擎、缺文件或不兼容时在本机说明原因，没有外部推理或隐式补下载。
6. 在“本地”暂停 / 续传、导入文件夹、管理独立参数与删除资产。LoRA 是平级记录，使用时明确选择兼容基础模型。任务通过同一手机队列执行；推荐 `m08 → m06 → m01` 不变。

## 数据和校验

App 内的 `lma.recipe-catalogue/1` 只有模板、参数、角色和依赖元数据。生成的 `lma.model-bundle/2` 含数据组件；不能携带 Python、SO、脚本、任意命令或用户插件。

| 文件来源 | 固定的预期校验 | 下载 / 导入完成后 |
| --- | --- | --- |
| HF LFS 权重等大文件 | 发布元数据的 SHA256 与完整大小 | 对实际内容计算并核对 SHA256 |
| HF 普通 Git 小文件 | 固定提交、Git blob SHA-1 与完整大小 | 对 `blob <字节数>\0` + 文件内容核对 Git 对象 ID，并另存实际内容 SHA256 |

Git blob SHA-1 **不是**原始文件 SHA-1，也不是发布者 SHA256。普通 Git 元数据没有提供预期 SHA256 时，界面不会伪造这一值。存储使用带命名空间的对象键；该键不是内容哈希声明。任务来源记录同时保留预期算法 / 摘要与已验证的实际 SHA256。校验不能证明来源可信、许可证允许使用或模型质量。

旧 `lma.model-bundle/1` 的 SHA256 对象与回执兼容保留；新模式要求每组件恰好一种预期校验。新配方以角色区分文件夹导入路径，例如 `model/model.onnx` 与 `vocoder/model.onnx`，避免跨仓库同名文件冲突；准确路径见下载计划。运行引用保护整个模型及适配器组件组，共享文件不会因为删除另一个模型而被提前移除。

原生端只接受当前固定仓库文件页中的选择。切换仓库 / 分页、变更模板后，过期命令被拒绝；WebView 不能自行拼接未展示的下载文件或提供引擎代码。相同模板 / 组件选择重复登记复用同一 ID；更改固定来源或配方形成新的不可变记录。登记新版本后可在“本地 → 版本管理”进行[独立更新 / 回退](MODEL_UPDATES.md)；完整旧记录迁移仍有同版工作未完成。

## 验证与演示边界

存储 / 校验 / 版本管理 445 项检查含 253 项配方与 Git 完整性断言；HF 元数据 / 原生控制器及 UI 回归另见 [development 回执](../verification/development/status.json)。桌面检查使用任意字节或显式模拟原生状态，未下载测试权重，不是模型输出、手机安装或锁屏耐久证据。

![HF 组件选择流程，显式 UI 测试数据](media/development/12-hf-components.png)

![组件文件与校验类型，显式 UI 测试数据](media/development/13-hf-component-files.png)

完整 v0.3.0 仍要求 F-01–F-12、01–14 / 16 / 17 的全部冻结子目标和 A1–A11 验收；本功能不删减、拆分或顺延这些要求。公开安装包仍为 v0.2.0。

元数据字段依据核对日期为 2026-10-28 的 [HF 官方 SDK `RepoFile` 解析](https://github.com/huggingface/huggingface_hub/blob/main/src/huggingface_hub/hf_api.py)及[官方文件树 API 说明](https://huggingface.co/docs/huggingface_hub/package_reference/hf_api#huggingface_hub.HfApi.list_repo_tree)：普通文件的 `oid` 与 LFS 的 `oid` 含义不同。当前新增控制器检查使用确定性元数据夹具；本轮直连 HF 超时、镜像 403，未取得新的实时文件树验收，也未下载权重。

![登记后的独立下载计划，界面测试数据](media/development/14-hf-download-plan.png)

## Nano 外置数据配方

第八种模板仅面向 MOSS-TTS-Nano browser ONNX 及完整 codec。`.model` SentencePiece 与 `.data` 外置权重都是用户单独选择的组件。八个核心角色必选，被图引用的数据在执行时同样必须齐全；登记不创建传输。详见 [Nano 角色、保护值、构建与证据](MOSS_NANO_ENGINE.md)。

## 文本 GGUF 配方

dev.8 增加 `text_gguf_cpu_v1`，必需角色仅 `text_gguf`，固定模型及内含 tokenizer 由用户下载或导入；不支持拆分 GGUF / 视觉组件 / 任意架构自动转换。新包可在同一队列提交 `text.generate` 并预览正文 / 思考。既有单文件入口和推荐保持，已有文件本地迁移见[迁移指南](MODEL_MIGRATION.md)，物理升级仍待验收。详见[文本基座指南](TEXT_ENGINE.md)。

dev.9 将原有完整文本 / HF / 导入 GGUF 纳入同一资产、参数、任务与版本协议，不重复下载；69 项主机检查不代替手机升级验收。见[迁移指南](MODEL_MIGRATION.md)。


dev.13 增加 Z-Image-Turbo、FLUX.2-klein 4B、Qwen-Image 2.1 与 Wan 2.1 T2V 1.3B 四个独立组件模板，总计二十个。编码器、VAE、词表均需用户明确选择；不能因主权重是 GGUF 就忽略依赖。详见[组件与参数](ADVANCED_DIFFUSION.md)。

## Sana 移动变体

dev.14 接入 [Sana 移动管线 / MNN](MNN_SANA_ENGINE.md)：真实 ARM64 CPU worker、13 个用户自选组件、Qwen3 metadata 白名单、分阶段释放编码器、独立 CFG / token / 线程参数与不可变任务快照。74 项主机 / C++ 检查不包含模型推理；全部 21 个模板仍只登记元数据、由用户确认下载。445 项基座与 208 项界面检查通过；37 张截图及录屏 / GIF 均标识 UI FIXTURE。没有 Android 生图 / 耐久证据，完整 v0.3.0 的冻结目标和发布门槛保持不变，未创建新 Release。

Qwen3-TTS 新增第 22 个模板和一个固定版本可选包：两个 GGUF 分别提供 Talker（内含词表 / Code Predictor / speaker encoder）和 12Hz codec。通用 `provides` 显示内含依赖，不额外下载。只匹配 0.6B Base，实际文件头已核对，手机执行仍待验收。详见 [Qwen 语音指南](QWEN_TTS_ENGINE.md)。

## MOSS Delay：可选参考编码器

第 23 个模板 `moss_delay_firstclass_cpu_v1` 需要匹配的原生 first-class 主模型和解码器；编码器只在用户需要参考 WAV 时选择。普通 MOSS GGUF、v2 codec 和其他 MOSS 架构不能替代。当前没有新增固定已核对下载候选；用户选择文件或导入转换包，App 不隐式补下编码器。完整流程与参数见 [MOSS Delay](MOSS_DELAY_ENGINE.md)，完整家族仍逐项验收。

[Local-v1.5 / SoundEffect-v2](OPENMOSS_ENGINE.md) 使用同次转换的主干和 extras 两个用户文件，内含 BPE / codec 用 provides 披露；两者不能混用，也不接受 first-class Delay 文件。登记、浏览与更新基座不触发下载。

同一原生引擎另外提供 TTS / v1.5 / TTSD / VoiceGenerator 四个独立配方：分别检查 32 / 16 路、8B / 1.7B 主干布局。它们输出 24 kHz 单声道，TTSD 双参考成对映射，VoiceGenerator 必填声音描述；组件与其他 MOSS 格式不互换。详见[完整流程、参数与发布者证据](OPENMOSS_ENGINE.md)。模型仍是同列表中的平级记录，带生音频 / TTS / 多说话人或声音设计以及独立基座依赖标签。

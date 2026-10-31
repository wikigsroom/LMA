# 语音与本地生 3D：v0.3.2

> 当前开发 v0.3.6 已实现 [F5 官方兼容分词 / 变调前端](F5_FRONTEND.md) 与独立 [Hunyuan Paint / PBR](LOCAL_MATERIALS.md)；完整待办见[编号清单](REMAINING_ADAPTATION.md)。下文 F5 实验前端和各模型缺口属于 v0.3.2 历史，不覆盖当前已实现内容。

> 本页记录 v0.3.2 的实现。v0.3.3 已另增 D03 Pixal3D MV 真实四视图子集，见[当前方案与剩余移植工作](MULTIVIEW_DIAGNOSTICS.md)。下方旧数量 / 证据按原版本理解。

[English](SPEECH_3D_EXPANSION.en.md) · [使用手册](USER_GUIDE.md) · [API](API.md) · [发布说明](releases/v0.3.2.md)

本版在原有完整基座上增加四类语音模型的可选方案，以及 TRELLIS.2 / Pixal3D 单图生 3D 路线。全部编码、推理、解码、网格处理和导出都在同一 Android 手机执行。APK 只增加程序，不携带或自动下载权重、音色、词表、分词器和发音词典。

“接入”指真实运行器已编入 ARM64 APK，并接通组件、设置、输入、任务和结果流程。按用户要求，本轮只做程序验证，没有下载完整模型、执行训练权重或使用 Android 真机。它不等于音质、数值一致性、速度、峰值内存或锁屏耐久验收。

## 1. 四类语音模型的结论

| 编号 | 用户指定模型 | 当前 Android 路线 | 格式与范围边界 |
| --- | --- | --- | --- |
| S01 | Kokoro PyTorch | 既有 sherpa-onnx Kokoro，加一个匹配的 INT8 可选包 | 执行匹配 ONNX 导出；不直接执行任意 `.pth`。新增包为英文前端；模型名称含 multi-lang 不代表此包覆盖全部语言。既有 54 音色选择保留 |
| S02 | MeloTTS Chinese | sherpa-onnx VITS/Melo 中文，INT8 与 FP32 两个包 | ONNX＋tokens＋带声调的 phones/tones 词典＋四份文本归一化 FST；固定中文音色，不是音色克隆 |
| S03 | F5-TTS v1 Base | 新增 `audio_cpp` CPU / `f5_v1` | 原版 v1 safetensors＋Vocos＋vocab；中文另需两个用户下载的拼音资源；参考音频与对应文本必填 |
| S04 | OmniVoice | 新增 `audio_cpp` CPU / `omnivoice` | 集成 Q8 GGUF，或原版 safetensors＋文本分词器＋音频 codec；支持自动 / 参考克隆 / 描述音色参数；本版输出完整 WAV |

来源：[Kokoro](https://github.com/hexgrad/kokoro)、[MeloTTS](https://github.com/myshell-ai/MeloTTS)、[sherpa-onnx VITS](https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/vits.html)、[F5-TTS](https://github.com/SWivid/F5-TTS)、[OmniVoice](https://github.com/k2-fsa/OmniVoice)。这是格式适配结论，不是同名任意仓库和任意权重都能运行的保证。

### 1.1 可选下载包

字节为固定 revision 下全部必需组件之和；共享资产命中后实际新增下载更少。这些数字不是运行 RAM。详细文件、固定提交、哈希与来源见[模型包](../catalogue/expansion-bundles.json)和[来源证据](../catalogue/expansion-bundle-evidence.json)。

| 编号 | 包 ID | 必需组件总字节 | 参数与说明 |
| --- | --- | ---: | --- |
| S01a | `kokoro82_int8_57adb37` | 148,710,413 | INT8 ONNX＋既有 voices / 英文 lexicon / tokens；保留固定来源与音色编号 |
| S02a | `melo_zh_int8_a0d5c6a` | 60,589,996 | 中文 INT8；语速、停顿、noiseScale / noiseScaleW、线程独立设置 |
| S02b | `melo_zh_fp32_a0d5c6a` | 177,502,116 | 同一配方的 FP32 选择，不与 INT8 包混用主模型 |
| S03a | `f5_tts_v1_base_84e5a41` | 1,413,398,722 | 原版 F5 v1、Vocos、vocab、字符和词组拼音资源 |
| S04a | `omnivoice_q8_874fcb4` | 1,350,296,096 | 一个集成 GGUF；无需另行套用 F5 / Kokoro codec |
| S04b | `omnivoice_original_c5fdb5c` | 3,267,439,234 | 原版模型＋配套 tokenizer / config / audio codec，按固定私有目录布局关联 |

Kokoro / Melo 是本轮较小的选择。F5、OmniVoice 仍有 GB 级权重，以及 codec 和中间激活开销；不能因为列入本轮就称它们适合所有手机。

### 1.2 输入、前端与许可

1. **Kokoro**：复用已有英文词典与音色控制。新增 INT8 主模型身份独立，不能把原始 PyTorch checkpoint 改扩展名当 ONNX。Apache-2.0 主模型不抹去共享词典的单独条款；目录保留待复核提示。
2. **Melo 中文**：使用固定 sherpa-onnx 中实际读取的带声调最长词组 lexicon，不把未使用的 `dict_dir` 当成中文支持。`date.fst / number.fst / phone.fst / new_heteronym.fst` 连同 tokens 明确列为组件。模型与词典、规则各自适用发布者条款。
3. **F5 v1**：参考音频须为 **24 kHz、单声道、PCM16 或 float32 WAV、1–12 秒、最多 8 MiB**，同时填写准确转写。中文使用外置字符与词组字典，做最长词组匹配和声调转换；不附字典到 APK。未知字或词表缺失会报错，不静默丢字。本地实现没有验证与官方 Python 的完整分词、变调和全部发音策略一致，中文音质仍属实验范围。代码 MIT，F5 权重 **CC-BY-NC-4.0**，Vocos 与拼音资源另有 MIT 条款。[F5 权重](https://huggingface.co/SWivid/F5-TTS)、[Vocos](https://huggingface.co/charactr/vocos-mel-24khz)、[字符](https://github.com/mozillazg/pinyin-data)、[词组](https://github.com/mozillazg/phrase-pinyin-data)。
4. **OmniVoice**：参考克隆同样需要准确文本，WAV 要求同上、时长 **1–30 秒**；描述模式填写 voiceInstruction，auto 可不提供参考。上游“600+ 语言”是作者能力声明，本轮没有逐语言验证。输出为完整 WAV，没有承诺原生增量 PCM 或 pseudo-streaming。代码 Apache-2.0、权重 CC-BY-NC-4.0，codec 条款单独适用。[原版](https://huggingface.co/k2-fsa/OmniVoice)、[GGUF](https://huggingface.co/audio-cpp/audio.cpp-gguf)。

F5 使用原版 v1 结构，未把 Habibi 的方言提示模板或其他 F5 变体套入本配方。Vocos `.bin` 由限定的 C++ tensor-storage 解析器读取，未引入 Python pickle 执行环境，也不代表支持任意 PyTorch 程序。

## 2. 对指定 3080 生 3D 测评的逐项检查

检查入口：[3080 生 3D 集合](https://benchmark.sidcloud.cn/collections/3080-3d)。本次集合包含 **12 条新轮次配置＋4 条旧轮次配置＝16 条记录**，不是 16 种独立架构，也没有 TripoSR 条目。逐条 case URL、来源文件 SHA256、项目 README 内容身份与修正链接保存在[审计记录](../research/expansion/benchmark-audit.json)。

测评在 Windows 原生 RTX 3080 上运行。它的成功、失败、耗时和已安装权重 GB 均不是 Android 数据；“已有网格贴图”“粗网格精修”“多视图融合”不能当作同一种单图几何生成。

| 编号 | 测评记录 / 模型 | 本版结果 | 具体边界或后续工作 |
| --- | --- | --- | --- |
| D01 | `3d-20261030-TRELLIS2` / TRELLIS.2 | 接入单图子集 | GGUF / CPU；512 几何、可选 512 / 1024 纹理组件。不是测评工作流、法线 / AO 导出和 3080 数值表现的逐项复刻 |
| D02 | `3d-20261030-Pixal3D` / Pixal3D | 接入单图子集 | 512 仅几何，1024 可选贴图；相机 FOV 手动参数，未集成 MoGe 自动估计 |
| D03 | `3d-20261030-Pixal3D-MV` | 当前未接入 | 多视图融合与相机条件不在本次单图 C++ 管线中；不能用多张图依次生成冒充 MV |
| D04 | `3d-20261030-UltraTex` | 当前未接入 | 输入已有网格＋图片，主要做 PBR 纹理；需要独立纹理后端和网格输入业务 |
| D05 | `3d-20261030-UniForge3D` | 当前未接入 | 测评为四视图、BF16、512 几何；需要模型算子、导出与多视图后端，不据此宣称 1024 / PBR |
| D06 | `3d-20261030-UltraShape1` | 当前未接入 | 需要已有粗网格的几何精修，并非从零建模；仍需独立精修运行器 |
| D07 | `3d-20261030-Hunyuan3D21` | 当前未接入 | 测评只覆盖几何；Paint 纹理不能因同系列名称被视为已支持 |
| D08 | `3d-20261030-SAM3D` | 当前未接入 | 图像、掩膜、深度与专有算子移植未完成；顶点颜色不等于 UV / PBR |
| D09 | `3d-20261030-MV-SAM3D` | 当前未接入 | 依赖 SAM 与多视图融合；需要额外模型和相机 / 掩膜流程 |
| D10 | `3d-20261030-SUPRA-Tex` | 当前未接入 | 测评卡在 NATTEN / CuMesh / NVCC 等环境依赖；该失败只说明该次环境未跑通，不证明模型在所有硬件永久不可运行 |
| D11 | `3d-20261030-TripoSG` | 当前未接入 | 灰模几何路线；需要匹配导出、算子与网格重建后端，不能以蓝色展示材质当作模型贴图 |
| D12 | `3d-20261030-PartCrafter` | 当前未接入 | 多部件输出需要独立运行器和部件结果结构；原测评项目链接 404，已核对正确项目 |
| D13 | `3d-TRELLIS2` / 旧轮次 | 同 D01 的单图架构子集 | 不继承旧轮次“passed”作为 Android 验收，也不声称复刻其顶点颜色工作流 |
| D14 | `3d-Pixal3D` / 旧轮次 | 同 D02 的单图架构子集 | 不等于额外新增一种架构或多视图支持 |
| D15 | `3d-TripoSG` / 旧轮次 | 当前未接入 | 与 D11 同架构，旧灰模成功不消除 Android 移植工作 |
| D16 | `3d-PartCrafter` / 旧轮次 | 当前未接入 | 与 D12 同架构，测评三个可编辑部件不代表本版已具备该输出协议 |

对应一手项目：[TRELLIS.2](https://github.com/microsoft/TRELLIS.2)、[Pixal3D](https://github.com/TencentARC/Pixal3D)、[UltraTex](https://github.com/yiboz2001/UltraTex)、[UniForge3D](https://github.com/xibushu/UniForge3D)、[UltraShape](https://github.com/PKU-YuanGroup/UltraShape-1.0)、[Hunyuan3D 2.1](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1)、[SAM 3D Objects](https://github.com/facebookresearch/sam-3d-objects)、[MV-SAM3D](https://github.com/devinli123/MV-SAM3D)、[SUPRA-Tex](https://github.com/Supra-3D/SUPRA-Tex)、[TripoSG](https://github.com/VAST-AI-Research/TripoSG)、[PartCrafter](https://github.com/wgsxm/PartCrafter) / [论文](https://arxiv.org/abs/2506.05573)。README 和环境依赖审阅不是对这些尚未移植模型的全算子数值审计。

### 2.1 当前五个 3D 下载选择

| 编号 | 包 ID | 必需组件总字节 | 生成选择 |
| --- | --- | ---: | --- |
| D01a | `trellis2_geometry512_cpu_v1` | 2,626,483,168 | 512 几何；贴图默认关闭 |
| D01b | `trellis2_pbr512_cpu_v1` | 4,202,445,664 | 512 几何＋贴图 |
| D01c | `trellis2_pbr1024_cpu_v1` | 4,932,966,240 | 512 前阶段与 1024 后阶段＋贴图 |
| D02a | `pixal3d_geometry512_cpu_v1` | 6,623,961,632 | 512 几何、固定手动 FOV 参数 |
| D02b | `pixal3d_pbr1024_cpu_v1` | 13,020,618,336 | 1024 几何＋贴图；该来源的 flow 文件很大，不属于轻量手机起步包 |

后端采用 [trellis.cpp](https://github.com/pwilkin/trellis.cpp) 中可移植的 C++ / GGML 单图实现，编入真实 CPU 编码、flow、解码、稀疏几何、网格简化、UV / PNG 材质导出代码。用户下载的 [TRELLIS GGUF](https://huggingface.co/ilintar/trellis2-gguf) 与 [Pixal3D GGUF](https://huggingface.co/vegax87/Pixal3D) 分开标注来源；共享编码器 / 解码器不代表主模型或许可相同。各组件上游许可与转换发布条款分别适用，不能把 C++ 后端的 MIT 当成全部模型的许可证。

背景去除可选择额外 BiRefNet 组件，自选配方才会下载；上表未包含它。未提供时使用输入 alpha / 阈值处理，建议透明背景 PNG。Pixal3D 512 没有对应 texture flow，界面和后端都将贴图参数归位为关闭。切换到 1024 / 贴图必须先配齐相应组件，否则预检报缺失，不自动补下载。

努比亚 Z20 仅为目标设备例子，本轮没有可用真机。即使文件放得下，运行时编码器、flow、中间稀疏体素、网格和图集仍会占用额外内存；这里的几 GB 下载量不能转换成“6 / 8 GB Z20 一定能跑”。上游桌面 CPU 的耗时 / RSS 也不能直接换算成手机承诺。程序允许资源未知的用户明确尝试，运行中继续使用共用内存、存储、温控与取消机制。

## 3. 用户操作闭环

### 3.1 语音

1. 在“模型 → 全部 / 搜索”找到方案，打开组件与许可详情，主动下载或导入。安装 App / 更新 APK 不会选择模型。
2. 在“模型 → 本地”打开该模型的设置。语速、音色、步数、线程、时长保护、OmniVoice 语言 / 音色描述等均跟随该模型保存；可选择预设，也可编辑。超出程序硬上限会自动归位；程序保护上限与作者模型能力上限分开标记。
3. 点击“使用”，填写文本。F5 先从设备导入符合格式的 WAV，并输入对应文本；OmniVoice 根据所选模式填写参考或描述。导入不是上传到其他设备。
4. 查看预检，必要时明确允许尝试尚无本机记录的配方，再提交同一本机队列。保存草稿不会生成音频。
5. 成功后在任务 / 结果库试听、导出 WAV 与生成记录；失败保留明确错误，不把空文件或半成品当作成功。

### 3.2 生 3D

1. 主动下载五个选择之一，或使用“单图生 3D”数据配方关联匹配 GGUF 组件。
2. 在“本地 → 生 3D”点“使用”。导入 **PNG / JPEG、最多 16 MiB / 4,194,304 像素** 的单张物体图；可刷新已导入图片列表。
3. 编辑或选择分辨率、各阶段步数、seed、面数目标、图集大小、引导强度、FOV 和贴图开关。分辨率 512 / 1024，面数 1,000–150,000，图集 256–2048；这些是本程序支持范围，不是所有模型的理论最高能力。面数是简化目标，不承诺任意拓扑精确达到此数。
4. “保存为此模型的设置”保存默认值；“保存草稿”保存本次图片与参数。恢复草稿不会沿用执行同意，不自动排队。
5. 点击“运行前检查”检查实际组件、图片、参数和资源；它不运行模型。条件满足后明确提交，重复点击只发出一个入队请求。排队、取消、重试、重启后的中断记录沿用共用调度。
6. 结果是内嵌资源 **GLB 2.0**，记录顶点、三角面、贴图数、来源和有效参数。App 提供拖动旋转、双指 / 滚轮缩放的几何光照预览；完整 PBR 材质随 GLB 导出，预览不冒充 PBR 渲染器。
7. 预览最多读取 128 MiB、100 万顶点 / 200 万索引；更大模型仍可导出至专业 3D 编辑器。关闭 / 切换结果会取消读取并释放 WebGL 资源。生成记录可单独导出，或“编辑后再次生成”恢复输入，由用户重新提交。

所有模型仍然平级；“生 3D”“生音频”“引擎 / CPU”“必需组件”“内容来源”“已安装”分别标记。新增模型没有凭架构推断 NSFW 标签，原有社区标签与 `m08 → m06 → m01` 推荐完整保留。

## 4. 同一本机 API

仍使用现有 `/v1/jobs/preflight`、`/v1/jobs`、任务事件、取消 / 重试、`/v1/artifacts` 与导出接口。没有远程推理地址或新的外部计算服务。鉴权和幂等键规则不变。[上传协议](LOCAL_INPUTS.md)取得 `artifactId` 后构造：

```json
{
  "bundleId": "trellis2_geometry512_cpu_v1",
  "type": "mesh.generate",
  "input": {
    "prompt": "Generate a 3D asset from the selected local image.",
    "artifacts": [{"role": "reference_image", "artifactId": "REPLACE_WITH_IMPORTED_IMAGE_ID"}]
  },
  "parameters": {"resolution": 512, "texture": false, "steps": 12, "faces": 30000},
  "allowUnmeasured": true
}
```

`prompt` 是该图像条件路线的固定描述，不是文本生 3D 提示词；不支持负面提示词。先预检、审阅结果，再明确提交 `POST /v1/jobs` 与 `Idempotency-Key`。`allowUnmeasured` 只在用户同意后设置，不触发模型下载，也不绕过缺少文件等硬错误。

F5 请求示例：

```json
{
  "bundleId": "f5_tts_v1_base_84e5a41",
  "type": "speech.synthesize",
  "input": {
    "prompt": "今天我们来介绍本地模型。",
    "artifacts": [{"role": "reference_audio", "artifactId": "REPLACE_WITH_IMPORTED_WAV_ID"}],
    "transcripts": {"reference_audio": "与该参考录音准确对应的文本。"}
  },
  "parameters": {"steps": 32, "maxAudioSeconds": 30, "threads": 2},
  "allowUnmeasured": true
}
```

OmniVoice 使用同一 `speech.synthesize`，在参数中选择 `voiceMode`（auto / clone / design）、`language`、`voiceInstruction` 和 `durationSeconds`。目标时长受 `maxAudioSeconds` 联动归位；这两条新语音路线本版没有声明增量音频流输出。

## 5. 实现、重建和测试

| 编号 | 本轮生产实现 | 程序验证范围 |
| --- | --- | --- |
| P25a | `AudioCppSpec / MeshSpec / ExpansionEngine` | 所有新增包的角色 / 格式 / 后端、独立默认值、硬约束、缺失组件、参考输入 |
| P25b | 新增 ARM64 CPU worker 和 Melo 前端 | 实际 NDK 编译；F5 前端的最长词组、声调、严格 UTF-8 与 OOV 错误使用微型合成字典检查 |
| P25c | 生产进程与私有组件布局 | Java `ExpansionEngine.generate` 启动真实主机子进程夹具；覆盖 F5、Omni GGUF / 原版、TRELLIS、Pixal，检查硬链接、codec 子目录与退出清理 |
| P25d | `GlbFile / ArtifactStore / glb-preview.js` | 合成 GLB 发布与重启读取、损坏 / 越界 / 外部 URI 拒绝、有限读取和几何预览；不是训练模型输出 |
| P25e | 完整页面与媒体 | 实际生产页面＋显式模拟桥，32 项新增交互检查、5 张截图、GIF / MP4；浏览器上下文结束关闭 |

固定源码见[源码锁](../third_party/expansion-source-lock.json)：audio.cpp `4f5afb6…`、trellis.cpp `11b8732…`、其 GGML `f8697b3…`。构建只取程序源码，不取模型数据；audio.cpp 只编译 F5 / OmniVoice 与 CPU 核心，不编译 CLI / HTTP server / 下载器。GGUF 模型采用随程序编译的家族规则，不接受模型自带任意资源路径覆盖程序布局。许可全文由收集器输出到独立新增引擎说明中。

在 Windows 原生 JDK / MSVC / Android NDK 环境下，接续[完整构建](BUILD.md)：

```powershell
python tools/fetch_expansion_sources.py --fetch
python tools/build_expansion.py speech_extra
python tools/build_expansion.py mesh
python tools/build_tts.py
python tools/collect_expansion_notices.py
python tools/test_expansion.py
python tools/build.py
python tools/verify_package.py
python tools/test_android_lint.py
node tests/ui-smoke.cjs
node tools/capture_workbench.cjs expansion
```

具体获取选项以脚本 `--help` 为准。构建使用临时且由任务持有的 ASCII 路径别名，结束移除；不使用 Docker / WSL / VM / Android 模拟器。完整发版还需运行[当前程序证据](../verification/program/status.json)要求的原有回归，不能只跑新增测试。

## 6. 页面、录屏与剩余范围

以下均为 **UI FIXTURE / 桌面页面 / 无模型推理**。立方体是合成测试几何，未声称由 TRELLIS / Pixal 生成。

| 语音选择 | 单图 3D 选择 | 生成表单 |
| --- | --- | --- |
| ![语音模型](media/development/expansion/01-speech-models.png) | ![3D 模型](media/development/expansion/02-3d-models.png) | ![3D 表单](media/development/expansion/03-3d-form.png) |

| 队列 | 合成 GLB 预览 |
| --- | --- |
| ![队列](media/development/expansion/04-3d-queue.png) | ![合成立方体](media/development/expansion/05-glb-preview.png) |

![新增功能程序演示](media/development/expansion/expansion-ui.gif)

[MP4](media/development/expansion/expansion-ui.mp4) · [媒体身份与 32 项检查](media/development/expansion/manifest.json)

| 编号 | 未完成事项 | 当前状态 |
| --- | --- | --- |
| R01 | 四类语音的完整权重音质、发音与官方数值对照 | 按本轮程序验证要求未执行；F5 中文前端差异已明确 |
| R02 | TRELLIS / Pixal 完整模型、RAM / 速度 / PBR 效果 | 未执行；无 Z20 或其他 Android 实机验收 |
| R03 | 多视图、其他 3D 架构、部件模型与独立贴图 / 精修管线 | 当前未集成，逐项见 D03–D12 / D15–D16，不作为已可运行模型包展示 |
| R04 | 真机锁屏、后台耐久与系统杀进程行为 | 未测试；本轮没有引入远程替代方案 |

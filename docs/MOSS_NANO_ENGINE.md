# MOSS-TTS-Nano 本地语音基座

[English](MOSS_NANO_ENGINE.en.md) · [完整范围](MULTIMODAL_RELEASE_PLAN.md) · [开发状态](DEVELOPMENT.md) · [HF 组件选择](HF_RECIPES.md)

内部检查点 **0.3.0-dev.6 / code 10** 接入实际编译的 `moss_nano_ort` ARM64 CPU worker，覆盖编号 09 的原生实现工作。**尚无 LMA 的实际 MOSS 语音输出或 Android 真机证据，编号 09 和完整 v0.3.0 均未通过验收。** 本实现不代替编号 12 的其他九种 MOSS 架构。

## 用户使用

1. 在模型 → 全部 / 搜索中查看配套 Nano ONNX 仓库，打开文件列表 → 选择组件配方 → `MOSS-TTS-Nano · ONNX + codec`。
2. 用户分别选择下表的八个必需组件，以及 ONNX 图实际引用的全部外置 `.data`。可从不同 HF 仓库绑定组件，每个选择保留固定提交、大小和 SHA256 / Git blob 校验身份。
3. 点击加入本地只登记模型。检查下载计划中的全部所选文件、总大小、复用量和许可，再单独点击下载。也可导入具有相同完整清单和校验数据的本地文件夹。
4. 安装完整组件后，在“本地”编辑此模型的参数，点击使用，填写新的朗读文本并提交语音任务。计算、分词和解码全部在同一手机，不依赖 ROOT、Termux、Python 或外部推理。
5. 成功输出由结果库保存为 PCM16 单声道 WAV，记录有效参数、组件校验回执、帧数、采样率及结束原因。任务取消后等待子进程退出，再移除临时执行链接；模型文件仍保留。

App 安装 / 更新不下载模型。此配方没有固定模型权重或内嵌音色；缺失依赖直接在本机报错，不会补下载、换模型或转出手机。官方来源仓库可参考 [TTS ONNX](https://huggingface.co/OpenMOSS-Team/MOSS-TTS-Nano-100M-ONNX) 与 [codec ONNX](https://huggingface.co/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX)。它们来自锁定的官方源码说明；本次未取得这些仓库的完整固定组件清单，因此没有新增冒充已核对的目录候选。

## 完整资产角色

| 角色 | 格式 | 内容 |
| --- | --- | --- |
| `manifest` | JSON | `browser_poc_manifest.json`，包含 token 配置、提示模板和用户下载的内置音色提示 codes |
| `tts_meta` | JSON | `tts_browser_onnx_meta.json`，TTS 图名称、维度和 I/O 接口 |
| `codec_meta` | JSON | `codec_browser_onnx_meta.json`，decode_full 图与采样率配置 |
| `text_tokenizer` | SentencePiece `.model` | 与 TTS 导出匹配的 `tokenizer.model` |
| `tts_prefill` | ONNX | prefill 图 |
| `tts_decode` | ONNX | decode_step 图 |
| `tts_local` | ONNX | local_fixed_sampled_frame 图 |
| `codec_decode` | ONNX | 音频 tokenizer 的 decode_full 图 |
| `tts_data_1`…`tts_data_4` | ONNX `.data` | HF 表单中用户明确选择的 TTS 外置权重 |
| `codec_data_1`…`codec_data_4` | ONNX `.data` | HF 表单中用户明确选择的 codec 外置权重 |

数据角色在通用模板中是可选项，因为是否外置以及文件数由具体图决定；**被图引用的文件在执行时必须全部存在**。手动导入清单可使用两组 `*_data_1`…`*_data_99`，总数最多 32；不代表自动发现文件或下载权限。图名称必须匹配 metadata，外置数据使用该图目录中的原始平面文件名；路径穿越、绝对路径、未选择的数据和 `EPContext` 外部执行上下文会被拒绝。

模型专用 manifest、提示 codes、词表、图和外置数据都属于用户资产，不进入 APK。不得把官方 Android 示例里预分词的固定句子或音色 codes 写进应用作为通用推理替代。

## 参数与生成路径

| 参数 | 应用保护范围 | 行为 |
| --- | --- | --- |
| `threads` | 1–16，默认 2 | ORT CPU 线程；不是设备最优值测量 |
| `speaker` | 0–127 的候选范围 | 提交时读取用户 manifest，自动归位到实际音色数减一 |
| `maxFrames` | 1–1500，默认 375 | 音频 token 帧上限；结合应用的 4096 行上下文保护进一步限制 |
| `maxInputTokens` | 1–2048，默认 1024 | 任意新文本经过实际 SentencePiece 分词后的预算；超出报错，不静默丢掉尾部 |
| `seed` | 0–2147483647，默认 1234 | 固定采样图的随机数输入；不承诺跨设备逐字节相同 |

这些是应用保护值，**不是经验证的模型最高上限**。朗读输入限制为 1–4000 字符，当前单次 codec 输出保护为 60 秒；超出会失败，不把截断音频记作成功。参数沿用模型 / 配方独立保存、可编辑预设和提交回填。固定采样图内的 temperature / top-k 等常量没有伪装成可编辑参数。本次提供用户已下载的音色提示 TTS，不提供参考音频克隆、流式音频接口或 WeText 额外规范化；数字读法和长文本仍需实际质量验收。

原生执行为 SentencePiece 编码 → 组合用户音色提示 → prefill → 自回归 decode / local sampled frame → codec decode_full → WAV。prefill 会话先释放，TTS 会话与 KV 缓存在加载 codec 前释放，以减少同时驻留的数据；具体峰值内存和 Z20 适配仍未测量。

`EngineWorkspace` 将持有租约的已校验内容对象硬链接到私有 `engine-work/work-UUID/tts` 与 `codec`，保留 ONNX 外置数据所需文件名。不会为改名再复制大模型。硬链接不可用则本机报错；正常、失败和取消路径清理链接，App 启动对账清理上次进程遗留目录。ONNX protobuf 检查覆盖 initializer、属性张量、子图、稀疏张量、函数和训练图；ORT 继续检查图本身。

## 构建、许可与证据

先按[构建指南](BUILD.md)准备原生 Windows NDK / 扩散源码以及共享 ORT，再运行：

```powershell
python tools/fetch_moss_nano.py --transport ssh
python tools/build_moss_nano.py
python tools/collect_moss_nano_notices.py
python tools/test_moss_nano.py
python tools/build.py
python tools/verify_package.py
```

代码锁见 [moss-nano-source-lock.json](../third_party/moss-nano-source-lock.json)：MOSS `8b7bcc9341b3b4ef3a3a58ba1338a7d85ff133eb`、SentencePiece 0.2.1 `31646a467d2051eb904e0b45de3a73e91fe1c1e3`、ORT 1.28.2 头文件 `33ca9628233dc8f002435e868d4c2e9f82766ca1`。MOSS / SentencePiece 为 Apache-2.0，ORT 为 MIT，静态依赖原文随 APK 打包；实际模型数据许可仍须分别核对。

编译 worker 为 902,776 字节，SHA256 `3cde4a274f286227a762b0dc6065c72e59fed7c1365a553e635fcaeedac785be`，API 28、16 KiB 对齐。复用 sherpa 引擎的同一份 ORT；打包器仅允许大小 / 哈希 / API 条件完全相同的依赖共用文件名，冲突拒绝构建。原生诊断不会直接输出用户文本；Android liblog 拦截效果仍待真机检查。

新增 190 项主机检查：136 项 Java 契约 / 真实硬链接 / 子进程生命周期、47 项实际执行的 C++ 外置数据解析检查、7 项共享依赖检查。夹具输出是明确标注的任意字节，**不是 WAV、MOSS 语音或真机推理证据**。完整新文本语音质量、三次加载卸载、资源预算、后台、升级和全部 v0.3.0 发布门槛仍须通过。

![Nano 组件选择，界面夹具](media/development/15-moss-nano-recipe.png)

上图及[录屏 / GIF](MEDIA.md)均为可见标识的界面夹具，不包含模型下载或生成结果。

# MOSS 原生语音、对话、声音设计与音效基座

[English](OPENMOSS_ENGINE.en.md) · [完整版本范围](MULTIMODAL_RELEASE_PLAN.md) · [开发证据](DEVELOPMENT.md)

内部检查点 **0.3.0-dev.19 / code 23** 扩展 `openmoss_native` ARM64 CPU worker 和生产 Java 适配器，现有七个平级配方。它实际链接原生图、分词、采样和 codec 代码，不调用 Python、Termux、外部服务或上游 HTTP server。**尚未运行完整模型或物理 Android 推理，不能宣称这些模型已通过手机验收。** 完整 v0.3.0 的冻结目标与门槛没有缩减，也没有创建新 Release。

## 新增四种 delay 布局

| 编号 / 配方 | 检查的布局 | 功能与输入 |
| --- | --- | --- |
| D18-01 `moss_tts_openmoss_cpu_v1` | MOSS-TTS：32 路、Qwen3-8B / 4096 hidden | 生音频 / TTS；文字、声音描述、语言；可选一个参考 |
| D18-02 `moss_tts_v15_openmoss_cpu_v1` | MOSS-TTS-v1.5：32 路、Qwen3-8B / 4096 hidden | 生音频 / TTS；同类输入；独立登记与配置 |
| D18-03 `moss_ttsd_openmoss_cpu_v1` | MOSS-TTSD-v1.0：16 路、Qwen3-8B / 4096 hidden | 生音频 / 多说话人；文本包含 `[S1]`、`[S2]`，参考成对选择或全部留空 |
| D18-04 `moss_voicegen_openmoss_cpu_v1` | MOSS-VoiceGenerator：16 路、Qwen3-1.7B / 2048 hidden | 生音频 / 声音设计；必填声音描述，不提供参考入口 |

四者均为 v1 codec、24 kHz 单声道 PCM16 WAV 输出。原生代码检查 GGUF 架构、codebook 数、主干层数 / 注意力头 / hidden、1025 行音频头与嵌入、codec 及 BPE 依赖。TTS v1.0 / v1.5 几何相同，**几何校验不能认证权重来源**；仍需核对用户选择的仓库、固定 revision、组件 hash 和同次转换关系。first-class Delay、Nano 与这里的 openmoss 转换格式不兼容。

官方 config、processor、modeling、README 的固定 revision、哈希与来源见[发布者核对记录](../catalogue/evidence/openmoss-delay-publishers.json)。只读取元数据 / 源码，没有下载权重或执行远程 Python。社区原生代码仍固定在下文列出的提交；v1.5 模板和几何兼容是源码评估，音质与完整权重执行继续待验收。

使用步骤：在“全部 / 搜索”选择匹配转换文件，明确选择配方和主干 / extras 两个物理文件，确认清单后才下载；也可导入自备完整包。安装、升级、登记和浏览不自动下载。下载完成后从“本地”进入该模型的设置或任务，修改参数，选择导入的参考素材，再提交任务。它们与其他模型同列，不按引擎分成不同产品。

各 delay 模型保留原有 9 个采样参数，另有 `voiceInstruction`（≤1000 字符）和 `language`（≤64 字符）；留空按官方模板使用 `None`，VoiceGenerator 的声音描述必须填写。输入上限默认 1024、最高 2048 个**实际格式化位置**；生成步数默认 375、最高 1500，包含 delay flush，不能当作精确时长。数值超限归位，描述超长或包含模板标记则报错。默认值按模型保存，本次任务覆盖不修改其他模型或已保存默认。未提供会被忽略的 TTSD 时长提示。

参考 WAV 不自动重采样：24 kHz 单声道、PCM16 或有限且归一化的 float32、1–10 秒、每个 ≤1 MiB。TTSD 按角色 ID 固定 `[S1]` / `[S2]`，数组顺序改变也不交换声音；只选一个、重复或不支持的角色会在启动子进程前报错。每个参考单独编码；TTSD 的续接前缀使用按声道拼接的 codes，解码后在采样级裁掉前缀，不把参考声音计入输出文件。该社区实现与“拼接 WAV 后重新编码”可能有边界差异，实际声音一致性仍待验收。

上下文保护在**实际生成路径**构造完整参考 / 前缀网格之后、prefill 之前执行。构建工具给固定源码的生成副本插入唯一预算检查，源码 checkout 保持干净；回执记录生成副本 SHA256，第三方来源记录声明修改。超过用户输入预算或 `prompt + steps + 8 > 4096` 直接失败，避免上游仅告警后截短。回执保存实际格式化位置、参考 / 前缀帧数、采样、codec、RTF 等真实运行数据；没有运行时不会生成测量结论。

全部组件同时驻留 CPU 内存，大主干和 codec 可能超出 Z20 的能力；此处无 Z20 成功或速度保证。新配方沿用共用任务队列、取消、进程生命期、租约与私有硬链接工作区。所有推理都在同一手机；没有远程回退。

## 1. 两条独立管线

| 配方 | 输入与本机管线 | 输出 | 任务接口 |
| --- | --- | --- | --- |
| `moss_local_v15_cpu_v1` | 文字 → 内嵌 BPE → Qwen3-4B 主干 → 每帧 12 路 Local Transformer → v2 codec；可选参考 WAV 先经原生编码器 | 48 kHz 双声道 PCM16 WAV | `speech.synthesize` |
| `moss_soundeffect_v2_cpu_v1` | 提示词 / 可选负面提示词 → Qwen3-1.7B 编码 → 30 层 DiT / flow matching → DAC VAE 解码与裁剪 | 48 kHz 单声道 PCM16 WAV | `audio.generate` |

这两条路线分别针对 **Local-Transformer-v1.5** 和 **SoundEffect-v2.0** 的转换布局；不支持用旧 Local、SoundEffect-v1、Realtime、普通文本 GGUF、Nano 或 first-class Delay 文件替代。没有参考转写续说、多说话人选择或训练界面，不能据此勾选完整 MOSS 九子目标验收。原 [Delay](MOSS_DELAY_ENGINE.md) 与 [Nano](MOSS_NANO_ENGINE.md) 路线保留。

## 2. 用户选择资产，App 更新运行代码

每个模型必须由用户明确选择同次转换、相互匹配的 **两个 GGUF**：

| 物理组件角色 | 内容 | APK 中是否携带 |
| --- | --- | --- |
| `backbone` | 匹配的 Qwen3 主干与内嵌 BPE | 否 |
| `extras`：Local | 音频 embedding、Local Transformer、v2 codec 编码器 / 解码器 | 否 |
| `extras`：SoundEffect | DiT 与 DAC VAE 解码器 | 否 |

内含依赖用 `provides` 展示和打标签，不要求用户再次下载相同词表或 codec。Local 的该转换格式把参考编码器包含在 extras 中，不能把它作为独立可选下载；参考 WAV 本身仍是可选的用户输入。

用户操作：在“全部 / 搜索”打开 HF 文件，选择对应配方并绑定两个组件；查看固定来源、版本、许可、大小与复用计划，登记后再点击下载。也可导入匹配的模型包文件夹。两组件完整校验后在“本地”管理和运行；仅登记、浏览、安装 App 或更新 App 都不下载 / 替换权重。任务缺资产时在本机失败，不自动补下载。此次没有新增未经文件头与固定身份核对的候选权重包。

文件可使用发布方的名称；工作区通过租约硬链接为 `models/model.gguf` 和 `models/model.extras.gguf`，满足原生旁挂文件约定，不重命名用户原文件。取消 / 成功 / 失败后等待实际子进程退出再释放工作区。宿主消失时子进程接收 `SIGKILL`，任务不虚构可续算 checkpoint。

## 3. 平级模型与独立参数

两条记录与其他模型同级，均标“生音频”，并分别带 `text_to_speech` / `text_to_audio`、引擎、架构、管线、CPU、GGUF、组件及未实测证据标签。推荐 `m08 → m06 → m01` 的内容、顺序和标签保持原样。“无审查”仍是独立内容标签，不能由引擎名称、导入或音频功能推定。

在“本地 → 模型设置”保存该模型默认值；任务表单只覆盖本次不可变快照，不修改其他模型或已保存默认值。输入框允许编辑和预设选择，超限归位；Java 和 native 各自检查。

| 参数 | 默认 | 可编辑范围 | 适用 |
| --- | --- | --- | --- |
| CPU 线程 | 4 | 1–32 | 两条；应用到主干与辅助 CPU 图 |
| seed | -1 | -1 或 0–2147483647 | 两条；-1 在启动时生成实际种子并写入回执 |
| 格式化输入上限 | 512 | 1–2048 | Local；含提示包装和参考帧 |
| 生成帧数上限 | 250 | 1–750 | Local；每帧 80 ms，最多 60 秒 |
| 继续 / 停止头温度 | 1 | 0–3 | Local；不暴露无效的文本 Top P / Top K |
| 音频温度 | 1.7 | 0–3 | Local |
| 音频 Top P / Top K | 0.8 / 25 | 0.01–1 / 1–1024 | Local |
| 音频重复惩罚 | 1 | 1–2 | Local |
| 输出秒数 | 5 | 1–30 | SoundEffect |
| 去噪步数 | 50 | 1–100 | SoundEffect |
| CFG / sigma shift | 4 / 5 | 各 1–10 | SoundEffect |

Local 的格式化输入 + 生成步数 + 8 必须容纳于实际模型训练窗口及 App 的 4096 上限；超过已选输入预算时拒绝任务，不静默截断文字。SoundEffect 两段格式化提示各最多 512 BPE tokens；超限拒绝，不沿用上游静默截断。负面提示词只在 SoundEffect 表单提供；CFG=1 时若仍填写负面提示词，会明确要求提高 CFG 或清空该输入，不静默忽略。

Local 的参考音频必须为 **48 kHz 双声道、PCM16 或有限归一化 float32、1–10 秒、≤4 MiB** 的完整 RIFF WAV。没有自动重采样；不合格式请用户先导入正确素材。原生编码采用上游响度归一化，参考 codes 只在该任务进程内使用。SoundEffect 不接受参考输入。

## 4. 资源、执行与接口

CPU 是本次唯一后端。主干和 extras 同时驻留，包含完整 codec；尚未实现分阶段卸载。**SoundEffect 始终对完整 30 秒 latent 去噪后裁剪，缩短输出不同比缩小 DiT 内存或采样工作。** 生成速度、峰值内存和质量没有 LMA 实测数据；不承诺 Z20 可用或实时输出。

加载前检查 GGUF 架构、BPE、维度、codec 版本、采样率 / 声道及必需 tensor。它们是布局边界检查，不能认证任意自定义权重的来源、正确性或质量。Local-v1.5 与 SoundEffect-v2 使用不同编码宽度、codec 及参数，不能互换。

通过已有鉴权 `POST /v1/jobs` 提交对应任务，使用同一 FIFO、进程槽、取消、输入素材租约和产物读取。没有新增 `/v1/audio/speech` 或远程推理接口。SoundEffect 进度来自实际 solver 步数，Local 提供阶段状态而不编造百分比。回执记录实际种子、模型加载 / 编码 / 采样 / 解码耗时、音频时长、RTF 和停止范围；上游桌面性能值未作为手机结果。

## 5. 固定来源与构建

原生实现来自 [pwilkin/openmoss 固定提交](https://github.com/pwilkin/openmoss/tree/bfb1f465e0a86fb5a52bbf93e67ceba4b7d0b4e1)，Apache-2.0；其 llama.cpp 固定为 `050ee92d04c2e1f639025786dea701c70e7d4204`，MIT。源码校验见 [source lock](../third_party/openmoss-source-lock.json)，许可见 [notices](../third_party/notices/openmoss-sources.json)。这是社区实现，不冒充 OpenMOSS 官方 Android 验证。

模型 / codec 的使用和再分发许可独立核对，不能继承引擎代码许可。转换由上游离线工具完成，不在 Android 自动运行转换或下载脚本；APK 不链接上游 CLI、HTTP server 或 WAV 文件处理实现。

```powershell
python tools/fetch_openmoss.py
python tools/build_openmoss.py
python tools/collect_openmoss_notices.py
python tools/build_recipe_templates.py
python tools/test_openmoss.py
python tools/build.py
```

使用本项目原生 Windows NDK r30 / API 28 / `armv8-a` / 静态 C++，不调用虚拟环境。GPU、动态后端、OpenMP 与 CURL 关闭；构建检查 16 KiB 对齐及网络、shell / exec、logcat 导入缺失。运行仍受 Android 前台服务、内存和厂商后台策略约束，不能仅以编译通过宣称锁屏耐久合格。

## 6. 本轮证据与未完成项

514 项限定检查：生产 Java 402 项（21 次实际主机子进程）、C++ 112 项（实际执行固定上游语音提示模板、音效格式化 / 噪声 / sigma 函数及预算、WAV 边界）。检查包含双参考映射、描述透传、错误回传和资产清理；WAV 为结构夹具，不执行 tensor、神经网络或 Android。详细记录见 [verification](../verification/development/openmoss.json)。其余回归及当前 APK 哈希见[双语版本说明](releases/v0.3.0-dev.19.md)。

截图、录屏和 GIF 都有 **UI FIXTURE** 标识，展示生产页面配合模拟安装状态，不展示实际模型输出：

![Local-v1.5 参数与参考音频](media/development/43-moss-local-parameters.png)

![SoundEffect-v2 参数](media/development/45-moss-sound-parameters.png)

[Local 组件](media/development/42-moss-local-components.png) · [音效组件](media/development/44-moss-sound-components.png) · [录屏](media/development/foundation-ui.mp4) · [GIF](media/development/foundation-ui.gif)

[可选双声道参考表单](media/development/46-moss-local-reference.png) · [音效提示词表单](media/development/47-moss-sound-prompt.png)

| 编号 | 本轮实现 | 验证边界 |
| --- | --- | --- |
| D18-05 | 现有 worker 增加四个 delay 配方 | 编译 / 打包与主机协议；未执行完整模型 |
| D18-06 | 双参考映射、声音描述与独立模型参数 | 生产 Java、实际主机子进程及界面夹具 |
| D18-07 | 真实生成网格的输入 / 上下文保护 | 固定源码生成副本、原生边界检查 |

| 编号 | 仍待完成，继续属于同一完整 v0.3.0 |
| --- | --- |
| P18-01 | 六条配方固定验收权重、实际新输入的断网输出、质量与资源档案 |
| P18-02 | 旧 Local、旧 SoundEffect、Realtime、SoulX、Stable Audio、旧 LTX 及全部其他必需适配 / 验收 |
| P18-03 | 全部管线的物理 Android 加载 / 卸载、跨模态、后台、锁屏、长期 API、升级与 A11 |
| P18-04 | 完整 F-01–F-12、01–14 / 16 / 17、所有冻结子目标通过统一门槛后，交付完整 v0.3.0 Release |

[TTSD 双参考界面](media/development/51-moss-ttsd-speakers.png) · [VoiceGenerator 声音描述](media/development/52-moss-voicegen-instruction.png) · [TTS 组件](media/development/48-moss_tts-components.png) · [v1.5 组件](media/development/50-moss_tts_v15-components.png) · [TTS 参数](media/development/49-moss-tts-parameters.png)


## 7. dev.19：旧 SoundEffect 的环境声音字段

新增平级配方 `moss_soundeffect_openmoss_cpu_v1`，架构 `moss_soundeffect`，16 路 delay / Qwen3-8B，输出 24 kHz 单声道。官方示例使用 `build_user_message(ambient_sound=text)`；LMA 将提示词放入 `Ambient Sound`，`Text` 为 `None`，与 v2 的 DiT / 48 kHz 路线分别处理。只需用户自选同次转换的主干 / extras；不接受参考音频、负面提示词、声音描述或语言字段，不混用同为 16 路的 TTSD / VoiceGenerator。实际模板函数的检查覆盖环境字段与 Text None。

默认格式化输入预算 1024（1–2048）、生成步数 375（1–1500，含 delay 收尾，不承诺精确时长）、文本继续 / 停止头温度 1（0–3）；音频温度 1.5（0–3）、Top P .6（.01–1）、Top K 50（1–1024）、重复惩罚 1.2（1–2）。线程和种子范围沿用上述语音配方。每模型参数 / 本次快照、预算保护、私有子进程和产物流程相同。任务表单按能力元数据隐藏没有实现的负面条件入口，仍保留 v2 的负面提示词。

旧 SoundEffect、旧 Local 和 Realtime 的固定发布者核对见[记录](../catalogue/evidence/moss-rq-publishers.json)。后两种架构由独立 [RQ 引擎](MOSS_RQ_ENGINE.md) 处理；不能用 delay 几何推断其支持。所有九个 MOSS 子目标已有各自代码路线，仍各自缺少完整权重 / 手机 / 质量与耐久验收，不标记“全家族已可用”。

<img src="media/development/53-moss_soundeffect_openmoss_cpu_v1.png" width="260" alt="旧 SoundEffect 环境音效表单，UI FIXTURE，非模型输出" />

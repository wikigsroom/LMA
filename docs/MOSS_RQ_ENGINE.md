# 旧 MOSS Local / Realtime 原生基座

[English](MOSS_RQ_ENGINE.en.md) · [SoundEffect 与其他 MOSS 路线](OPENMOSS_ENGINE.md) · [完整版本范围](MULTIMODAL_RELEASE_PLAN.md) · [本轮双语说明](releases/v0.3.0-dev.19.md)

内部检查点 **0.3.0-dev.19 / code 23** 增加 `moss_rq_native` ARM64 CPU 引擎。它实际链接分词、全局 / 深度 Transformer、采样、音频编码与解码源码，由生产 Java 适配器调用。**没有完整权重推理或 Android 真机证据**；配方可选择及原生编译成功不能当作手机可用验收。所有冻结目标仍在同一完整 v0.3.0，无新 Release。

## 1. 两种独立布局

| 编号 | 平级配方 / 模型 | 原生模型格式与结构 | 输出 / 接口 |
| --- | --- | --- | --- |
| D19-01 | `moss_local_v10_rq_cpu_v1` / 旧 MOSS-TTS-Local-Transformer | `moss-tts-local`；Qwen3-1.7B 全局、4 层 Qwen3 深度、输入及 33 组逐通道输出 MLP，32 路音频编码 | 24 kHz 单声道 PCM16 WAV；单次文本，可选声音描述 / 语言 |
| D19-02 | `moss_realtime_rq_cpu_v1` / MOSS-TTS-Realtime | `moss-tts-rt`；Qwen3-1.7B 全局、4 层 RoPE 深度，16 路音频编码、15 组深度输入嵌入 | 24 kHz 单声道 PCM16 WAV；单次文本，逐步注入余下文本 |

旧 Local 官方 config 的 `MossTTSDelayModel` 名称不能替代实际模型源码核对。它与 Local-v1.5 的单层 GPT-J / 12 路 / 48 kHz 双声道结构不同，也不复用 Delay 的一键开关。

Realtime 是模型名称；当前接口仍一次接收完整文本。dev.29 可在本模型设置中开启[逐帧音频与边生成边听](AUDIO_STREAMING.md)，输出 PCM 并保留采样一致的完整 WAV；默认整段模式保留原响度处理。没有增量文本会话、WebSocket 输出或低延迟承诺；不暴露原生离线路径不消费的声音描述、语言或文本采样字段。实际速度与 RTF 需要手机测量。

官方模型、processor、codec 和 tokenizer config 的固定 revision / 哈希见[发布者核对记录](../catalogue/evidence/moss-rq-publishers.json)。核对只读取 JSON / Markdown / Python 文本；没有下载权重或执行发布者 Python。

## 2. 用户自主选择的三个组件

| 角色 | 必需文件 | 校验要点 |
| --- | --- | --- |
| `model` | 对应 `moss-tts-local` / `moss-tts-rt` GGUF | 全局词表容量 155648 / 151936，层数、注意力头、深度结构、音频头 / 嵌入形状 |
| `codec` | `moss-audio-tokenizer` GGUF | v1：24 kHz、hop 1920、32 量化器、1024 codebook、dim 8、RVQ dim 512 |
| `tokenizer` | 匹配模型的 `moss-tokenizer` / `qwen2-bbpe` GGUF | 非空 BPE 数组、词表不越过模型容量、所需特殊 ID 与内容一致；旧 Local 与 Realtime 不能互换 |

词表无需填满模型嵌入容量；转换脚本保留到实际最大 token ID，发布者增加 token 至 151668。不能以“数组长度必须等于模型词表容量”误拒绝合法文件。几何和特殊 token 检查也**不能认证权重身份或音质**，仍需用户核对来源、固定 revision、转换关系与 hash。

这三个组件由用户显式选择或导入，界面显示完整依赖；App 不内置权重、BPE、codec 或音色数据，不自动下载、转换或更新模型。moss-tts.cpp、openmoss、Nano、first-class GGUF 布局彼此不能混用。LoRA 不用于这些语音配方。

## 3. 操作与参数

1. 在模型中选择对应配方，明确选择三个匹配 GGUF；核对尺寸、来源和依赖，再自行下载或导入。尚无完整模型验收包，不把任意同名 GGUF 标为兼容。
2. 安装完成后，从“本地”打开模型设置；设置只保存在该模型中，选择预设或自行编辑。数值超过声明边界时自动归位；无效字符串、未知字段和模板标记报错。
3. 打开生成任务，输入普通朗读文本，可选导入一份 **24 kHz 单声道、1–10 秒、≤1 MiB、PCM16 或有限 float32 WAV**。不自动重采样 / 混音；不接受负面提示词、重复或未知参考角色。
4. 本次参数为独立快照；选用未实测配方后进入既有 FIFO，在同一手机的原生 CPU 子进程运行。可查看阶段、取消、任务回执与本地产物。

| 参数组 | 旧 Local | Realtime |
| --- | --- | --- |
| CPU / 种子 | `threads` 1–32，默认 4；`seed` -1 自动或 0–2147483647 | 相同 |
| 输入 / 生成步 | `maxInputTokens` 1–2048 / 默认 1024；`maxNewTokens` 1–750 / 默认 375 | 相同；格式化输入预算包含余下文本 |
| 音频采样 | 温度 1.7、Top P .8、Top K 25、重复惩罚 1.1 | 温度 .8、Top P .6、Top K 30、重复惩罚 1.1 |
| 采样范围 | 温度 0–3、Top P .01–1、Top K 1–1024、重复惩罚 1–2 | 相同 |
| 文本继续 / 停止头 | 温度 1.5 / 0–3、Top P 1 / .01–1、Top K 50 / 1–1024 | 不暴露 |
| 声音描述 / 语言 | 普通文本最多 1000 / 64 字符，空值为 `None` | 不暴露 |

生成步包含停止步，不保证精确秒数；最多约 60 秒的代码帧预算不是速度或质量承诺。实际模板、参考和余下文本组成后、prefill 前校验：输入不越过用户上限，prefill + 步数 + 8 不越过 4096；Realtime 步数不足以消费余下文本时明确拒绝。长文本不会静默绕过预算。

## 4. 执行、API 与资源

使用现有鉴权 `POST /v1/jobs` 的 `speech.synthesize`，以及任务 / 输入素材 / 产物接口；没有新增语音流或远程执行入口。模型、分词、参考编码、生成和 WAV 解码都在同一手机。缺失文件或失败只在本地报错，不转出推理。

三组件通过私有硬链接工作区和租约使用，原件不移动；关闭输入、终止子进程后才释放工作区。父进程死亡绑定 `SIGKILL`，stdout 只传 JSON，库诊断不进入 logcat。CPU 后端固定，GGML 线程数量实际设置，头部并行关闭以服从线程预算。APK 不链接上游 CLI / HTTP server / Python。

回执包含实际种子、CPU、格式化 prefill、余下文本 / 参考帧数、生成步数、音频帧数、加载 / prefill / 生成 / 全管线耗时、时长、RTF、停止原因及 `single_text_to_wav`。预处理开销和深度首步包含在所标记阶段中；这些是本机运行后产生的测量字段，开发检查没有伪造手机 RTF。

这条 CPU 路线同时驻留模型、codec 和 tokenizer。1.7B 主干不代表整包只有 1.7B，codec 与 KV / 图内存也需计入。尚未证明 Z20 6/8 GB 能加载或生成，不提供 GPU / 远程回退。

## 5. 固定源码与复查

社区实现 [mudler/moss-tts.cpp](https://github.com/mudler/moss-tts.cpp/tree/ee722b8e9205ee9b1b1c398a4e87e4e393e9be41)，GGML `e705c5fed490514458bdd2eaddc43bd098fcce9b`，见[source lock](../third_party/moss-rq-source-lock.json)。上游在 README 中声明 MIT / Ettore Di Giacinto；**该提交没有单独 LICENSE 文件**，因此原样保留实际 [README 许可声明](../third_party/notices/moss-rq-upstream-README.txt) 和 [GGML LICENSE](../third_party/notices/moss-rq-ggml-LICENSE.txt)，不虚构上游许可文件。模型资产许可独立核对。

原始 checkout 保持干净；LMA 只在生成的两份管线副本插入预算及阶段回调，生成文件 hash 进入构建回执。使用 Windows NDK r30、API 28、`armv8-a`、静态 C++、16 KiB ELF 对齐；检查不导入网络、shell / exec、logcat，不使用 Docker / WSL / VM / 模拟器。

```powershell
python tools/fetch_moss_rq.py
python tools/build_moss_rq.py
python tools/collect_moss_rq_notices.py
python tools/test_moss_rq.py
python tools/build.py
```

178 项限定检查：132 Java（10 次真实主机子进程）、30 C++ 策略、14 个实际 GGUF 元数据校验、2 个上游微型计算图测试。后两者执行 Local 深度块及 Realtime 两步深度生成，使用 3360 / 15616 字节的合成张量夹具，**不是模型 checkpoint 或完整语音推理**。结构 WAV 也不是神经生成结果。详见[开发验证](../verification/development/moss-rq.json)。

| 待完成编号 | 保留在完整 v0.3.0 的工作 |
| --- | --- |
| P19-01 | 两条完整权重与 codec 的新输入断网输出、质量、内存 / 温度 / RTF / 加载卸载记录 |
| P19-02 | MOSS 九子目标分别验收；三条本轮路线接入不代表九者手机支持完成 |
| P19-03 | F-01–F-12、01–14 / 16 / 17 的所有冻结子目标，以及 A1–A11 / R-01–R-05 |
| P19-04 | 15 分钟锁屏、1 小时交替 API、升级 / 零模型启动与资产保留；满足门槛后才能发布完整 Release |

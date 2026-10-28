# SoulX-Podcast 本地音频引擎

[English](SOULX_ENGINE.en.md) · [开发状态](DEVELOPMENT.md) · [本轮编号交付](releases/v0.3.0-dev.21.md) · [本地输入](LOCAL_INPUTS.md)

## 1. 当前交付边界

0.3.0-dev.21 将完整 SoulX 原生执行器接入 App，共用模型包、独立参数、素材、任务队列、鉴权 API 和结果库。`soulx_native / soulx_podcast_cpu_v1 / cpu` 是实际编译打包的内部引擎；APK 没有权重、词表、音色、示例音频或已训练声源常量。所有模型平级，输出标签为生音频，能力为文字转语音 / 多说话人 / 参考原文；GGUF、ONNX、CPU 与组件依赖标签独立于安装及验证状态。

**它仍不是完整 v0.3.0 或目标13的验收通过。** 已运行完整训练模型的生产 worker 主机测试；没有物理 Android、音质、可懂度、说话人相似度、Z20 内存 / 速度或后台耐久结论。合成参考 PCM 不提供有效的语音原文关系，测试中的“原文”只用于协议探测，不能冒充真实语音演示。

**公开下载候选仍待补齐。** 模板支持用户选择组件、显式下载 / 导入及独立管理，但目前没有已核对的、含全部转换组件的公开 HF 条目。原始 `flow.pt / hift.pt` 不能直接作为此配方的图；已有开发转换工具不是普通用户必装依赖，也不表示已完成“搜索后直接下载即可用”的目标13用户流程。当前可导入匹配的完整模型包；最终发版仍须补齐可复查的用户资产来源和下载验收。

## 2. 一份配方，14份用户资产

以下是执行文件名。HF 中的原文件可有不同路径，由引擎在已校验、持有租约的私有工作区建立固定文件名硬链接。不会为运行复制整份权重，也不接受模型包提供可执行程序。

| 角色 | 执行文件 | 格式 |
| --- | --- | --- |
| `language` | `language.gguf` | 完整 SoulX Qwen3 GGUF，含配套词表 |
| `s3` | `reference-s3.onnx` | S3v2 图 |
| `s3_data` | `reference-s3.onnx.data` | 配套外部权重 |
| `speaker` | `reference-speaker.onnx` | CAMPPlus 图 |
| `speaker_data` | `reference-speaker.onnx.data` | 配套外部权重 |
| `flow_encoder` | `flow-encoder.onnx` | Flow 编码图 |
| `flow_encoder_data` | `flow-encoder.onnx.data` | 配套外部权重 |
| `flow_estimator` | `flow-estimator.onnx` | Flow 估计图 |
| `flow_estimator_data` | `flow-estimator.onnx.data` | 配套外部权重 |
| `hift_f0` | `hift-f0.onnx` | 基频图 |
| `hift_f0_data` | `hift-f0.onnx.data` | 配套外部权重 |
| `hift_spectrum` | `hift-spectrum.onnx` | 频谱图 |
| `hift_spectrum_data` | `hift-spectrum.onnx.data` | 配套外部权重 |
| `hift_source` | `hift-source.f32` | 10个 float32 已训练声源合并参数，恰好40字节 |

那40字节也是模型权重，不能用通用占位常数替代或写进 APK。HF 将 `.f32` 识别为二进制数据组件。每份组件须有固定来源 / 大小 / 校验身份；同版 ONNX 图只能引用相邻同名 `.data`。参考 / 声学图上限128 MiB，外部权重由共享资产存储校验。任意 Qwen、任意 ONNX、原始 PyTorch checkpoint 都不会自动兼容此布局。

用户仍通过“全部 / 搜索 → 配方 → 逐份选择组件 → 查看完整计划 → 明确下载”，或导入完整清单 / 文件夹。在“本地”管理暂停 / 续传 / 删除 / 独立设置 / 更新。声明、浏览、缺组件报错和 App 升级均不启动下载，重启中的传输保持暂停；推荐 m08 → m06 → m01 保留。

## 3. 表单与素材

导入1–4段参考 WAV：24 kHz 单声道、PCM16 或 float32，1–15秒，≤1,536,000字节，采样值须有限且在[-1,1]。当前不在后台隐式重采样 / 混音，其他格式需先由用户转换。S1必选，S2–S4按连续编号选择，每段填写它**实际说出的原文**。只给参考音频或只给原文都拒绝；已导入素材及历史 WAV 结果均可按规则选用。

单段提示词默认S1；多段每行一个标记：

```text
[S1] 第一位说话人的第一段。
[S2] The second speaker answers locally.
[S1] 第一位说话人继续。
```

每个目标说话人必须有对应参考，最多64段，文字总长1–4000 UTF-16单位，参考原文每段最多4000。内部 SoulX 控制 token 不接受为普通原文。输入、素材身份与原文一起保存到不可变任务；之后编辑模型参数或表单不会改写已排队任务。刷新素材列表保留未提交的选择与原文，取消选择可选音频会停用对应文本框。

## 4. 参数及真实执行

| 参数 | 默认 / 范围 | 处理 |
| --- | --- | --- |
| context | 4096 / 256–8192 | 应用上下文保护；仍受实际 GGUF 约束 |
| maxNewTokens / minNewTokens | 512 / 8；最大3000 / 2999 | 输出≤context−64，最少采样次数<输出上限 |
| temperature / useRas | 0.6 / true | 温度0自动将本次有效RAS归位为false，并记录调整 |
| repetitionPenalty / topK / topP | 1.25 / 100 / 0.9 | 原生重复惩罚与概率截断；RAS可恢复原始分数，包括EOS |
| rasWindow / rasTau | 25 / 0.2 | 窗口1–256，比例0.0001–1 |
| maxHistoryTurns / historyTurns / textHistoryTurns | 10 / 2 / 2 | 5–64 / 1–8 / 0–16；完整历史≤maxHistoryTurns−4，为四个参考段预留 |
| historyThreshold | 4096 / 128–8192 | ≤context；必需参考、历史、目标及输出仍不够时明确失败 |
| steps / cfg | 15 / 0.7 | Flow Euler 1–100步，CFG 0–10 |
| seed / threads | −1 / 4 | −1固定为本次实际种子；CPU线程1–32 |
| pauseMs / maxOutputSeconds | 200 / 120 | 段间0–2000 ms；全任务1–960秒，含静音 |

数值输入支持预设与自行编辑，UI / Java联合归位，原生worker再次拒绝越界快照。最大值多为应用保护或固定导出约束，不代表所有设备承受得住。每段语义码为40 ms，总计最多24000码；实际输出时长再次校验。语言EOS / 达到输出上限 / 为后续历史补充的分隔符分别记录，不以Qwen通用EOS替代语音EOS。

一个受App拥有的原生子进程依次执行：参考特征与 S3 / CAMPPlus → 完整 Qwen3语义生成 → 释放语言模型 → 每段 Flow编码 / Euler估计 / HiFT F0 / 频谱与DSP → 24 kHz单声道PCM16 WAV。ORT图会话最多同时一个；参考特征与代码可保留，完整权重不同时常驻。llama使用现有相邻基线CPU后端，ORT使用现有CPU运行库，不加载用户插件、不连接其他推理设备。

写入完成前仅有私有临时WAV，成功才移动到任务输出。Java跟踪子进程、引用租约和工作区，取消 / 错误后先终止并回收进程再清理；Android源码提供SIGTERM到ORT终止 / llama解码中止，强杀由共享进程管理兜底。主机测试确实强制结束两个阶段的进程，但**没有验证Android协作取消或锁屏生命周期**。执行记录包含真实种子、每段码数 / EOS、图与模型加载释放次数、时长 / RTF；主机耗时不能当成Z20性能。

## 5. 同一鉴权任务接口

先使用[素材上传接口](LOCAL_INPUTS.md)或App导入拿到素材ID，再向已有 `POST /v1/jobs` 提交，沿用Bearer密钥和幂等键：

```json
{
  "bundleId": "YOUR_INSTALLED_SOULX_BUNDLE_ID",
  "type": "speech.synthesize",
  "input": {
    "prompt": "[S1] 第一位说话人。\n[S2] The second speaker.",
    "artifacts": [
      {"role": "reference_s1", "artifactId": "YOUR_FIRST_ARTIFACT_ID"},
      {"role": "reference_s2", "artifactId": "YOUR_SECOND_ARTIFACT_ID"}
    ],
    "transcripts": {
      "reference_s1": "第一段参考音频实际说出的原文。",
      "reference_s2": "The actual words spoken in the second reference."
    }
  },
  "parameters": {"maxNewTokens": 160, "steps": 15},
  "allowUnmeasured": true
}
```

返回202仅表示入队。查询任务 / 事件，完成后按产物ID预览 / Range读取 / 导出WAV；不能提交任意文件路径、URL、客户端校验回执或外部执行地址。未提供的参数取该模型保存配置，再固定本次有效值；任务覆盖不保存为模型默认。没有新增OpenAI语音端点兼容声明。

## 6. 复查与剩余门槛

已明确准备的开发权重与转换步骤沿用[参考 / 声学](SOULX_REFERENCE.md)和[语言](SOULX_LANGUAGE.md)。以下编译 / 检查本身不下载模型：

```powershell
python tools/build_soulx.py
python tools/build_soulx.py --android
python tools/collect_soulx_notices.py
python tools/test_soulx.py
python tools/test_soulx_worker_trained.py
python tools/build.py
python tools/verify_package.py
```

222项限定检查含146 Java / 76 C++与6个真实协议子进程；结构WAV不算推理。95项完整训练worker检查实际使用14份模型资产、4个生产worker子进程：两说话人新文字、四说话人明确截断，以及语言 / 声学阶段两次主机强制结束。完整训练输出保存在忽略目录，不进Git / APK / Release，也不作为音质演示。

ARM64 worker为472,400字节，SHA256 `424d609440603a4c93238d5130b316e384d0ead58613a53e5fdbe3608b4963bf`；API28、16KiB对齐，复用五份既有运行库。固定源码 / 模型身份见四份SoulX来源锁与训练资产锁；完整Apache、MIT、KISS FFT、Snake、ORT依赖许可随APK提供。

还须补齐目标13用户可用下载候选、真实语音参考 / 音质与说话人评价、实际Android资源 / 取消 / 连续加载释放 / 后台 / 升级证据。01–14 / 16 / 17、九个MOSS子目标、两种LoRA和旧LTX的全部冻结要求仍共用完整v0.3.0发版门槛。


共享原生库仅在名称、大小、SHA256 与 Android API 约束完全一致时复用，并拒绝 worker 冒用基础库文件名。`python tools/test_native_payload.py` 的 10 项回归通过，`verify_package.py` 核对最终 APK 的 27 个唯一原生文件。

# MOSS 参考输入：独立诊断

[English](MOSS_REFERENCE_DIAGNOSTICS.en.md) · [模型使用](MOSS_TTS15.md) · [完整待办](releases/v0.3.0-dev.42.md)

dev.42 检查已有真实失败，未修改生产原生引擎、权重或采样参数。参考模式正常结束和文本遵循仍阻塞验收。

## 官方格式对照

固定官方 `OpenMOSS-Team/MOSS-TTS-v1.5@cdd3b911b1585e3f2dbc7775ef10f9926f58850a` 的配置、处理器、模板和词表，共九份开发文件，按[清单](../research/openmoss_reference/official-sources.json)核对。直接编译生成的生产 pipeline 翻译单元，以真实 GGUF 词表和官方原方法体比较英文、中文、不同长度参考及混合语言的七个提示网格。

**0/7 完全一致**：原生每次多一行 assistant `audio_start`，其余网格内容一致。这只是词表 / 格式化检查，未执行主干或 codec，不能证明它就是生成失败的原因。[原始报告](../verification/research/openmoss-prompt-issue/first-run.json)、驱动和原始输出保留。

仅移除该行的实际 CPU 候选保持原参考文本、种子、采样参数、375 步上限和完整权重。1800 秒时限结束时到达 332/375 步，没有 WAV 或完整 execution 结果。候选**未进入生产**；超时不等于达到输出上限，也不表示自然结束已修复。[候选原报告](../verification/research/openmoss-prompt-candidate/results.json)、请求、日志、驱动和候选源码保留。

## 原始音频的独立 ASR

开发诊断显式取得固定 [OpenAI Whisper tiny.en](https://huggingface.co/openai/whisper-tiny.en/tree/87c7102498dcde7456f24cfd30239ca606ed9063)，随后离线在本机 CPU 识别完整原始 WAV，不提供目标文本或初始提示。权重 / 词表不进入 App 或 Git，App 不增加下载行为。[开发资产锁定](../research/speech_asr_reference/assets.json)记录精确 SHA 与修订。

| 原始案例 | 独立固定目标 | 识别结果 |
|---|---|---|
| Kokoro 控制 | Hello world. The sun is shining. | 完整词一致，0 错误 |
| MOSS 无参考英文 | Hello world. | 完整词一致，0 错误 |
| MOSS 原参考模式 | Hello world. | 重复参考内容及多余词，35 错误 / 2 个目标词 |

原参考 WAV 为 27.44 秒，SHA `6a6080b55f241563f95ff023c0c4c609127453d6a388f0ac5d94b28dd8e06808`。除未自然结束外，出现文本遵循失败信号。WER 可以超过 100%；35/2 为 17.5。识别可能出错，这不是主观音质、音色相似度、所有语言或 Android 通过记录。

[当前可复现报告](../verification/development/speech-intelligibility.json) · [首次独立识别](../verification/research/openmoss-reference-asr/original-transcriptions.json)。工具遇到不一致返回非零，保留两项通过、一项失败，不放宽阈值。

## 开发复现

```powershell
# 默认离线核对已有资产；显式 --download 才取得开发参考文件
python tools/fetch_openmoss_reference.py
python tools/fetch_speech_asr_reference.py
python tools/test_openmoss_prompt.py
python tools/test_speech_intelligibility.py
```

提示工具最终目录调整未重跑；首次失败的原驱动与源码快照作为历史证据，不冒充当前通过。ASR 使用 torch 2.14.0+cpu、transformers 5.17.0、SciPy，两条 CPU 线程、greedy / beam=1 / max_new_tokens=128。超过 30 秒的 WAV 拒绝而不截取。以上只用于开发，App 全部推理仍要求同一台 Android，无外部执行。

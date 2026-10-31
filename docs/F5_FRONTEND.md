# F5-TTS v1 中文前端

[English](F5_FRONTEND.en.md) · [贴图基座](LOCAL_MATERIALS.md) · [完整待办](REMAINING_ADAPTATION.md)

开发代码新增 `F5-TTS v1 · 官方兼容中文前端` 自选组件配方。已发布的 v0.3.5 APK 仍是原先的拼音字典实现；此页描述尚未合并为下一次完整 APK 交付的开发内容。

## 1. 用户选择与使用

1. 用户自行取得 F5 v1 Base、Vocos 和配套 `vocab.txt`；模型许可独立适用。旧模型和已保存的参数继续保留。
2. 明确准备下节的 `f5-frontend.json` 语言资产；它包含词频、HMM 概率、拼音数据，不包含语音神经网络权重。APK 不附带这些表，也不会在安装、浏览或升级时获取它们。
3. 在组件配方中选择“F5-TTS v1 · 官方兼容中文前端”，分别选择模型、声码器、词表和前端 JSON，保存为一个模型包。“本地”中管理该模型自己的文件和参数。
4. 使用时选择 24 kHz 单声道、1–12 秒 WAV，填写准确的参考转写，再输入要朗读的文本。步数、语速、CFG、种子、时长与帧预算跟随模型保存，输入超限由基座归位。
5. 预检后提交共用队列。手机 C++ 完成分词、拼音和模型执行，不调用 Python、Termux 或其他设备。输出完整 WAV；不声称此适配已支持逐块音频流。

旧的 `f5_v1_safetensors_cpu_expansion_v1` 配方继续允许原有拼音字典。只有明确选择新前端资产的包才执行兼容前端；不会静默改变既有用户模型的发音。

## 2. 精确程序边界

| 部分 | 实现 |
| --- | --- |
| 固定参考 | F5 源码 `45868abaabd74aabf03cd673d6dd00cc9d9c01ae` 的 `convert_char_to_pinyin` |
| 分词 | rjieba 0.2.2 / jieba-rs 0.11.0 的默认词频 DAG、HMM、新词及非汉字分段规则 |
| 拼音 | pypinyin 0.55.0、`Style.TONE3`、`tone_sandhi=True`；有限字典条目由固定库预计算，手机做最长词条匹配 |
| 格式 | 官方中英混排空格、标点转换、逐字符分支；未知词元 ID 为 0 |
| 稳定约束 | 严格 UTF-8；单输入最多 65,536 字节 / 12,000 字符 / 24,000 词元，语言资产最多 96 MiB |
| 错误 | 错版本、非有限概率、错字符对齐、损坏 JSON、非法 UTF-8 明确失败，不降级调用其他前端 |

比较的是固定默认字典和上述函数的程序语义。用户自定义 rjieba 词典、修改 pypinyin 全局表、其他版本与完整 F5 Python 音频管线均不由该对照证明。

## 3. 显式离线准备

使用原生 Python；不启动虚拟化环境。工具需要 pypinyin 0.55.0；对照检查另需 rjieba 0.2.2。源码归档、语言数据与许可身份固定在 `third_party/f5-frontend-source-lock.json`。

```powershell
# 只取固定源码、语言数据和许可，不取语音权重或运行安装脚本
python tools/fetch_f5_sources.py

# 用户明确执行；输出路径必须是新路径
python tools/export_f5_frontend.py `
  --jieba-dict build/frontend-reference/jieba-data/dict.txt `
  --hmm-model build/frontend-reference/jieba-macros/src/hmm.model `
  --output my-assets/f5-frontend.json
```

同时生成 `.receipt.json`，含真实字节数、SHA256、词条数和固定依赖版本。只把用户选定的语言资产复制到手机并导入，不需要将准备电脑接入任何手机推理流程。

## 4. 程序验证

`python tools/test_f5_frontend.py` 编译实际生产 C++ 前端，使用 2,222 组固定与随机混合文本，对照固定 F5 Python 函数、rjieba 与 pypinyin 的分词、词元和 ID，包括多音字、变调、标点、英文、罕见字、表情和预算 / 损坏资源分支。当前通过 **6,671 项**；完整训练模型下载 / 推理和真机检查为 0。

源代码和许可随工具提供，语言表由用户独立准备和选择。详细状态以对应检查的当前源码指纹为准；不将文本前端一致性表述为音质或手机性能验证。

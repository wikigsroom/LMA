# LMA 内置无审查模型

LMA 0.1.2 的内置目录只收录具有作者无审查依据的权重版本。2026-10-26 已核对全部 14 个作者模型卡和对应固定 GGUF 来源。构建会校验依据与实际下载权重的仓库、版本和 SHA256 一致。

| ID | 无审查模型 | 作者说明中的处理方式 | 固定作者说明 |
| --- | --- | --- | --- |
| m01 | Dolphin 3 · Qwen 0.5B Uncensored | Dolphin 作者声明不强加自身伦理或准则，行为由用户的系统提示词控制。 | [作者模型卡](https://huggingface.co/dphn/Dolphin3.0-Qwen2.5-0.5B/blob/f41a6b451e746c75992623d8d4548ed29438ff34/README.md) |
| m03 | Qwen 3.5 · 0.8B Abliterated | 作者明确声明通过 abliteration 去除拒答的无审查版本。 | [作者模型卡](https://huggingface.co/huihui-ai/Huihui-Qwen3.5-0.8B-abliterated/blob/4813135658fe51b2e535b8e77927d2f23909ce42/README.md) |
| m04 | Dolphin 3 · Llama 1B Uncensored | Dolphin 作者声明不强加自身伦理或准则，行为由用户的系统提示词控制。 | [作者模型卡](https://huggingface.co/dphn/Dolphin3.0-Llama3.2-1B/blob/e753b6ebd7adf87036eb6a3e6de68acca5850e2f/README.md) |
| m05 | Gemma 3 · 1B Abliterated | 作者明确声明通过 abliteration 去除拒答的无审查版本。 | [作者模型卡](https://huggingface.co/mlabonne/gemma-3-1b-it-abliterated/blob/33c47e9a7c53e677e160c4b0ae799de66f34a7a0/README.md) |
| m06 | LFM 2.5 · 1.2B Uncensored | 作者使用 Heretic 方向消融去除拒答的无审查版本。 | [作者模型卡](https://huggingface.co/zaakirio/LFM2.5-1.2B-Instruct-Uncensored/blob/1a666fb441c9e7fa6c597acab1ad16aaf55eebac/README.md) |
| m08 | Qwen 3 · 1.7B Abliterated | 作者明确声明通过 abliteration 去除拒答的无审查版本。 | [作者模型卡](https://huggingface.co/mlabonne/Qwen3-1.7B-abliterated/blob/62f9c246cf426703a08183aa883a0d8149984bb0/README.md) |
| m09 | Qwen 3.5 · 2B Abliterated | 作者明确声明通过 abliteration 去除拒答的无审查版本。 | [作者模型卡](https://huggingface.co/huihui-ai/Huihui-Qwen3.5-2B-abliterated/blob/b2e291a65f29a9b148981fa5299caea5d35bd4c8/README.md) |
| m10 | LFM 2.5 · 2.6B Uncensored | 作者合并 Abliterix Trial 65 去拒答修改的无审查版本。 | [作者模型卡](https://huggingface.co/SC117/LFM2.5-2.6B-Uncensored/blob/f5d7df0e26409afdfead05f3bc0da5043f2a794e/README.md) |
| m11 | Dolphin 3 · Qwen 3B Uncensored | Dolphin 作者声明不强加自身伦理或准则，行为由用户的系统提示词控制。 | [作者模型卡](https://huggingface.co/dphn/Dolphin3.0-Qwen2.5-3b/blob/f258b471c4a02470fb87e134f7e0f46525471637/README.md) |
| m12 | Dolphin 3 · Llama 3B Uncensored | Dolphin 作者声明不强加自身伦理或准则，行为由用户的系统提示词控制。 | [作者模型卡](https://huggingface.co/dphn/Dolphin3.0-Llama3.2-3B/blob/392a6f57223e7ccfe6ef4ebdb2ff101a42d57364/README.md) |
| m13 | Llama 3.2 · 3B Uncensored | 作者明确声明通过 abliteration 去除拒答的无审查版本。 | [作者模型卡](https://huggingface.co/chuanli11/Llama-3.2-3B-Instruct-uncensored/blob/27bd02b95b56f9886daf3d4be4101916b15809d1/README.md) |
| m14 | Qwen 3 · 4B Instruct 2507 Abliterated | 作者明确声明通过 abliteration 去除拒答的无审查版本。 | [作者模型卡](https://huggingface.co/huihui-ai/Huihui-Qwen3-4B-Instruct-2507-abliterated/blob/c9bd464550d4078c72af0dd22aa18d0437868ce3/README.md) |
| m15 | Qwen 3.5 · 4B Uncensored | HauhauCS 发布的 Aggressive 无审查权重版本。 | [作者模型卡](https://huggingface.co/HauhauCS/Qwen3.5-4B-Uncensored-HauhauCS-Aggressive/blob/c09cdbcdb1fefad6d335809d445621b5f5ba0c6e/README.md) |
| m16 | Gemma 3 - 4B Abliterated v2 | 作者明确声明通过 abliteration 去除拒答的无审查版本。 | [作者模型卡](https://huggingface.co/mlabonne/gemma-3-4b-it-abliterated-v2/blob/375331eeafe1b66df84075c63e5cadb13ff42b94/README.md) |

Dolphin 属于作者声明由用户控制行为准则的无审查指令微调路线；Abliterated 条目有作者去拒答处理说明；HauhauCS 条目采用作者发布的 Aggressive 无审查权重。应用界面逐项展示处理方式与作者说明入口。

默认系统提示词只指定助手、语言和回答风格，用户可以修改或留空。LMA 的生产对话路径未增加关键词拦截、提示词内容分类、云端审核或模型回复内容过滤；正常的长度、格式、资源与接口鉴权校验仍按功能需要执行。

用户自行添加或导入的 GGUF 显示“属性未核对”，由用户确认其权重来源。其名称即使含有 uncensored，也不会自动变成已核对的内置模型。

作者声明与实际拒答率分别记录。当前没有 Android 真机，尚未运行实际模型拒答率测试，也未确认所有条目在 Z20 上成功推理。此限制保留在交付验证记录中。

复核细节：Dolphin 的旧组织名 cognitivecomputations 已通过 HF API 的模型 ID 核对到 dphn；Gemma 1B 的 GGUF 卡 front matter 错写了 12B 基座，因此使用同一作者正文中的 1B 具体型号、无审查声明和既有实际文件探测作为归属依据。

完整结构化依据位于 catalogue/uncensored-evidence.json；工具 tools/audit_uncensored.py 可重新读取作者说明。此次网络曾返回 HTTP 429，后续使用本轮已下载、按 SHA256 复核的说明文件完成审计，并重新查询组织更名记录；没有把限流响应作为成功证据。

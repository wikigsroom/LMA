# 旧 LTX 0.9.8：原生 T5 文本编码组件

[English](LTX098_TEXT.en.md) · [DiT 与采样](LTX098_SAMPLING.md) · [同一完整版本范围](MULTIMODAL_RELEASE_PLAN.md)

本组件为冻结目标 17 补充本地文本编码能力。它是独立研究执行器，尚未注册为 App 视频引擎；不代表完整视频、画质或 Android 真机验收。App 仍只更新基座，模型和配套数据由用户自行选择、下载、导入和管理。

## 接口与执行逻辑

固定旧版管线只对提示词执行 `str.strip()`，最多 256 个 token。原生实现检查 UTF-8，按 Python 的 Unicode 空白集合裁去首尾空白，保留大小写和正文；使用外部 GGUF 的学习词表 / 归一化表和原始外部 tokenizer 配置。固定的 Transformers 5.17 后处理总会追加 EOS，包括用户正文已含显式 EOS 的情况；超限截断保留末尾 EOS。不声称与历史 4.x tokenizer 行为完全相同。

编码结果为逐 token 的原始 final-RMSNorm embedding，形状 `[1,有效token数,4096]`，不池化、不做 L2 归一化。输出附带相同长度的全 1 遮罩。独立参考分别检查紧凑有效序列与原始 256-token padding / attention mask 的有效行，防止把 padding 当成正文；PAD ID 作为显式输入 token 时仍是一个有效位置。

编码器检查 `t5encoder`、24 层、4096 宽度、64 头、64 维 key/value、10240 FFN、32128 词表、32 个相对位置桶、`1e-6` RMS epsilon。未训练小宽度文件必须显式加 `--fixture`，生产模式拒绝它们。

执行采用 GGML CPU、只读文件映射和独立 T5 图。相对位置偏置、非因果注意力、gated-GELU FFN、残差和最终归一化均在本机执行。GELU 使用显式 F32 tanh 公式，避免复用运行库的 F16 查表精度损失；不修改或替换现有 App 运行库。量化矩阵在各次 matmul 前临时解量化为 F32，避免直接量化 CPU matmul 的额外 Q8 激活舍入；图分配器复用已失效的矩阵缓冲，不常驻整份 F32 检查点。映射文件 / 张量字节与峰值图缓冲独立报告，不能当作进程总内存。每次输入重建有界计算图，同一实例复用权重；析构释放图、权重映射和词表。

CLI 只接受本地文件，无网络或进程调度接口。严格检查请求键、重复键、整数 / token / 线程范围和输入数量；保护既有输出，失败和取消不发布最终产物。CPU 中止回调覆盖实际神经计算，进度分别报告加载、编码和计算进入点。

## 外部模型与来源

| 资产 | 固定来源 | 身份与边界 |
| --- | --- | --- |
| T5 Q5_K_M encoder | `city96/t5-v1_1-xxl-encoder-gguf` @ `005a6ea51a7d0b84d677b3e633bb52a8c85a83d9` | 3,386,856,640 字节；SHA256 `b51cbb10b1a7aac6dd1c3b62f0ed908bfd06e0b42d2f3577d43e061361f51dae`；社区量化，不是 Lightricks 官方量化 |
| 独立参考配置 / 词表 | `google/t5-v1_1-xxl` @ `3db67ab1af984cf10548a73467f0e5bca2aaaeb2` | 固定 config、SentencePiece、tokenizer config、special-token map；仅开发者参考资产 |
| 原生代码 | llama.cpp @ `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4` | MIT；复用已固定的 Android CPU 运行库身份，研究程序不进 APK |

资产的 Apache-2.0 声明、代码许可、文件大小 / SHA、源代码与 Python 参考文件指纹见 [source lock](../third_party/ltx098-text-source-lock.json) 和 [NOTICE](../research/ltx098_text/NOTICE)。旧 LTX DiT / VAE 仍适用各自的模型许可，不能以 T5 许可替代。

社区 GGUF 将 100 个 sentinel 位置标为未使用 padding，因此仅靠其中的分词元数据不完整。`TOKENIZER_CONFIG.json` 是必须单独选择的原始文件；原生程序读取其中的 sentinel 名称并应用 T5 公开的倒序 ID 约定。独立检查逐项比较全部 32000 个学习词条 / 分数及完整 237539 字节归一化表。

所有权重、词表、SentencePiece、字符归一化数据和参考输出仅保存在被 Git 忽略的 `build/`。安装、升级、浏览、构建、测试和缺件错误都不会自行下载模型。这里的开发者资产准备不等于 App 已提供完整公开视频模型候选。

## 复现

从仓库根目录在原生 Windows PowerShell 执行。代码 / 工具依赖的准备遵循 [构建说明](BUILD.md)，不使用 Docker、WSL、虚拟机或模拟器。

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:TEMP="$PWD/build/tmp"
$env:TMP="$PWD/build/tmp"
python tools/fetch_ltx098_text.py --download --download-oracle-assets
python tools/build_ltx098_text.py
python tools/ltx098_text_oracle.py --trained
python tools/test_ltx098_text.py --trained
python tools/build_ltx098_text.py --android
```

获取工具默认只核验；网络镜像只能替换下载来源，revision / 大小 / SHA 不变。原生构建必须顺序运行，临时 SUBST 在 finally 释放。缺少 Python 参考依赖时需要按锁文件显式准备；脚本不会安装它们。当前参考使用锁定文件哈希的 Transformers 5.17.0、Torch 2.14.0+cpu、NumPy 2.4.2、SentencePiece 0.2.1 和固定 gguf-py。

CLI：`lma_ltx098_text_cli MODEL.gguf TOKENIZER_CONFIG.json REQUEST.json OUTPUT THREADS [--fixture]`。请求示例：

```json
{"operation":"encode","max_tokens":256,"inputs":[{"prompt":"A red balloon floats above a quiet lake."}]}
```

`tokenize` 输出连续 little-endian int32；`encode` 输出连续 little-endian F32。stdout JSON 给出每项的 token、mask、shape、字节偏移和生命周期计数；stderr 提供阶段事件。每个请求最多 4 项、每项最多 65536 UTF-8 字节、线程 1–32。可提供 `cancel_file`，该文件出现后取消。

## 验证边界

独立参考直接运行未修改的已安装 `T5EncoderModel` forward。未训练案例覆盖 2 / 24 层、完整外部词表、短序列 / 256 token、字面 PAD / 词表边界；分词覆盖空白、中文、重音、特殊 token、未知字符和截断。训练参考将固定 GGUF 逐张量解量化为 F32，一次只加载一个原始模块，实际使用全部 219 张量。

这能检查原生执行器与该量化文件的语义，**没有**比较未量化 Google 权重，也没有证明社区量化的提示词或视频质量。固定门槛在执行前写入锁文件，不能以放宽门槛代替修复。Android ARM64 / API28 / 16KiB 的编译和依赖检查，与主机真实权重推理、App 注册和手机执行分别记录。

本轮结果与编号待办见 [交付记录](releases/v0.3.0-dev.21-ltx-text.md)。后续仍须串联生产噪声 / 采样 / VAE / 帧与 MP4、完整用户资产与 App 管理、真实质量 / 资源 / 取消及物理 Android 后台验收；01–14 /16 /17、全部冻结子目标和 F-01–F-12 均保留在同一个完整 v0.3.0。

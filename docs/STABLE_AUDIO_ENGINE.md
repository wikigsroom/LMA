# Stable Audio Open Small 本地音频基座

[English](STABLE_AUDIO_ENGINE.en.md) · [开发状态](DEVELOPMENT.md) · [完整版本需求](MULTIMODAL_RELEASE_PLAN.md)

本页对应 **0.3.0-dev.20 / code 24** 的源码与限定检查，不是完整 v0.3.0 的支持声明。原编号 **14** 仍须完整权重、新输入离线音频、质量和物理 Android 验收。当前没有可用真机，未生成完整模型音频。

## 1 · 执行方案与资产边界

`stable_audio_litert` / `stable_audio_small_litert_v1` 使用手机上的 **LiteRT 2.2.0 CPU CompiledModel C API**，依次运行 T5 / 时长编码器、DiT 和音频解码器。每阶段结束先释放其模型、编译对象和张量缓冲，再进入下一阶段；DiT 采样期间保留其运行对象。取消会终止子进程并释放私有硬链接工作目录，用户模型对象受租约保护。

APK 只增加原生 worker、LiteRT 代码和配方元数据；不含权重、T5 词表、音频 codec 或音色数据。安装、升级、浏览、缺件均不自动下载。此路线上没有远程推理、外部转换服务、Termux、ROOT 或用户可安装的 native 插件。

| 用户选择的组件 | 文件 / 格式 | 固定导出约束 |
| --- | --- | --- |
| `conditioner` | `conditioners_float32.tflite` / TFLite | int64 IDs / mask `[1,128]`，float32 秒数 `[1]`；输出 cross `[1,65,768]`、mask `[1,65]`、global `[1,768]` |
| `diffusion_model` | `dit_model.tflite` / TFLite | float32 latent `[1,64,256]`、时间 `[1]`、cross `[1,65,768]`、global `[1,768]`；输出同形 latent |
| `audio_decoder` | `autoencoder_model.tflite` / TFLite | float32 latent `[1,64,256]` → 双声道平面音频 `[1,2,524288]` |
| `tokenizer` | 配套 `spiece.model` / SentencePiece | T5-base 的 32000 个 SentencePiece 项、pad 0 / EOS 1；不等同于含额外 sentinel 的 tokenizer 逻辑词表或 embedding 容量 |

组件必须匹配固定的 Arm 导出。图在创建 CPU 运行对象前校验签名数量、输入输出数量、dtype、rank 和精确 shape；不接受动态 shape、stride 或任意同名 TFLite。用户可以改本地文件名，组件角色和内容约束不变。所有图的外部接口为 float32 / int64，内部权重量化由兼容导出决定。LiteRT 仅选 CPU，采用运行库默认 XNNPACK 标志，未强制 FP16；APK 不装其 GPU 加速器。运行库本身依赖系统 EGL / GLESv3，这是 ELF 依赖，不表示本管线使用 GPU。

## 2 · 使用逻辑

1. 在模型页的“全部 / 搜索”查找用户有权访问的兼容导出仓库，进入文件列表，选择本配方。HF 搜索支持 TFLite 文件识别，但不表示任意 HF 模型都可运行。
2. 逐项绑定四份组件，核对来源、固定 revision、大小和完整性后明确下载；已有配套资产也可通过模型包导入。原始 `.ckpt` / `.safetensors` 不能直接绑定为这份 TFLite 配方；App 不自动转换模型。
3. 在“本地”检查组件，编辑此模型的默认参数。选择模型、填写英文声音描述、确认本机尝试，再加入共用队列。缺件 / 格式错误直接在本机失败。
4. 手机完成分词、条件编码、扩散、解码、裁切及 WAV 保存；产物进入本机音频列表。API 使用同一个 `audio.generate` 任务与持久任务 / 产物接口，详见 [API](API.md)。
5. 暂停 / 恢复下载、独立更新、删除及引用保护复用共用资产基座。任务参数为快照，不修改模型默认值；升级恢复下载时保持暂停。

没有把某个社区仓库列为已核验可直接运行的四文件发行包；本轮固定的是代码 / 图契约及官方仓库元数据，仍需要用户选择匹配资产并完成整模型验收。模型条目平级，功能标签为 `task:audio`、`text_to_audio`、`short_audio`、`english_prompts`、`fixed_latent_length`；引擎、pipeline、架构、格式、依赖、设备证据、许可和内容标签分别保存。它不自动获得 Uncensored 标签。

## 3 · 参数、采样与输出

| 参数 | 默认 / 范围 | 依据与行为 |
| --- | --- | --- |
| 秒数 | 5 / 1–11，整数 | 模型公开时长范围；输出裁切为 `44100 × seconds` 帧 |
| 扩散步数 | 8 / 1–32 | 8 为上游默认；32 是应用保护上限，不是模型理论极限 |
| 有效输入 token | 64 / 1–64 | 包含 EOS；Arm 编码器输入 128，但仅前 64 项进入 DiT。超预算报错，不静默丢弃后半提示词 |
| CPU 线程 | 4 / 1–32 | 应用保护，不表示手机有 32 核 |
| 种子 | -1 / -1 或 0–2147483647 | -1 在执行前解析为具体随机种子，写入任务执行回执 |

本地设置和本次参数都用可编辑预设输入框，数值超限归位。后端重新校验快照；不暴露未消费的 CFG、负面提示词、参考音频、语音克隆、图像 LoRA 或逐段音频流。

保持 Arm 的 ping-pong 策略：`sigmoid(-linspace(-6,2,steps+1))`，首尾改为 1 / 0；先 `denoised=x-t×velocity`，再与下一时刻噪声混合。初始噪声用所选种子，每步噪声用 `seed + step + 4564`。种子保证同一实现的重现性，不承诺跨 PyTorch / 标准库逐位一致。

**1 秒输出同样执行完整 256 latent 帧和 524288 解码帧**，再裁切为请求时长，不能按输出秒数线性降低内存预估。解码必须全部为有限 float，左右平面交错为 44.1 kHz / 立体声 PCM16；峰值超过 1 时衰减，保留较小信号音量。回执包含实际 prompt token、步数、固定长度、各阶段耗时、整体 RTF 和停止原因。耗时字段来自执行测量，当前没有可发布的完整模型测量数值。

Arm 参考要求约 8 GB RAM，并讨论 DotProd / i8mm 优化；顺序加载不等于已经证明内存足够。努比亚 Z20 的 SoC、6 / 8 GB 内存型号、可用内存和系统温控须单独测试。目前不宣称实时、可后台无限运行或 Z20 可用。公开模型主要针对英文短声音 / 音效，不将它描述为完整歌曲、可靠歌声或通用 TTS。

## 4 · 来源、许可与重建

- [Arm-Examples / ML-examples](https://github.com/Arm-Examples/ML-examples/tree/0e453847ea28043194c32791a591d0f5a8a5ae2e/kleidiai-examples/audiogen)，固定 `0e453847ea28043194c32791a591d0f5a8a5ae2e`，Apache-2.0；布局与采样参考。LMA 改为 C API、顺序加载、严格验证、私有协议、受控 PCM16 输出。
- [LiteRT v2.2.0](https://github.com/google-ai-edge/LiteRT/releases/tag/v2.2.0)，官方 Android Maven AAR 与同版 SDK，保留其 LICENSE 及完整第三方 NOTICE。ARM64 runtime 为 5,508,376 bytes / SHA256 `97355a36cb8ac7628cf407773291e98da79f3ef184cc43cb0e57dedf5f0c0637`。
- SentencePiece 固定 `31646a467d2051eb904e0b45de3a73e91fe1c1e3`，关闭 embedded data / 测试 / 共享库；只编译通用代码。
- [官方模型](https://huggingface.co/stabilityai/stable-audio-open-small)采用独立的 Stability AI Community 条款且有访问门槛；用户须自行取得权限。App 的源码许可不替代模型许可，也不绕过 gated 访问。[元数据记录](../catalogue/evidence/stable-audio-publisher.json)固定模型 revision `dc620d91535857b72ebb59b4ca45978db6d417f5`、T5 revision `a9723ea7f1b39c1eae772870f3b547bf6ef7e6c1`；元数据核对未下载模型 / 词表。

完整版本、hash、notice 见 [源码锁](../third_party/stable-audio-source-lock.json)。原生 Windows NDK r30 / API28 / CMake / Ninja；不调用 Docker / WSL / VM / 模拟器。在仓库根目录依次运行：

```powershell
python tools/fetch_stable_audio.py
python tools/build_stable_audio.py
python tools/collect_stable_audio_notices.py
python tools/test_stable_audio.py
python tools/build.py
python tools/verify_package.py
```

主机测试另需 Python `flatbuffers` 包、MSVC、Java；脚本获取固定的官方 Windows LiteRT wheel，仅提取 DLL 与 schema 来生成无训练权重的 ADD / CAST 测试图，不安装到 APK。所有缓存与输出在仓库 `build/`，模型转换不是本构建步骤。测试脚本使用临时 SUBST 别名，避免与其他使用同类别名的原生构建并发。

## 5 · 本轮编号交付与未完成项

| 编号 | 已实现 / 检查 | 实际边界 |
| --- | --- | --- |
| SA-01 | ARM64 worker + 官方 LiteRT 2.2.0，16 KiB 对齐 | 完成编译；未在 Android 执行 |
| SA-02 | 四组件选择 / 租约、顺序阶段、取消与 WAV 校验 | 生产代码及 6 次实际主机子进程；音频是静音结构夹具 |
| SA-03 | 144 项 = Java 51 + C++ 93 | 6 次实际 LiteRT 微型图运行、3 次各图加载释放、固定 Arm 采样比对；没有训练 checkpoint 或模型音频 |
| SA-04 | 独立参数、超限归位、平级标签与 UI 媒体 | 标记 UI FIXTURE；不表示手机生成 |

| 编号 | 待处理 / 待完成 | 门槛 |
| --- | --- | --- |
| SA-P01 | 匹配四文件模型包、真实新提示词离线音频、质量 / 资源 / 取消 | 14 仍未完成端到端验收 |
| SA-P02 | Android 多次装卸、锁屏 15 分钟、1 小时交替 API、升级资产保留 | 物理设备证据为 0，不创建新 Release |
| SA-P03 | 其余完整范围 | F-01–F-12、既有生文、01–14 / 16 / 17 全部冻结子目标和 A1–A11 / R-01–R-05 继续属于同一 v0.3.0；包括九种 MOSS、SoulX、旧 LTX、两类 LoRA 的各自验收 |

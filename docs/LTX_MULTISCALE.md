# 旧 LTX 0.9.8：原始 PixArt T5 与多尺度

[English](LTX_MULTISCALE.en.md) · [本版实现](IMPLEMENTATION_V030.md) · [程序验证](PROGRAM_VALIDATION.md)

v0.3.0 为 selection 17 增加原始 PixArt T5 F32 和多尺度程序路线。既有 Google T5 Q5 单尺度保留独立身份、配置和历史记录，不充当本路线的替代。仅做程序验证，未执行完整训练模型、未验证画质或手机资源。

## 用户取得与管理资产

1. 用户明确导入或下载固定的 `ltx098_source_r8984fa2` 来源模型包。
2. 在本地对用户已有权重运行 `ltx098_dit_vae_v1` 准备方案。APK 提供程序与计算结构；不内置权重、不拉取其他模型。
3. 明确选择 `ltx098_pixart_generation_v1` 关联方案，把 20 个已准备的 DiT / VAE 组件关联到 `ltx098_runtime_pixart_multiscale_v1`。关联复用数据，不能替换来源身份。
4. 在详情查看其余 7 个依赖后，明确下载或导入：T5 配置、分片索引、两个 F32 分片、分词配置、SentencePiece 文件和学习型空间放大器。没有已准备的组件时，完整包下载按钮不会假装这些组件可直接取得。
5. 全部 27 个组件校验通过后，在“本地”保存独立设置，再从使用入口提交视频任务。缺组件和资源未知会在预检中说明，不自动降级成其他模型或外部执行。

运行资产共 **25,616,311,982 字节，约 23.86 GiB / 25.62 GB**；T5 两分片约 17.74 GiB。源文件和准备临时文件需要额外磁盘空间。映射读取避免制作另一份 T5 转换文件，但不证明系统 RAM 足够，更不代表 Z20 适用。

## 固定身份

| 来源 | 固定 revision | 用途 |
| --- | --- | --- |
| PixArt-alpha/PixArt-XL-2-1024-MS | `b89adadeccd9ead2adcb9fa2825d3fabec48d404` | 原始 T5 配置、索引、两个 F32 safetensors、分词资源 |
| Lightricks/LTX-Video | `8984fa25007f376c1a299016d0957a37a2f797bb` | 0.9.8 distilled 来源与 505,024,432 字节空间放大器 |

完整文件大小、SHA256 和元数据头身份在 [锁定清单](../third_party/ltx098-official/identity.json)、[模型包](../catalogue/model-bundles.json)及[专用参数校验](../app/src/main/java/com/lma/app/core/LtxPixArtSpec.java)。本次只读取小型配置、分词文件与有界 safetensors 头，未下载完整权重。模型许可分别遵守 LTX-Video Open Weights 0.x 和 PixArt OpenRAIL++，不能由 App MIT 许可代替。

## 手机内顺序执行

| 阶段 | 程序行为 |
| --- | --- |
| 1 | 初次几何为输出尺寸 × 0.6666666 后向下对齐 32，生成确定性噪声 |
| 2 | CPU 直接映射两个原始 F32 T5 分片；原始 SentencePiece、额外 token、EOS 与注意力 mask；不转换成 Google T5 |
| 3 | Vulkan DiT 固定 7 步，sigma 为 1、.9937、.9875、.9812、.975、.9094、.725；末步到 0 |
| 4 | 将 token 重新排成 128 通道 latent |
| 5 | CPU ORT 单个空间放大会话：VAE 通道去归一化 → 学习型 2 倍空间放大 → 归一化 → 通道 AdaIN（无偏标准差）；会话释放后进入下一阶段 |
| 6 | 在 .9094 重新加噪并产生独立的 VAE decode 噪声 |
| 7 | Vulkan DiT 固定 3 步，sigma .9094、.725、.4219，末步到 0 |
| 8 | 重新排回细化 latent |
| 9 | CPU 九段 VAE，解码 timestep .05 / noise .025；分段释放 |
| 10 | 原像素先截断到 [-1,1]，双线性 align_corners=false 缩到请求尺寸，再由手机 MediaCodec 编码 AVC MP4 |

CFG=1、STG=0。提示词直接编码；不隐式下载可选提示词增强模型。当前 LMA 随机流可复现，但不承诺同 seed 与 PyTorch / 上游生成内容逐字节一致。输出宽高 128–256、32 倍数；9–33 帧、8n+1；fps 1–60；线程 1–8；固定 10 步。参数的应用范围不等于模型理论极限。

22,474 字节 ONNX 资源只含运算和常量结构，72 个学习张量均为指向用户原始放大器文件的 external-data 引用。安装包检查重建计算图并核对字节、引用和无内嵌学习张量。任务持有组件引用；任一阶段失败或取消，等待子进程退出后释放工作目录和资源，不发布半成品。

## 本版验证范围

- 89 项有界检查：原始 T5 文件布局与分词、微型随机 T5 对照、72 张量结构的随机小型放大器对照、AdaIN、上游未改调度器、噪声与最终缩放。没有完整训练权重。
- 280 项生产 Java 引擎 / 队列流程检查：十个顺序阶段、配置快照、错误、缺失 / 重复回执、取消、编码失败及资源清理。神经阶段使用明确的替身，生产描述校验拒绝替身文件。
- 旧单尺度路线保留独立的 127 项程序检查；两路线不合并成数值 / 画质通过。
- Android ARM64 / API28 编译、16 KiB 对齐与最终 APK 核对；21 项新页面交互、4 张截图、GIF 和 MP4。桌面媒体标明 UI FIXTURE，录制后关闭浏览器。

[当前记录](../verification/program/status.json)与历史失败分开。根据用户指令，不继续跑完整模型、ASR、手机推理或长时间锁屏测试；未验证的质量、速度、资源、真机状态保持未验证。

# Wan 本地视频

dev.40 新增按模型解码控制：128–1024像素空间分块与实验性时间分段；既有模型和旧任务兼容，默认128 / 时间分段关。五组完整几何实验与原版 CPU VAE 对照仍复现末帧伪影，不能作为质量通过。[完整设置、资源和画质诊断](WAN_DECODER.md)。

[English](WAN_VIDEO.en.md) · [中文首页](../README.md) · [完整同版范围](MULTIMODAL_RELEASE_PLAN.md)

LMA 新增 Wan 2.1 T2V 1.3B Q4 可选模型。它与生文、生图、音频模型平级，显示“生视频 / 文生视频”和 Vulkan、CPU 文字编码 / 画面解码等标签。APK 更新只提供运行基座，四个模型组件仍由用户明确选择、下载或导入。浏览、安装 App 或升级不会下载权重。

该入口复用现有模型管理、独立参数、任务队列、不可变输入、取消、结果和来源记录。它没有 ComfyUI 画布、节点、插件或外部推理服务。原有 CPU 配方、用户模型与历史任务保留。

## 1. 使用流程

1. 在“模型 → 全部”选择“生视频”，打开 **Wan 2.1 · 1.3B Q4 · 本地 GPU 视频**。推荐仍保持原有三项及顺序。
2. 查看四个组件、约 **4.74 GB** 下载量、发布者与许可；点击下载才开始获取所选文件。已有完整 SHA 匹配对象可复用，不会因此自动安装另一模型。也可从 HF 搜索选择文件并用对应配方组装，或明确导入完整文件。
3. 在“本地”管理安装、下载暂停 / 继续、导入和删除。模型文件、独立设置与生成结果分别管理；删除模型不会自动删除结果。
4. 在该模型设置中编辑宽高、步数、帧数、帧率、CFG、种子、线程和 flow shift。选择输入框允许自定义，超过模型字段上限会归位；运行准备还会按 Wan 约束整理尺寸和 `4n+1` 帧数。
5. 使用模型，输入提示词，确认资源未实测提示后提交。任务保存模型身份、组件完整哈希和当时参数快照；后续修改设置不会改变已提交任务。
6. 共用任务页显示模型运行与视频编码进度，可取消、查看错误、重试和管理结果。完成后保存 MP4 与实际参数、组件来源、运行后端记录。后台任务由原生服务拥有；本轮没有真机锁屏续跑验收。

默认参数为 **512×288、17 帧、8 fps、20 步、CFG 6、Euler / discrete、flow shift 3、VAE tiling**。这是可编辑配方默认值，不是努比亚 Z20 性能或内存保证。验证可显式选用较小的 256×256 / 5 帧 / 4 步配置；小配置结果不代表默认画质。

## 2. 完整组件

| 角色 | 固定文件 | 完整字节数 |
|---|---|---:|
| 生成器 | off-grid-ai/Wan2.1-T2V-1.3B-GGUF · Wan2.1-T2V-1.3B-Q4_K_S.gguf | 816,061,024 |
| 文字编码器 | off-grid-ai/Video-Companions-GGUF · umt5-xxl-encoder-Q4_K_M.gguf | 3,655,145,312 |
| 画面解码器 | 同上 · wan_2.1_vae.safetensors | 253,815,318 |
| 分词数据 | google/umt5-xxl · tokenizer.json | 16,853,013 |

合计 **4,741,874,667 字节**。完整版本、SHA256、规范 HF 地址及 Apache-2.0 声明记录在[组件锁](../research/wan_trained/assets.json)、[可选目录](../research/wan_trained/catalogue-bundle.json)和[来源说明](../research/wan_trained/NOTICE)。它们不进入 Git / APK。文件名建议只辅助选择，不证明架构、内容标签或手机兼容性；1.3B 配方不自动选 14B，不在多种量化之间静默猜测。

## 3. 同一手机的运行基座

`wan_sd_cpp` 使用固定 sd.cpp / ggml 源码，UMT5 分词与编码在 CPU，扩散在 `Vulkan0`，VAE 在 CPU。Java 接收真实 RGB 帧，再用同一手机的 Android MediaCodec / MediaMuxer 编码 MP4。没有 ROOT、Termux、RPC、其他设备解码或外部视频合成。

GPU worker 与原 `sd_cpp` CPU worker 身份独立，拒绝后端不匹配。缺少 Vulkan 时明确失败，不自动改到 CPU。只有观察到一次实际完成、位于非主机 Vulkan 缓冲区的 GPU 矩阵运算，才允许发布结果；检测到显卡名称不等于执行成功。实际后端随结果来源记录保存。

用户可以选择参数，但字段上限不等于设备资源预算。手机 GPU 驱动、内存、发热、生成耗时及 Android 编码均须独立验收。对 Z20 目前没有 LMA 实机证据，不能据此承诺长视频或持续后台运行。

## 4. 开发复现与证据边界

全部命令在仓库内运行，仅使用原生 Windows 工具；不启动 Docker、WSL、虚拟机或模拟器。

```text
python tools/fetch_wan_trained.py
python tools/fetch_wan_trained.py --download --jobs 2
python tools/build_sd_vulkan.py --android --jobs 2
python tools/test_wan_trained.py
python tools/test_wan_app_host.py
python tools/render_wan_trained.py
node tools/capture_workbench.cjs wan
```

首条只验证本地已有资产；只有第二条明确下载。网络不参与推理。资产较大时可由操作者明确选择下载镜像，收据保留实际传输来源，最终仍验证固定完整 SHA。测试不会自动获取模型。

原生主机检查覆盖真实提示词、采样参数变化、采样取消、错误和恢复，并要求实际 Vulkan 运算与运动帧。生产 Java 检查覆盖完整离线导入、对象复用、模型独立设置、租约、任务快照、实际子进程、结果与重启 / 删除。Windows 测试专用编码端使用本机 FFmpeg，明确标记 **不是 Android 编码**；APK 使用生产 Android 编码器。

页面截图和录制来自实际生产 HTML 与明确标记的模拟桥接，不属于手机截图或模型运行证明。实际模型帧和视频另行展示，保留原始输出及失败。主机运行、ARM64 编译、独立数值、画质、手机资源和正式 Release 是不同门槛。

本目标仍属于同一个完整 v0.3.0，未因新增配方或主机产物关闭 16 号全部验收；其他冻结目标、原 LCM / Sana / LTX 失败及全部手机 / 发布门槛继续保留。


## 5. 实际产物 / Actual artifacts

[实际默认配置视频 / Default host video](media/development/wan-trained/default.mp4) · [帧比较 / Actual frames](media/development/wan-trained/default-frames.png) · [页面录制 / UI recording](media/development/wan/wan-ui.mp4) · [完整编号交付 / Numbered delivery](releases/v0.3.0-dev.39.md)

![Actual Wan host output; not Android footage or generation timing](media/development/wan-trained/default.gif)

默认配置为一次明确标记的完整主机 smoke；小配置七场景及生产 Java 业务另外校验。Default output is a labelled complete host smoke; small-configuration scenario checks and production Java lifecycle checks are separate. Quality and phone acceptance remain pending.

实际默认示例的后段可见块状伪影，不能作为画质通过。原始全部帧与该问题一并保留；数值对照和视频质量修复仍属于本次完整 v0.3.0 的待完成事项。


验证 / Validation: **22 suites /3,057 checks** =2,801 shared controls +117 tokenizer +39 complete native Wan +100 production Java. Signed development APK:61,325,834 bytes;35 native files;Lint0 errors /17 warnings. Actual host MP4 input frames match direct native output byte-for-byte. These checks do not accept video quality, physical Android or the complete Release.

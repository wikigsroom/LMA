# Z-Image、FLUX、Qwen-Image 与 Wan 的本机基座接入

[English](ADVANCED_DIFFUSION.en.md) · [扩散基础](DIFFUSION_ENGINE.md) · [HF 配方](HF_RECIPES.md) · [实施状态](DEVELOPMENT.md)

适用内部 **0.3.0-dev.13 / code 17**，不是完整 Release。已接入组件契约、任务采样计划、原生参数及 ARM64 CPU worker；**尚无这些模型的 Android 输出、质量、速度、内存或锁屏实测**。06 / 07 / 08 / 16 及其他全部目标仍须在同一完整 v0.3.0 验收。

## 用户资产与组件

App 只交付签名代码、配方与标签，不包含下表的任何权重或词表。用户在 HF 文件页选择对应模板，逐项选择配套文件；可以跨仓库选择，每个文件固定 revision、大小和完整性身份。确认清单后先登记，再单独点击下载或导入文件夹。在“本地”管理参数、更新、回退、删除。浏览、App 升级和缺组件任务均不触发下载。

| 独立模板 | 必须由用户提供 | 功能 / 基座标签 |
| --- | --- | --- |
| `z_image_turbo_split_cpu_v1` | Z-Image-Turbo diffusion、匹配 Qwen3 4B 编码器、FLUX.1 VAE、Qwen merges.txt | 生图 / 文生图、sd_cpp、z_image_turbo、CPU |
| `flux2_klein_4b_split_cpu_v1` | distilled klein 4B diffusion、匹配 Qwen3 4B、**FLUX.2 VAE**、Qwen merges.txt | 生图 / 文生图、sd_cpp、flux2_klein_4b、CPU |
| `qwen_image_21_split_cpu_v1` | Qwen-Image 2.1 diffusion、匹配 Qwen3-VL 8B Instruct、**2.1 专用 VAE**、Qwen merges.txt | 生图 / 文生图、sd_cpp、qwen_image_21、CPU |
| `wan21_13b_split_cpu_v1` | Wan 2.1 T2V 1.3B diffusion、UMT5 XXL 编码器、Wan 2.1 VAE、UMT5 tokenizer.json | 生视频 / 文生视频、sd_cpp、wan21_13b、CPU |

权重角色接受 GGUF / Safetensors，词表分别为 text / JSON，最大 32 MiB。以上为独立组件配方；拒绝将单个文件声明为完整 checkpoint、漏组件、错误架构声明或额外不使用的组件。格式、文件名和四个文件齐备不能证明张量内容彼此兼容。模板不转换模型、不自动下载、不安装引擎，也不扩展原有推荐。

Qwen 只接入文生图，未接入参考图 / mmproj、图像编辑、旧 Qwen-Image 或 2.1 Turbo 固定 sigmas。FLUX 配方对应 distilled klein 4B，不代替 base / 9B / dev。Wan 对应 T2V 1.3B，不代替 I2V、VACE、14B 或 Wan 2.2；冻结验收仍要求所选 Q4 资产。Z-Image 配方对应 Turbo，不把普通 base 当作蒸馏模型。

## 参数与执行

| 管线 | 本次采样 | 尺寸 / 视频规则 |
| --- | --- | --- |
| Z-Image-Turbo | euler / discrete、CFG=1、1–8 步，不使用负面提示词 | 宽高按 16 对齐 |
| FLUX.2-klein distilled | euler / flux2、CFG=1、1–4 步，不使用负面提示词 | 宽高按 16 对齐 |
| Qwen-Image 2.1 | euler / flux，保留普通 CFG 与负面提示词 | 宽高按 **32** 对齐；引擎按分辨率计算调度 |
| Wan 2.1 T2V | euler / discrete，默认 CFG=6、flowShift=3 | 宽高按 16 对齐；帧数 **4n+1**，5–129；fps 1–60 |

这些步数、尺寸 64–2048、fps 和 flowShift 范围是当前应用配方 / 保护约束，不冒充模型官方最大能力或手机已测预算。数值支持可编辑预设和归位；例如 Wan 18 帧归位 17，Qwen 宽 1008 归位 992。每模型参数独立保存；任务 `diffusionPlan` 另存有效参数及调整原因，不改写基础模型设置。

四条路线的 `flowShift` 均实际绑定到 `sd_sample_params_t.flow_shift`。**0 表示自动**，原生层映射为上游 INFINITY 哨兵，不能把 0 当作实际流偏移；非零值上限为 32。Z / FLUX / Qwen 默认自动，Wan 默认 3。JSON 中仅使用有限数值。采样器、调度器、负面条件、尺寸和帧数也在原生层复核。

原生加载后核对张量家族名：Z-Image、Flux.2 klein、Qwen Image 2.1、Wan 2.x，防止其他家族进入该路线。**家族检查不能证明 Turbo 训练方法、4B / 9B 或 Wan 1.3B / 14B / 2.2 等共享家族的具体身份。** 精确组件来源 / revision / hash 和真实运行验收仍须逐项核对，不能仅凭模板获得“设备已验证”。

Wan 使用 `generate_video()` 生成运动帧；原生返回数量和 fps 必须与有效请求一致，再由同一手机的 Android MediaCodec / MediaMuxer 编码 MP4。重复静态帧不计完成。生成库会持有全部返回帧，随后还需私有 RGB 文件和 MP4 磁盘空间；512×288 / 17 帧预设不等于已证明手机能承担整条管线。编码、取消与产物可播放性仍需真机验证。

## 检查与证据边界

- 174 项扩散检查：117 项生产 Java / 实际主机子进程协议，57 项执行共享 C++ 策略。覆盖全部必需组件缺失、架构 / 多余组件拒绝、派生参数、用户资产路径 / 词表环境、计划防篡改、采样和几何约束。
- 子进程只写协议 JSON，不生成模型图片；Wan 主机 codec 端口明确拒绝编码，不能据此声称 MP4 生成。没有执行模型张量。
- 基座 425 项（配方 / 完整性 233），UI 203 项；原生 Windows NDK ARM64 构建与签名包检查通过。界面媒体明确标记 UI FIXTURE；不是 Android 安装证明。
- 未完成：精确目标组件的逐一设备输出、质量、资源测量、三次装卸、锁屏 / 长时后台、Android 编码和升级验收。其余 MNN / 音频 / 旧 LTX 等必需管线仍在同一版本范围；不创建缩减 Release。

## 对应源码依据

技术行为按固定 sd.cpp 提交 `be486498eadc29dc3cd234d944c2180ed42b1415` 核对：[Z-Image](https://github.com/leejet/stable-diffusion.cpp/blob/be486498eadc29dc3cd234d944c2180ed42b1415/docs/z_image.md)、[FLUX.2](https://github.com/leejet/stable-diffusion.cpp/blob/be486498eadc29dc3cd234d944c2180ed42b1415/docs/flux2.md)、[Qwen 2.1](https://github.com/leejet/stable-diffusion.cpp/blob/be486498eadc29dc3cd234d944c2180ed42b1415/docs/qwen_image_2.1.md)、[Wan](https://github.com/leejet/stable-diffusion.cpp/blob/be486498eadc29dc3cd234d944c2180ed42b1415/docs/wan.md)。采样默认及家族名来自其 `src/model/integrations`，帧对齐来自 `src/pipeline/diffusion_engine.cpp`。

使用者须按所选模型及各组件的实际许可使用。尤其 [Qwen-Image 2.1 模型卡](https://huggingface.co/Qwen/Qwen-Image-2.1) 标记 Qwen Research License，不能沿用旧 Qwen-Image 的 Apache 说明；本项目代码许可不授予模型权重权限。

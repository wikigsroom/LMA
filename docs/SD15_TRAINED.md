# SD 1.5：真实权重与生产源码主机验证

[English](SD15_TRAINED.en.md) · [扩散基座](DIFFUSION_ENGINE.md) · [编号交付与全部待办](releases/v0.3.0-dev.24.md)

适用 **0.3.0-dev.24 / code 28**。本轮修正生产 worker 的进度阶段，并为现有 SD 1.5 配方补充真实权重验证。主机执行、Android 编译、App 真机执行、质量及后台验收分别记录；单个 SD 1.5 候选不能证明其他生图模型、LoRA 或完整 v0.3.0 已完成。

## 用户逻辑与资产边界

App 仅更新基座，不包含以下文件，也不因安装、升级或浏览而下载模型。用户在“全部 / 搜索”选择候选、查看模型和分词依赖，再明确点击下载；也可从文件夹导入对应文件。在“本地”管理该模型的参数、资产、版本、暂停/续传和删除。“推荐”的 m08 → m06 → m01 保留，生图标签与安装、运行证据、内容标签互相独立。

本次固定候选为 `sd15_ss_q4_0_r031b5f5`，使用 `sd15_cpu_v1` / `sd15` / `sd_cpp` / CPU。完整 checkpoint 含 CLIP、UNet 和 VAE；CLIP 的 merges 必须另外由用户提供。不是任意同名 SD 1.5 文件的兼容性承诺。

| 角色 | 固定来源 | 文件 | 字节 |
| --- | --- | --- | --- |
| model | [second-state/stable-diffusion-v1-5-GGUF，031b5f5…](https://huggingface.co/second-state/stable-diffusion-v1-5-GGUF/tree/031b5f5df991f511b3f5fa8fed6d99048ababb69) | stable-diffusion-v1-5-pruned-emaonly-Q4_0.gguf | 1,566,768,416 |
| clip_merges | [stable-diffusion-v1-5/stable-diffusion-v1-5，451f4fe…](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/blob/451f4fe16113bff5a5d2269ed5ad43b0592e9a14/tokenizer/merges.txt) | tokenizer/merges.txt | 524,619 |

合计 **1,567,293,035 字节**。完整 revision、大小、SHA256 和源许可 CreativeML Open RAIL-M 保留在[候选清单](../catalogue/model-bundles.json)及[开发资产回执](../verification/development/sd15-assets.json)。两文件 SHA256：

```text
model        b8944e9fe0b69b36ae1b5bb0185b3a7b8ef14347fe0fa9af6c64c4829022261f
clip_merges  9fd691f7c8039210e0fced15865466c65820d09b63988b0174bfe25de299051a
```

用户对已完整安装模型选择使用，填写提示词和独立参数，再加入共享本机队列。此次验证使用 512×512、20 步、Euler / discrete、CFG 7、seed 42、4 线程、VAE tiling；这些是验证快照，不会替换用户保存值。后台服务、进度/API、产物和取消由既有共用基座处理。Android 输出和锁屏验收仍须补齐。

## 实现与进度修正

[生产 worker](../native/sd_worker.cpp)通过 stable-diffusion.cpp C API 执行加载、架构检查、分词/CLIP、去噪、VAE 和 PNG 写入；[外部词表适配](../native/vocab_external.cpp)代替上游内置学习词表。没有 Python、桌面推理服务或其他设备回退进入 APK。

上游同一个 progress callback 用于加载张量、采样和 VAE 分块。旧 worker 把所有回调统一标成 `sampling`；dev.24 使其跟随实际顶层 `loading` / `generating` 阶段。`generating` 包括延迟加载、采样和 VAE；其内部 steps 是相应操作的局部进度，不能全部当成扩散步数。该修正没有改变模型运算、采样器或权重。

Windows 测试使用[隔离兼容层](../research/sd_host/NOTICE)编译相同生产 worker、策略和外部词表源，仅为 POSIX 父进程保护提供 Windows 本地实现。它不是 Android 进程或远程后端，不能验证 Android `prctl`、Java Service 或锁屏行为。测试构建固定 sd.cpp `be486498eadc29dc3cd234d944c2180ed42b1415` 和 GGML `a5915eb0e47adef21c3f25b889a008925ea838c2`，CPU，无内置模型数据。

## 验证与媒体

[真实训练报告](../verification/development/sd15-trained.json)保留两条不同提示词、A/B/A 三次完整 PNG、无效请求、真实采样中的取消及恢复、原始请求/日志/PNG 身份和采样内存。取消仅在生成阶段、固定 20 步采样至少完成第 1 步后触发，排除加载和 VAE 回调。A/B/A 使用不同本机子进程，恢复 A 位于取消后；同种子结果比较完整 PNG 字节。

首次尝试确实生成了首张 PNG，但发现旧进度分类会让取消测试在加载阶段触发，因此主动停止该尝试。原文件与原因保留在忽略的开发目录，最终公开验收以修正阶段后的重新执行为准，不把加载中取消算作采样取消。

本轮实际结果如下，耗时包含进程启动、加载和完整生成。内存是 Windows 子进程工作集/私有提交的采样观察，不是 Android 可用内存或 GPU 显存。

| 执行 | 秒 | 观察峰值工作集（字节） | 采样峰值私有提交（字节） | PNG 字节 |
| --- | --- | --- | --- | --- |
| prompt-a | 563.58 | 1,698,885,632 | 513,703,936 | 367,115 |
| prompt-b | 485.46 | 1,698,828,288 | 513,474,560 | 598,785 |
| recovery-a | 549.65 | 1,698,816,000 | 513,548,288 | 367,115 |

三次均记录真实采样 0–20 步和完整 512×512 RGB PNG；A 与恢复 A 的完整文件 SHA256 相同，B 不同。第 1/20 步后触发取消，随后 **0.226 秒**退出，没有完成事件或输出文件；错误 schema、空提示词、线程越界均返回明确错误。后续独立进程重新加载并完整生成 A，通过恢复检查。

人工查看可辨认 A 的红色茶壶与 B 的帆船、蓝色湖面、雪山；B 的树林和山体存在明显纹理/表面瑕疵。这里只记录样图观察，未建立覆盖提示词、细节一致性和伪影的系统质量评分，因此 `semantic_quality_accepted=false` 保留。

![实际训练主机 PNG，不是 Android 截图](media/development/sd15-trained-contact-sheet.png)

[GIF](media/development/sd15-trained-slideshow.gif) / [MP4](media/development/sd15-trained-slideshow.mp4)是实际主机静态图片的展示轮播，**不是 App 录屏、模型生视频或手机推理录像**。[媒体来源回执](media/development/sd15-trained-media.json)绑定真实源 PNG 和公开报告。资源和耗时只代表该主机当时的运行，不能推导努比亚 Z20 的速度、内存可用性或后台时长。生成图片仍需逐项质量验收，不以像素非空和复现性代替质量。

## 开发复现

原生 Windows、MSVC、已取得的固定 sd.cpp/GGML 源码、项目内 CMake/Ninja，以及 Python/Pillow；媒体另需本机 FFmpeg。没有 Docker、WSL、虚拟机或 Android 模拟器。

```powershell
# 明确的开发者资产取得；不属于 App 安装步骤
python tools/fetch_sd15_trained.py --download
# 默认源不通时可显式选择镜像；仍核对固定 revision、完整大小和 SHA256
python tools/fetch_sd15_trained.py --download --origin https://hf-mirror.com
python tools/build_sd_host.py
python tools/test_sd15_trained.py
python tools/render_sd15_trained.py
```

不带 `--download` 只校验已有文件。测试和构建不会下载模型；开发资产、构建、原始输出留在忽略的 `build/`。断点文件绑定同一模型身份，完整校验通过后才原子激活。临时 ASCII 驱动器别名只指向当前工作目录并由创建者释放。

SDK 构建的 `LMA-0.3.0-dev.24-arm64-v8a.apk` 位于本地 dist，保留原签名；它不包含开发权重/词表/输出。没有创建完整 v0.3.0 Release。全部冻结模型、用户资产流程、实际手机输出/质量/资源、3 次加载卸载、15 分钟锁屏、1 小时 API、升级及 A1–A11/R01–R05 继续属于同一版本的必需项。

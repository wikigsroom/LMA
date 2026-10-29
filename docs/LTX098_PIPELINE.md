# 旧 LTX 0.9.8：真实提示词到视频的主机管线

[English](LTX098_PIPELINE.en.md) · [T5](LTX098_TEXT.md) · [采样](LTX098_SAMPLING.md) · [VAE](LTX098_VAE.md) · [同一完整版本范围](MULTIMODAL_RELEASE_PLAN.md)

此管线串联真实用户提示词、完整训练 T5、旧 LTX 2B 0.9.8 distilled 的完整 28 层 DiT / 八步采样、完整训练 VAE 和视频帧封装。它是独立开发工具，尚未注册为 App 引擎。主机输出、Android 编译、App 接入、用户模型获取、画质和真机验收分别记录，不能相互替代。

## 固定方案与来源边界

[管线锁](../third_party/ltx098-pipeline-source-lock.json) 固定单尺度、LinearQuadratic 八步 Euler、CFG=1、STG=0、关闭提示词增强、解码 timestep=0.05 / noise scale=0.025，不启用 tone mapping。它使用固定版本上游代码允许的单尺度路径，**没有复现官方 YAML 的默认多尺度 / 空间上采样 / 提示词增强组合**。

文本资产为此前已独立验证的 `city96/google-t5-v1_1-xxl-encoder-Q5_K_M` 与原始 Google 外部分词配置；官方旧 LTX 默认配置指向 PixArt 的 T5。结构相同不证明权重相同，当前没有做 PixArt 权重身份比较，也没有比较原始未量化 T5。记录和演示都必须保留这一变体标识。该管线继续使用确切旧版 0.9.8 distilled DiT / VAE，不以新 LTX2 或随机小模型替代。

## 执行与数据流

1. 显式开发命令核验已有四个原生执行器和全部 21 份外部模型 / 配置资产的完整 SHA；缺件、变更或旧指纹立即失败，不自行下载。
2. 可移植 C++ 组件产生初始 `[1,N,128]` 高斯噪声，再从同一连续随机流产生 VAE 所需 `[1,128,T,H,W]` 噪声。冻结 RNG 为 SplitMix64 + Box–Muller F32 v1，不承诺与 PyTorch 相同 seed 的位模式一致。
3. T5 仅对真实提示词执行 Unicode `strip()`、分词和最多 256-token 截断，返回逐 token `[1,L,4096]` embedding 和全 1 有效遮罩；没有合成 caption，也没有远程提示词增强。
4. 独立原生 Vulkan DiT 完成全 28 层的八步轨迹，C++ 组件按原始 `SymmetricPatchifier` 顺序还原 NCTHW。
5. 九段原生 ORT CPU VAE 顺序加载 / 执行 / 卸载，先在归一化空间混噪，再通道反归一化，保留原始时间条件和首帧裁剪。
6. C++ 按原始 Diffusers 反归一化、裁剪、乘 255 并截断到 uint8，生成 `LMAFRM1` RGB24 帧容器。该容器与已有 Android `VideoEncoder` 接口一致，尚未在此管线中调用 Android 编码器。
7. **开发主机**使用本机 FFmpeg/libx264 写 MP4，ffprobe 逐项检查 codec / 尺寸 / 帧数 / 帧率。它不是 App 的编码或运行依赖；App 接入仍须在同一手机调用已有 MediaCodec / MediaMuxer。

子进程顺序运行，不同时保留 T5、DiT 和 VAE 执行器。两套不同 GGML 修订通过进程边界隔离；不能直接把同名符号混合链接。每个任务保留独立不可变参数、逐阶段原生结果、资产身份、实际子进程耗时和 Windows 内存观测；这些不是 Android 内存、GPU 显存或整机峰值。失败 / 取消清理未发布的最终帧和视频，保留忽略目录中的诊断中间件。

当前开发 profile 为 64–256 像素、32 的倍数，9–33 帧且为 8n+1，1–60 fps。它约束本实现的验证范围，不表示该低分辨率已经满足视频质量或冻结目标 17 的验收。一次完整任务只生成一个视频，不承诺实时速度。

## 独立验证

[基础检查](../tools/test_ltx098_tensors.py) 将 RNG 与独立标量定义比较，将张量还原与上游原始 patchifier 比较，将完整 RGB 字节与原始 Diffusers 像素转换比较，并覆盖边界、重复键、NaN / Inf、损坏字节数、取消、既有文件保护和失败回滚。它不加载任何训练权重。

[管线检查](../tools/test_ltx098_pipeline.py) 使用两组不同真实提示词和相同噪声，按 A/B/A 顺序运行完整训练模型，检查重复任务逐字节一致、提示词产生实际差异、实际装卸和视频容器。非平坦 / 非静态统计只是结构诊断，不是语义、运动连贯性或画质验收。

[独立完整参考](../tools/ltx098_pipeline_oracle.py) 不调用原生推理执行器：执行未改写的 Transformers T5EncoderModel、发布者 Transformer3DModel / RectifiedFlowScheduler / Decoder 前向。参考直接从固定资产分别还原相同量化 T5 / 转换后 F16 DiT 权重；共享显式噪声输入，从独立文本 embedding 开始传播误差到最终 RGB，不将原生中间输出喂给参考下一层。比较固定门槛为 maxabs ≤ 0.003、relative RMSE ≤ 0.0003、cosine ≥ 0.99999；RGB max ≤ 2、mean ≤ 0.02 字节。门槛事先冻结，失败不能通过放宽数值来标记成功。

## 原生 Windows 复现

先按 T5、采样、VAE 三篇指南显式准备全部固定开发资产、原生执行器和 VAE 导出。以下命令不获取模型，不调用 Docker / WSL / 虚拟机或模拟器。所有缓存、临时文件和结果都留在项目 `build/`。

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:TEMP="$PWD/build/tmp"
$env:TMP="$PWD/build/tmp"
python tools/build_ltx098_tensors.py
python tools/build_ltx098_tensors.py --android
python tools/test_ltx098_tensors.py
python tools/test_ltx098_pipeline.py
```

MSVC 与 Android 构建须顺序执行，使用项目缓存的 CMake / NDK；Android 编译只证明 ARM64/API28/16KiB ELF 可构建，不运行手机、不复制到 APK。管线完整重测会运行三份真实模型任务和两份独立原始前向参考，可能耗时较长，不会自动改小模型或降低门槛。结果分别在 `build/ltx098-tensors-tests/results.json` 与 `build/ltx098-pipeline-tests/results.json`。

## App 与资产生命周期仍需完成

APK 只包含基座代码，不包含训练权重、词表、ONNX 模型数据、通道统计或声音 / 语言资产。当前导出仅为开发者准备测试资产，不是 App 已具备手机端转换或公开一键获取能力。最终引擎必须通过共用 model/component/recipe、能力标签、每模型参数、持久任务和产物管理接入；所有模型平级，不增加模型 ID 专属 UI / 队列分支，也不引入 ComfyUI 画布、节点或插件体系。

用户必须明确选择并下载 / 导入整套依赖，缺件时就地报错。安装、升级、浏览、恢复队列或运行失败均不得触发模型下载；恢复的传输保持暂停。原始检查点约 6.34 GB、转换 DiT 3.85 GB、VAE 2.21 GB、T5 3.39 GB 的磁盘占用需逐项披露；现有文件不可静默替换或删除，移除原始件由用户决定。此处是磁盘字节，不是运行内存要求。

模型许可、量化来源与代码许可分别沿用各组件 [NOTICE](../research/ltx098_pipeline/NOTICE) 和固定锁；T5 的 Apache-2.0 声明不能替代旧 LTX 的独立模型条款。无 ROOT、同一 Android 手机上的全链路执行、实际画质 / 资源门槛、每模型三次装卸、15 分钟锁屏、1 小时交替 API、升级保留与 A1–A11 / R01–R05 仍是完整 v0.3.0 必需项，不以主机演示关闭。


## 已执行的主机任务与基础组件

2026-10-29：基础组件 157 检查 /43 原生进程 /31 防护通过；独立 RNG 标量对照最大误差为 0，三组原始 RGB 对照逐字节相同。主机 helper 为 164,352 字节；Android helper 为 426,272 字节，API28 /16KiB，依赖仅 libc / libm / libdl，尚未进入 APK。

| 任务 | 提示词 | 含组件加载的任务耗时 | 输出 |
| --- | --- | --- | --- |
| 1 | A：红气球 | 1410.89 秒 | 256×256 /33帧 /24fps |
| 2 | B：蓝色玩具车 | 574.40 秒 | 256×256 /33帧 /24fps |
| 3 | A：重复 | 398.16 秒 | 256×256 /33帧 /24fps |

任务计时不包含整套资产预先 SHA 核验或独立原始参考，不能作为手机或固定缓存条件的速度基准。21 份运行资产共 9,448,036,748 字节；三次任务的 Windows 子进程峰值工作集最大值分别为 T5 3,651,268,608、DiT 1,221,013,504、VAE 1,279,008,768 字节。DiT 的进程私有提交量不等于 GPU 显存；未测 GPU 显存或整机峰值。

抽查可辨识红气球 / 蓝色玩具车，随时间有变化；这不证明指定方向的运动准确、连续动作、完整质量或 Android 验收。正式完整链路精度结论以单独导出的开发 JSON 为准，所有模型资产仍留在忽略目录。


## 固定精度验收：当前未通过

完整验证记录为 **163 项检查：157 通过、6 项浮点门槛未通过**。三次训练任务、A/B/A 位重复、独立原始前向与产物均已执行；这不等于完整数值验收通过。两组的 TNC latent、对应 NCTHW latent、最终解码浮点帧各有一项失败，共六项；两个文本 embedding 与两个最终 RGB 对照通过。

| 指标 | 红气球 A | 蓝色玩具车 B | 固定上限 |
| --- | --- | --- | --- |
| latent 最大绝对误差 | 0.00830925 | 0.00499147 | 0.003，未通过 |
| latent relative RMSE | 0.000394183 | 0.000305552 | 0.0003，未通过 |
| 解码浮点最大误差 | 0.00375907 | 0.00617547 | 0.003，未通过 |
| RGB 最大字节误差 | 1 | 1 | 2，通过 |
| RGB 平均字节误差 | 0.00607022 | 0.00381639 | 0.02，通过 |

额外同输入诊断将 A 的独立原始 T5 embedding 送入原生 Vulkan DiT，八步最终 latent 最大误差降至 0.00172329、relative RMSE 为 0.0000833611，落在原门槛内。这提示文本编码微小误差被采样放大是主要贡献之一；它仅是同 caption 的 latent 诊断，不能替代完整链路或质量验收。诊断保留八步输出、12 个捕获文件的尺寸 / SHA 和真实子进程资源。

`test_ltx098_pipeline.py` 会先写出完整通过 / 失败记录，再对数值失败返回 **exit 1**；不放宽门槛、不把出片记为精度通过。`--reuse-native` / `--reference` 可重新核对本机已捕获且源指纹仍有效的任务 / 参考，每个输出重验 SHA，记录明确标注复用和本次实际执行数量。当前公开记录复用本轮三次真实任务与两份参考，校验重放没有再次推理。

开发仓库审计通过仅说明代码 / 证据 / 媒体及失败状态一致，不会覆盖该失败。`ltx098_complete_prompt_to_video_host_executed=true`，`ltx098_complete_prompt_to_video_host_tested=false`，`ltx098_full_chain_numeric_accepted=false`；App / 物理 Android / 质量 / 完整 Release 也继续为 false。下一步需改进跨文本编码 / 采样的数值稳定性，再按相同门槛重测。

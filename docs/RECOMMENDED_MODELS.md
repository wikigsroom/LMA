# 推荐模型与首次使用 · v0.3.8

[English](RECOMMENDED_MODELS.en.md) · [使用手册](USER_GUIDE.md) · [发布说明](releases/v0.3.8.md)

模型页默认进入“推荐”，共有 **14 个条目**：生文 3、生图 3、生视频 2、生音频 3、生 3D 3。原有生文 `m08 → m06 → m01` 的顺序、标签和来源保持在前；新增 11 个是现有 82 套已登记目录包的精选子集，没有增加权重到 APK。推荐与“全部”“本地”使用相同模型身份和管理流程。

## 1. 推荐列表

以下体积为十进制 MB / GB，取固定目录中所有必需组件之和；共享组件可复用，实际剩余下载量以模型详情为准。下载体积不是运行内存。名称中的精度不表示所有伴随组件均使用相同精度。

| 编号 | 功能 | 模型 / 配置 | 完整下载量 | 基座 / 后端 | 选择理由与条件 | 内容标签 |
| --- | --- | --- | --- | --- | --- | --- |
| M01 | 生文 | Qwen3 1.7B Abliterated · `m08` | 1.11 GB | llama.cpp / CPU | 原有中文推荐 | 保留原有声明 |
| M02 | 生文 | LFM2.5 1.2B Uncensored · `m06` | 731 MB | llama.cpp / CPU | 原有轻量推荐 | 保留原有声明 |
| M03 | 生文 | Dolphin3 Qwen0.5B Uncensored · `m01` | 约 400 MB | llama.cpp / CPU | 原有小容量推荐 | 保留原有声明 |
| M04 | 生图 | [SD-Turbo Q8_0](https://huggingface.co/Green-Sky/SD-Turbo-GGUF) | 2.02 GB | sd_cpp / CPU | 少步数，512 像素起步 | 不新增 NSFW 声明 |
| M05 | 生图 | [Realistic Vision 6.0 B1 FP16](https://huggingface.co/SG161222/Realistic_Vision_V6.0_B1_noVAE) | 2.47 GB | sd_cpp / CPU | SD1.5 写实风格，包含配套 VAE | NSFW · 来源声明 |
| M06 | 生图 | [AbyssOrangeMix2 NSFW FP16](https://huggingface.co/WarriorMama777/OrangeMixs) | 2.13 GB | sd_cpp / CPU | SD1.5 插画风格 | NSFW · 来源声明 |
| M07 | 生视频 | [Wan2.1 1.3B Q4](https://huggingface.co/off-grid-ai/Wan2.1-T2V-1.3B-GGUF) | 4.74 GB | wan_sd_cpp / Vulkan | 量化短片，需要较大内存 | 不新增 NSFW 声明 |
| M08 | 生视频 | [NSFW Wan EXP E14](https://huggingface.co/NSFW-API/NSFW_Wan_1.3b) | 6.76 GB | wan_sd_cpp / Vulkan | 社区变体，需要较大内存 | NSFW · 来源声明 |
| M09 | 生音频 | [MeloTTS Chinese INT8](https://huggingface.co/csukuangfj/vits-melo-tts-zh_en) | 60.6 MB | sherpa_tts / CPU | 中文 / 英文朗读，单女声 | 不新增 NSFW 声明 |
| M10 | 生音频 | [Kokoro82M INT8 English](https://huggingface.co/csukuangfj/kokoro-int8-multi-lang-v1_0) | 148.7 MB | sherpa_tts / CPU | 已适配英文多音色 profile | 不新增 NSFW 声明 |
| M11 | 生音频 | [OmniVoice Q8 GGUF](https://huggingface.co/audio-cpp/audio.cpp-gguf) | 1.35 GB | audio_cpp / CPU | 自动 / 参考音色 / 音色描述 | 不新增 NSFW 声明 |
| M12 | 生 3D | [TRELLIS.2 geometry512](https://huggingface.co/ilintar/trellis2-gguf) | 2.63 GB | trellis_native / CPU | 单图生成无贴图 GLB，长任务 | 不新增 NSFW 声明 |
| M13 | 生 3D | [TRELLIS.2 PBR512](https://huggingface.co/ilintar/trellis2-gguf) | 4.20 GB | trellis_native / CPU | 单图生成 PBR GLB，长任务 | 不新增 NSFW 声明 |
| M14 | 生 3D | [Pixal3D geometry512](https://huggingface.co/vegax87/Pixal3D) | 6.62 GB | trellis_native / CPU | 单图几何进阶，需要较大内存 | 不新增 NSFW 声明 |

两个视频条目属于同一个 Wan2.1 1.3B 架构的不同权重选择；TRELLIS 几何与 PBR 也是不同配置，不作为不同架构计数。Pixal3D 包复用 TRELLIS 编码器，各组件来源独立保留。Kokoro 本条目只开放已适配的英文 profile；OmniVoice 的多语言控制不表示所有语言已验。

## 2. 用户操作

1. 启动或升级后进入“模型 → 推荐”。功能按钮显示推荐数量；点击只筛选列表，所有模型平级。
2. 查看模型详情，检查功能、架构、运行基座、组件、许可、固定版本、SHA256、体积和资源提示。NSFW 是独立来源标签，不是输出检测或画质结论。
3. 用户点击“下载”才下载所选包与已披露必需组件；共享文件经校验复用。浏览、筛选、查看详情、安装和升级均不下载。缺资产时不隐式补下载。
4. 在“本地”管理下载、暂停 / 继续、校验、删除、导入及该模型独立保存的参数。推荐页和本地页始终指向相同包。
5. 下载完成后选择“使用”，填写功能表单，选择本机参考图 / 音频，检查资源和匹配资产后明确提交。视频先用低分辨率短片；3D 必须提供参考图，几何与材质配置不同。计算和媒体处理均在同一手机。
6. 其他模型在“全部”或 HF 搜索中发现；82 套登记包和完整 HF 发现流程保留。HF 可发现不等于任意架构可执行。

## 3. 选取标准与验证边界

优先选择已有完整 HTTPS 固定组件来源、现成 Android 基座、共用管理入口及用途明确的模型包。推荐数量、任务与体积由 `recommendations.json` 对实际目录自动核对。视频 / 3D 的高资源提示随卡片显示。推荐不是手机性能排名，不承诺 Z20、X30 或当前手机完成全部模型。

本轮检查推荐顺序、分类数量、固定包身份、独立标签、无自动下载、显式下载路由、全部 / 本地管理、缺元数据回退及窄屏布局；实际 Android 检查分类页面和零模型接口。按用户要求不下载、复制或运行完整训练权重，生成质量、耗时、峰值 RAM、温度和长期锁屏推理未测。

## 4. 页面与复现

[桌面分类 GIF](media/development/recommendations/recommendations-ui.gif) · [MP4](media/development/recommendations/recommendations-ui.mp4) · [媒体身份](media/development/recommendations/manifest.json) · [实际手机生图页](media/device/v0.3.8/02-recommended-image.png) · [真机记录](DEVICE_ACCEPTANCE.md)

```powershell
python tools/recommendations.py
node tests/ui-smoke.cjs
node tools/capture_workbench.cjs recommendations
```

桌面演示标记 UI FIXTURE，下载命令使用模拟桥；真机演示不点击下载或运行模型。浏览器页面和录制服务在完成后关闭。各模型 / 组件独立许可和[第三方条款](../THIRD_PARTY_NOTICES.md)继续适用。

# Z-Image-Turbo：完整本地模型与用户流程

本指南保留 dev.38 的固定主机实验；完整报告按原字节归档。当前开发见 [Wan](WAN_VIDEO.md)。

[English](ZIMAGE_TURBO.en.md) · [模型选择](CURATED_DIFFUSION.md) · [组件建议](COMPONENT_SUGGESTIONS.md) · [接口](API.md) · [本轮交付与完整待办](releases/v0.3.0-dev.38.md)

适用 dev.38 / code42。App 只更新基座；Z-Image-Turbo 是可选的平级生图模型，不随安装、升级或浏览自动下载。推荐 m08→m06→m01 保留。源码、真实 Windows CPU 执行、页面夹具与 Android ARM64 编译分别留证；独立完整数值、画质、资源和物理手机验收尚未完成，不能据此认定努比亚 Z20 可运行或可持续后台。

## 1. 选择和取得组件

在“模型 → 全部”按生图筛选，打开 **Z-Image-Turbo · Q4_0 + Qwen3-4B**，查看四组件、完整大小、固定版本与哈希；再自行点击下载，或明确选择完整文件夹导入。也可在 HF 搜索打开仓库，选择 `z_image_turbo_split_cpu_v1` 配方，逐个选择匹配组件后登记，再单独下载。

完整运行文件共 **6,349,991,011 字节**。本方案使用原 Qwen3-4B（官方配置 40960 上下文 / rope_theta 1000000）和官方完整 16 通道 VAE；不会暗中换为 Instruct-2507、FLUX.2 VAE 或小型解码器。其他模型变体须用户核对自己的匹配方案。上述上下文配置用于核对编码器版本；图片提示词仍受到实际管线和 App 输入约束。文件名建议只帮助选择，不证明张量兼容、许可或手机可用。

| 编号 | 角色 | 固定来源 / 文件 | 字节 | SHA-256 |
|---|---|---|---:|---|
| 1 | `diffusion` | [z_image_turbo-Q4_0.gguf](https://huggingface.co/leejet/Z-Image-Turbo-GGUF/resolve/c61c0e422dc8b541b7548cf33a4ef8302b0f8085/z_image_turbo-Q4_0.gguf) | 3,683,370,944 | `2bc57986874c84f7ec6d02d9d7070a53b0029954a0e38a6e1342eb91095572f5` |
| 2 | `llm` | [Qwen3-4B-Q4_K_M.gguf](https://huggingface.co/unsloth/Qwen3-4B-GGUF/resolve/22c9fc8a8c7700b76a1789366280a6a5a1ad1120/Qwen3-4B-Q4_K_M.gguf) | 2,497,281,312 | `f6f851777709861056efcdad3af01da38b31223a3ba26e61a4f8bf3a2195813a` |
| 3 | `vae` | [vae/diffusion_pytorch_model.safetensors](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo/resolve/f332072aa78be7aecdf3ee76d5c247082da564a6/vae/diffusion_pytorch_model.safetensors) | 167,666,902 | `f5b59a26851551b67ae1fe58d32e76486e1e812def4696a4bea97f16604d40a3` |
| 4 | `qwen_merges` | [tokenizer/merges.txt](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo/resolve/f332072aa78be7aecdf3ee76d5c247082da564a6/tokenizer/merges.txt) | 1,671,853 | `8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5` |

模型按生图 / 文生图 / 蒸馏采样和 sd_cpp / z_image / CPU 等标签筛选，不增加未经核对的无审查标签。缺件时本机明确报错；不自动补下载，不转给其他设备。

## 2. 本地管理与独立配置

下载完成后在“模型 → 本地”查看状态、暂停/续传、导入、更新/回滚或删除。参数按不可变模型 ID 保存，使用可直接编辑的预设输入框；超限归位，不修改其他模型设置。

| 参数 | 本方案 | 边界含义 |
|---|---|---|
| 宽 / 高 | 默认 1024；64–2048，16 对齐 | 管线对齐及 App 保护，不是所有尺寸画质或内存已验收 |
| 步数 | 默认 8；1–8 | 当前蒸馏采样策略 |
| CFG / 负面提示词 | 固定 1 / 不支持 | 无负面条件或隐式适配器 |
| 采样 / 调度 | Euler / discrete | 与选定管线绑定 |
| 线程 | 默认 4；1–64 | App 范围，实际速度由设备决定 |
| 种子 | 默认 −1；−1–2147483647 | −1 请求随机；固定种子记录到执行信息 |
| flow shift / VAE 分块 | 默认 0 自动 / 开启 | 偏移 0–32；编码、采样及解码均在本机 |

运行中的资产和配置受租用保护；结束后恢复编辑。编辑新任务不改变已提交任务的提示词、模型、参数或组件。

## 3. 提交、取消、恢复和结果

选择本地模型，填写提示词，复核运行前检查，再加入共用本机队列。模型准备和生成使用已有前台服务、通知、资源检查及任务 API；不会因为提交任务而下载模型。完成后先检验 PNG，再保存结果和不可变来源。取消或失败不发布半成品；再次执行是用户明确提交的新任务。重启后读取已提交结果；删除模型保留既有结果和保留的独立设置。

内容哈希相同的组件可以复用。例如已经由用户取得的匹配 Qwen3-4B 和词表，无需再次存储相同对象。复用文件不会自动安装目录中的另一个模型，也不会自动开始生成；下载计划显示可复用和仍缺少的大小。

## 4. 分词、证据与复现

Z-Image 官方 `tokenizer.json` 的完整 SHA 与已独立验证的 Qwen 参考文件相同；merges 文件也完全一致。共用读取器在内存处理 HF 文件头、BOM / CRLF 和 NFC，原始文件及 SHA 不变。已验证 151,643 个基础词项、26 个特殊词项、33 组文本和三种表示，共117检查；这不能代替完整模型数值或画质验收。

- [实际原生执行](../verification/history/0.3.0-dev.38/zimage-trained.json)：完整组件、不同提示词/步数、真实采样取消、错误、恢复与 Windows 资源观测。
- [生产 Java/native 流程](../verification/history/0.3.0-dev.38/zimage-app-host.json)：完整导入、独立配置、租用、不可变任务、实际生成/取消/恢复、PNG 来源、重启和删除模型。
- [实际产物及展示记录](media/development/zimage-trained/manifest.json)、[界面录制记录](media/development/curated/manifest.json)、[分词独立对照](../verification/history/0.3.0-dev.38/qwen-tokenizer.json)。

![实际 Windows CPU 图片展示；非 Android 录屏](media/development/zimage-trained/zimage-trained.gif)

GIF / MP4 展示真实 PNG，不能用来推断生成时间或手机性能；页面录制带 UI fixture 标记。所有完整 v0.3.0 目标和原始失败继续保留。

```powershell
python tools/fetch_zimage_trained.py --download --reference-tokenizer
python tools/test_zimage_trained.py
python tools/test_zimage_app_host.py
python tools/render_zimage_trained.py
```

默认不带 `--download` 只核验本地文件。测试不联网取模型；`--execute-only` 只保存实际 Java 采集，随后 `--verify-run build/zimage-app-host-tests/run-…` 核对源码、原生构建、原始产物和直接执行结果，无需重复推理。原生 Windows 开发不用 Docker / WSL / 模拟器。四组件之外的完整 tokenizer.json 仅为开发参考，不属于运行包，也不进入 App。

各模型文件的 Apache-2.0 许可声明来自对应固定版本作者页面；[官方模型卡](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo/blob/f332072aa78be7aecdf3ee76d5c247082da564a6/README.md)、量化发布者与 App / 引擎许可分别保留。


## 5. 本轮主机观测

512×512、seed42、6线程、CPU；a / b / recovery-a 为8步，one-step为1步。开发测试并发运行，时间和内存仅记录本次 Windows 主机过程，不能据此认定努比亚 Z20 的最低内存、速度、温控或后台耐久。

| Case | Seconds | Observed peak working set (MiB) |
|---|---:|---:|
| a | 867.06 | 5912.2 |
| b | 1099.03 | 5911.6 |
| one-step | 316.90 | 5911.3 |
| recovery-a | 1327.24 | 5912.6 |

采样第1/8步取消后未保留半成品；恢复与初次同参数PNG逐字节一致。不同提示词和步数得到不同实际图片；这些检查不等于完整画质或独立数值验收。

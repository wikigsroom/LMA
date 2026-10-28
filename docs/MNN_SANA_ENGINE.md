# Sana 移动管线与 MNN 本地引擎

[English](MNN_SANA_ENGINE.en.md) · [完整版本需求](MULTIMODAL_RELEASE_PLAN.md) · [HF 组件选择](HF_RECIPES.md) · [开发状态](DEVELOPMENT.md)

内部检查点 **0.3.0-dev.14 / code 18** 接入真实 MNN CPU worker 和 Java 任务绑定。它是编号 04 允许的“明确匹配的 MNN 移动变体”路线，**不是原版 Sana 600M 的通用加载器**。已完成原生编译、主机协议和 APK 检查；没有 Android 生图、质量、速度、内存或后台耐久证据，也未发布完整 v0.3.0。

## App 基座与用户资产

APK 只增加 MNN 引擎代码、数据配方、参数与许可。没有权重、模型 tokenizer、meta queries 或音色数据。原有推荐 `m08 → m06 → m01` 不变；新模板不会被自动下载。

在“全部 / 搜索”打开 HF 文件，选择 `Sana mobile · Qwen3 + MNN`，逐项选择匹配版本的 13 个组件。登记清单后查看完整下载计划，再由用户点击下载；也可导入已取得并能通过校验的文件。“本地”管理独立设置、暂停 / 续传、更新、导入与删除。浏览、升级 App、缺文件或提交任务均不会隐式下载模型。

配方标签为 `task:image`、`text_to_image`、`engine:mnn_diffusion`、`pipeline:sana_mnn_v1`、`backend:cpu`，组件格式为 `mnn / mnn_data / json / text`。它与文本、音频、视频模型平级；组件齐全、引擎可用和真机验证是不同状态。没有根据模板自动添加无审查标签。

## 匹配关系与完整组件

参考是官方 [MNN-Sana-Edit-V2](https://huggingface.co/taobao-mnn/MNN-Sana-Edit-V2)，所检查的元数据提交为 `dd5955b4e63359b5822fa29a3b3711a112212046`。这是匹配关系的参考，**不是内置下载地址或已完成推理的模型**。用户仍要核对所选版本与各组件许可；已检查的模型卡标为 Apache-2.0。

| 组件角色 | 运行时受控文件名 |
| --- | --- |
| `diffusion / diffusion_data` | `models/transformer.mnn / transformer.mnn.weight` |
| `connector / connector_data` | `models/connector.mnn / connector.mnn.weight` |
| `projector / projector_data` | `models/projector.mnn / projector.mnn.weight` |
| `vae / vae_data` | `models/vae_decoder.mnn / vae_decoder.mnn.weight` |
| `llm / llm_data` | `llm/llm.mnn / llm.mnn.weight` |
| `llm_config` | `llm/llm_config.json`，只读取并白名单重建 |
| `tokenizer` | `llm/tokenizer.txt`，匹配 MNN 格式 |
| `meta_queries` | `llm/meta_queries.mnn` |

MNN 图与同名 `.weight` 必须对应同一导出。此配方只实现文生图，不自动获得源模型的图像编辑、图生图或 LoRA 能力；不需要 VAE encoder，也不接受任意外部 `config.json`。普通 Sana、SD 的 VAE、通用 HF tokenizer 或不同 Qwen3 导出不能因文件格式相同而互换。

## 手机内执行与参数

1. 原生工作进程按匹配的 Qwen3-0.6B 格式编码文本，追加 256 个 meta queries；CFG 启用时编码正负两个分支。格式后的输入必须落在用户的 token 预算内，超出时报错，不静默截断。
2. 检查编码结果为 `[1 或 2, 256, 1024]` 浮点特征，复制成独立常量后释放编码器，再加载 connector、projector、transformer 和 VAE decoder。
3. 使用上游实际的特征输入采样路径生成并保存 PNG；任务队列沿用同一手机的单引擎执行槽、后台通知、取消、模型引用保护与产物校验，没有远程执行或降级。

| 模型独立参数 | 范围 / 默认 |
| --- | --- |
| 宽 / 高 | 256–2048，32 对齐；默认 512；是实现边界，最高值不等于手机资源可承受 |
| 采样步数 | 1–50，默认 10 |
| CPU 线程 | 1–32，默认 4；传入编码器及扩散执行 |
| 输入 token 预算 | 1–1792，默认 512；包括格式提示词，另保留 256 个 meta queries |
| `useCfg / cfg` | 默认关闭 / 强度 4，强度限制 0–30；负面提示词要求显式启用，增加批次和资源开销 |
| 随机种子 | -1 自动生成或 0–2147483647；生成前记录实际种子 |

界面继续使用模型独立的可编辑预设。通用参数校验与 Sana 管线再次归位并固定本次 `diffusionPlan`；执行前重算核对快照。归位不覆盖保存的模型偏好，修改设置只影响后续任务。原生代码再次检查边界。

## 配置隔离与构建

用户模型 metadata 只提取 Qwen3 类型、1024 hidden size、float/full attention 和经过文件范围校验的 tied embedding 布局；不执行 Jinja，也不合并 `base_dir`、文件名、缓存、网络或其他任意配置。LMA 生成固定相对路径的 CPU config。运行目录是已校验且持有引用的组件硬链接，不复制多 GB 权重、不改写安装文件；工作进程实际退出后才清理，异常重启再对账孤立目录。

MNN 固定为 [35a20ca](https://github.com/alibaba/MNN/tree/35a20ca0995bb7e4a549b7def42c4acb30559a94)。使用原生 Windows NDK r30 / CMake / Ninja 构建 API 28、ARM64、16 KiB 对齐的 `liblma-mnn.so`，不调用 Docker、WSL 或模拟器。生成覆盖文件加入加载失败检查、token 上限、线程绑定和组件完整性检查；上游 Git checkout 保持干净。CPU 构建关闭 HTTP resource、Logcat、OpenCL、Vulkan、ARM82 与 OpenMP。子进程只输出结构化事件，避免上游将提示词和私有路径输出到日志。

```powershell
python tools/fetch_mnn.py
python tools/build_mnn.py
python tools/collect_mnn_notices.py
python tools/test_mnn.py
python tools/build.py
python tools/verify_package.py
```

前提沿用[构建说明](BUILD.md)，包括已准备好的固定 sd.cpp JSON header、Windows NDK / CMake、Java 与测试 JSON jar。源代码 / header / 许可 / ELF 的哈希均有锁定；源码构建工具不下载模型。主机 C++ 检查需要 MSVC。

## 验证边界

74 项 Sana 检查覆盖生产 Java 配方 / 参数 / 配置、真实主机协议子进程、硬链接及延迟清理和 15 项共享 C++ 参数策略。子进程故意只写标记为 `JSON_NOT_AN_IMAGE` 的协议夹具，不运行 MNN 或模型，不能作为生成图片证据。另有通用后端、HF 元数据、界面、Lint、APK 和资产分离检查。

![Sana 组件页面，明确的 UI FIXTURE](media/development/36-sana-mobile-components.png)
![Sana 独立参数页面，明确的 UI FIXTURE](media/development/37-sana-mobile-parameters.png)

截图、[录屏](media/development/foundation-ui.mp4)和 [GIF](media/development/foundation-ui.gif)均为实际 HTML/CSS/JS 配合显式演示桥接，未安装或运行模型。参考模型全部组件的离线 Android 新输入生图、重复装卸、质量、资源、锁屏 / 长时间后台及升级仍是同一个完整 v0.3.0 的必过项目。

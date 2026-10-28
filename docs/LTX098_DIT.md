# 旧 LTX-Video 0.9.8：原生 DiT 组件

[English](LTX098_DIT.en.md) · [文档导航](README.md) · [编号交付与待办](releases/v0.3.0-dev.21-ltx-dit.md)

本次实现服务于冻结目标 **17：LTX-Video 2B 0.9.8 distilled**。它是尚未接入 App 的原生 DiT 研究组件，不能作为完整生视频支持。开发 APK 仍为 **0.3.0-dev.21 / code 25**，公开 Release 仍为 **v0.2.0**。全部 F-01–F-12、01–14 / 16 / 17 及子目标继续属于同一个完整 v0.3.0。

## 1. 固定架构与来源

| 项目 | 固定内容 |
| --- | --- |
| 发布者源码 | [Lightricks/LTX-Video](https://github.com/Lightricks/LTX-Video/tree/4b2d053057623ddd4d0a1d3e9cd28890e9ef487f)，Apache-2.0 |
| 原始检查点 | [ltxv-2b-0.9.8-distilled.safetensors](https://huggingface.co/Lightricks/LTX-Video/blob/8984fa25007f376c1a299016d0957a37a2f797bb/ltxv-2b-0.9.8-distilled.safetensors)；本轮只读取固定文件头，不读取训练张量 |
| DiT 结构 | 28 层、隐藏宽度 2048、32 个注意力头、头宽 64、输入 / 输出 128、文本宽度 4096；715 张量、1,923,385,472 参数 |
| 原生计算 | 固定 GGML `a5915eb0e47adef21c3f25b889a008925ea838c2`；独立 C++ 图；显式 CPU 或 Vulkan，无自动 CPU 回退 |
| 资产格式 | 独立 GGUF 标识 `lma-ltx-video-098`；F32 或仅密集权重 F16，其余参数 F32；尚无生产模型转换器 |
| 构建 | 原生 Windows MSVC / NDK r30；项目内 CMake、Ninja、Vulkan / SPIRV headers、新版 shaderc；无虚拟化环境 |

[源码锁](../third_party/ltx098-source-lock.json)记录源码 / 依赖文件 SHA256、检查点头与完整布局摘要、Python oracle 版本，以及 Windows shaderc 的来源和散列。Google 发布的未签名 SLSA 声明与下载 ZIP 摘要、源码提交一致；没有声称验证发布者签名。编译器只留在忽略的开发缓存中。

本轮未使用 LLM-Hub 的实现；其许可单独核查。[stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp) 中较新的 LTX2 管线也没有被当成旧 0.9.8 的实现。源代码许可和模型的 LTXV Open Weights License 0.X 分开处理，见 [NOTICE](../research/ltx098/NOTICE) 与完整许可文本。

## 2. 实际实现

`research/ltx098/` 提供加载、图构建、后端执行和原始 velocity 输出：

1. 核对架构标识、旧版常量、全部张量名称 / 形状 / 编码及完整文件字节范围；生产形状固定，小尺寸夹具必须显式 `--fixture`。
2. 实现输入投影、双层 caption 投影、256 维时间嵌入与 AdaLN 六组调制；支持全局或逐 token sigma。
3. 实现完整 28 层自注意力、交叉注意力、QK RMSNorm、三轴 RoPE、遮罩、残差、GELU FFN、最终 LayerNorm / 投影。RoPE 在拆头之前作用于完整隐藏维，保留旧版布局与最大位置常量。
4. 用显式浮点 tanh 公式避免 CPU GELU 半精度查表；物化连续注意力矩阵，并要求浮点累加。当前 Vulkan 采用浮点 shader，禁用该进程内会降低输入精度的 cooperative / F16 arithmetic 路径；F16 权重仍可存储并在 GPU 上计算。性能尚未评估。
5. 采用 RAII 释放权重、后端、图和计算缓冲。限制 token、文本、线程、sigma、遮罩、非有限输入，拒绝覆盖已有输出；未编译的 Vulkan 请求明确失败。

执行器仅接受本地路径和 JSON，不包含网络 / shell 调用。输入要求已编码的 caption、latent、位置和 sigma；输出是 **原始浮点 velocity**，不是图片、视频或已采样 latent。

## 3. 独立验证与边界

`tools/ltx098_fixture.py` 导入锁定的官方 `Transformer3DModel` 原始实现。首先在 meta device 上实例化完整模型，核对 715 张量 / 1,923,385,472 参数的布局与实际检查点文件头一致，然后以固定随机种子生成未训练的小宽度网络。

| 检查 | 实际覆盖 | 不能据此得出的结论 |
| --- | --- | --- |
| 官方前向对照 | 2 / 3 / 28 层，宽度 24 / 32；全局时间、逐 token 时间、文本遮罩与被遮罩文本扰动 | 不是完整宽度训练 checkpoint 的推理 |
| 双精度路径 | F32、F16 密集权重分别与官方浮点前向比较；F16 oracle 先按同样权重格式舍入 | 不代表任意量化格式兼容 |
| 双后端 | 真实原生 CPU 与 NVIDIA RTX 3060 Vulkan 子进程；显式记录设备及计算策略 | 不是 Android GPU / Z20 实测 |
| 固定精度门槛 | F32 最大误差 ≤ `1e-4`、RMSE ≤ `3e-5`；F16 最大误差 ≤ `.005`、RMSE ≤ `.001` | 没有测视频质量、速度、热量和峰值 RSS |
| 防护 | 缺失 / 额外张量、错误配置、截断文件、shape / sigma / mask / 线程越界、无 fixture 许可、后端回退与输出覆盖 | 尚未构成生产用户资产解析器的完整安全验收 |
| Android | ARM64 / API28 / 16 KiB ELF 编译与依赖核对单独记录 | 编译不等于手机执行、无 ROOT 后台或完整视频可用 |

固定 GGML Vulkan 后端要求 **Vulkan 1.2**；cm2 着色器另有 1.3 路线，本组件禁用该路线。Android API28 仅是编译下限，不能据此认定旧手机驱动兼容。努比亚 Z20 的驱动能力、可用内存与完整管线资源仍须实测；没有机型支持结论。

具体数字、每项误差与范围见 [原生比对证据](../verification/development/ltx098-transformer.json)、[Android 构建证据](../verification/development/ltx098-transformer-arm64.json)和[编号交付](releases/v0.3.0-dev.21-ltx-dit.md)。这些证据保持 `trained_weights_loaded / video_outputs / engine_registered / physical_android / complete_video_pipeline = false`。

## 4. 复现

在原生 Windows PowerShell 中，从仓库根目录运行。需要已有项目工具链与 CPU torch / numpy；精确版本见源码锁。Python 依赖、下载缓存、编译器与临时文件必须留在本项目 `build/`。准备步骤是开发者显式执行的代码 / 工具获取，不是 App 的后台模型下载。

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:TEMP=Join-Path $PWD 'build/tmp'
$env:TMP=$env:TEMP
python tools/fetch_native.py
python tools/fetch_ltx098.py --python-dependencies
python tools/test_ltx098.py
python tools/build_ltx098.py --android --vulkan
python tools/export_development.py
python tools/check_repository.py --development
```

`test_ltx098.py` 顺序构建 / 复用经当前指纹核对的主机 CPU、Vulkan 执行器，运行真实子进程和官方 oracle；失败时不会留下通过报告。模型夹具、原始输出与日志只在 `build/ltx098-tests/`。原生构建通过临时 SUBST 使用 ASCII 路径，在 `finally` 中移除自己建立的盘符；不得并行启动这些构建。`--cpu-only` 只用于排错，不能满足当前双后端证据检查。

## 5. 产品需求与完整待办

APK 仅更新基座。后续用户仍从平级模型列表按需选取、下载、导入、更新、回滚和删除资产。安装 / 升级 / 浏览 / 缺件不自动下载；参数跟随模型，任务持有不可变快照；推荐 m08 → m06 → m01 保留。

目标 17 的功能标签继续为 **生视频**，基座标签为 **ltx_video_098**，后端路线为 **ltx_vulkan_port / ltx_qnn_port**，另附格式、设备、许可、证据与内容标签。两条路线需要各自的设备 / 包格式兼容性证据，不能因为有 QNN 包或主机 Vulkan 就启用另一条路线；本研究组件尚未注册上述 App 运行支持。

| 编号 | 待完成事项 | 完成标准 |
| --- | --- | --- |
| P-01 | 完整用户资产与转换 | 精确旧版 DiT、T5 / tokenizer、匹配 VAE 的固定来源 / 格式 / 校验和 / 许可，用户显式下载或导入；无数据进入 APK |
| P-02 | 完整同机视频管线 | 文本编码、实际 latent 坐标 / 时间处理、蒸馏采样、VAE 解码、帧与 MP4 编码、顺序生命周期、资源预算和取消 |
| P-03 | 训练权重与质量 | 全尺寸真实 checkpoint 对照、新输入视频、画质、资源和设备范围；当前缩小宽度数值检查不能替代 |
| P-04 | App 接入 | 独立参数、资产依赖 / 兼容标签、共用队列 / API / 产物 / 取消及迁移；不引入节点画布或插件生态 |
| P-05 | Android 与发布 | 逐管线真机、3 次加载卸载、15 分钟锁屏、1 小时交替 API、升级保留、A1–A11 / R01–R05；全部冻结模型和子目标同版通过后发布 |

已知没有可用 Android 真机。该事实保持在待验收记录中，不把桌面输出、Android 编译或 UI FIXTURE 当作手机视频实录。此次无 App 页面修改，沿用 dev.21 的真实界面夹具截图 / 录屏 / GIF，未制作或展示伪造的视频生成演示。

# 本机 PBR 贴图基座

[English](LOCAL_MATERIALS.en.md) · [形状 / 精修](SPATIAL_SHAPE.md) · [F5 中文前端](F5_FRONTEND.md) · [完整待办](REMAINING_ADAPTATION.md)

开发代码已接入 `hunyuan3d_21_paint`，与形状模型平级。它给用户选定的 GLB 制作参考图驱动的 PBR 贴图，输出含 albedo、metallic-roughness 两张 PNG 和新 UV 的自包含 GLB。此内容尚未发布为 APK；下载页的 v0.3.5 不包含这条 Paint 路线。

## 1. 应用使用闭环

| 编号 | 操作 | 行为 |
| --- | --- | --- |
| M01 | 准备并导入同批匹配资产 | 配置、采样程序、五组 ONNX 及其外部数据，实际 SHA256 校验；无已核实公开整包，不虚构下载按钮 |
| M02 | 模型 → 本地 | 管理该包文件、独立参数、删除与恢复；安装和浏览不自动取权重 |
| M03 | 导入输入 | 一张 RGB / RGBA PNG、一份自包含静态 GLB；可选用已有本机形状任务结果 |
| M04 | 编辑该模型参数 | CPU 线程、步数、种子、引导、UV 图集尺寸、RealESRGAN 4× 开关；超限归位 |
| M05 | 预检 / 草稿 / 提交 | 缺参考或缺网格不提交；草稿记录明确输入；预检不启动生成 |
| M06 | 共用后台任务 | 条件渲染、编码、UniPC 采样、解码、可选增强、UV 烘焙全在同一手机 |
| M07 | 取消 / 失败 | 等待子进程结束后清理执行目录，不提交不完整 GLB，不调用外部服务 |
| M08 | 结果管理 | 校验 GLB 后原子提交；App 内显示内嵌基础色、金属 / 粗糙度与 UV，支持旋转、缩放和完整 GLB 导出 |

功能标签为 `3d / mesh_texturing / image_conditioning / multi_view_material / pbr_material / uv_baking`；基座为 `spatial_ort / cpu / onnx`。内容分级独立标记，不将贴图架构默认认定为 NSFW 或无审查。原推荐 `m08 → m06 → m01`、HF 全部搜索和其他模型包保留。

## 2. 实际运行组成

| 组件 | 固定接口与用途 |
| --- | --- |
| `material-config.json` | 固定发布者源码、图像尺寸、六视图、DINO 与 VAE 配置，最多 64 KiB |
| `sampler.json` | 固定 Diffusers 0.35.1 的线性 UniPC 更新系数，1–100 步可编辑，最多 8 MiB |
| `image_encoder.onnx` | DINOv2 1536 维特征；图像归一化和裁切在 C++ |
| `vae_encoder.onnx` | 每张参考 / 法线 / 位置图的后验均值与 logvar；手机用所选种子采样 |
| `flow.onnx` | 双 PBR、参考 UNet、材质 / 多视图注意力、位置 RoPE、DINO 投影；三路参考引导 |
| `vae_decoder.onnx` | 逐视图解码 albedo 和 MR |
| `upscale.onnx` | 配套 RealESRGAN x4plus，逐张本地增强；关闭增强时仍保留明确选定的完整资产包 |
| 每个 `.onnx.data` | 仅同名配套外部数据，不接受任意路径、脚本、用户插件或网络执行 |

固定来源为 Hunyuan3D 2.1 `82920d643c0dc2f7bfd7255f45f62d386edfe60c`、BasicSR `651835a1b9d38dbbdaf45750f56906be2364f01a`。不会执行上游带下载器或 CUDA 初始化的整套 Python 管线。

源推理默认使用 **UniPC / trailing / 15 步**，本实现保留此路径及用户自选步数。配置中的模型输出转换、历史缓存、predictor / corrector、低阶启动与收尾由固定库对独立基向量求得，再在 C++ 执行。修复该库在 1000 训练步 / 61 推理步时额外产生 `-1` 时间步的浮点端点问题，保留准确的 61 个有效步。

## 3. 共享几何与资源边界

- 固定六个正交视角、发布者反射 / 居中 / 缩放变换，CPU 深度遮挡、面法线和位置图；PNG 白底合成。
- xatlas 生成 UV，按视角权重与法线余弦四次方融合；深度检查排除遮挡。未观察的 UV 和边缝以最近可见 texel 填充。事件保留覆盖 / 未观察数量，不将填充表述为神经补全。
- 模型 MR 的 R（金属度）/ G（粗糙度）转换为 glTF B / G；两张 PNG 内嵌，原始坐标和网格形状保留。
- 图像导出为 64–512、64 的倍数，潜变量为图像尺寸的 1/8；六视图固定，UV 目标 256–4096。xatlas 实际图集大小可能接近目标但不完全相等。
- 输入 PNG 最多 16 MiB / 4,194,304 像素，网格最多 30 万三角面。限制 UV / 光栅工作量、图集尺寸、图字节数及模型数据；图按阶段依次驻留。
- 增强后六视图总像素最多 16,777,216；512 导出应关闭 4× 增强。超过保护范围明确失败，用户调整本模型参数。

这是独立 CPU 光栅 / 烘焙实现，未逐像素复刻 CUDA raster、全部边界腐蚀、草图排除和上游纹理修补；原生高斯随机流也不与 PyTorch 逐位相同。它提供可执行的 Paint 路径，不能据此声称原论文质量、完整后处理一致性或 Z20 可承受全部权重。图仍可能超过手机 RAM，程序检查不替代真实设备测量。

## 4. 用户明确选择的离线转换

准备电脑只用于资产转换，手机推理期间无需连接它。所有输入来自用户已有本地文件；工具不拉权重、不执行任意配置 target，不使用普通 pickle 构造。

```powershell
python tools/fetch_spatial_sources.py
python tools/fetch_paint_sources.py
python tools/export_paint.py `
  --unet my-assets/paint/unet `
  --vae my-assets/paint/vae `
  --dino my-assets/dinov2-giant `
  --scheduler my-assets/paint/scheduler/scheduler_config.json `
  --upscaler my-assets/RealESRGAN_x4plus.pth `
  --image-size 320 --output my-assets/lma-paint
```

UNet / VAE 目录分别包含匹配 `config.json` 与唯一 `.safetensors` 或 weights-only `.bin` 权重；DINO 只接受本地安全张量目录。RealESRGAN 读取 weights-only `params_ema` / `params`，严格核对全部键与形状；不以随机或遗漏权重补缺。

工具最后写出 `lma-bundle.json` 与导出记录，包含实际字节数、SHA256、来源身份和导出范围。复制到手机后导入清单及明确组件。转换时会运行用于描图的虚拟前向；不把它表述为完整模型生成验收。

预览只读取内嵌 PNG，不请求外部贴图；最多 128 MiB GLB、8 个贴图 / 1,677 万总像素、单边 4096。基础色按 sRGB 处理，金属和粗糙度使用 B / G 通道；简单 GGX 光照用于交互查看，不是专业离线渲染。超出范围可导出查看。关闭结果窗口时释放图片、纹理、缓冲区、画布事件和 WebGL context。

## 5. 验证

| 程序范围 | 已通过 |
| --- | --- |
| 独立射线对照、UV、遮挡、PNG / GLB、错误分支 | 61 项 |
| 100 组采样步数、原始网络 → ONNX、真实工作器两种增强模式、负向请求 | 227 项 |
| 共用 Java 导入 / 参数 / 子进程 / 取消 / 回收及旧路线回归 | 592 项 |
| 实际离线转换 CLI、真实组件哈希和禁止覆盖 | 17 项 |
| 生产页面、素材角色、独立参数、草稿、幂等队列、实际 PBR 像素 / UV / 资源回收 | 新增 34 项；全页面 687 项 |
| Android 原生编译 | ARM64 / API28 / 16 KiB；无网络或外部进程导入 |

全部使用小型随机网络或确定性程序输入，未获取或运行完整训练模型。当前检查报告位于 `build/material-tests/`、`build/paint-tests/`、`build/expansion-tests/`。最终版本还要统一更新全部证据指纹、媒体和发布包，不能用 v0.3.5 的旧汇总替代当前提交验收。

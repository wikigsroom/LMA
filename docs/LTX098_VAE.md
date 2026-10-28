# 旧 LTX 0.9.8：训练 VAE 解码

[English](LTX098_VAE.en.md) · [文本编码](LTX098_TEXT.md) · [采样](LTX098_SAMPLING.md) · [完整同版范围](MULTIMODAL_RELEASE_PLAN.md)

冻结目标17仍是 **LTX-Video 2B 0.9.8 distilled**。本组件处理去噪 latent 到原始 RGB 浮点帧；文本编码、DiT、VAE、视频封装、App 绑定、输出质量和手机验收分别记录。开发主机执行不替代同一 Android 手机完成全部阶段的要求。

## 1. 固定资产与许可

- 原始检查点：`Lightricks/LTX-Video`，revision `8984fa25007f376c1a299016d0957a37a2f797bb`，`ltxv-2b-0.9.8-distilled.safetensors`，6,340,744,492字节，SHA-256 `76aa8c4786af752fa6f951947129d5290c3c6c0b2fadcadea6b5e114ae2cad8f`。
- 只读取132个 `vae.decoder.*` 张量、552,814,641个参数及两个通道统计张量。原始BF16参数显式转为F32；不加载VAE encoder，不用随机权重替代训练权重。
- 原始实现：Lightricks source revision `4b2d053057623ddd4d0a1d3e9cd28890e9ef487f`，Apache-2.0。权重使用 **LTX-Video Open Weights License 0.x**，与代码许可不同。固定身份、完整布局、配置、数值门槛见[锁文件](../third_party/ltx098-vae-source-lock.json)。
- 导出的ONNX及其external-data属于模型资产，**不进入APK或Git**。当前导出是开发者离线验证工具，尚不代表用户一键下载候选或手机端转换能力。App更新只提供基座，用户仍自行选择、下载、导入、更新、删除模型。

## 2. 解码顺序

1. 在归一化latent空间先混合显式噪声：`mixed = latent * (1 - noise_scale) + noise * noise_scale`。
2. 以原始 `std-of-means` 与 `mean-of-means` 反归一化；不能换成 `mean-of-stds`，也不能先反归一化再混合。
3. 非因果Conv3D在时间两端复制边界帧，空间零填充；像素归一化沿通道维计算。带时间条件的残差块使用训练的 `timestep_scale_multiplier`、时间嵌入和scale/shift表。
4. 三次时空上采样每次去掉首帧，时间长度为 `2*T-1`。最后空间unpatchify倍率4。输入 `[1,128,T,H,W]` 输出 `[1,3,8*(T-1)+1,32*H,32*W]`；例如 `[1,128,3,2,2] → [1,3,17,64,64]`。
5. 输出保留原始NCTHW F32帧，没有额外色调变换、裁剪或视频编码。固定配方默认 `timestep=.05`、`noise_scale=.025`、tone-map compression `0`。噪声由调用者显式提供，当前CLI不宣称实现完整管线的随机数约定。

## 3. 九段顺序执行

| 编号 | 段 | 内容 | 权重生命周期 |
| --- | --- | --- | --- |
| V-01 | stage00 | 混噪、通道反归一化、conv_in | 单段会话 |
| V-02 | stage01 | 1024通道、5个带时间条件的残差单元 | 最大块：300,980,224参数，另共享标量 |
| V-03 | stage02 | 时空上采样，1024→512 | 上一段先卸载 |
| V-04 | stage03 | 512通道残差块 | 上一段先卸载 |
| V-05 | stage04 | 时空上采样，512→256 | 上一段先卸载 |
| V-06 | stage05 | 256通道残差块 | 上一段先卸载 |
| V-07 | stage06 | 时空上采样，256→128 | 上一段先卸载 |
| V-08 | stage07 | 128通道残差块 | 上一段先卸载 |
| V-09 | stage08 | PixelNorm、时间条件、SiLU、conv_out、unpatchify | 完成后卸载 |

CPU ONNX Runtime会话复用[现有研究辅助层](../research/soulx_ort/runtime.hpp)；只执行这里的VAE网络，不调用SoulX音频网络。使用API17表、单段生命周期、关闭CPU内存arena及memory pattern、执行中取消。主机ORT1.24.3与Android ORT1.28.2分别固定；Android产物只依赖现有 `libonnxruntime.so` 及系统库。

每段一个ONNX和一个数据sidecar，共18个外部文件。CLI核对固定布局、文件尺寸、路径和IO；外部引用必须落在声明的同目录sidecar内。**当前研究CLI本身不计算资产SHA**：离线测试在执行前逐文件核对完整SHA；未来App集成还必须接入已有资产完整性管理，不能把CLI尺寸检查称为内容校验。

## 4. 复现

在仓库根目录使用原生Windows工具，临时文件留在仓库 `build/tmp`；不使用Docker、WSL、模拟器或其他设备推理。开发者先按[采样指南](LTX098_SAMPLING.md)显式取得固定原始检查点；下列命令不会自动下载任何模型。

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:TEMP="$PWD/build/tmp"
$env:TMP="$PWD/build/tmp"
python tools/ltx098_vae.py export
python tools/ltx098_vae.py references
python tools/build_ltx098_vae.py
python tools/build_ltx098_vae.py --android
python tools/test_ltx098_vae.py
```

导出器拒绝覆盖已有模型目录；需要重做时显式指定新的 `--output`，并管理自己生成的开发资产。独立参考直接执行**未修改的原始 `Decoder.forward`**，其hook记录conv_in及七个up block，最终帧另行记录；导出包装器不是参考实现。

CLI：`lma_ltx098_vae BUNDLE REQUEST.json OUTPUT.f32`。请求支持 `operation:decode`、本地 `latents/noise` 文件、`latent_shape`、`timestep`、`noise_scale`、`threads` 以及可选取消文件和全新trace目录。固定batch1/128通道；研究边界T=1…5、H/W=1…8、threads=1…32，并不表示所有对应分辨率已通过手机性能验收。既有输出不会覆盖；失败或取消不保留最终产物。

数值门槛在训练VAE推理前固定：最大绝对误差≤0.002、相对RMSE≤0.0002、cosine≥0.999999、所有值有限。不同时间/空间尺寸、时间条件和噪声比例，逐段及最终帧与独立原始实现比对。Windows子进程资源观察不包含GPU/系统总量，不可作为努比亚Z20的内存或速度数据。

## 5. 交付边界

| 编号 | 层级 | 本组件涵盖 | 仍须完成 |
| --- | --- | --- | --- |
| P-01 | 源码 | 九段F32导出、原生CPU执行、独立原始参考和数值/生命周期测试 | 持续按实际检查记录标注结果 |
| P-02 | 模型 | 固定训练VAE及通道统计 | 完整提示词到视频、种子/后处理、代表性视频质量和资源门槛 |
| P-03 | Android | ARM64/API28编译与ELF检查 | 原生链路、App注册、用户公共资产候选、安装后自主下载闭环 |
| P-04 | 手机 | 无真机证据 | 各模型3次装卸、15分钟锁屏、1小时交替API及升级保留 |
| P-05 | Release | 不新增APK或Release | 同版F-01–F-12、既有生文、01–14/16/17及全部冻结子目标、A1–A11/R01–R05 |

模型标签保持平级：`生视频`是输出能力，`T5 / DiT / VAE / ONNX Runtime / CPU / F32 / ARM64`分别描述依赖或执行条件；`host验证 / Android仅编译 / 未完成手机验收`是不同证据状态。是否无审查为独立有来源的内容标签，不能从视频类型或模型名称推断。


## 6. 本轮验证结果

**355项检查 /36个真实原生子进程 /31项防护通过**。四组训练解码几何为17×64×64、1×32×32、17×32×64、9×64×32；40个逐段 /最终误差记录通过固定门槛，最终输出与stage08 trace分开核对。最大中间绝对误差 `1.1444091796875e-4`，最大最终帧误差 `2.1457672119140625e-6`，最大相对RMSE `2.4708418913210748e-6`，最小cosine `0.9999999999969488`。44个参考文件和18个模型图 /数据在执行前逐一核对尺寸与完整SHA。

五次完整原生解码（含一次重复）共45次图执行；训练权重下的实际计算中取消再执行一段、在第二段中断，合计46次成功图执行。所有报告的会话装卸平衡，最多同时存在一个会话；真实ORT终止计数1。取消测试使用较大的5×4×4 latent和单CPU线程，在Run开始后触发，不能以预先设置标记代替。

| 项目 | 实测范围 | 限制 |
| --- | --- | --- |
| 原生CPU耗时 | 四组CLI约7.40…15.46秒，含九段加载/卸载和trace落盘 | SHA检查已暖文件缓存；不是冷启动或手机速度 |
| Windows进程 |20ms采样共1402点；observed peak working set最大1,238,388,736字节，sampled peak private最大92,758,016字节 | mapped权重与private不是同一口径；不是手机 /GPU /系统总量，采样可能遗漏末段 |
| 主机CLI |217,088字节；SHA `abfa7108963be7a2be1d91b7c81b7643f783be913885ee8741e5573fdc10e550` | 仅开发主机 |
| ARM64 CLI |504,400字节；SHA `da89cbac98b1e7feba625b9c2f425a507a5f898f0f1542570999c0b1b22e15a1` | API28/16KiB编译；依赖ORT及系统库；不在APK，未执行 |

[数值与生命周期记录](../verification/development/ltx098-vae.json) / [主机构建](../verification/development/ltx098-vae-host.json) / [Android编译](../verification/development/ltx098-vae-arm64.json) / [编号交付与完整待办](releases/v0.3.0-dev.21-ltx-vae.md)。这不新增提示词视频、质量、App或手机验收结论。

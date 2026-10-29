# 旧 LTX 本地视频业务链路

[English](LTX098_APP_FLOW.en.md) · [编号交付与完整待办](releases/v0.3.0-dev.30.md) · [完整版本要求](MULTIMODAL_RELEASE_PLAN.md)

内部 **0.3.0-dev.30 / code 34** 将旧 LTX 的本地组件连接到生产队列、模型独立设置和结果库。新增的是运行基座，APK 不含视频权重、T5、分词配置或 VAE 数据。新配方明确标记为实验状态：原数值门槛仍有失败，视频质量、手机资源及 Android 运行尚未验收。

## 1. 用户操作

1. 从“全部 / 搜索”选择确切的旧 **LTX 2B 0.9.8 distilled** 源模型，用户自行下载或导入；不可用 LTX 2/2.3 等其他架构替代。
2. 在“本地 → 源模型 → 运行资产”明确准备 DiT 和九段 VAE。任务进入共用队列，可以取消；源文件保留，不会静默更新或替换。
3. 准备完成后选择 **旧 LTX · Google T5 Q5 单尺度生成** 的关联方案。它建立新记录 `ltx098_runtime_google_q5_v2`，复用已准备文件。旧 `v1` 资产记录与设置保持原样，不会自动变成可生成模型。缺少的 T5 / 分词配置继续显示为未完成，由用户选择下载或导入。
4. 完整安装后，在该模型的“模型设置”中编辑预设输入框。宽高最高 256、32 倍数；帧数 9/17/25/33；帧率 1–60；线程 1–8；种子 -1 为自动；蒸馏固定八步。超限归位，联合约束在提交和执行前再次检查。设置只影响之后的任务。
5. 点“使用”，填写完整提示词，复核本机资源及实验状态，明确提交。队列依次显示噪声、提示词编码、视频采样、潜变量布局、解码、媒体编码与保存。可离开页面查看其他模型，或取消任务。
6. 成功后从结果库预览、导出 MP4、查看来源或编辑再生成。失败、取消或服务中断不会把部分张量或半成品发布为成功结果，也不会自动从头重跑。

模型与其他生文、生图、生音频模型平级，以“生视频”、所需基座与安装状态分别标记。推荐顺序 m08→m06→m01、HF 发现和其他模型设置保持原逻辑。不提供远程推理或外部编码回退。

| 明确的变体与资产 | 模型独立参数 |
|---|---|
| ![模型状态，界面测试数据](media/development/ltx/01-model-profile.png) | ![独立设置，界面测试数据](media/development/ltx/02-model-settings.png) |

| 明确提交 | 共享队列与取消 |
|---|---|
| ![视频表单，界面测试数据](media/development/ltx/03-video-request.png) | ![视频队列，界面测试数据](media/development/ltx/04-video-queue.png) |

[页面录屏](media/development/ltx/ltx-ui.mp4) · [GIF](media/development/ltx/ltx-ui.gif) · [媒体清单](media/development/ltx/manifest.json)。这些是生产页面与明确标识的桌面桥接测试数据，不是手机或模型演示。

## 2. 同手机执行结构

`Ltx098Engine` 使用共用模型租约、不可变任务和受管工作区，顺序启动固定的签名组件：

| 阶段 | 本机后端 | 阶段间数据 |
|---|---|---|
| 确定种子、生成初始噪声 | 原生 CPU | 有限大小的 F32 文件 |
| Google/community T5 XXL Q5_K_M 编码 | 原生 CPU | token / mask / caption 文件 |
| 完整 28 层 DiT、八步采样 | Vulkan | 采样潜变量文件 |
| unpatchify | 原生 CPU | NCTHW 文件 |
| 九段 VAE 依次加载、运行、卸载 | ONNX Runtime CPU | 解码 F32 文件 |
| RGB 帧转换 | 原生 CPU | 有界帧流 |
| AVC 编码、结果检查与提交 | Android MediaCodec / 结果库 | MP4 与来源记录 |

上一个进程退出并回收后才进入下一阶段，避免 T5、DiT、VAE 同时占用模型内存。大张量不进入 Java JSON；每阶段检查协议收据、退出码、形状、精确字节数及有限数值。取消与服务关闭停止自有进程，释放租约、硬链接和中间文件。Android 子进程额外使用父进程退出信号。模型文件不能提供执行命令或插件。

这仍需要较大存储、内存及支持 Vulkan 的手机。顺序卸载不等于努比亚 Z20 已可用；不能用桌面 GPU 的结果推断手机速度或承载能力。前台服务与锁屏保活仍受 Android / 厂商管理，完整长时间验收保留在同一版本要求内。

## 3. 精确支持边界与验证

当前新增配方 `ltx098_single_scale_google_q5_v1`：单尺度、Google/community 量化 T5、CFG=1、STG=0、LinearQuadratic 八步 Euler、VAE timestep 0.05 / noise 0.025。它**不等于官方 PixArt T5 / 多尺度默认管线**。旧科学验证的六项数值失败、LCM 的像素失败等均保留；生产业务接通不改变这些门槛。

`tools/build_ltx098_app.py` 只使用锁定的已有源码构建四个 Windows / Android ARM64 组件，不获取模型；`tools/package_ltx098_app.py` 复核并打包代码与已有共享库。`tools/test_ltx098_app.py` 运行实际生产 Java 队列与适配器，普通模式使用合成神经阶段协议及三个真实张量子阶段，覆盖成功、错误收据、错误输出、编码失败、取消及中断。`--trained` 只接受已有完整本地资产，逐个校验大小 / SHA；主机使用明确的 FFmpeg 编码测试端口，Android 产品使用 MediaCodec。两者的执行证据必须区分。

当前执行记录、精确断言数量、APK 身份与未完成项见[本轮检查表](releases/v0.3.0-dev.30.md)及[证据索引](../verification/development/status.json)。所有训练质量、官方变体与真机要求仍属于一个完整 v0.3.0，不移到后续版本。

## 4. 本轮实际训练模型输出

完整 **9,448,043,488 bytes / 22 组件**逐个校验后，由实际生产 Java 队列执行六个原生子阶段，38 项训练链路检查通过。256×256、33 帧、24 fps、种子 42 的输出为 **17,738 bytes** MP4。七个中间文件和该视频与原主机原生基线逐字节相同，说明业务接入保留了既有运算；原独立数值比较的六项失败保持原样，不能据此宣布数值或质量验收通过。

![实际主机输出第 0 / 16 / 32 帧，非手机结果](media/development/ltx-app-trained/frames.png)

[完整原始 MP4](media/development/ltx-app-trained/video.mp4) · [带 HOST 标签的 GIF](media/development/ltx-app-trained/preview.gif) · [媒体清单](media/development/ltx-app-trained/manifest.json)。原视频 SHA256：`67c56a3c362fa2df106451179e275a0bbd50ca7aefe699535ba8665516ecad1d`。此处是桌面实际模型结果，使用 FFmpeg 编码端口；不代表 Android MediaCodec 已执行。

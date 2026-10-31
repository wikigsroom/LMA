# 多视图 3D 与本机诊断 · v0.3.3

[English](MULTIVIEW_DIAGNOSTICS.en.md) · [使用手册](USER_GUIDE.md) · [实现](IMPLEMENTATION_V033.md) · [版本说明](releases/v0.3.3.md)

本版继续补齐可进行程序验证的开发：新增真正的 Pixal3D MV 运行器、四视图输入与相机检查、可选组件导入，以及失败任务也保留的运行观察。单图 TRELLIS.2 / Pixal3D、四类语音和原有全部基座继续保留。APK 不带模型，不自动取得任何模型资产，全部实际执行阶段均在同一 Android 手机。

## 1. 已实现范围

| 编号 | 实现 | 明确边界 |
| --- | --- | --- |
| M01 | `pixal_multiview` CPU / ARM64 引擎，调用上游真实 `trellis_run_mv` | 四图特征投影与融合；不是四次单图生成拼接 |
| M02 | 四张带 alpha 的 PNG、标准转台或自定义相机 | 不包含自动去背景、自动相机估计、任意照片集对齐 |
| M03 | F16 / Q8 × 仅几何 / PBR 四个平级可选模型包 | **校验导入方案**；尚未核实可公开下载的对应权重端点 |
| M04 | 独立参数、草稿、预检、明确提交、队列与 GLB 结果 | 复用原有任务与资源保护，不增加远程执行或 ComfyUI 界面 |
| M05 | 阶段耗时、支持 worker 的进程峰值 RSS、失败记录持久化 | 程序观测，不代表画质、完整模型数值或后台耐久通过 |
| M06 | 省电 / 待机 / 后台限制 / 通知状态与显式诊断导出 | 系统限制可见，不保证 Android 永不停止进程 |

总计 **82 个模型包、45 个配方模板、15 个扩展引擎＋既有文本引擎**。推荐仍为 `m08 → m06 → m01`。所有模型平级，任务、基座依赖、内容依据、取得方式与安装状态分开标记。没有根据 3D 架构猜测 NSFW 或 Uncensored 属性。

## 2. 取得匹配权重

| 编号 | 模型包 ID | 组件 |
| --- | --- | --- |
| M03a | `pixal3d_mv_f16_geometry_v1` | F16，7 个必需组件 |
| M03b | `pixal3d_mv_f16_pbr_v1` | F16，9 个必需组件 |
| M03c | `pixal3d_mv_q8_0_geometry_v1` | Q8_0，7 个必需组件 |
| M03d | `pixal3d_mv_q8_0_pbr_v1` | Q8_0，9 个必需组件 |

固定版本的文件名、大小和 SHA256 来自[上游模型清单元数据](../research/multiview/model-manifests.json)，见[四个模型包](../catalogue/multiview-bundles.json)与[来源说明](../catalogue/multiview-bundle-evidence.json)。这是**发布者清单身份**，本轮未取得或测量完整权重。未把同名单图 flow 或其他 GGUF 当成 MV 权重。

1. 在“模型 → 全部”找到 Pixal3D MV，打开“查看并导入”。页面标记“校验导入”，不显示可用的一键下载来源。
2. 如果已合法持有与该包精确身份匹配的文件，在组件管理中逐一导入。程序检查字节数与完整哈希；错误文件不会成为已安装组件。
3. 如果后来在 HF 找到匹配 MV 的文件，可使用 `pixal3d_mv_gguf_cpu_v1` 自选数据配方，逐个检查架构、布局和许可后主动选择。HF 搜索结果不因此获得本目录的已核对身份。
4. APK 安装、升级、查看模型或预检都不会补齐权重。没有匹配文件时，本功能不能完成模型生成，不能把这个限制隐去。

必需布局：`dinov3.gguf`、`pixal3d_naf.gguf`、`ss_dec.gguf`、`shape_dec.gguf`、`pixal3d_ss_flow_mv.gguf`、`pixal3d_shape_flow_512_mv.gguf`、`pixal3d_shape_flow_1024_mv.gguf`。PBR 另外需要 `tex_dec.gguf` 和 `pixal3d_tex_flow_1024_mv.gguf`。文件名相同不代表不同发布包的解码器哈希相同；按组件清单选取。

这些组件依然达到 GB 量级。磁盘下载总量不是工作内存需求；没有据此证明 6 / 8 GB 努比亚 Z20 足够运行。

## 3. 四视图操作

1. 在“本地”选中完整安装的 MV 模型，点“使用”。分别选择 **正面、右侧、背面、左侧** 四个本机输入。各文件必须为 **8-bit RGBA PNG、最多 16 MiB、最多 4,194,304 像素**；JPEG 和不带 alpha 的 RGB PNG 不适用。输入应已去背景且对应同一物体。
2. 留空相机参数时使用标准转台：四个方位、零仰角、水平 FOV **20°**、距离 **3.119204998**，尺度由 `meshScale` 指定。输入照片必须与该相机约定相符；仅按文件名排列真实手持照片不会自动校准。
3. 有标定数据时，填写四帧 `cameraPoses` JSON，顺序与四个输入完全一致。矩阵为上游使用的 camera-to-world 约定；每帧只允许 `transform_matrix` 和弧度 `camera_angle_x`，不接受路径、URL 或其他额外字段。
4. 编辑模型独立设置，超限自动回填；保存设置只影响该模型。草稿保存四张输入、相机和有效参数，但不继承运行授权。
5. 预检检查真实文件、组件、相机、参数与资源；它不执行模型。对于没有本机测量记录的方案，由用户明确选择尝试，再提交到共用队列。
6. 成功后在结果库预览 / 导出 GLB 与生成记录。几何预览有界，完整 PBR 资源保存在 GLB；这不是全功能 PBR 渲染器。取消、失败后清理私有临时图片链接、相机 JSON 和附属网格文件。

| 参数 | 本程序范围 |
| --- | --- |
| resolution | 固定 1024；不能将 MV 切成现有单图 512 管线 |
| threads / steps | 1–16 / 每阶段 1–50 |
| faces / atlas | 简化目标 1,000–150,000；图集 256–2048，步进 256 |
| maxTokens | 稀疏 token 保护 1,024–49,152，默认 8,192；越小越可能限制生成结构 |
| guidance / meshScale | 0–15 / 0.1–10 |
| texture | 几何包默认关闭；开启前需完整贴图组件 |
| cameraPoses | 最多 16,000 字符；四个有限 4×4 刚体矩阵，右手旋转、非原点位置；FOV 在 0 与 π 之间 |

这些是应用与已移植实现的范围，不是所有模型的理论极限。面数是简化目标，不保证任意网格恰好达到目标。

## 4. 本机 API

先按[本机输入协议](LOCAL_INPUTS.md)取得四个 PNG 的 `artifactId`。以下为请求主体；先 `POST /v1/jobs/preflight`，审阅后再带当前 Bearer 密钥与新的 `Idempotency-Key` 提交 `POST /v1/jobs`。

```json
{
  "bundleId": "pixal3d_mv_q8_0_geometry_v1",
  "type": "mesh.generate",
  "input": {
    "prompt": "Generate one 3D asset from four posed local views.",
    "artifacts": [
      {"role": "reference_front", "artifactId": "IMPORTED_FRONT_ID"},
      {"role": "reference_right", "artifactId": "IMPORTED_RIGHT_ID"},
      {"role": "reference_back", "artifactId": "IMPORTED_BACK_ID"},
      {"role": "reference_left", "artifactId": "IMPORTED_LEFT_ID"}
    ]
  },
  "parameters": {"resolution": 1024, "steps": 12, "maxTokens": 8192, "texture": false},
  "allowUnmeasured": true
}
```

`prompt` 是固定的任务描述，不是文本生 3D。`allowUnmeasured` 仅对应用户已明确同意的尝试，不绕过缺件、相机或资源硬错误。自定义相机是 `parameters.cameraPoses` 的 JSON **字符串**，根对象只有 `frames` 数组；四帧的格式为 `{"camera_angle_x":0.34906585,"transform_matrix":[[1,0,0,0],[0,1,0,0],[0,0,1,3],[0,0,0,1]]}`。此单帧仅用于说明字段；实际四个矩阵必须与四张图逐一对应，不应重复这个示意位置当作真实四视图。

## 5. 观察与诊断

`audio_cpp`、`trellis_native`、`pixal_multiview` 的 worker 在正常完成或可捕获错误时报告 `lma.worker-observations/1`：总耗时、最多 64 个阶段耗时，以及 Android `getrusage(RUSAGE_SELF)` 的进程峰值 RSS。Windows 程序检查明确记为 RSS 不可用，没有编造 RAM 数值。

**RSS 是该 worker 进程的峰值，不是全 App、所有子进程合计或模型所需的最低内存。** 其他引擎继续使用已有共用资源观察，不据此声称每条引擎都新增了 native RSS。系统强杀或直接取消可能来不及发送最终 worker 观察；已收到的执行信息、任务时间和共用资源采样仍保留。

同一任务的后续观察会合并保存，保留先前的 pipeline / backend 身份，合并后仍受 16,000 字符限制。失败、重启后可读取已持久化观察；重试是新任务，不继承旧的测量值。实际推理结果仍独立记录组件身份和有效参数。

在“服务”中可查看当前 Android 的省电、待机、后台活动限制和通知状态。通过原有“导出日志”动作**主动**导出时，新增 `lma.runtime-diagnostics/1`，只含最近 64 条任务的白名单观察、版本和设备状态，不含该诊断对象中的提示词、模型参数、文件路径或密钥。原有日志部分仍需使用者检查与脱敏；这里没有声称整个日志导出都已匿名化。无自动上传。

## 6. 程序检查与重建

```powershell
python tools/fetch_multiview_sources.py --fetch
python tools/build_multiview.py --host
python tools/build_multiview.py
python tools/collect_expansion_notices.py
python tools/test_expansion.py
python tools/test_multiview.py
node tests/ui-smoke.cjs
node tools/capture_workbench.cjs multiview
```

前置为[完整原生 Windows 工具链](BUILD.md)、固定 sd.cpp 的 JSON 头与 Python / JDK / MSVC。构建器只取固定源代码，不执行模型；临时盘符只在空闲字母上创建，`finally` 释放，不修改用户已有 `S:`。

固定 [pixal3d.cpp](https://github.com/raven38/pixal3d.cpp/tree/d1b4926452f9e09702b891db5f05acc845e153ed) 与 [ggml](https://github.com/pwilkin/ggml/tree/737e88f25d4f62254f3b7a726fd9663036cc94da)。生成补丁提取真正 MV 入口、连接步数 / 简化目标 / 阶段事件、强制 token 保护，并修正 MSVC 所需捕获；保留原始与生成文件 SHA，不改上游 checkout。APK 编入 CPU 计算、相机投影、稀疏融合与 GLB 导出，排除服务器、自动下载、CUDA / Vulkan 和安装器。

新增专门的 **63 项**检查包括实际上游相机 / 投影函数和 **12 个真实 native 进程拒绝路径**。共用扩展套件覆盖实际生产 Java、MV 成功 / 失败子进程夹具、临时目录清理、执行信息合并持久化与诊断字段筛选。UI 另有 **19 项**交互，四组当前媒体共 20 张截图 / 4 GIF / 4 MP4。模型组件和 GLB 为有界合成夹具；未执行完整训练模型、未运行 Android 模拟器 / 真机。

## 7. 其余测评模型仍需什么

[本次固定源码审计](../research/portability/audit-v0.3.3.json)逐项复核 D04–D12 的 README / 安装依赖，不安装或执行它们。D03 已新增四视图子集；其他 **9 条配置 / 8 组架构家族**仍需要实际 Android 原生移植，不能以本次测试替代开发：

| 编号 | 模型 | 对应开发缺口 |
| --- | --- | --- |
| D04 | UltraTex | 网格输入、G-buffer、BTD/BSA 稀疏注意力与配套 diffusion/VAE、贴图烘焙 |
| D05 | UniForge3D | VGGT 位姿、anchor 多视图融合、稀疏几何解码；现有 CuMesh / FlexGEMM / nvdiffrast 依赖需移植 |
| D06 | UltraShape | 粗网格输入、体素查询 / RoPE 精修、独立 surface extraction |
| D07 | Hunyuan3D 2.1 | 匹配 shape flow / VAE / 网格后端；Paint 是另外的运行通道 |
| D08–D09 | SAM 3D / MV-SAM3D | 掩膜 / 深度条件、稀疏与布局算子；MV 还需 Depth Anything 3 和场景融合 |
| D10 | SUPRA-Tex | 材质预测、completion、稀疏 / 光栅算子；可选外部背视图阶段必须改成本机或排除 |
| D11 | TripoSG | RF / SDF VAE、匹配导出与 surface extraction |
| D12 | PartCrafter | 部件生成 / 解码、多个部件结果协议；上游可选 VLM / stylization 服务不属于本机方案 |

这些是实际代码缺口，**不是要求重新做耗时模型验收**。官方桌面 Python / CUDA 依赖说明原样安装不能成为 Android 运行器，也没有证明永久无法移植。本版没有声称全部测评架构已经支持；原有 F-01–F-12、文本、01–14 / 16 / 17 完整冻结范围继续保留。

![四视图本地流程；UI FIXTURE，不是训练模型输出](media/development/multiview/multiview-ui.gif)

[四个可选包](media/development/multiview/01-multiview-models.png) · [校验导入](media/development/multiview/02-import-plan.png) · [四图输入](media/development/multiview/03-four-view-form.png) · [队列](media/development/multiview/04-multiview-queue.png) · [后台状态](media/development/multiview/05-background-observations.png) · [MP4](media/development/multiview/multiview-ui.mp4) · [媒体身份](media/development/multiview/manifest.json)

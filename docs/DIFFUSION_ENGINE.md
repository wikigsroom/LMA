# 扩散基座：SDXL、SD-Turbo 与 LCM

[English](DIFFUSION_ENGINE.en.md) · [HF 组件选择](HF_RECIPES.md) · [LoRA](ADAPTERS.md) · [开发状态](DEVELOPMENT.md)

新增 [LCM 小型本地条件准备](LCM_LOCAL_PREPARATION.md)：独立原生程序生成 5,696 字节来源绑定组件；底层真实出图不等于生产 `SdSpec` 配方已支持。App 接入、完整官方管线、画质和真机仍待处理。 新 C++ 候选像素门槛仍失败（8 > 5），未提升为产品支持。

新增实际主机专项：[SD-Turbo 与独立 LCM checkpoint](SD_DISTILLED_TRAINED.md)。SD-Turbo 完整 HF / 导入 / 原生链路通过；LCM 转换漏掉条件分支，固定引导候选完成完整 UNet 数值与实际 PNG 对照，但画质、完整官方管线和产品准备 / Android 均未验收。

适用内部 **0.3.0-dev.13 / code 17**。这里记录实际接入的代码、配方、Windows 原生编译与限定开发检查。尚未取得 Android 模型输出、图像质量、内存或锁屏证据；编号 01 / 02 / 03 / 05 及其他全部所选目标继续属于同一完整 v0.3.0。

## 用户选择与组件

App 只更新签名运行代码、数据配方和标签。模型、LoRA、CLIP 编码器、VAE 与词表由用户选择下载或导入。安装 / 升级 / 浏览 / 缺组件任务不下载模型；本次没有内置权重，也不要求用户安装全部模板。

1. 在“全部 / 搜索”打开 HF 仓库，进入“构建模型包 / LoRA 配方”，明确选择模型架构和配方。
2. 按角色选择匹配组件，可跨仓库；每个文件固定来源提交、大小和校验。检查全部必需依赖与总下载量。
3. 登记清单后在详情单独确认下载，或从文件夹导入；在“本地”暂停 / 续传、管理参数、版本和删除。
4. 对完整模型点击使用；对 LoRA 点击配对使用，明确选择已安装且声明兼容的基础模型。缺少基础模型不自动下载。
5. 填写文本提示和本次参数，明确允许尝试未测配方，再加入共用本机队列。实际资源不足、模型不符或引擎失败时在手机报错。

| 配方 | 用户选择的组件 | 功能 / 依赖标签 |
| --- | --- | --- |
| SD 1.5 / SDXL 完整 checkpoint | `model`，可选匹配 `vae`；已披露的 `clip_merges` | 生图 / 文生图，`sd_cpp` / CPU / 对应架构 |
| SD 1.5 独立 diffusion | `diffusion`、`clip_l`、`vae`，以及 `clip_merges` | 生图；组件必须完整 |
| SDXL 独立 diffusion | `diffusion`、`clip_l`、`clip_g`、`vae`，以及 `clip_merges` | 生图；双 CLIP 编码器必需 |
| SD-Turbo | 含编码器 / VAE 的完整 SD 2.1 Turbo checkpoint、可选 VAE，以及 `clip_merges` | 生图 / 蒸馏采样，`pipeline:sd21_turbo` |
| SD 1.5 / SDXL LCM checkpoint | 同架构完整 LCM checkpoint、可选 VAE，以及 `clip_merges` | 生图 / 蒸馏采样，`pipeline:sd15_lcm` 或 `sdxl_lcm` |
| SD 1.5 / SDXL LCM-LoRA | 独立 `lora`，另行选择同架构普通基础模型 | 平级生图适配器 / 蒸馏采样 / 需要基础模型 |

权重组件接受 GGUF / Safetensors；扩展名和声明不证明张量匹配。完整 checkpoint 需实际包含全部编码器及 VAE；独立 diffusion 模板明确要求分离组件。SDXL 可单独提供匹配的替代 VAE。原生 worker 加载后核对 SD 1.x / SD 2.x / SDXL 架构，错误家族、inpaint 等其他变体不会冒充当前文生图配方。蒸馏方式仍取决于用户选中权重的真实来源，架构检查不能证明训练方法或质量。

四类功能标签、安装状态、设备证据和无审查内容标签彼此独立。所有模型保持平级；推荐 `m08 → m06 → m01` 保留。现有生产扩散配方只接受文字，不因本地素材导入而自动获得图生图或编辑能力。

## 本次任务的采样约束

| 来源 | 原生采样器 / 调度器 | 步数保护范围 | CFG |
| --- | --- | --- | --- |
| 普通 SD / SDXL 与风格 LoRA | 使用所选模型配方 | 使用模型独立设置 | 使用模型独立设置 |
| LCM checkpoint 或一个明确声明的 LCM-LoRA | `lcm` / `lcm` | 1–8 | 1，关闭 CFG |
| SD-Turbo | `euler_a` / `discrete` | 1–4 | 1，关闭 CFG |

这些是当前应用采样配方的保护边界，不是所有模型训练的理论上限。sd.cpp 以 CFG=1 表达关闭 classifier-free guidance；不要照搬其他运行库的数值约定。低步数配方不接受负面提示词，界面禁用该输入，API 明确报错。

选择 LCM-LoRA 时显示实际策略，本次步数超限回填；取消选择恢复表单原值。基础模型的已保存步数、CFG 等设置保持独立。一次最多一个 LCM 加速来源，不再给 LCM checkpoint 叠加 LCM-LoRA；LCM-LoRA 强度必须为正。其他声明兼容的普通风格 LoRA 可以同时选择，最多八个适配器。

`adapter` 可增加受限声明 `"sampling":"lcm"`，其余配对约束沿用 `lma.adapter/1`。只有明确的这一声明启用加速，名称包含 LCM 不会自动改变策略。未知策略、跨架构配对、缺组件与缺适配器租约均拒绝。

## API、快照与原生边界

客户端仍提交正常的 `POST /v1/jobs`，选择实际已安装包 ID：

```json
{
  "bundleId": "your_sd15_base_bundle",
  "type": "image.generate",
  "input": {"prompt": "A cabin in morning mist."},
  "parameters": {"steps": 4},
  "adapters": [{"bundleId": "your_sd15_lcm_lora_bundle", "scale": 1}],
  "allowUnmeasured": true
}
```

服务端固定 `diffusionPlan`，包含 `schema: lma.diffusion-plan/1`、采样策略、有效参数和调整原因；原请求参数另行保留，避免把强制 LCM 值写回普通模型参数或令旧配方无法重试。客户端不能提交这一派生字段。任务重试剥离旧派生计划后重新核对，执行时用持有租约的不可变模型 / 适配器再次计算并对比计划；不同则在启动前失败。JSON 落盘前统一数值表示，避免 `1.0` 与 `1` 导致错误拒绝。

原生调用只获得已校验组件的私有路径和显式适配器顺序。CLIP merges 以托管用户组件路径提供，APK 不含词表数据。Java 与 C++ 分别约束低步数策略；C++ 另外核对实际加载的张量架构。全部分词、编码、采样、VAE 解码与 PNG 写入都在同一 Android 手机，不增加外部执行回退。

## 开发证据与剩余验收

- [扩散回执](../verification/development/diffusion.json)：174 项，含 117 项生产 Java 计划 / 绑定 / 实际主机子进程协议检查，以及 57 项执行共用 C++ 策略的检查。子进程写的是协议 JSON 字节，不是图片或模型输出。
- 基座 425 项，其中组件配方 / 完整性 233 项；UI 203 项。当前共二十个数据模板，登记不下载。
- Android ARM64 worker 原生 Windows NDK 构建、APK 签名 / 19 个原生文件 / API 28 / 16 KiB 对齐与 Lint 检查通过；没有 Android 运行结果。
- 完整固定模型来源 / 许可、SD1.5 / SDXL LoRA 效果、LCM 与 Turbo 质量 / 速度 / RAM、加载释放、锁屏 / 升级与全部其他目标仍须在同一 v0.3.0 验收。此检查点不创建 Release。

实现：[SdSpec](../app/src/main/java/com/lma/app/core/SdSpec.java)、[SdEngine](../app/src/main/java/com/lma/app/SdEngine.java)、[C++ 策略](../native/sd_policy.hpp)、[worker](../native/sd_worker.cpp)。来源核对：[固定版本 sd.cpp LCM 说明](https://github.com/leejet/stable-diffusion.cpp/blob/be486498eadc29dc3cd234d944c2180ed42b1415/docs/lcm.md)、[SD 模型 / 组件说明](https://github.com/leejet/stable-diffusion.cpp/blob/be486498eadc29dc3cd234d944c2180ed42b1415/docs/sd.md)、[官方 SD-Turbo](https://huggingface.co/stabilityai/sd-turbo)、[LCM-LoRA SD 1.5](https://huggingface.co/latent-consistency/lcm-lora-sdv1-5)、[LCM-LoRA SDXL](https://huggingface.co/latent-consistency/lcm-lora-sdxl)。上游能力不替代 LMA 手机证据。


其他四条扩散 / 视频路线、完整组件和 flowShift / 几何约束见[高级接入指南](ADVANCED_DIFFUSION.md)。同一扩散回执同时覆盖这些新增路线。


## dev.24 生产进度与真实权重

[真实 SD1.5 验证](SD15_TRAINED.md)补充本配方的主机训练输出、采样取消/恢复和外部词表流程。进度 callback 跟随 loading/generating；局部操作 steps 不统一当成扩散步数。Android编译、UI夹具、主机模型执行与手机验收分别记录，其他家族/LoRA仍需独立验收。

[完整 SDXL 与双架构 LoRA / LCM-LoRA 实测](SD_VARIANTS_TRAINED.md)进一步使用完整训练文件、外部词表和未修改生产 worker，检查零强度 / 启用、LCM 权重反事实、实际采样取消恢复与生产 Java 全量导入。实际 PNG、耗时与主机内存观察独立记录；低步数样例未通过画质验收，03 的独立 SD-Turbo / LCM checkpoint 也仍待完整验收。源码、主机输出、Android 编译和手机 / 锁屏 / 完整 Release 不互相替代。

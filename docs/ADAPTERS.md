# LoRA 平级模型与显式配对

[English](ADAPTERS.en.md) · [资产控制核对](ASSET_CONTROL_AUDIT.md) · [开发状态](DEVELOPMENT.md) · [完整需求](MULTIMODAL_RELEASE_PLAN.md)

适用于内部 **0.3.0-dev.12 / code 16**。这里说明已接入的配对、存储和任务代码；**尚无 LMA Android LoRA 生成证据**。编号 02 的 SD 1.5 / SDXL 实际权重、质量与生命周期验收仍属于同一完整 v0.3.0，不能按此文计为完成。

## 用户使用逻辑

1. 用户分别选择基础模型包和 LoRA 包，通过明确下载操作或“添加模型”的清单 / 文件夹导入安装。包详情分别展示文件、大小和许可；本次没有新增已核对的 LoRA 下载候选。
2. 基础模型和 LoRA 都是模型库中的平级条目，可通过“生图”筛选；LoRA 另外显示 `LoRA / 需要基础模型`。推荐 `m08 → m06 → m01` 保持不变。
3. 对已安装 LoRA 点击“配对使用”，在已安装的兼容基础模型中明确选择。没有匹配项时返回模型库自行安装，不自动选择 / 下载基础模型。也可从基础模型“使用”表单勾选 LoRA。
4. 填写提示词，选择最多八个兼容 LoRA，编辑各自强度。每个适配器有独立设置；本次任务中的强度编辑不改动保存值。强度超限自动回填到该适配器声明边界，原生引擎绝对保护范围为 `-4…4`。
5. 提交到共用队列后固定基础包 ID、适配器包 ID、顺序、有效强度及参数修正记录。后续设置修改不改变已排队快照。
6. 运行期间同时持有基础包及适配器引用，阻止删除其资产或修改相关设置。成功、失败、取消和部分获取失败都释放引用；排队时被用户删除的资产会在执行时本机失败，不隐式下载。

所有加载、采样和结果处理都在同一手机。App 更新只携带基座代码，不携带 LoRA、基础权重或模型专用词表。LoRA 是可选模型资产，不是用户插件或可执行脚本。

## 清单约束与 API

基础包继续使用 `lma.model-bundle/1`。LoRA 包复用相同存储协议，增加以下数据声明；这段是清单片段，实际包仍须提供真实名称、ID、组件 SHA256 / 大小等全部字段：

```json
{
  "engine": "sd_cpp",
  "backend": "cpu",
  "architecture": "sd15",
  "pipeline": "lora",
  "tasks": ["image"],
  "capabilities": ["image_adapter"],
  "adapter": {
    "schema": "lma.adapter/1",
    "kind": "lora",
    "baseArchitectures": ["sd15"],
    "basePipelines": ["sd15"]
  },
  "parameters": {
    "version": 1,
    "fields": {
      "scale": {
        "type": "number", "label": "LoRA 强度", "default": 1,
        "minimum": -4, "maximum": 4, "presets": [0.5, 0.75, 1],
        "limitSource": "application_guard"
      }
    }
  }
}
```

组件必须恰好一个，角色 `lora`，格式 `safetensors` 或 `gguf`；它的哈希和字节数按实际文件填写。SDXL 使用 `architecture: "sdxl"`、对应 `baseArchitectures / basePipelines`。架构列表只能有一个与适配器相同的 SD 1.5 / SDXL 架构；可选 `baseModelIds` 进一步限制特定基础模型 ID。LoRA 自身不能再作为基础模型，未知版本 / 命令字段拒绝导入。

`basePipelines` 约束配对管线。dev.12 的专用 LCM-LoRA 模板另加 `"sampling":"lcm"`，与同架构普通基础模型配对时固定本次 LCM 采样 / 调度、CFG=1 与 1–8 步保护，基础设置保留；不接受负面提示词。普通兼容声明本身不启用 LCM，名称不推断训练方式。详见[扩散基座](DIFFUSION_ENGINE.md)。官方 [SD1.5](https://huggingface.co/latent-consistency/lcm-lora-sdv1-5) 与 [SDXL](https://huggingface.co/latent-consistency/lcm-lora-sdxl) 权重不能互换。

在原有 `POST /v1/jobs` 图像任务中增加可选 `adapters`：

```json
{
  "bundleId": "your_installed_sd15_bundle",
  "type": "image.generate",
  "input": {"prompt": "A cabin in morning mist."},
  "parameters": {},
  "adapters": [{"bundleId": "your_installed_lora_bundle", "scale": 0.75}],
  "allowUnmeasured": true
}
```

示例 ID 需要替换为本机实际已安装包。省略 `scale` 时读取适配器保存值，并固定到任务。重复适配器、自身依赖、超过八个、非有限数值、路径或未知字段、非生图任务的适配器选择都会被拒绝。API 客户端不能指定原生文件路径。产物来源另存完整适配器清单、任务参数和有效强度。

## 验证与剩余边界

实现位于 [AdapterSpec](../app/src/main/java/com/lma/app/core/AdapterSpec.java)、[ModelSelection](../app/src/main/java/com/lma/app/core/ModelSelection.java)、[BundleStore](../app/src/main/java/com/lma/app/core/BundleStore.java)、[LocalJobs](../app/src/main/java/com/lma/app/LocalJobs.java) 和 [SdEngine](../app/src/main/java/com/lma/app/SdEngine.java)。只有完整引用组内已校验组件的私有对象路径会交给已打包 worker 的 `loras` 数组。

本次新增 45 项主机契约检查，使用明确的任意字节夹具验证双架构配对、错误拒绝、上限、冻结快照、原子引用和无隐式下载；不是权重解析或图像输出。共 130 项基座检查、97 项 UI 检查通过；截图 / 视频 / GIF 全程标记 UI FIXTURE。

实际兼容性仍取决于权重命名 / 张量维度、训练基础、量化应用方式、引擎版本和内存。清单中的兼容声明不等于读取权重后的验证。资源准入增加适配器字节数四倍的保守内存保护量，它不是实测峰值。固定实际配方、LoRA 效果对照、完整 HF 多组件选择、真机加载 / 取消 / 释放和耐久尚未完成。

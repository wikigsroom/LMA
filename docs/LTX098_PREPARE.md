# 旧 LTX 的本机资产准备组件

[English](LTX098_PREPARE.en.md) · [编号交付与完整待办](releases/v0.3.0-dev.21-ltx-prepare.md) · [完整版本范围](MULTIMODAL_RELEASE_PLAN.md) · [完整主机视频与数值缺口](LTX098_PIPELINE.md)

本次增加可原生编译的 **safetensors → DiT GGUF 流式转换组件**，为后续用户在同一 Android 手机上准备已选模型提供基础。它读取用户已有的本地文件，不需要 Python / Torch、ROOT、Termux、网络或其他设备服务。它是尚未接入 App 的独立源码组件；Android 编译成功不表示手机执行或 17 号模型完整支持。

App 继续只更新基座。权重由用户选择、下载或导入；本组件不包含、获取、删除或静默替换原始模型。准备转换也必须由用户明确操作触发，不能成为安装、升级、浏览或发现缺件后的自动行为。

## 具体处理

| 编号 | 处理 | 约束 |
| --- | --- | --- |
| C-01 | 有界头部检查 | 请求 ≤32 KiB；safetensors 头 ≤16 MiB；拒绝重复键、深层嵌套、非法尺寸 / 类型 / 范围与未覆盖字节 |
| C-02 | 旧版结构 | 精确 715 张量 / 1,923,385,472 参数 / 冻结布局 SHA；旧 transformer 常量与 distilled 八步时刻表；开发夹具通过独立 CLI 参数区分 |
| C-03 | 流式转换 | 按源偏移连续读取，保留原头部张量顺序写 GGUF；二维 `.weight` 为 F16，其余 F32；输入支持 BF16 / F16 / F32 |
| C-04 | 有界内存 | 4 MiB 输入缓冲、最多 8 MiB 转换缓冲；不分配完整张量或整个 checkpoint；头部 / JSON 另计 |
| C-05 | 完整身份 | 每一字节源数据进入 SHA-256，包括未转换的 VAE 等部分；转换与哈希消费同一批字节；有限值与 F16 范围校验 |
| C-06 | 事务提交 | 独占临时目录、源文件稳定性检查、输出 flush 与完整 SHA、持久化转换收据，最后无覆盖目录提交；已有文件 / 目录始终保留 |
| C-07 | 中途取消 | 分块检查取消标记；正常错误或取消只清理本次已创建的两个文件及空目录，不递归删除用户目录 |
| C-08 | 本机边界 | 绝对本地路径；拒绝 URL / UNC / Windows 网络盘 / 末端文件链接；无网络、外部进程或推理依赖 |

布局身份取自[旧版锁文件](../third_party/ltx098-source-lock.json)，不是模型名称判断。用户提供的可信下载 SHA 与大小必须和完整源文件一致；单独检查模型结构并不能证明下载文件可信，也不表示其他 LTX 版本可用。结构元数据编入基座，训练数据不会编入。

```mermaid
flowchart LR
  U[用户明确选择本地 checkpoint] --> H[头部及旧版结构校验]
  H --> S[连续读取及完整源 SHA]
  S --> T[F16 / F32 分块写入独占暂存目录]
  T --> V[源身份 / 稳定性 + 输出完整 SHA]
  V --> C[写收据并无覆盖提交]
```

`inspect_dit` 只进行头部 / 结构 / 输出预算预检，必须保留 `source_sha256_verified=false`，也没有输出哈希。它不能冒充下载校验或成功转换。

## 调用协议

当前调用用于开发者验证。生产 App 的显式准备入口、SAF 授权文件复制 / 选择、用户资产登记、进度与持久任务集成仍待接入；用户不应为此安装桌面 Python 或准备一台推理电脑。

```json
{
  "operation": "convert_dit",
  "checkpoint": "/data/user/0/com.lma.app/files/models/user-selected.safetensors",
  "expected_source_bytes": 6340744492,
  "expected_source_sha256": "76aa8c4786af752fa6f951947129d5290c3c6c0b2fadcadea6b5e114ae2cad8f",
  "storage_root": "/data/user/0/com.lma.app/files/models",
  "output_name": "user-selected-ltx098-dit",
  "cancel_file": "/data/user/0/com.lma.app/files/jobs/prepare.cancel",
  "max_output_bytes": 4000000000
}
```

以上路径是协议示例，不表示目前 App 已创建这些文件。大小 / SHA 是已核对旧版发布者 checkpoint 的示例，未来应来自用户选中下载项的可信记录。`storage_root` 必须存在，`output_name` 必须是新的内部 basename；最终目录只包含 `ltx098-dit.gguf` 和 `conversion.json`。`cancel_file`、`max_output_bytes` 可省略。`inspect_dit` 必须省略 `storage_root` / `output_name`；未知字段直接失败。

成功 / 错误通过 stdout 输出单个 JSON，进度在 stderr 按 `convert` / `verify_output` / `committed` 输出字节计数。失败退出 1；成功退出 0。取消失败不会提交最终目录。进程被系统强制终止时，未提交暂存目录可能保留；后续 App 的任务恢复 / 孤立暂存回收需要单独实现，不能由本组件的正常取消检查代替。

## 存储和模型设置

原始 checkpoint 为 **6,340,744,492 bytes**；本次 DiT 输出为 **3,849,516,416 bytes**。转换时会同时保留两者，并要求输出之外至少 1 MiB 可用空间作为收据余量。T5、VAE、其他运行缓存不包含在这两个数字内。用户自行决定之后是否删除原文件；转换成功不隐式删除源文件。

这是资产格式准备，不能由转换内存推算视频生成 RAM、GPU 显存、耗时或 Z20 可用性。转换收据也不能替代模型独立参数、任务快照、标签、许可证和设备兼容性检查。各模型继续平级，生文 / 生图 / 生音频 / 生视频及所需基座标签与下载状态独立；本组件尚未注册为可用模型能力。

## 复现与证据

只使用原生 Windows 工具构建；不会启动虚拟环境、模拟器、Docker 或 WSL。Android 构建为 ARM64 / API 28 / 静态 C++ / 16 KiB 对齐，并检查动态导入中没有网络 / 外部进程接口。

```powershell
python tools/build_ltx098_prepare.py
python tools/build_ltx098_prepare.py --android
python tools/test_ltx098_prepare.py --trained
python tools/export_development.py
python tools/plot_ltx098_prepare.py
python tools/check_repository.py --development
```

训练验证复用开发者已经显式取得的本地文件，没有新增下载。`--trained` 要求原始 checkpoint 和独立 Python 转换结果均在现有忽略的 `build/` 目录。小夹具包含所有 63,488 个有限 FP16 位型、65,280 个有限 BF16 位型、190,462 个 FP32 舍入边界值，及与载荷顺序不同的头部张量顺序。它们用于格式转换，不表示任何神经网络输出。

[公开验证结果](../verification/development/ltx098-prepare.json)单独记录原生 Windows 实际转换、整文件 Python / hashlib 字节身份、进程内存观测、失败保护，以及[Android 编译](../verification/development/ltx098-prepare-arm64.json)。[主机编译身份](../verification/development/ltx098-prepare-host.json)、[图的来源与哈希](media/development/ltx098-native-prepare.json)均可独立核对。

![真实主机资产转换数据；不是 App 界面或手机运行](media/development/ltx098-native-prepare.png)

## 完整版本仍待完成

此组件没有修复完整旧 LTX 链路的六项浮点失败，也没有完成 VAE 的同机用户资产准备、生产 adapter / App API / 同机媒体编码整合、生成质量、手机资源或耐久验收。全部冻结模型和 F-01–F-12 仍在同一个完整 v0.3.0 内，不默认顺延、不缩减为预览版本。见[本轮编号待办](releases/v0.3.0-dev.21-ltx-prepare.md)。

本轮完整测试执行为 **156 项检查 / 46 组失败保护 / 51 个原生子进程**，包含 1 次完整训练资产转换。观测主机峰值工作集 **13.22 MiB**；转换进程 539.92 秒，含源 / 输出全量哈希。环境与 I/O 会影响耗时，不能作为手机速度或生成资源指标。

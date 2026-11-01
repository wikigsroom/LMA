# Android 真机程序验证 · v0.3.11
## 当前 v0.3.11

最终原签名 APK 通过 **23 项真机程序检查**与 **60.239 秒锁屏接口健康检查**，保留 5 个已安装模型及逐模型设置。授权的限时模型实跑另行记录；一步 Wan 生成可解码但接近空白的 MP4，两种 3D 均未完成 GLB。不声称常用尺寸画质或长线后台推理通过。

[当前操作与边界](ON_DEVICE_MODEL_REPAIR.md) · [正式版说明](releases/v0.3.11.md)

## 历史 v0.3.10 调查

**v0.3.11 当前：** [真机管理 / API 程序检查](../verification/releases/v0.3.11/physical-device.json)与[授权模型实跑](../verification/releases/v0.3.11/physical-models.json)分别计数。Wan CPU 已输出视频，3D 限时结果不等于完整 GLB 成功。下文 v0.3.10 调查与数字属于历史记录。

[English](DEVICE_ACCEPTANCE.en.md) · [版本说明](releases/v0.3.10.md) · [23 项程序检查](../verification/releases/v0.3.10/physical-device.json) · [10 项故障检查](../verification/releases/v0.3.10/task-diagnostics.json)

本轮通过已授权 USB ADB 连接真实手机并保留数据升级。设备实际报告 **motorola edge plus / burton、Android 12 / API31、SM8250、约 11.4 GiB 系统可见 RAM**；不能写成 X30、骁龙 8 Gen 1 或努比亚 Z20 的测试。电脑负责安装和转发管理请求，App、接口和探针均在手机执行，无 ROOT 或虚拟环境。

## 1. 当前结果

当前 APK 为 **0.3.10 / code60**，保留原签名和用户数据。原有 7 条任务包含 5 失败 / 2 成功；5 条失败逐条备份后清理，2 条成功、5 项素材 / 结果、5 个已安装模型和独立参数保留。[逐条原因、修复与可选 CPU 配方](TASK_FAILURES.md)。

| 编号 | 检查内容 | 结果与范围 |
| --- | --- | --- |
| A01 | 完整目录、82 包和实际设备状态；原生桥、WebView | 真实应用程序通过，已有模型保留 |
| A02 | 推荐 14 项、原文本前缀及生图 3 / 视频 2 / 音频 3 / 3D 3 分类；全部、本地与各导航 | 真机 DOM 操作通过；本轮不录入私人任务媒体 |
| A03 | 提取原生程序权限、SQLite 中断恢复、前台服务命令响应 | Android 框架通过 |
| A04 | 测试退出后普通应用接口继续服务 | 前台服务恢复通过 |
| A05 | 错误密钥 401、浏览器来源 403；模型 / 引擎 / 任务 / 结果 / 草稿 / 上传读取 | 经 ADB 转发访问手机 HTTP 服务 |
| A06 | 缺少文本权重返回 409；模型清单不变 | 无自动模型下载 |
| A07 | 熄屏 60.29 秒、7 次认证健康请求和服务检查 | 短时程序存活通过，不代表推理耐久 |

以上共 **23 项程序检查**，与 **10 项故障专项**分别计数。专项使用四字节自有文件、17 组件大小 / 校验记录和原生 `--info` / `--devices`；修复后的工作目录可用，生产 Wan 预检拒绝不兼容 GPU 且任务数不变。不加载完整权重，不执行生图 / 生视频 / 生音频 / 生 3D。

API 密钥仅在验收进程内存中传递，公开记录不含密钥、序列号、Wi-Fi 端点、个人提示词或素材。原始诊断与清理备份在本机忽略目录。

## 2. 程序验证复现

使用原生 Windows Android SDK / JDK / Python，保持已授权手机解锁。先确认无运行中任务；安装测试可能重启目标应用。`SERIAL` 使用 `adb devices` 中的已授权设备。无线配对后还需要连上手机公布的连接端口。

```powershell
python tools/build.py
python tools/build_acceptance.py
python tools/device_check.py --serial SERIAL --install --run --program-api --existing-models --minutes 1
```

`--existing-models` 允许保留已安装资产后做管理 / 接口检查；不传此项时仍要求零安装模型。**不要传 `--model`**，它是历史完整模型下载 / 执行模式。没有导入或运行任何替代 CPU 包。

故障专项需单独运行已安装的 `com.lma.app.acceptance/com.lma.app.DeviceTaskDiagnostics`；它只检查已有问题模型组件的元数据和小文件链接。如果设备没有这些模型，缺失属于前置条件，不应下载完整模型来满足诊断。验收后移除测试 APK，正常应用继续保留。

## 3. 媒体与历史修复

本版十组桌面生产页面重新录制 **57 PNG / 10 GIF / 10 MP4**，均标明 UI FIXTURE，测试浏览器在完成后关闭。[媒体索引](MEDIA.md)。

实际 Android 录屏保留 **v0.3.9 原身份**：[推荐页](media/device/v0.3.9/01-recommended.png) · [分类视频推荐](media/device/v0.3.9/02-recommended-video.png) · [MP4](media/device/v0.3.9/physical-walkthrough.mp4) · [GIF](media/device/v0.3.9/physical-walkthrough.gif) · [身份清单](media/device/v0.3.9/manifest.json)。本轮手机已有私人任务和素材，不把其页面复制到公开媒体，也不把历史视频绑定到新 APK。

| 编号 | 保留的既有修复 |
| --- | --- |
| D01 | 未准备资产的旧 LTX 条目只记录自身输入表单错误，不再截断整份状态 |
| D02 | 测试 APK 的资源表不压缩并对齐，可在 Android 12 安装 |
| D03 | ADB 媒体导出使用仓库相对路径，避开含中文绝对输出路径问题 |
| D04 | v0.3.9 将状态整理移到单一后台线程，复用模型描述与页面，修复空闲卡顿 |

v0.3.9 的 4,061 → 230 ms / 4,228 → 24 ms 暖态测量见[性能说明](PERFORMANCE.md)。当前 8 项记录核对相关源码及历史证据保持不变，没有进行本版延迟测量。所有原发布附件均不覆盖。

## 4. 未验证与验证偏差

| 编号 | 尚无结论 | 处理 |
| --- | --- | --- |
| U01 | 修复后的完整 3D / Wan CPU 输出、画质、速度、峰值内存 | 依照程序验证要求不在手机重跑完整模型 |
| U02 | 当前 Wan GPU 驱动兼容性 | 已明确拒绝；满足 Vulkan 要求需要兼容驱动 / 设备，或用户明确选 CPU |
| U03 | 长时间锁屏推理、温度、省电和重启恢复 | 短时健康检查不能代替耐久 |
| U04 | X30、Z20、其他设备、任意 HF 架构及所有上游工作流 | 保持 62 配方 / 82 包 / 18 扩展引擎加文本的有界范围 |

**验证偏差如实保留：** 回归时误选旧 Nano 主机完整模型工具，使用已有主机资产启动 3 个子进程并生成 2 份输出记录。旧 Qwen 检查在生成前因证据指纹过期退出。两项均不纳入程序断言或真机通过；手机完整模型没有重跑。正确的小夹具检查已另行完成。[偏差记录](../verification/releases/v0.3.10/validation-deviation.json)。

# Android 真机程序验证 · v0.3.8

[English](DEVICE_ACCEPTANCE.en.md) · [版本说明](releases/v0.3.8.md) · [当前证据](../verification/releases/v0.3.8/physical-device.json)

本轮使用已配对的无线 ADB，在真实手机安装和升级 LMA，无需 ROOT。设备实际报告 **motorola edge plus / burton、Android 12 / API31、SM8250、约 11.4 GiB 系统可见 RAM**。不能将这份记录写成 X30、骁龙 8 Gen 1 或努比亚 Z20 的测试。电脑只负责安装、操作和转发请求，接口与应用程序都在手机执行。

## 1. 保留 v0.3.7 修复与本版分类检查

| 编号 | 实际问题 | 修复后的行为 |
| --- | --- | --- |
| D01 | v0.3.6 零模型启动时，未准备资产的旧 LTX 条目在读取输入表单时触发严格执行校验，状态只返回部分字段，整页模型卡片和内存信息无法显示 | 目录逐项记录 `inputSchemaError`；单个条目不影响其余目录、设备和界面状态。任务执行仍校验真实匹配资产 |
| D02 | 验收工具把 `resources.arsc` 压缩，Android 12 拒绝安装测试 APK | 保持资源表不压缩并对齐；独立验收 APK 能安装 |
| D03 | 旧 ADB 在含中文的绝对输出路径导出媒体时报错 | 使用仓库工作目录内的相对输出路径；截图与录屏可导出 |

原 v0.3.6 标签和已发布附件不覆盖。当前 APK 为 **0.3.8 / code58**，保留原签名、应用数据和用户自主模型选择。历史失败另存证据，未改写为通过。

## 2. 检查覆盖

| 编号 | 实测内容 | 证据性质 |
| --- | --- | --- |
| A01 | 完整零模型状态、82 套目录包及实际内存；原生桥接和模型卡片 | 真机应用与 WebView |
| A02 | 推荐 14 项，生文前缀 `m08 → m06 → m01`；四类推荐的数量与卡片；全部注册条目、本地管理及聊天 / 任务 / 服务 / 设置导航 | 真机 DOM、页面截图 |
| A03 | 提取的原生可执行文件权限、真实 SQLite 中断恢复、前台服务命令响应 | Android 框架 |
| A04 | 无模型也可启动接口；测试退出后普通应用继续服务 | 真机前台服务 |
| A05 | 鉴权错误返回 401、浏览器来源返回 403；模型 / 引擎 / 任务 / 结果 / 草稿 / 上传读取 | 实际手机 HTTP 服务，经 ADB 转发 |
| A06 | 缺文本权重返回 409；不自动下载、不产生已安装模型 | 本机预检拒绝路径 |
| A07 | 后台且屏幕关闭约 60 秒；7 次认证健康请求和前台服务状态检查 | 短时程序存活，非推理或耐久 |

共 **23 个真机程序检查点**。接口密钥只在受信任的验收进程内存中传递，不进入日志、公开证据或媒体。公开记录不含设备序列号、Wi-Fi 地址或配对口令。应用未下载、复制或运行完整训练模型。

## 3. 复现

使用原生 Windows Android SDK / JDK / Python；不启动模拟器、Docker、WSL 或虚拟机。先在手机允许调试并解锁。无线调试的配对端口与连接端口不同；二维码配对成功后仍需连接设备公布的连接端口。标准流程见 [Android 官方 ADB 文档](https://developer.android.com/tools/adb#wireless-android11-command-line)。

```powershell
python tools/build_acceptance.py
# DEVICE_IP:CONNECT_PORT 由手机无线调试页面提供，不是配对端口。
python tools/device_check.py --serial DEVICE_IP:CONNECT_PORT --install --run --program-api --minutes 1
# 锁屏检查后手动解锁，再录制页面；不再主动锁屏。
python tools/device_check.py --serial DEVICE_IP:CONNECT_PORT --run --program-api --minutes 0 --capture-media
```

不要传 `--model`；该历史选项会下载和运行完整模型，不属于本轮程序验证。`--program-api` 只适用于没有已安装模型的验收设备，发现已有模型时保留文件并停止该专项。普通安装使用 `-r`，不清除应用数据。录屏前必须解锁；系统锁屏密码由用户本人输入。

## 4. 页面与录屏

[真机截图](media/device/v0.3.8/01-recommended.png) · [实际录屏 MP4](media/device/v0.3.8/physical-walkthrough.mp4) · [录屏 GIF](media/device/v0.3.8/physical-walkthrough.gif) · [媒体身份](media/device/v0.3.8/manifest.json)

媒体来自实际手机屏幕；仅保留 LMA 页面，不包含个人桌面、锁屏密码或其他应用。与 `docs/media/development/` 中带 **UI FIXTURE** 标记的桌面页面演示分别保存。录制展示操作，不表示生成速度或模型输出。

## 5. 保留的未测边界

| 编号 | 尚无结论 | 处理方式 |
| --- | --- | --- |
| U01 | 生文 / 生图 / 生视频 / 生音频 / 3D 的完整训练模型输出、质量、tokens/s、峰值 RAM 和温度 | 按用户要求不做完整模型运行，不阻塞程序补丁发行 |
| U02 | 长时间锁屏推理、厂商省电、重启与异常强停后的完整模型恢复 | 本轮只记录 60 秒程序接口存活；不承诺长期持续 token |
| U03 | X30、努比亚 Z20、其他 Android / SoC 的真机表现 | 本机记录仅适用于上述实际设备 |
| U04 | 任意 HF 架构、全部上游 CUDA 工作流及大型公开完整 3D 导出包 | 保留 62 配方 / 82 包 / 18 扩展引擎加文本的有界支持范围与来源限制 |

## 6. v0.3.8 分类媒体

新增四项真机检查：生图 3 / 生视频 2 / 生音频 3 / 生 3D 3。11 张 PNG 与实际 MP4 / GIF 绑定当前 APK 和测试源码。[生图](media/device/v0.3.8/02-recommended-image.png) · [生视频](media/device/v0.3.8/02-recommended-video.png) · [生音频](media/device/v0.3.8/02-recommended-audio.png) · [生 3D](media/device/v0.3.8/02-recommended-3d.png)。未下载或运行模型。

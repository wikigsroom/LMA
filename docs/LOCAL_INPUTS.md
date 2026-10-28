# 本地输入素材、任务引用与上传

[English](LOCAL_INPUTS.en.md) · [开发状态](DEVELOPMENT.md) · [API](API.md) · [共用调度](SCHEDULING.md)

状态：**0.3.0-dev.11 / versionCode 15，内部开发检查点，未发布。** 已接入本地素材管理和任务输入契约；现有生产文本、扩散、Sherpa、Nano 配方仍只接受文字，没有因此获得图像编辑、参考音频克隆或图生视频能力。完整 v0.3.0 的全部所选模型、输入管线和物理 Android 验收继续保留。

## 使用流程

1. 打开“任务 → 素材与结果 → 导入素材”，在 Android 系统文件选择器明确选择一个文件。
2. 前台服务将文件复制到 App 私有目录，校验实际媒体结构并计算 SHA256。退出页面不主动取消；可点击“取消导入”或通知中的“停止服务”。中断的系统文件导入需要用户重新选择文件，不伪装成可续步任务。
3. 在“全部 / 生成结果 / 导入素材”筛选中预览、播放、导出或删除。导入文件标记“导入素材”，不能冒充模型生成结果；旧版结果没有来源字段时按生成结果兼容显示。
4. 选择已安装模型。只有签名引擎为该配方声明了媒体输入角色，任务表单才显示对应选择框。可选择匹配的导入素材或已有生成结果；格式、大小、时长、尺寸限制来自该配方。必需输入不能省略。
5. 提交任务后固定素材 ID、实际 hash、大小和元数据；排队与执行期间保护删除。执行前再次计算完整 hash，文件缺失或变更在本机失败，不重新下载、不换成其他素材。

目前可导入 **PNG / JPEG、未压缩 PCM / float WAV、MP4**，单个文件 **1 字节至 512 MiB**；实际结构校验还会排除空文件、损坏或不支持的编码。其他图片、压缩音频和容器暂不接受，不隐式转换。WAV 支持 8–192 kHz、1–8 声道、16/24/32 位整数 PCM 或 32 位 float；各引擎可以继续收紧条件。图片最大边 16384；视频也限制尺寸、连续采样时间戳和帧表数量。Android 图片解码与 MP4 轨道探测尚缺真机验收，MP4 元数据检查不证明每种 codec 都能播放或被模型使用。

源文件只在明确选择时读取。私有副本不依赖用户随后保留原系统 URI；产物来源记录保存显示名，不导出文件系统路径或 `content://` URI。模型权重、词表、音色包仍走模型包管理，不通过素材上传安装。

## 引擎和持久引用

`InputSpec` 由签名 App 引擎实现声明，包含角色、必需性、MIME、字节数及可选时长 / 像素上限。HF 元数据和模型包不能自行开启输入算子。所有现有模块默认 `promptOnly()`，未知角色明确失败；后续每种实际管线必须显式实现并实测。

`TaskInput` 只接受 `input.artifacts: [{role, artifactId}]`，最多八个不同角色。客户端不能传本地路径、远程 URL、可信 hash 回执或可执行脚本。`InputSelection` 在素材锁内准备快照，并与 JobStore 持久发布保持相同锁顺序；API 与 UI 调用同一生产任务运行器。

JobStore 的非终态请求保护排队输入，进程重启后排队引用仍在。执行时取得读取租约并复核 hash；引擎上下文按角色获得受控私有文件。取消或超时后，即使任务已终止，也要等实际子进程退出才能释放输入租约。结果来源包含固定输入回执。完成 / 失败 / 中断历史保留回执但不永久占用素材，明确删除后重试会因缺输入失败。

素材预览、API Range 下载和系统导出同样持有读取租约。删除旧任务不会删除素材或结果；删除上传会话也不会删除已经导入的素材。用户分别管理这些记录。

## API 分块上传

所有端点沿用 Bearer 密钥；默认仅手机回环监听，用户开启 LAN 后可接收客户端提交的数据，执行仍在同一手机。拒绝浏览器 Origin，不开放 CORS。不接受远程文件 URL、任意路径、multipart、HTTP chunked transfer 或 `Expect: 100-continue`。

| 请求 | 行为 |
| --- | --- |
| `POST /v1/uploads` | JSON `{name, bytes, sha256}` 显式创建输入会话，返回 202、ID、`received`、`chunkBytes` |
| `GET /v1/uploads` / `GET /v1/uploads/ID` | 列出 / 查询会话状态和已提交偏移；支持 HEAD |
| `PUT /v1/uploads/ID` | `application/octet-stream`、准确 Content-Length、`Upload-Offset: N`，每块 1–262144 字节 |
| `POST /v1/uploads/ID/complete` | 空 JSON，复核完整 SHA256 和实际媒体后原子入库，返回 artifact；重复完成返回同一 ID |
| `DELETE /v1/uploads/ID` | 删除会话及其部分文件；已导入素材继续保留 |

最多四个活动会话、待接收总量 1 GiB、会话历史 64 条，磁盘预留至少 128 MiB。请求体依然最多 256 KiB，不把整个文件放入 Java 内存。大小必须为整数，SHA256 为 64 位小写十六进制；显示名 1–160 字符，不含路径或控制字符。

每块在 fsync 后更新原子元数据。相同偏移和相同已提交字节可重试；不同字节、缺口或跨越已提交末尾的块返回冲突。重启将未提交的文件尾部截回持久偏移；短文件进入失败状态，用户明确删除 / 重建。启动时清理未登记的中断导入 / 上传临时文件，保留已登记部分文件。完成时文件移动与产物元数据提交后，即使上传状态更新中断，也按 import ID 对账，不重复入库。没有自动网络续传，客户端查询偏移后显式继续。

基本请求错误为 400，缺密钥 401，Origin 403，未知 ID 404，状态冲突 409，超大请求 413，类型不符 415；全文件 digest / 媒体结构或本地存储失败沿用现有 503 错误及具体说明。错误不会发布有效素材；声明不可更改时应删除会话后重新创建。

以下脚本上传用户指定的本地 WAV，不提交推理任务：

```python
import hashlib, json, os, urllib.request

base = "http://127.0.0.1:8080"
key = os.environ["LMA_API_KEY"]
filename = "reference.wav"

def call(method, path, data=None, mime="application/json", extra=None):
    headers = {"Authorization": "Bearer " + key, "Content-Type": mime}
    headers.update(extra or {})
    request = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request) as response:
        return json.load(response)

digest = hashlib.sha256()
with open(filename, "rb") as source:
    for chunk in iter(lambda: source.read(262144), b""):
        digest.update(chunk)
declaration = {"name": os.path.basename(filename), "bytes": os.path.getsize(filename), "sha256": digest.hexdigest()}
session = call("POST", "/v1/uploads", json.dumps(declaration).encode())
path = "/v1/uploads/" + session["id"]
with open(filename, "rb") as source:
    source.seek(session["received"])
    offset = session["received"]
    for chunk in iter(lambda: source.read(session["chunkBytes"]), b""):
        result = call("PUT", path, chunk, "application/octet-stream", {"Upload-Offset": str(offset)})
        offset = result["received"]
artifact = call("POST", path + "/complete", b"{}")
print(artifact["id"], artifact["sha256"])
```

支持相应角色的真实配方才能提交 `input: {"prompt":"…", "artifacts":[{"role":"reference_audio", "artifactId":"用户所选 ID"}]}`。这里的角色名是契约示例，不代表当前 TTS 模型已支持参考音频。查看 `/v1/models` 的 `input_schemas`；现有生产配方不声明媒体角色。

## 检查与交付边界

`python tools/test_inputs.py` 通过 **64 项**真实主机文件、生产 WAV 校验和 HTTP 断言。`python tools/test_scheduler.py` 当前 **49 项**，新增生产任务入队引用保护、真实子进程读取所选字节、固定来源、同大小损坏阻止启动、取消后释放。PCM 为程序构造的采样数据；主机图像 Inspector 明确为测试端口，子进程只复制字节，没有执行模型。

UI 回归合计 **182 项**。开发媒体共 **30 张截图及录屏 / GIF**，全程 UI FIXTURE；输入表单使用明确的契约夹具，不冒充已适配的语音克隆模型。Android 文件选择器、真实图片 / 视频 codec、锁屏、升级和所有冻结模型的离线新输入输出仍待物理设备验收。

![导入素材库：界面夹具](media/development/29-imported-media-library.png)

[输入表单截图](media/development/30-local-input-role-form.png) · [录屏](media/development/foundation-ui.mp4) · [GIF](media/development/foundation-ui.gif) · [检查回执](../verification/development/inputs.json) · [开发更新说明](releases/v0.3.0-dev.11.md)


## dev.21 配套原文与时长约束

签名引擎的输入角色可声明 `transcript: {label, maxLength}` 和 `minDurationMs`。选择该角色素材后，`input.transcripts` 必须包含同名非空原文；每项最多4000字符、总计最多8项，整个请求仍不超过32000字符。没有素材、角色未声明文本能力、额外 /空 /错误类型原文均拒绝。该结构向后兼容原有仅素材角色；提示说明由引擎schema提供并转义显示。

UI按最短 /最长时长筛选素材，选择音频后启用必填原文，刷新保留未提交配对；任务冻结原文和素材ID /摘要，执行前再次检查规则及实际文件。[SoulX](SOULX_ENGINE.md)使用连续的 `reference_s1`–`reference_s4`，每个所选参考都有原文；实际采样率 /声道 /PCM数值在引擎与原生层再核对。没有新增路径 /远程音频URL输入，也不启动模型下载。

# LMA API 接入

> 当前 v0.3.3：[四图标定、MV 校验导入、独立参数、API 与主动诊断](MULTIVIEW_DIAGNOSTICS.md)。原有能力保留，下方旧开发检查点按原版本理解。[当前实现](IMPLEMENTATION_V033.md) / [仅程序验证](PROGRAM_VALIDATION.md)。

> v0.3.2：新增四类语音与单图生 3D，完整格式 / 组件 / 操作 / API / 构建 / 程序检查见[扩展指南](SPEECH_3D_EXPANSION.md)；原有功能保留，以下开发检查点按原版本理解。

> 当前 / Current: **v0.3.0**. [完整程序集成 / implementation](IMPLEMENTATION_V030.md). [仅程序验证策略 / validation](PROGRAM_VALIDATION.md) 优先于下文历史完整模型 / 手机运行门槛；旧检查点与失败记录保留为历史。Original PixArt multiscale LTX is now integrated; quality/device acceptance remains untested. [Release](releases/v0.3.0.md).


dev.38 新增 [Z-Image-Turbo 完整四组件、下载与本地业务](ZIMAGE_TURBO.md)，复用匹配原 Qwen3-4B 和外置词表，保留独立八步配置与全部冻结验收门槛。

FLUX.2-klein 4B 新增完整四组件可选目录和匹配 HF 文件建议；[使用逻辑、参数与证据](FLUX2_KLEIN.md)。App 只交付基座，所有下载仍由用户主动选择。

dev.36：超限上传继续返回 413，正文内存上限仍为 256 KiB。解析失败先发送完整响应，再以最多 256 KiB + 1 字节、250 ms 的限制清理输入并关闭，避免未读请求导致 TCP reset 吞掉错误响应。慢速或过大输入不会无限占用连接。

当前 dev.30：[旧 LTX 本地视频闭环](LTX098_APP_FLOW.md) / [English](LTX098_APP_FLOW.en.md)，[编号交付与完整同版待办](releases/v0.3.0-dev.30.md)。新增顺序执行的 T5 / Vulkan DiT / VAE / 手机 AVC 适配器，复用模型独立设置、共享队列和结果库；旧资产记录保持不可变，新生成变体由用户明确关联。官方变体、数值 / 画质 / Android 与完整 Release 尚未验收。

dev.29 历史检查点：[本机增量音频与流式试听](AUDIO_STREAMING.md) / [English](AUDIO_STREAMING.en.md)，[编号交付及完整同版待办](releases/v0.3.0-dev.29.md)。模型独立选择流式设置；接口与页面共用有界缓存；完整 WAV 校验后发布。训练 Realtime / Android 尚未验收，历史失败保留。


dev.28 的 LCM 准备 / 关联复用本页的 `model.prepare` / `model.assemble` / `image.generate` 与共用任务协议。只能选择随 App 分发的固定方案，不接受程序路径或隐式补下载；见[来源、参数和使用顺序](LCM_APP_FLOW.md)。

[历史管理 API](TASK_RECOVERY.md#4-本地-api)：先 `GET /v1/jobs/history` 检查计划，再明确将其中 `ids` / `review` 提交到 `POST /v1/jobs/history/clear`。只清理所选终态记录及幂等键，素材和活动任务保留。

新增 [运行前检查 API](TASK_PREFLIGHT.md)：`POST /v1/jobs/preflight` 与实际生成提交共用校验器，返回缺失条件、有效参数与资源；不创建任务或下载模型。

[English](API.en.md) · [文档目录](README.md)

新增 [生成草稿 / 请求恢复 API](TASK_WORKBENCH.md#本地-api)：草稿独立保存，任务与结果可取得可编辑请求，再由客户端明确提交到同一本机队列。

下列原有文本接入示例对应公开 **v0.2.0**。内部 **0.3.0-dev.2** 的独立接口、异步任务和产物接口见本文末节；开发包没有完成全部模型或真机验收。

## 地址、鉴权和模型

- 本机默认 Base URL：`http://127.0.0.1:8080/v1`。
- 外部设备：先在“服务”开启局域网，改用界面显示的手机 IP；客户端与手机需要网络可达。
- 请求头：`Authorization: Bearer YOUR_LMA_API_KEY`。密钥从手机界面复制，不是云端 OpenAI 密钥。
- `GET /v1/models` 返回当前加载模型的别名，例如 `m08`。HF 下载模型使用稳定的 `hf_...`，手动添加使用 `custom_...`，不要从文件名猜测 ID。HF 令牌只用于仓库访问，不能代替推理 API 密钥。
- 模型必须已加载且就绪；仅下载文件不足以提供接口。单模型、单推理槽不保证并行吞吐。

这里只承诺所述 OpenAI 兼容 models / chat-completions / SSE 表面，不承诺 Responses、语音、图像、嵌入、工具调用或所有供应商参数。

## curl

```bash
curl http://PHONE_IP:8080/v1/models \
  -H "Authorization: Bearer YOUR_LMA_API_KEY"

curl -N http://PHONE_IP:8080/v1/chat/completions \
  -H "Authorization: Bearer YOUR_LMA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"m08","messages":[{"role":"system","content":"请清楚简洁地回答。"},{"role":"user","content":"你好"}],"temperature":0.7,"max_tokens":256,"stream":true}'
```

`PHONE_IP`、密钥和模型 ID 都需替换。`-N` 关闭 curl 输出缓冲。非流式请求使用 `"stream":false`；生成较慢时应适当延长客户端超时。

## Python（仅标准库）

设置 `LMA_BASE_URL` 与 `LMA_API_KEY` 环境变量，密钥不写进仓库或示例文件：

```python
import json
import os
import urllib.request

base = os.environ.get("LMA_BASE_URL", "http://127.0.0.1:8080/v1").rstrip("/")
headers = {"Authorization": "Bearer " + os.environ["LMA_API_KEY"]}
request = urllib.request.Request(base + "/models", headers=headers)
with urllib.request.urlopen(request, timeout=30) as response:
    model_id = json.load(response)["data"][0]["id"]

payload = {"model": model_id, "messages": [{"role": "user", "content": "你好"}],
           "stream": True, "max_tokens": 256}
request = urllib.request.Request(base + "/chat/completions",
    data=json.dumps(payload).encode("utf-8"),
    headers={**headers, "Content-Type": "application/json"})
with urllib.request.urlopen(request, timeout=300) as response:
    for raw in response:
        line = raw.decode("utf-8").strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        event = json.loads(data)
        choices = event.get("choices", [])
        if choices:
            print(choices[0].get("delta", {}).get("content") or "", end="", flush=True)
print()
```

示例只输出正文；某些模型会通过 `reasoning_content` 或 `reasoning` 给出思考内容，客户端可单独处理。读取 HTTP 行会重组网络字节分片，不应把一次 socket 读取当成一个 token 或完整 SSE 事件。原生 ChatRunner 对生产流另外做 UTF-8、事件长度和错误检查。

## PowerShell 非流式示例

```powershell
$lmaBase = 'http://PHONE_IP:8080/v1'
$lmaHeaders = @{ Authorization = "Bearer $env:LMA_API_KEY" }
$lmaModels = Invoke-RestMethod "$lmaBase/models" -Headers $lmaHeaders
$lmaBody = @{
    model = $lmaModels.data[0].id
    messages = @(@{ role='user'; content='Hello' })
    max_tokens = 128
    stream = $false
} | ConvertTo-Json -Depth 6
Invoke-RestMethod "$lmaBase/chat/completions" -Method Post -Headers $lmaHeaders `
    -ContentType 'application/json; charset=utf-8' -Body $lmaBody -TimeoutSec 300
```

## 参数和边界

“本地”中每个模型独立保存的线程、上下文和思考模式影响其引擎启动；全局服务端口保留在“设置”。每个模型的输出上限、温度、系统提示词用于应用内默认对话。详见[模型参数与约束](MODEL_SETTINGS.md)。外部客户端应显式发送自己的消息、采样参数和输出上限；LMA 不把界面系统提示词强行注入所有外部请求。

生成在 EOS、token 上限、客户端取消或引擎故障时结束。进程停止或重载会打断现有连接。只有实际生成才有 token 输出；“后台接口”不表示无请求时自动无限生成。

局域网为明文 HTTP，未内置 TLS / 公网穿透。默认仅本机；可见 API 密钥和“复制示例”含实际凭据，不要截图或提交。模型下载采用 HTTPS，与推理接口是不同链路。

| 问题 | 核对 |
| --- | --- |
| 无法连接 | 模型就绪、手机 IP、LAN 开关、端口、网络隔离 |
| 鉴权失败 | 当前安装的密钥及 Bearer 请求头 |
| 模型不匹配 | 重新查询 `/v1/models`，切换模型会改变别名 |
| 请求过大 / 上下文不足 | 缩短历史、提示词与输出，或在内存允许时调上下文 |
| 流中断 / 没有结束标记 | 保留已收正文并显示错误，不把它计为完整成功 |

示例依据固定上游接口及桌面协议检查编写；尚未通过手机实际运行的 ARM 引擎作端到端验证。

## 0.3.0-dev.2：独立接口、任务与结果

这是当前开发代码，尚未发布完整 v0.3.0。服务页的“启动接口”无需安装或加载模型；“关闭接口”只关闭客户端入口，文本模型可独立保留。模型选择器中可停止文本模型；通知中的“停止服务”仍停止全部运行工作。安装 / 升级不替用户启动新的模型下载。App 内任务和异步 API 使用同一个 `LocalJobs`、任务 / 产物存储及校验。

所有下列接口均要求 `Authorization: Bearer YOUR_LMA_API_KEY`，包括 `/health`、事件和结果读取。默认绑定手机 `127.0.0.1`；显式开启局域网仅允许客户端向这台手机提交请求，计算仍全部在手机。原生文本引擎使用单独的随机回环端口和独立进程密钥，不能通过公开端口绕过准入与模型设置。

| 方法与路径 | 行为 |
| --- | --- |
| `GET /health` | 接口状态、文本状态、当前任务；零模型也可运行 |
| `GET /v1/models` | 仅列用户已安装的模型，包含 `task_tags`、引擎、配方 / 参数、`loaded`；目录条目不等于安装，安装也不等于设备验证 |
| `GET /v1/engines` | 实际注册的引擎构建元数据；不创建空引擎 |
| `POST /v1/chat/completions`、`POST /v1/completions` | 当前已加载文本模型的纯文本请求，支持原始 SSE；不自动切换 / 下载其他模型 |
| `POST /v1/jobs` | 校验后持久入队，返回 `202` 和任务 ID；不代表已生成成功 |
| `GET /v1/jobs`、`GET /v1/jobs/ID` | 有界任务摘要 / 完整快照、状态、错误与产物 ID |
| `POST /v1/jobs/ID/cancel`、`POST /v1/jobs/ID/retry` | 显式取消；只对失败 / 中断 / 取消记录创建新任务重试 |
| `DELETE /v1/jobs/ID` | 删除终态历史；活动任务须先取消 |
| `GET /v1/events`、`GET /v1/jobs/ID/events` | JSON 游标事件；请求 `Accept: text/event-stream` 获取 SSE |
| `GET /v1/artifacts`、`GET /v1/artifacts/ID` | 结果摘要 / 原始元数据与来源参数 |
| `GET /v1/artifacts/ID/content` | 原始字节，支持一个 `Range` 与 `206 / 416`；`HEAD` 仅返回头 |
| `DELETE /v1/artifacts/ID` | 独立删除未被使用的结果；下载 / 预览 / 导出读取期间有引用保护 |

从已安装的模型包记录（具有 `recipe` 字段）选择对应 `id` 作为 `bundleId`，不要从名称猜测。既有文本记录保留聊天 / completions，并可使用其不可变 `bundle_id` 提交异步 `text.generate`。示例只表示调用结构，所选包、实际引擎与任务能力必须匹配；当前目录中未实测的 SD1.5 候选不能据此称为已支持。只有用户明确同意尝试未测配方时才发送 `allowUnmeasured: true`。

```bash
curl http://PHONE_IP:8080/v1/jobs \
  -H "Authorization: Bearer YOUR_LMA_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: my-image-request-1" \
  -d '{"bundleId":"USER_SELECTED_BUNDLE_ID","type":"image.generate","input":{"prompt":"A small garden"},"parameters":{"seed":123},"allowUnmeasured":true}'
```

任务输入接受 `prompt` / `negativePrompt` 文本及显式 `artifacts: [{role, artifactId}]`；媒体角色必须由所选签名引擎声明，现有生产配方仍只接受文字。`parameters` 必须为 JSON 对象、`allowUnmeasured` 必须为布尔值；其他输入不被静默忽略，也不会转为网络获取。输入回执由服务端固定，执行前复核完整 hash；排队和执行期间禁止删除素材。见[本地输入](LOCAL_INPUTS.md)。参数先应用模型 / 配方独立配置，再执行同样的约束与归位；任务保存不可变有效参数。相同幂等键和相同请求返回原任务；改变请求返回冲突。任务重试产生新 ID，历史不被重写。缺资产、缺引擎、资源不足、未授权尝试未测配方均在本机失败，接口不会触发下载。媒体任务与文本回复共用执行槽，等待当前回复并自动回收 / 切换引擎；完整设备调度验收仍在本版待办。

文本请求采用所选模型的输出 / 温度默认值，输出上限归位到该模型已保存的限制及上下文边界；不注入 App 系统提示词。只接受受支持的纯文本字段，拒绝媒体 URL、工具等未接入字段和多推理槽。外部文本请求占用期间，App 聊天、模型切换和需要重载的参数变更不能越过占用检查。停止或断开文本连接释放其原生连接；断开任务事件订阅不会取消持久任务，取消必须调用对应端点。

事件查询使用 `?after=SEQUENCE` 或 `Last-Event-ID`，两者同时提供须一致。`/v1/events` 还可用 `job_id=ID`。JSON 的 `cursor` 表示已读取到的全局序号；保留 512 条事件，过旧游标返回 `truncated`，SSE 会发送 `reset` 提醒重新读取任务快照。SSE 单连接最长 120 秒、每约 10 秒心跳，客户端按游标重连；同时最多两路事件流，仍可改用 JSON 轮询。

传输限制：请求头 16 KiB、请求体 256 KiB、JSON 嵌套 32 层；POST / PUT 要求 `Content-Length`，不接受 HTTP chunked / multipart / `Expect`。分块素材上传每次 PUT 最多 256 KiB，沿用同一鉴权。不提供文件系统路径或远程转发端点。所有响应关闭缓存、启用 `nosniff`；不开放浏览器 CORS，原生客户端和 App 自己的桥接不受此限制。原始产物同时最多三路读取；超出数量返回 `503`，活动读取结束即可重试。明文 HTTP / 无 TLS 的既有限制仍适用。

当前开发证据：67 项接口检查使用实际本机 socket、生产路由 / 存储和显式执行替身；文本后端还检查生产 `ApiHost` 对真实子进程替身的代理与占用释放。它们不是 Android 模型输出或后台耐久证据。完整余项见[实施记录](DEVELOPMENT.md)。

dev.3 的已安装 TTS 候选使用相同异步任务接口，`type: "speech.synthesize"`、`input: {"prompt": "Hello world."}`；参数独立属于模型。输入 1–4000 字符，不接受负面提示词，缺语言组件不会下载 / 转出执行。当前完整配方和限制见[语音基座](TTS_ENGINE.md)；没有手机推理证据。

## dev.4：显式 LoRA 选择

`POST /v1/jobs` 的 `image.generate` 可选 `adapters: [{"bundleId": "本机适配器包ID", "scale": 0.75}]`，最多八个，省略强度时固定各自保存值。基础模型与适配器必须完整安装且声明兼容；重复、自身、路径、未知字段或非生图任务的选择拒绝。缺资产不下载。配对 / 强度 / 来源与验证边界见[LoRA 指南](ADAPTERS.md)；没有真机生成证据。

dev.7：通用包的 `/v1/models` 条目增加 `version` 元数据（尚无版本组时为 `{}`），包含 `groupId` / `activeBundleId` / `isActive` / `members`，有更新计划时附 `pending`。已安装的旧版仍以原 ID 列出；“当前版本”不重定向旧请求。更新 / 差异 / 确认切换目前使用 App 原生命令，不新增 HTTP 更新端点。见[模型更新](MODEL_UPDATES.md)。

## 0.3.0-dev.8：文本包任务

用户新建并安装的 `text_gguf_cpu_v1` 包可以向 `POST /v1/jobs` 提交 `{"bundleId":"USER_SELECTED_BUNDLE_ID","type":"text.generate","input":{"prompt":"介绍本地模型"},"parameters":{"maxTokens":128},"allowUnmeasured":true}`。沿用密钥与可选幂等键，用户须明确同意尝试未测配方；不会下载模型。选择实际安装的包 ID，任务固定该版本。

结果的鉴权 `/v1/artifacts/ID/content` 返回 `application/vnd.lma.text+json`，包含 `schema: lma.text-result/1`、`content`、`reasoning`、`finishReason: stop|length` 和已提供的 `usage` token 计数。输出增量由私有引擎 SSE 消费，公共任务事件仍是阶段 / 状态事件；此异步接口不冒充聊天 token SSE。

`GET /v1/models` 新增通用包的 `parameter_error` 字段；不兼容导入单独报告，不阻断其他模型列表。现有 chat / completions 仍针对已加载旧文本路径。dev.9 已接入旧记录本地迁移，dev.10 已接入共用执行槽；完整设备验收仍待完成。详见[文本实现与边界](TEXT_ENGINE.md)。

dev.9 迁移后的旧文本行继续使用原 `id`，并返回 `bundle_id`。异步 `text.generate` 请求明确使用该不可变值作为 `bundleId`；不会自动下载或切换聊天模型。同步接口使用用户已选文本模型，暂时卸载时可等待同一执行槽；其他引擎的真实输入管线和真机门槛仍待完成。见[迁移与 ID 规则](MODEL_MIGRATION.md)。

## 0.3.0-dev.10：共用执行槽

`GET /health` 增加 `scheduler`：`policy: single_engine_fifo`、`active` 和 `waiting` / `waitingCount`；票据包括 `kind`（load / chat / api / job）、`modelId` 与状态（active / waiting / reaping）。无模型时槽为空，不自动选择或下载。

已选文本模型在媒体任务期间暂时卸载时，同步文本请求可等待槽并恢复原模型。参数在等待前按模型规范化；响应仍为原 JSON / SSE。另一条交互式文本请求活跃或等待时返回忙碌；关闭 API 监听取消等待者，独立异步任务继续。客户端等待可能较长，持续任务使用异步接口。详见[顺序、取消与进程边界](SCHEDULING.md)。

## 0.3.0-dev.11：本地素材上传

`POST /v1/uploads` 明确声明 `{name, bytes, sha256}`；`GET /v1/uploads/ID` 查询偏移，`PUT /v1/uploads/ID` 使用 `application/octet-stream` 与 `Upload-Offset` 续传，`POST /v1/uploads/ID/complete` 校验后返回素材 ID，`DELETE` 清理会话。最大单文件 512 MiB，最多四个活动会话；已有结果和导入素材共用 `/v1/artifacts` 的读取 / 导出 / 删除保护。完整请求、限制、Python 示例和证据边界见[输入指南](LOCAL_INPUTS.md)。这不会增加当前模型的媒体输入算子。

dev.12 扩散任务由服务端生成 `diffusionPlan`：保留普通请求参数，另外固定实际采样策略 / 参数 / 调整记录。客户端不能提交该派生字段；重试剥离旧计划，执行前用不可变模型与适配器租约复核。LCM / SD-Turbo 配方关闭 CFG、拒绝负面提示，不修改基础模型设置。完整组件、配对与请求例子见[扩散指南](DIFFUSION_ENGINE.md)。


dev.13 的四条[高级扩散 / 视频路线](ADVANCED_DIFFUSION.md)复用现有任务 API。使用已选择 / 安装的 bundleId，Wan 提交 video.generate，其他三条提交 image.generate。flowShift、尺寸、frames / fps 随该模型 schema 归位；服务端派生 diffusionPlan，客户端不能自行提供。缺组件失败，不触发下载；仍无这些模型的 Android 输出证据。

Qwen3-TTS 0.6B Base 复用 `POST /v1/jobs` 的 `speech.synthesize` 与本地 `reference_audio` 输入；不新增 OpenAI `/v1/audio/speech` 兼容声明。有效采样参数、实际种子、音频帧与 RTF 保存在执行记录，未测不能声称实时；见 [Qwen 语音接口示例](QWEN_TTS_ENGINE.md)。

## MOSS Delay 本机任务

`moss_delay_native` 复用 `speech.synthesize`、模型独立参数、共用队列和 WAV 产物。只有所选包含原生编码器时才提供可选 `reference_audio`；普通 TTS 不需要编码器或默认音色。详见 [MOSS Delay 管线与执行回执](MOSS_DELAY_ENGINE.md)。没有新增 `/v1/audio/speech` 兼容性声明。

[MOSS Local-v1.5 / SoundEffect-v2](OPENMOSS_ENGINE.md) 共用 POST /v1/jobs，分别使用 speech.synthesize / audio.generate；没有新增远程 provider 或 /v1/audio/speech 兼容声明。参数、参考素材、取消和回执按各配方独立校验。

### MOSS 对话与声音设计

四种新增 openmoss delay 配方共用 `POST /v1/jobs` / `speech.synthesize`。使用自己已安装的 `bundleId`；`voiceInstruction` / `language` 是每模型参数，本次任务覆盖不会保存为默认。VoiceGenerator 必须填写声音描述，且不接受参考输入；TTSD 文本须含 `[S1]`、`[S2]`，可选的 `reference_audio_s1` / `reference_audio_s2` 素材角色须成对提供。素材由用户导入，不能在请求中提供任意文件路径或远程推理地址。完整格式与边界见 [MOSS 指南](OPENMOSS_ENGINE.md)。

```json
{
  "bundleId": "your_installed_voicegen_bundle",
  "type": "speech.synthesize",
  "input": {"prompt": "你好，这是由用户选择的本地模型任务。"},
  "parameters": {"voiceInstruction": "成年、低沉、温暖的声音", "language": "zh", "maxNewTokens": 375},
  "allowUnmeasured": true
}
```

`allowUnmeasured` 表示用户明确尝试尚无当前设备记录的配方，不是兼容性证明；资源或组件不满足仍在本机失败。模型加载、推理、编码 / 解码都发生在运行 LMA 的同一手机。


## dev.21 SoulX配套输入

`POST /v1/jobs` 的 `speech.synthesize` 可选择实际已安装的SoulX包，通过 `input.artifacts` 绑定 `reference_s1`–`reference_s4`，并在 `input.transcripts` 用同名角色填写实际原文。任务冻结两者；缺原文、编号断档、未提供参考的说话人或外部路径均拒绝。仍沿用相同鉴权、幂等键、事件、取消、重试及产物读取，不增加远程推理或语音端点兼容声明。完整JSON、参数和未完成门槛见 [SoulX接口与使用逻辑](SOULX_ENGINE.md#5-同一鉴权任务接口)。

## dev.22：明确的运行资产准备任务

[准备 API 合同与示例](MODEL_PREPARATION.md)增加 `model.prepare`，使用现有 `POST /v1/jobs`、鉴权、幂等、事件、取消和重试。只接收所选 bundleId、准备方案ID和指纹；服务器冻结源包身份，拒绝客户端文件路径/URL/模块/生成参数。成功保存准备回执，不伪造媒体产物。`GET /v1/models`增加 `preparation_plans` / `prepared_assets`，包含只有派生资产的本地记录；`installed`仍表示源组件安装状态。准备程序不登记为生成引擎，完整视频生成仍未开放。独立删除派生文件通过App，不提供任意路径删除接口。

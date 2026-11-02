# v0.4.0 · 对话与本地创作

[English](CONVERSATION_V040.en.md) · [20261102 原始范围](UPDATE_DIRECTION_20261102.md) · [Release](releases/v0.4.0.md)

本版将 20261102 方案的 D01–D12 作为同一批程序功能接入。APK 仍只提供基座；用户选择模型、明确下载或导入，全部推理、预处理和合成在同一 Android 手机完成。原推荐、62 配方、82 包、18 扩展引擎加文本、端口 52187、原签名和既有模型文件保留。

这里的“程序实现”不等于每个模型都已在手机成功生成。本次没有可用 ADB 设备，不下载完整模型做验收；Android 视觉预处理、MediaCodec 合成、此版本实机交互耗时和锁屏耐久尚无新的真机结果。旧版测评保留原 APK 身份，3D 的 `empty_structure` 和视频质量问题没有被改写为成功。

## 入口与日常操作

| 编号 | 操作 | 行为与边界 |
| --- | --- | --- |
| U01 | 在“模型”选择推荐／全部 HF／本地 | 保留原推荐顺序；输入、输出、工具、证据、本地状态可组合筛选。未知不是不支持。HF 发现仍有界分页、显式搜索和离线缓存。 |
| U02 | 对话切换生图／视频／配音／音乐／3D | 选择已安装的兼容模型，填写提示词和本次参数，直接发送；无需安装或加载语言模型。 |
| U03 | 引用素材 | 先导入或从结果库选择，再明确选择画面／配音／音乐等用途。相同类型有多个候选时不能替用户猜测。 |
| U04 | 点击任务卡 | 与工作台和 API 使用同一任务 ID；查看阶段、取消、结果、错误和编辑后重试。失败记录和原产物保留。 |
| U05 | 编辑失败任务 | 从原请求恢复提示词、模型和临时参数，重新预检后创建新尝试；记录父任务，原失败不覆盖。 |
| U06 | 修改“本次参数” | 可编辑数值和 JSON；数值越界在界面／原生预检中归位。不会写回模型默认值；默认值仍在本地模型设置里保存。 |
| U07 | 打开历史 | 会话每页 40 条，消息每页最多 60 条，游标访问较早内容。换页不会重新生成任务。 |
| U08 | 选择主题 | 新安装、缺失或非法偏好默认暗色；有效的暗色／浅色／跟随系统偏好保留。启动背景、原生窗口和网页首帧一起处理。 |

图片、音视频和 GLB 在消息中保存为受管引用；点击后才打开原有查看器。离开页面释放播放器，消息内不嵌入完整媒体字节。会话、活动任务、任务链和文件租约共同保护被引用素材；删除会话解除其引用，不自动删除共享产物或模型。

## 能力标签与视觉配对

14 个语言模型逐个保存精确仓库、revision、文件以及原生能力声明、LMA 接入、组合能力、证据字段。Gemma 3 1B、普通 Qwen2.5、Llama 3.2 文本变体不继承其他视觉产品能力。Uncensored／Abliterated／NSFW 仍是独立内容标签。

本机视觉桥使用已打包的 llama.cpp server／mtmd，以主 GGUF 和匹配 projector 显式启动；图片内容实际传入 `image_url` 内容块，不以文件名冒充视觉。视觉组件不会出现在独立可对话模型广播中。

1. 停止驻留文本模型，选择正确的具体变体，打开“视觉配对”。
2. 核对主 GGUF SHA256、架构及 projector 的仓库、固定 revision、SHA256、字节数、下载地址和许可。保存只声明组件。
3. 在模型管理中明确下载该组件，或用其清单从手机文件夹导入；完成后再加载主模型。
4. 引用图片后发送。缺组件、主哈希不符、纯文本变体和不支持的输入都会明确阻止。
5. 更改配对前先停止模型。解除配对后才能清理该组件；其他共享引用和活动租约仍受保护。

预置 **m15 Qwen3.5 4B HauhauCS** 的发布者配对：主文件 `79e28e…62741`，projector `a1e32e…a0f22`，675,568,768 字节，固定 revision `c09cdbcdb1fefad6d335809d445621b5f5ba0c6e`，Apache-2.0。来源：[发布者固定版本文件](https://huggingface.co/HauhauCS/Qwen3.5-4B-Uncensored-HauhauCS-Aggressive/blob/c09cdbcdb1fefad6d335809d445621b5f5ba0c6e/mmproj-Qwen3.5-4B-Uncensored-HauhauCS-Aggressive-BF16.gguf)、[LFS 身份指针](https://huggingface.co/HauhauCS/Qwen3.5-4B-Uncensored-HauhauCS-Aggressive/raw/c09cdbcdb1fefad6d335809d445621b5f5ba0c6e/mmproj-Qwen3.5-4B-Uncensored-HauhauCS-Aggressive-BF16.gguf)。这提供配对来源，不代表手机输出或质量通过。m03／m09／m16 未取得足够的固定组件身份，保留待核对状态，可由用户提供明确核对的完整清单；没有自动替换为其他模型。

视觉输入限 1–4 份受管素材，图片最长边缩放至 768，源图最多 4096² 像素，请求图像字节总计最多 4 MiB。视频限 30 秒，每段最多 3 张带时间戳的采样帧，总帧数最多 4；受上下文、文字及输出预算共同限制。抽帧属于组合图片理解，不标为原生视频理解。服务端仍对实际 token 数做最终约束；这些保守估算不保证任意 tokenizer 适配。原生音频、转写、专门 OCR 任务和 3D 理解保持未接入状态。参考 [llama.cpp 多模态接口](https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md)。

## 自动模式与工具草稿

自动模式依赖用户明确加载的本地语言模型及其模板；并不保证小模型能正确选择工具。程序分别接收普通文字、思考和流式 `tool_calls`，按索引合并片段，校验完整 JSON、唯一 call ID、工具白名单、模型和素材、临时参数后保存草稿。普通回答或代码块不会成为指令。

工具包括 `image_generate`、`video_generate`、`speech_synthesize`、`audio_generate`、`mesh_generate`、`media_compose`、`task_status`、`asset_select`。用户核对／编辑后才接纳生成任务，未实测配方需要明确同意；没有下载、删除、任意路径、shell 或外部推理工具。

每个计划最多 8 个步骤。无效格式保留记录，可明确请求一次模型格式修正；超过一次改为手动操作或新计划。调用和结果摘要按 call ID 保存，任务结束后使用原结果续写。同一会话已有新用户输入时，不自动插入旧计划续写。中断续写可明确恢复。媒体阶段仍使用原重计算执行槽，释放／暂停文本驻留后计算，空闲时按既有逻辑恢复。

## 模板与同机合成

| 编号 | 模板 | 配置 |
| --- | --- | --- |
| W01 | 提示词 → 图片 | 选择图片模型；规划器可选。 |
| W02 | 图片 → 短视频 | 选择真实接受图片角色的视频路线，显式绑定上一步产物。生成视频必须实际大于 5 秒。 |
| W03 | 提示词 → 旁白 → TTS | 选择文本、TTS 模型；已有旁白可勾选省略语言模型。 |
| W04 | 图片 → 3D → 可选材质 | 选择几何路线，可增加兼容的材质步骤；原有 GLB 查看器复用。 |
| W05 | 画面＋配音／音乐 → 成片 | 使用内置 `media.compose`，无需下载 AI 模型。 |
| W06 | 素材理解 → 回答 | 进入受能力与组件约束的视觉对话；不把 TTS／生成模型当作理解模型。 |

每步可选择 operation、模型、提示词、临时参数和受管输入；未来输入以 `step`／`output`／`role` 绑定，只能依赖前面的明确步骤，最多 8 步。没有节点画布、插件、任意脚本或外部工作流导入。

计划先持久保存，使用稳定的步骤／尝试编号接纳原任务。失败阻断依赖步骤，取消传递给活动任务并阻止新接纳；已成功步骤不重算。单步重试保留旧尝试和成功产物。程序重启在 SQLite outbox 与任务存储间对账，卡片和任务跨存储提交前后均以原编号恢复。

`media.compose` 接受一份 PNG／JPEG／MP4 画面和至少一条 WAV 声轨，可分别配置配音／音乐音量 0–2，线性重采样、混音和饱和限幅，短音频补静音，长音频裁剪。原视频音轨被所选混音声轨替换；视频不足目标时长会拒绝，不循环或补帧。图片成片明确标记静态展示，限 15 秒；视频合成限 60 秒，目标 5.1–60 秒，需核对实际输出大于 5 秒且存在真实 AAC 音轨。生成运动视频原有检查不使用静态展示豁免。源文件保留，取消和损坏输入会清理本次临时文件。

## API 合同与示例

本机 `http://127.0.0.1:52187/v1`；用户打开内网访问后使用手机 IP。原鉴权、缓存、模型发布条件、任务、事件和上传接口保留。`GET /v1/models` 仍只广播安装完整、配置有效的 AI 模型；能力声明放在 `x_lma.native_capabilities`，不把组合能力升格成该模型的可执行 operation。

`GET /v1/capabilities` 增加独立内置合成工具、任务链限制，以及 `chat_input_types: ["text"]`。**公共 OpenAI 对话仍为文本子集**；本次 App 视觉桥使用进程内构造的受管附件内容，不因此开放公共 URL 抓取、任意 `image_url` 或音频输入。标准图片／语音接口仍输出 PNG／WAV，视频、音乐、3D、合成和任务链使用明确的 LMA 异步扩展；Sub2API 客户端按声明路由。

```json
{
  "model": "builtin_media",
  "type": "media.compose",
  "input": {"prompt": "本机成片", "artifacts": [
    {"role": "visual", "artifactId": "替换为真实图片或视频ID"},
    {"role": "voice", "artifactId": "替换为真实WAV_ID"}
  ]},
  "parameters": {"durationSeconds": 6, "voiceGain": 1, "musicGain": 0.25}
}
```

以上请求发至 `POST /v1/lma/jobs`，同时提供 `Authorization: Bearer <手机设置中的密钥>` 和稳定 `Idempotency-Key`，先用 `/v1/lma/jobs/preflight` 核对。内置工具不放入 AI 模型列表。

任务链：`POST /v1/lma/chains`，Body 为 `{ "template": "W02", "steps": [...] }`；每步 `request` 使用公共 `model` ID，可有 `dependsOn: [0]` 和 `bindings: [{"step":0,"output":0,"role":"具体引擎要求的角色"}]`。查询 `GET /v1/lma/chains/{id}`，取消 `POST .../{id}/cancel`，单步重试 `POST .../{id}/retry`、Body `{"step":1}`。重复相同键和 Body 返回原计划，冲突 Body 拒绝。会话内部 ID 和私有默认提示词不进入公开返回。

生成不设固定总耗时上限；HTTP 同步等待、SSE 连接寿命、编码器无进展检测与任务生命周期分开。超时后先查询原任务，不换新键重复生成。

## 本轮实现与验收

| 编号 | 实现 | 程序证据与实际限制 |
| --- | --- | --- |
| D01 | 精确变体能力描述、标签、组合筛选 | 元数据／视觉配对／HTTP 集成检查；未知能力不开放。 |
| D02 | mtmd 加载、组件管理、图片／抽帧输入 | Android 编译、固定配对、负例；此 APK 尚未做手机视觉输出验证。 |
| D03 | SQLite v2、旧字节兼容读取、游标、outbox | 真实 host SQLite 100 会话／1000 旧消息、失败回滚；不是 Android 框架实机测试。 |
| D04 | 统一模式、附件、临时参数 | 无 LLM 的五类直接任务界面用例，双层参数约束。 |
| D05 | 持久原任务卡与新尝试父关系 | 崩溃窗口、幂等、编辑／取消／重试检查。 |
| D06 | 工具合并、严格 JSON、确认、结果续写 | 白名单、重复 ID、越权、预算、无效格式负例；模型规划可靠性未知。 |
| D07 | 素材引用、来源链、删除保护 | 原件不删除；旧来源缺失如实记录，不伪造哈希。 |
| D08 | 受控依赖、模板、复用、父取消 | 生产状态机与实际存储重开、进程退出窗口测试。 |
| D09 | 本机混音、编码、合成 | 真实 PCM、损坏 WAV、增益、重采样和静音补齐；Android 编解码输出尚待真机。 |
| D10 | 暗色首帧、增量块、按需媒体、定向快照 | 1000 混合消息仅挂载 60 条；token 只改目标行。不是本版手机性能测评。 |
| D11 | 发现合同、独立工具／链 API | 实际 host HTTP 鉴权、绑定、幂等、查询／取消；公共对话输入明确为文本。 |
| D12 | 冻结范围回归、双语文档、媒体、正式发版 | 发布包、签名、源文件指纹与稳定 Release 检查；不沿用旧版 APK 的实机结论。 |

完整测试记录随 [v0.4.0 证据](../verification/releases/v0.4.0/status.json) 发布；A01–A33 逐项映射见 [实施清单](../catalogue/conversation-20261102-implementation.json)。`program_verified`、`android_compiled`、`device_not_run` 分开记录，不以总数掩盖未执行项。

程序界面材料：[分块对话](media/conversation-v040/01-block-chat.png)、[直接任务](media/conversation-v040/02-direct-generation.png)、[显式声轨](media/conversation-v040/03-explicit-composition.png)、[顺序模板](media/conversation-v040/04-sequential-template.png)、[录屏](media/conversation-v040/walkthrough.mp4)、[GIF](media/conversation-v040/walkthrough.gif)。这些是生产 HTML／CSS／JS 加显式模拟原生桥的界面检查；不是真机，也不是模型生成样例。

OpenAPI: [v0.4.0](proposals/sub2api-openai.openapi.json). 新增链和内置合成直接调用手机服务；当前 Sub2API 源码网关保留既有媒体路由，不转发这两个新增工具。New chain/composition tools use the phone endpoint directly; the current opt-in Sub2API source gateway retains its existing media routes and does not forward them.

# LMA 0.2.0 架构

本文描述当前 APK。尚未实现的多模态扩展以[现行需求与发版计划](MULTIMODAL_RELEASE_PLAN.md)为准：所有模型平级，以功能 / 基座标签分类，采用任务表单与本机队列，不建设 ComfyUI 画布 / 节点生态。执行与后台见[本机任务](WORKFLOWS.md)，来源见[可行性研究](MULTIMODAL.md)，共用契约与源码迁移见[基座评估](FOUNDATION.md)。

## 运行链路

```text
MainActivity / 本地 WebView 资源
  │ JSON 命令、状态快照
  ▼
LmaService（specialUse 前台服务、通知、停止操作）
  ├── Downloads → HTTPS / SAF → .part → GGUF / SHA256 → .gguf
  ├── EngineHost → nativeLibraryDir/libllama-server.so
  │                   └── libllama-server-impl.so + CPU 内核
  └── ChatRunner → 本机 HTTP / SSE → SQLite 持久化

外部客户端 → 本机或局域网 API → 同一个 llama-server
```

前台服务和推理进程的生命周期独立于 WebView 页面。界面退到后台不会主动取消推理；重新打开界面时从 SQLite 和持久下载记录恢复显示。

## HF 发现与本地模型管理

`LmaApp` 持有 `HubCatalog`，由 `HubClient` 使用原生 HTTPS 查询 HF。搜索和文件树各有独立串行工作线程；查询代次防止旧结果覆盖新搜索。分页状态含前后游标，仓库提交在读取文件树前固定。单次元数据最多读取 8 MiB，搜索每页至多 24 仓库、文件树每页至多 100 条目。元数据浏览不启动前台服务；进入后台时不承诺元数据任务永久存活，模型服务由原有前台服务维持。

`MainActivity` 直接派发 HF 搜索 / 文件 / 令牌命令，下载选择必须与原生端当前文件页的仓库、提交和路径一致。`LmaService.addHubModel` 将经过复核的模型交给 Store / Downloads。HF ID 根据仓库、提交和路径确定，重复选择去重，不改变 `m08 → m06 → m01` 推荐；已下载与未完成任务在“本地”统一显示，存储路径和下载状态复用既有实现。

“HF 全部格式”仅扩大仓库发现；文件选择只展示 GGUF，并解释、阻止分片、视觉投影器、超限大小和已知非文本任务。格式、架构、量化及内存仍在加载时决定。普通模型不要求无审查属性；已核对标签与在线元数据提示分开处理，见 [HF_MODELS.md](HF_MODELS.md)。

可选 HF 令牌保存在私有 SharedPreferences，页面仅收到配置布尔值。认证请求固定官方源；Net 对每次重定向重新判断目的主机，仅将令牌发送到官方 HF HTTPS 默认端口。公共请求可使用镜像回退。日志会隐藏活动 API 密钥和 HF 令牌，备份禁用；不宣称硬件加密或真实私有仓库验收。

## 引擎实现

引擎来自 ServLlama 1.2.2 发行包中的 llama.cpp v0.4.1，记录的上游提交为 `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4`。LMA 只重新分发其中 14 个 CPU 路径所需的原生库，保留 ARMv8.0 至 ARMv9 的动态 CPU 内核，不打包可选的 OpenCL / Hexagon 模块。

原生 ELF 从 APK 安装时解压到 `nativeLibraryDir`，由 `ProcessBuilder` 直接启动，不使用 shell，也不从应用可写目录执行下载的代码。API 密钥通过环境变量传入，日志会再次过滤该密钥。

服务参数固定为单推理槽、CPU 后端、批量 64；上下文和线程可配置。`--reasoning off|auto|on` 直接传给已核对版本的引擎。不同模型可能忽略思考开关。

启动前等待旧进程退出并检测端口；成功条件同时包括引擎 `/health` 就绪、携带密钥的 `/v1/models` 返回预期模型别名。进程意外退出最多恢复三次，持续失败会停止恢复并保留日志。加载超时为五分钟。

## 下载和存储

模型、进度记录和 SQLite 数据位于应用私有存储。卸载应用会删除它们。

模型路径只使用受限目录 ID，不接受 URL 或用户输入作为本地相对路径。下载只允许 HTTPS，并验证重定向协议。续传校验 `Content-Range`；服务器返回 200 时从头写入；416 只有在文件总长吻合时进入完整性校验。

内置目录的 14 个文件固定仓库提交、准确大小与 SHA256。默认自动模式先连接 Hugging Face，首个源连接超时为 8 秒、响应头读取为 10 秒；连接失败或源返回失败状态后尝试 HF Mirror。完整传输的网络读超时为 30 秒，自定义其他域名不改写到镜像。

下载串行排队，单文件上限 12 GiB，并预留 64 MiB 存储空间。导入通过系统文件选择器获取 URI，从流复制，避免将模型读进 Java 内存。导入中断后从头重新复制。

已知发布者 SHA256 不匹配的文件不会安装，转为 `.rejected`，不会接着追加损坏内容；删除模型时一并清理。不同 Service 实例对同一模型的写入共用锁，避免快速停启服务后并行写入。

下载状态持久化为 queued / downloading / pausing / verifying / done / paused / error。排队任务立即暂停；正在执行的任务断开连接后完成持久化。最终暂停状态和移除任务在同一锁下完成，避免断连时工作线程已结束而界面仍被写回 pausing。进程重建时，上次 downloading / verifying 标记为可恢复；用户主动暂停的任务保持暂停。

## 聊天

请求和 SSE 消费运行在原生线程。分块文本每约 160ms 保存到 SQLite；界面按状态通知重新读取。停止生成、网络异常、进程重建均保留已保存文本。单条回复文本和思考合计上限为 1 MiB；过大的 SSE 事件会拒绝继续读取。

聊天历史从最近 32 行中保留最多 16 条消息，按完整 user / assistant 对选择。空的失败回复连同对应用户消息一起跳过；有正文的中断回复保留，避免严格模板遇到连续 user 角色。历史按字符数保守限制；这不是模型的精确 tokenizer。当前用户提示与系统提示仍可能超过特定模型的上下文，引擎返回的错误会显示在消息中。输出长度是应用内对话默认值，外部 API 客户端可自行指定请求参数。

命令包含独立 requestId；原生端在实际执行后返回成功或失败，界面只根据对应命令的确认结果清理草稿或结束设置保存状态。快速完成的回复也会清空已发送草稿。

## 每个模型的配置

`Store` 在 AtomicFile `models-state.json` 中按 ID 保存 `profiles` / `metadata`，升级时将旧全局参数迁移到已有模型后移除全局键。`GgufMetadata` 有界读取该文件的 `general.architecture` 和对应 `context_length`，按文件大小 / 修改时间缓存。`ModelSettings` 统一归一化数值、设备及共享上下文约束；元数据未知时明确采用应用兜底。

界面从“本地”的模型卡设置打开参数，使用可编辑预设框。原生保存再次归一化并回传实际值。仅当前运行模型的加载参数变化触发重载，生成时拒绝这类变更；其他模型互不影响。`EngineHost` 使用 `app.settings(id)`，`ChatRunner` 使用 `app.settings(engineModel)`，明确读取对应模型；外部 API 生成参数仍由请求决定。详见[参数和迁移](MODEL_SETTINGS.md)。

## Android 后台

服务使用 `foregroundServiceType=specialUse`，可见通知提供停止入口，持有 CPU / Wi-Fi 唤醒锁；无工作时自动停止前台服务并释放锁。持续提供 API 的模型即使空闲也保持服务，供客户端连接。

可选开机接收器只处理受保护的开机或本应用更新广播；仅在用户开启恢复、此前服务启用且模型文件仍在时尝试启动。厂商限制、强行停止和系统资源回收无法由普通应用绝对规避。

## 界面与网络边界

WebView 只加载随 APK 分发的虚拟 HTTPS 源资源；禁止文件访问、外部网络请求和远程页面进入 JS 桥接上下文。模型名称、正文、日志、代码块均转义显示，不执行模型输出的 HTML。

默认 API 为 `127.0.0.1:8080`。用户开启局域网后监听 `0.0.0.0`；推理 API 要求安装时随机生成的密钥。局域网传输为 HTTP，不提供 TLS 或公网穿透。日志导出不包含设置中的 API 密钥，也不导出聊天数据库。

dev.14 接入 [Sana 移动管线 / MNN](MNN_SANA_ENGINE.md)：真实 ARM64 CPU worker、13 个用户自选组件、Qwen3 metadata 白名单、分阶段释放编码器、独立 CFG / token / 线程参数与不可变任务快照。74 项主机 / C++ 检查不包含模型推理；全部 21 个模板仍只登记元数据、由用户确认下载。445 项基座与 208 项界面检查通过；37 张截图及录屏 / GIF 均标识 UI FIXTURE。没有 Android 生图 / 耐久证据，完整 v0.3.0 的冻结目标和发布门槛保持不变，未创建新 Release。

## dev.23：准备到运行模型的显式关联

`ModelAssemblies`读取App签名元数据；`AssemblyPlan`在运行环境绑定准备/目标清单及唯一角色映射。`TaskInput → LocalJobs → PreparedModelAssembly`沿用持久任务和执行槽，以准备资产租约完整验哈希，再通过`BundleStore.adoptAvailableLocal`关联已有组件。目标不完整时保持暂停、未安装；下载器和生成引擎没有被调用。API可发现用户已选择的部分运行记录及方案指纹，用户随后明确取得依赖。原子提交后的取消保留已校验缓存、任务取消和无媒体结果，重启不会自动下载。见[完整结构与验证边界](MODEL_ASSEMBLY.md)。

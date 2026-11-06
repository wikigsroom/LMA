# m04 / DSH 完整工具调用：修复评估 · 2026-11-06

[English](DSH_M04_TOOL_TEMPLATE_ASSESSMENT_20261106.en.md) · [工具接口合同](DSH_TOOLS.md) · [客户端复核](DSH_CLIENT_AUDIT.md) · [本轮来源与模板对照](../verification/research/dsh-m04-template/assessment.json)

## 1. 结论与版本范围

客户反馈指向可修复的模板链路缺口，应作为功能故障处理。公开固定版本的 GGUF 发布元数据、上游 tokenizer 和当前源码相互印证：m04 的 GGUF 模板没有渲染工具定义和调用历史，LMA 只开启 Jinja，没有提供经核对的工具模板或拒绝不具备工具能力的生效模板。不能据 1B 参数量判定权重没有工具能力。

客户环境为 Motorola Edge Plus / Android 12、LMA 1.1.0/code68、DSH 1.4.76/code327。当前公开版本为 1.2.0/code69；本次逐一核对 EngineHost、ApiHost、TextRequest、ChatProtocol、ToolReply、GgufMetadata，它们从 v1.1.0 到 v1.2.0 的内容一致。因此，v1.2.0 的 UI 更新也尚未解决这一 m04 问题。

本轮交付是代码、来源、模板渲染和修复项评估；没有修改运行代码、生成新 APK、发布修复版本或操作手机。手机此前由其他任务占用，用户要求先做代码复核；本轮未撤销该约定。客户提供的原生 token 数和实际任务表现按“客户报告”记录，不能当作本轮重新实测。下一修复 APK 可使用 v1.2.1/code70（实施时再次核对空闲版本号），不得覆盖现有 Release。

## 2. 已核实事实与待核实边界

| 编号 | 事实 | 证据与范围 |
| --- | --- | --- |
| E01 | 目录中的 m04 精确匹配客户提供的仓库、revision、文件 | [models.json](../app/src/main/assets/models.json)：807,697,440 bytes，SHA256 `7ed39ee0638e18d3e47bf12e60e917c792ca5332606a72bd1882ab1f62a13a7a`；固定 revision 的 LFS 元数据一致。尚未核对手机实际加载文件 |
| E02 | 固定 GGUF 发布元数据中的模板只遍历 role/content | revision `617f94be9dfb802a3fa0ec64b12d7d085482a308`；模板 SHA256 `58c1a1f04baa7adaeaba1f90267c3d57d9396f0c1f0129bdde9e76d3c6784af7`，没有 tools、assistant.tool_calls 或专用结果分支 |
| E03 | 固定上游 tokenizer 有完整工具相关分支 | revision `e753b6ebd7adf87036eb6a3e6de68acca5850e2f`；template SHA256 `0067535d4b21c9be3ab1da0d2b99aa71a158711a485da6c5c8a30a6d2227363f`，包含工具说明、调用历史和 tool_response；配置文件 Git blob 身份相符 |
| E04 | 固定 GGUF 比上游模板修改更早 | 发布元数据 lastModified 分别为 2025-01-05 与 2025-04-25；与 GGUF 未同步后续模板更新相符，不据此推断权重的实际调用正确率 |
| E05 | LMA 接收并向本机引擎传递工具字段 | [TextRequest](../app/src/main/java/com/lma/app/core/TextRequest.java)保留工具字段；[ApiHost](../app/src/main/java/com/lma/app/ApiHost.java)把规范化请求同时送给 /apply-template 和聊天接口。没有发现 auto/required 路径统一删除工具的代码 |
| E06 | 启用 Jinja 不等于模板支持工具 | [EngineHost](../app/src/main/java/com/lma/app/EngineHost.java)使用 --jinja，没有模板 profile/override；[GgufMetadata](../app/src/main/java/com/lma/app/GgufMetadata.java)目前提取上下文后即可返回，不校验工具模板 |
| E07 | required 的 502 是输出检查拒绝缺少调用的响应 | [ToolReply](../app/src/main/java/com/lma/app/core/ToolReply.java)的 required 检查与客户错误文本一致。该保护应保留，增加可诊断的模板／解析／参数／长度分类 |
| E08 | 当前具名选择会收窄本轮传给引擎的定义数组 | [ChatProtocol](../app/src/main/java/com/lma/app/core/ChatProtocol.java)把 tools 改为所选一个函数，并改传 required。这是旧原生版本的兼容措施，需要满足本次完整41定义的更严格要求 |
| E09 | m15 的既有测试不能覆盖 m04 | [旧版真实 SDK 记录](../verification/releases/v1.1.0/physical-tools.json)标明 m15、6次生成、DSH App未测；本轮不将客户提供的 m15 bash/write/read 成功重新标作我们的实测 |

HF 主站本轮连接失败，固定 revision 的公开配置与 API 元数据通过 hf-mirror 取得；原始来源、镜像传输、文件摘要和 Git blobId 分开记录。没有下载 GGUF 文件或张量。GGUF API 的模板是发布仓库元数据，并非本轮从手机或指定 GGUF 二进制头重新提取的结果；手机实际文件与生效 /props 仍是验收前提。

## 3. 无模型执行的模板对照

使用固定模板原文与 Python Jinja2，保持消息一致，只改变工具定义。41个工具均为明确的模拟声明，不是客户 DSH 的真实工具集；数值是提示词字符数，不是原生 tokenizer 的 token 数。

| 条件 | GGUF 发布模板 | 上游候选模板 |
| --- | ---: | ---: |
| 无工具 | 106 | 207 |
| 一个工具 | 106 | 823 |
| 一个工具，扩长说明 | 106 | 35,640 |
| 41个模拟工具 | 106 | 10,277 |

旧模板的四份输出 SHA256 完全相同，工具信息没有进入模板渲染结果；候选模板会渲染工具定义。对调用历史补充对照，旧模板丢失函数调用内容，候选模板保留调用与专用结果标记。结果详见[机器记录](../verification/research/dsh-m04-template/assessment.json)。

这是客户 token 对照的独立来源验证，不是手机推理或原生 minja 验收。普通聊天的候选提示词也有默认 system 内容差异，说明不能直接把候选模板塞入所有模型：需要核对空态、已有 system/developer、BOS/EOS、特殊 token、字符串／对象参数，以及普通聊天回归。

## 4. 编号修复清单

P0 表示完整工具闭环交付前必须完成；P1 表示同一修复版的回归、可观察性与插件适配工作，不代表获准忽略。

| 编号 | 优先级 | 需要实施的修复 | 主要位置 | 通过条件 |
| --- | --- | --- | --- | --- |
| R01 | P0 | 明确实际模型、文件与生效模板身份；区分预期目录记录和运行文件 | Store/BundleStore、GgufMetadata、新模板解析器、EngineHost 的就绪诊断 | 记录实际租用文件、大小／可复用的已校验摘要、模板来源／版本／哈希、原生 revision、BOS/EOS 与 caps；不在 UI 线程反复哈希807MB文件 |
| R02 | P0 | 建立按模型身份绑定的、可版本化的工具模板 profile；m04 接入经核对的上游模板 | 新共用 TemplateProfiles 层及 assets 清单；EngineHost；TextEngine | --jinja 与批准的 --chat-template-file 或等效专用 tool_use 路径一致；不按“Llama/1B”全局替换；不改权重或模型选择 |
| R03 | P0 | 模板就绪与工具准入检查；防止丢弃定义后仍开始普通聊天 | EngineHost 就绪阶段、ApiHost.openText、模板能力诊断 | 真实 /props 和 /apply-template 证实定义进入输入；不只检查模板源码含有 tools 字样；未就绪给明确错误。普通请求不反复跑41工具自测 |
| R04 | P0 | 工具调用输出解析与候选格式一致 | 锁定 llama.cpp 的 common/chat、Jinja/autoparser 路径；ToolReply | 真实调用标记由原生解析为标准 tool_calls；验证 null content、arguments 字符串／对象、特殊字符、结束原因；不得扫描普通代码块制造调用 |
| R05 | P0 | 具名选择保留完整41定义，并独立限制本轮允许调用的函数 | ChatProtocol.tools、原生选择／语法约束适配、ToolReply | 模板仍可见原始41定义，所返回函数必须为具名目标；auto/required 不减工具。不仅取消旧收窄逻辑后退化为 auto；评估原生补丁或受控渲染与允许集分离方案 |
| R06 | P0 | 多轮工具历史完整渲染和调用ID关联 | ChatProtocol.messages、模板 profile、原生解析、ApiHost | assistant.tool_calls、role:tool、tool_call_id、失败结果和继续调用保留；每次结果匹配唯一ID；缺失／重复／孤立ID明确拒绝 |
| R07 | P0 | 流式与 strict 交付正确性 | ToolReply、JsonSchema、ApiHost；DSH流式客户端回归 | 重组 index/id/name/arguments，正确 finish_reason；strict 合法成功、错误类型／额外键／缺键／非法JSON失败；失败调用不得被 DSH 执行。保留当前有界 schema 子集说明 |
| R08 | P0 | 保存参数、准确上下文与加载生命周期 | ModelSettings、ApiHost 的 apply-template/tokenize、EngineHost 缓存身份／执行槽 | m04、131072及全部保存参数不变；用包含41工具的实际模板计数；超限明确失败，不截断；模板变化后安全重载同一文件，不能复用旧模板的 ready 进程 |
| R09 | P1 | 细化模型工具状态与错误，修正兼容范围说明 | ModelCapabilities、ModelPublication、运行管理、诊断和双语文档 | 分别显示上游声明、模板就绪、原生解析、手机实测与可靠性；不能把全局 function_tools:true 当成所有模型已可用；错误不泄露完整提示词／密钥／文件内容 |
| R10 | P0 | 增加能发现本次缺口的真实模板门禁 | 原生无权重模板/解析检查、API回归、独立版本证据 | 固定 GGUF 模板负例、候选模板正例、0/1/长说明/41定义、历史、named、SSE、strict；真实 minja/parser，不能只用返回预设tool_calls的假引擎 |
| R11 | P0 | m04 + 完整41工具 + DSH App 的真实任务闭环 | Android 真机、LMA API、DSH自身工具 | 命令执行→写入→独立读取→基于结果续答；保留调用ID、结果、文件／摘要及失败。不得由外部脚本代执行或只以HTTP200判定 |
| R12 | P1 | 独立检查 dsh-pet 的安装、启用和 Android WebUI 运行 | DSH 插件管理／命令、Node依赖、Cordis/WebUI；必要时插件的Android适配 | 由DSH工具完成安装，核对目标profile、插件版本、依赖、启用／重载和实际页面。安装、展示、桌面悬浮、可选语音分别验收 |

R01–R12 可纳入同一个修复版，按“身份与模板→原生解析与协议→程序回归→真机任务和插件”顺序推进；没有拆成多条版本工作线路。基础链路可修复，m04 在完整代理任务上的正确率只能在修复后实测。

## 5. 原生与协议实现注意点

锁定原生 revision 为 `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4`。该版 /apply-template 与聊天接口共用 oaicompat_chat_params_parse；因此，LMA 当前预检可以忠实计数“一个丢了工具的模板”，但这种计数准确不代表工具定义已渲染。需要模板能力检查补齐，而不是取消上下文检查。

当前源码已有 special handler 和 differential autoparser；不能仅依据旧文档的 Hermes/Generic 名称决定候选模板一定可解析。需要使用这份实际原生版本验证最终生效模板、参数对象规范化和解析器生成。如果仅靠模板覆盖不能让原生解析稳定工作，再作最小原生补丁或经回归的引擎升级；升级成本与其它模型回归必须明确。

模型保存的 context=131072 是允许窗口，不等于每次都预填充131072个输入token。补入约37KB定义后，实际输入token、预填充时间、缓存占用及剩余输出预算会变化。手机资源不足应独立报告，不应静默缩短上下文、更换权重、降低已存参数或把错误吞掉。已有输出token上限、明确取消和真实资源保护仍保留。

[DSH客户端复核](DSH_CLIENT_AUDIT.md)已经发现默认300秒空闲计时不会被SSE注释重置；完整工具的预填充和strict缓冲可能触发它。需要实测并说明合理等待配置，不添加假的内容／思考事件，不关闭代理功能，也不恢复LMA模型生成总时限。

## 6. 真机验收表

所有设备测试记录 APK/SHA256、版本、原生 revision、模型文件／模板哈希、完整41定义摘要、上下文与采样设置。实际请求、返回和工具结果可私下完整留存；公开证据去除密钥、私人文件内容和无关个人路径。

| 编号 | 场景 | 必须保留的证据 |
| --- | --- | --- |
| A01 | 同一已装m04、相同参数和实际有效模板 | 手机文件身份、运行进程／私有端点身份、/props、模板profile哈希、升级前后参数对照 |
| A02 | 无工具／1工具／扩长说明／真实41工具 | 原生渲染或可核查摘要、完整定义数量与身份、输入token；对照排除缓存统计口径影响 |
| A03 | auto | DSH完整41声明、实际tool_calls或真实未选择结果；任务正确率重复记录，不挑一次冒充稳定 |
| A04 | required及具名 | required至少真实调用；具名目标严格一致；渲染的完整定义仍为41；none不产生调用 |
| A05 | 流式 | 按index重组的真实ID／函数／参数，跨片段与Unicode／引号／换行，正确结束原因、usage或真实错误 |
| A06 | 工具结果与连续调用 | 每个call ID匹配结果；至少三次独立工具事件与最终答复；回填失败结果后能继续或诚实报告 |
| A07 | strict成功与失败 | 合法对象成功；缺键／错误类型／额外键／非法JSON拒绝。模型未自然产生的错误可用明确标识的注入负例验证保护，不算模型实测成功 |
| A08 | 错误与生命周期回归 | 孤立／重复ID、上下文超限、输出截断、取消、资源不足、排队429、卸载／重载；不伪造DONE或任务完成 |
| A09 | DSH命令→写文件→独立读→续答 | DSH实际执行得到不可预知测试值；write写唯一测试文件；read独立读取；可授权的文件界面／只读设备核对确认内容与摘要；外部只观察不代写 |
| A10 | dsh-pet安装 | DSH自身发起的安装工具记录、退出码与日志、精确插件版本／profile、启用／重载与页面结果；不存在人工或外部脚本代装 |
| A11 | 权限与Android适配 | DSH应用UID可达路径、Node／依赖版本、WebUI宿主服务、WebView解码、可选系统权限；与工具未产生的故障分别归因 |
| A12 | 模型执行能力测评 | 完整41工具下固定任务集多次尝试；工具选择率、参数正确率、闭环成功率、耗时／取消／资源错误、失败样本。保留全部失败，不改变模型和设置作隐式补救 |

A07包含两种不同证据：手机模型真实生成的strict响应，以及对实际网关的受控错误注入；不得混合成“模型生成所有负例”。自动工具模式允许模型不调用，因此某次没有调用可为协议合法，但指定必须执行的任务仍未通过任务验收。

## 7. dsh-pet 与 Android 权限的独立边界

本轮固定检查 [dsh-pet commit 60bb2eb](https://github.com/PC2005-cloud/dsh-pet/tree/60bb2eb4113eca92b2636ab906f8e6c9c934ae13)。其[包配置](https://github.com/PC2005-cloud/dsh-pet/blob/60bb2eb4113eca92b2636ab906f8e6c9c934ae13/dsh-pet/package.json)声明 Node >=22.12.0、DSH/Cordis宿主依赖和 Web 客户端；这不能直接从 Android 外壳版本号1.4.76推定满足。需核对手机实际运行时及宿主接口。

项目有浏览器内 overlay 的适配途径；[桌面Helper](https://github.com/PC2005-cloud/dsh-pet/blob/60bb2eb4113eca92b2636ab906f8e6c9c934ae13/dsh-pet/src/host/plugin/desktop/spawn.ts)与[Electron下载器](https://github.com/PC2005-cloud/dsh-pet/blob/60bb2eb4113eca92b2636ab906f8e6c9c934ae13/dsh-pet/scripts/ensure-electron.mjs)则面向桌面运行环境，没有找到Android桌面Helper实现。Android WebView内宠物、Android原生跨应用悬浮窗、桌面Electron宠物是不同交付目标，不能以安装目录存在宣称全部通过；不得以Docker/WSL/虚拟化绕过本机运行要求。

DSH工具运行在DSH自身的Android权限和可访问目录内；LMA只提供推理，并不赋予root／ADB权限。应用内工作目录读写和全局应用操控分别验收，后者可能需要用户明确授予的无障碍、媒体投影或其它相应权限。若插件的可选聊天／语音启用，还应核对其模型/TTS使用本机接口；安装成功不等于这些可选服务已经全部本地化。

## 8. 本轮完成与待完成

| 编号 | 本轮已完成 | 状态 |
| --- | --- | --- |
| C01 | v1.1.0/v1.2.0加载、规范化、预检、解析与保护路径核对 | 源码确认 |
| C02 | 固定HF模型身份、双模板、发布时间与函数训练资料对照 | 发布元数据／固定配置确认；镜像来源明示 |
| C03 | 四组模板输入对照及调用历史渲染 | 仅Jinja2程序复现，无模型／原生／手机执行 |
| C04 | dsh-pet固定源码、Node/Web宿主/Electron边界核对 | 源码评估，未安装 |
| C05 | R01–R12修复清单、A01–A12验收、双语文档与当前已知问题同步 | 评估交付 |

| 编号 | 待完成 | 说明 |
| --- | --- | --- |
| P01 | R01–R10：生产模板与原生／API修复及回归 | 本轮评估没有修改运行代码，不能称已修复 |
| P02 | R11、A01–A09/A12：手机实际文件、原生API、DSH完整41工具闭环与能力测评 | 待可用设备；客户报告和旧m15证据不代替m04新验收 |
| P03 | R12、A10–A11：DSH自行安装插件及Android展示／权限 | 插件适配失败须与模型／协议失败分开 |
| P04 | 新签名APK、版本证据、正式Release | 修复与对应验收完成后交付；保留原签名、权重、用户参数及现有发布资产 |

既有多模态／模型冻结范围不削减；本次拟修复的是共享文本工具链路，必须对现有模型、队列、删除／Unload与媒体业务作相应回归。本评估不新增任何模型质量或后台耐久通过结论。

来源：[固定GGUF仓库](https://huggingface.co/bartowski/Dolphin3.0-Llama3.2-1B-GGUF/tree/617f94be9dfb802a3fa0ec64b12d7d085482a308)、[固定上游tokenizer](https://huggingface.co/dphn/Dolphin3.0-Llama3.2-1B/blob/e753b6ebd7adf87036eb6a3e6de68acca5850e2f/tokenizer_config.json)、[上游模型卡](https://huggingface.co/dphn/Dolphin3.0-Llama3.2-1B/blob/e753b6ebd7adf87036eb6a3e6de68acca5850e2f/README.md)、[锁定原生函数文档](https://github.com/ggml-org/llama.cpp/blob/b29c606e28a01b1bc8c1351026a0fa6e616bf6c4/docs/function-calling.md)。

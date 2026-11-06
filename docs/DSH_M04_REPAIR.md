# m04 工具模板与 DSH 修复 · v1.2.1

[English](DSH_M04_REPAIR.en.md) · [工具协议](DSH_TOOLS.md) · [修复前评估](DSH_M04_TOOL_TEMPLATE_ASSESSMENT_20261106.md) · [版本说明](releases/v1.2.1.md)

## 1. 修复范围与判断

客户指出的模板缺口成立。固定 GGUF 的 291 字符模板只拼接普通消息；传入 `tools`、开启 `--jinja`，都不能让这个模板自动处理函数。此前 `prompt_tokens` 不随工具声明增长，首先是输入链路问题，不能据此推断权重没有工具训练。

v1.2.1/code70 修复模型加载、有效模板检查、具名选择、原生解析和历史回填。保持原 m04 文件、131072 上下文、131071 保存输出上限、8 线程、原采样设置与 DSH 全部工具。工具仍由 DSH 执行，LMA 不执行命令或代装插件。**模板／协议可用与 1B 模型能否可靠完成复杂代理任务分别验收。**

## 2. 两个实际根因

1. **GGUF 模板落后于上游。** 上游固定 tokenizer 配置已有工具定义、助手调用与工具结果分支，GGUF 内嵌模板遗漏这些内容。修复采用绑定实际文件身份的审核 profile，而非给所有 Dolphin/Llama 模型套同一模板。
2. **仅补上 XML 模板仍不够。** 第一版真机候选中，m04 自动模式输出裸函数 JSON，XML 解析模式将其作为文本；强制模式还可能等到输出预算耗尽。这不是实际工具执行。最终 profile 保留上游工具及历史结构，明确要求并渲染结构化函数 JSON，交给锁定 llama.cpp 原生 autoparser；不从普通命令文字猜测调用。

无工具、无工具历史时，继续使用原 GGUF 模板的完全相同分支。带工具历史但本轮未再声明工具时，仍正确渲染已有调用和 `<tool_response>`。并行结果在私有渲染副本中按调用 ID 对齐，公共请求和完整内容保持不变。

## 3. 可审计身份

| 项目 | 固定值 |
| --- | --- |
| GGUF 仓库 | `bartowski/Dolphin3.0-Llama3.2-1B-GGUF` |
| GGUF revision | `617f94be9dfb802a3fa0ec64b12d7d085482a308` |
| 文件 | `Dolphin3.0-Llama3.2-1B-Q4_K_M.gguf`，807697440 字节 |
| 文件 SHA256 | `7ed39ee0638e18d3e47bf12e60e917c792ca5332606a72bd1882ab1f62a13a7a` |
| 原内嵌模板 SHA256 | `58c1a1f04baa7adaeaba1f90267c3d57d9396f0c1f0129bdde9e76d3c6784af7` |
| 上游 tokenizer revision | `e753b6ebd7adf87036eb6a3e6de68acca5850e2f` |
| 上游工具模板 SHA256 | `0067535d4b21c9be3ab1da0d2b99aa71a158711a485da6c5c8a30a6d2227363f` |
| LMA profile | `dolphin3-chatml-tools-v1`；派生修改在 manifest 中逐项披露 |
| 生效模板 SHA256 | `59cae1fe1315e4b081877ebdfdec8d2ac433ba402f24ae68d8ba8a76928d7705` |
| llama.cpp | `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4` |

[审核 manifest](../app/src/main/assets/chat-template-profiles.json) · [模板源文件](../app/src/main/assets/chat-templates/dolphin3-chatml-tools-v1.jinja)。上游固定配置通过 HF 镜像取得并核对内容，未下载或替换模型权重；镜像访问不冒充手机运行证据。[原配置](https://huggingface.co/dphn/Dolphin3.0-Llama3.2-1B/blob/e753b6ebd7adf87036eb6a3e6de68acca5850e2f/tokenizer_config.json)。

## 4. 加载、选择与失败处理

| 编号 | 位置 | 行为 |
| --- | --- | --- |
| R01 | `GgufMetadata` / `TemplateProfiles` | 有界读取实际模板、架构；审核 profile 必须同时匹配文件大小、实际 SHA256、架构、原模板摘要 |
| R02 | `EngineHost` / `TextEngine` | 共享解析器，显式 `--chat-template-file`；不改权重、上下文、用户参数或下载状态 |
| R03 | 原生 `/props` 与 `/apply-template` | 对照真正生效模板摘要，检查工具 sentinel 实际进入输入及工具解析能力；选择了 profile 本身不算就绪 |
| R04 | `NativeToolRequest` | 具名请求保留公共完整工具列表；原生 grammar 只允许目标，template kwargs 仍携带全部声明；客户端不能注入私有 kwargs |
| R05 | `ApiHost` | 上下文预检与生成使用同一渲染副本，工具定义计入输入；不截断历史或偷偷缩短上下文 |
| R06 | `ToolReply` | 验证 ID、声明函数、具名目标、并行限制、strict JSON/schema 和结束状态；不合格调用不交付给工具执行者 |
| R07 | 状态与模型发布 | 显示模板状态，模型列表携带 `lma.toolTemplate`；模型执行可靠性仍独立标为未验证 |
| R08 | `/health` | 鉴权后提供最多12条内存诊断摘要：工具数量／名称、定义摘要、输入token、调用ID／参数摘要、结果ID和交付状态；无完整提示词、参数、结果或密钥 |

未知模型保留其自己的模板；不凭名称替换。模板未正确呈现工具或原生工具解析器未就绪，工具请求返回 `422 tool_template_unavailable`，普通聊天仍可使用。审核 profile 的实际生效摘要不符则加载明确失败。原签名、默认52187端口、有界队列、显式取消及外层卸载／删除保持。

## 5. 真机与程序记录

设备为 Motorola Edge Plus、Android12；DSH1.4.76/code327。测试前后核对同一已装 m04 文件、全部安装资产及保存参数，不下载权重。最终 APK 身份以[真机工具记录](../verification/releases/v1.2.1/physical-tools.json)为准。

| 项目 | 实际结果与范围 |
| --- | --- |
| 无权重原生检查 | 17项：真正 pinned Jinja renderer、grammar、parser；auto/required/具名的41声明、30KB说明增长、工具历史、普通模板等价 |
| 最终 APK／OpenAI SDK | 21项真机检查；具名 strict、结果回填、SSE、双并发、UI卸载与API重载均通过；6次真实生成 |
| strict 具名 | 18.858秒，298输入／24输出token；包含首次加载与输入处理，不能当解码速度 |
| 结果回填／SSE | 5.700秒／2.895秒；流式14个事件，ID、参数、结束原因和usage检查通过 |
| 双并发 | 合计6.523秒，峰值2个已接纳请求；健康请求最长26毫秒 |
| 完整 DSH 长任务 | 实际41工具，渲染输入19309token；运行14分4秒仍无完整工具执行结果，明确人工取消测试；原生日志约1.4token/秒、已生成超过700token，不能称闭环成功 |
| DSH B1，取消观察 | 41工具、19050输入token；观察9分56秒后在DSH停止，底层请求一度仍在计算，随后升级终止。该次可能尚在输入处理，不能据此判定模型不会工具；不纳入最终APK通过数 |
| DSH C1，自然结束 | 候选 `d1cdd364…`，实际41工具、19058输入token；19分57秒后正常 stop，仅复述运行环境，没有 tool_calls。输入处理约17分钟到97%，不可把整个等待时间当解码耗时；不是协议422/502，也不是完整工具闭环 |
| DSH D1，最终包自然结束 | 最终 `2dbc586b…` APK、41工具、19132输入token，17分16秒后 stop，仅返回时间／时区，没有调用或工具结果；独立读取确认目标文件不存在，bash→write→read未通过 |
| 最终 APK 直接 API | auto / required / 具名均返回真实 `lma_sum` 调用，流式重组ID及JSON；回填同ID的客户端结果43后回答43。无效 strict schema 返回400及具体字段；这组小请求不代替DSH实测 |
| 环境消息位置对照 | 两个小请求分别将同一system环境消息放在任务前／后，均产生正确原生调用（3.886／4.050秒）。不能把真实DSH失败归为“任何后置环境消息都不支持”；长系统提示、41工具与任务可靠性仍有独立边界 |

DSH 真实任务与后续短任务、文件及插件结果另见[DSH 验证记录](../verification/releases/v1.2.1/physical-dsh.json)。程序负例可证明错误保护，不能称模型自己生成了全部负例。早期候选的 XML 失败与输入法损坏提示词单独保留，不能混入最终 APK 的通过数。

A1／B1保留为早期候选观察；未保存可公开绑定的完整APK摘要，因此明确放入 `earlier_unbound_trials`，不补猜摘要、不充当最终APK验收。C1和最终包D1分别有完整APK绑定。

最终APK共记录14次实际完成生成：SDK六次、直接API及对照七次、DSH D1一次。其中D1任务失败，不能因原生生成自然结束而计作工具任务通过。C1属于另一候选，早期取消与负例预校验不混入这14次。

### 客户验收项逐项对应

| 编号 | 约束 | 当前证据及边界 |
| --- | --- | --- |
| A01 | 保留 m04、权重、131072上下文和参数 | 真机完整文件SHA256及升级前后参数／资产／LMA历史比对通过 |
| A02 | 不删41工具，不改成普通聊天 | 实际DSH请求携带41项，原生输入超过19000token；定义摘要和完整名称保留 |
| A03 | auto / required / 具名 / SSE | 最终APK直接API均返回真实调用；完整DSH自动选择的独立失败另列，不由这些小请求代替 |
| A04 | 调用ID、结果回填、多轮 | SDK与直接API真实往返通过；DSH命令／文件三步闭环尚未通过 |
| A05 | strict成功与失败 | 真机严格整数调用成功；无效schema真机400；错误模型参数的502／流式保护使用明确标注的生产程序夹具 |
| A06 | 真正 bash→write→read→依据结果回答 | 尚未验收成功；不把复述、代码或HTTP200计为执行，不由ADB代写测试文件 |
| A07 | DSH自行安装dsh-pet | 未确认安装成功；没有DSH安装工具事件及结果就不记成功，独立平台限制见第7节 |
| A08 | 并发及容量 | 两个真机请求排队通过；正文4MiB／1024消息／单内容1MiB等容量和错误使用程序边界测试，不能外推任意子代理吞吐 |
| A09 | 无新增生成总超时 | 保持原生推理读取无总时限；测试明确取消与自然stop分别记录，不调整用户输出上限 |
| A10 | m15与其他模型 | 共享链路有程序回归；本轮没有切换到m15代替m04验收，也不把以前m15的通过数移入本版 |

## 6. 使用与排错

1. 原签名升级 APK，保留已下载 m04 和参数；需要加载一次才能建立实际模板／文件身份记录。
2. 在运行管理检查“工具模板”。API `/v1/models` 的 `capabilities.lma.toolTemplate` 和鉴权 `/health` 提供相应状态；“已核对”表示模板／解析就绪，不表示代理任务全部成功。
3. DSH 地址继续使用手机 `http://127.0.0.1:52187/v1` 及原密钥，选择 m04；保留全部工具与标准模式。按调用ID检查实际工具事件，再独立确认文件内容；代码示例不是执行证据。
4. `tool_template_unavailable`：查看模型身份、profile和原生能力；不要静默改模型。`invalid_model_output`：查看实际输出、schema、所选函数和结束状态。长任务未产出完整调用：区分输入计算、实际生成及客户端等待，可显式停止。
5. 本版不加入生成总耗时上限。过大的保存输出上限可能使不收束的模型持续生成；本次实测保留131071不变。用户可自行在本地模型设置选择较短输出，测试不会替用户修改。

DSH 文件工具只能使用其 Android UID 可访问目录；写入自有 app-files 不需要 ROOT，全局操控另受无障碍／系统权限限制。LMA 不给 DSH 增加 Android 权限。

## 7. 插件与验收边界

`PC2005-cloud/dsh-pet` 的 Node、Cordis/WebUI、Electron Helper 和 Android 悬浮窗分别核对。源码提供浏览器 overlay 路线，桌面 Helper 不等于 Android 原生悬浮窗支持。插件必须由 DSH 自己的工具安装；没有工具事件就不能认定安装完成，也不由外部脚本代装后计作成功。

源码检查固定在[插件提交60bb2eb](https://github.com/PC2005-cloud/dsh-pet/tree/60bb2eb4113eca92b2636ab906f8e6c9c934ae13)，`package.json` 要求 Node `>=22.12.0`；INSTALL 中的 `dsh plugin --profile web add dsh-pet` 是上游CLI示例，不能直接视为Android应用的已验证安装流程。浏览器内显示、Electron桌面宠物和跨应用Android悬浮窗需要各自验证；源码资料不证明当前手机已安装或兼容。

本版交付模板与协议修复、真实测试和诚实的模型能力边界；**不宣称 m04 已可靠完成全部41工具代理任务、插件安装或任意 Android 应用操控。** 新 profile 的模型绑定机制可继续扩展，但其他权重需要独立来源审核和实际验证，不按参数量或家族名称猜测兼容。

## 8. 模板来源与条款

派生配置保留上游来源、修改说明及发布者标注的 `llama3.2` 条款。**Built with Llama**；完整署名和许可随 APK 及源码的 `chat-template-dolphin3-llama32-NOTICE.txt` 分发，参见[第三方说明](../THIRD_PARTY_NOTICES.md)。没有附带模型权重或 tokenizer 词表，LMA 自有代码的 MIT 不改变第三方条款。

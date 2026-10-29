# LMA 0.2.0 全面复查记录

日期：2026-10-27。当前结论：0.2.0 已保留推荐，接入 HF 分页发现、文件选择、本地管理，以及每个模型独立的可编辑参数和超限归位。226 项桌面断言、5 项实时公开 HF 元数据检查，以及构建 / APK / Lint 检查通过。没有可用 Android 真机，真实 ARM 推理、Android 服务生命周期、局域网与锁屏耐久仍未验收。

全程使用 Windows 原生工具，没有运行 Docker、WSL、虚拟机或 Android 模拟器。界面检查结束后关闭全部测试页面及浏览器进程。

## 0.2.0 本轮变化

- 推荐继续使用 `m08 → m06 → m01`，保留已有标签与证据；HF 搜索不会改写精选。
- “全部”和搜索动态查询 HF，提供格式 / 排序、仓库 / 文件分页及固定版本量化文件下载；“本地”统一管理模型和下载任务。
- 普通模型可添加；无审查已核对标签与元数据提示分开，明确其他格式、分片、投影器和任务限制。
- 可选 HF 令牌只用于官方 HTTPS 源，不转发到镜像 / CDN。真实 TLS 测试核对自定义域名及重定向不接收令牌。
- 修复暂停下载时断连和工作线程结尾竞争导致状态停在 pausing 的问题；在同一锁内最终持久化状态并移除任务。
- 重录 12 张截图、MP4、4 份 GIF；添加双语 HF 指南并同步使用、架构、构建和发布说明。

## 模型参数验证

新增二进制 GGUF v2/v3、32/64 位上下文、键顺序 / tokenizer 跳过、不完整头部、有界数组、未知元数据兜底、超限归位、模型间独立性、AtomicFile 持久化与旧版迁移检查。真实子进程启动参数及 HTTP 请求核对当前模型配置；界面检查覆盖编辑、预设、键盘、归位、保存拒绝和切换模型。仍使用明确的框架 / UI 替身，不代表真机执行。见[模型参数](MODEL_SETTINGS.md)。

## 保留的 0.1.2 历史修复

| 复查发现 | 0.1.2 的处理（历史行为，当前范围见上） |
| --- | --- |
| 用户要求仅内置无审查模型，原目录部分名称及说明未明确属性 | 14 个条目逐个核对作者说明；名称补全 Uncensored / Abliterated，显示“无审查”标签、具体处理方式及作者说明入口；构建强制校验对应权重哈希，自定义文件标为“属性未核对” |
| Gemma 4B 条目指向 tensorblock 仓库中不存在的 Q4_K_M 文件，实际返回 404 | 改用作者 mlabonne 自己的 Q4_K_M 文件，并固定提交、大小和 SHA256 |
| 部分文件无预期哈希，所有链接跟随 main 变化 | 14 个内置条目均固定 40 位仓库提交、准确大小和 64 位 SHA256 |
| 当前网络无法直连 Hugging Face，首次下载需要人工切换源 | 默认自动尝试原站，失败后尝试 HF Mirror；其他自定义域名保持原地址 |
| 失败或取消的空回复会留下孤立 user 消息，后续严格聊天模板可能报错 | 按完整 user / assistant 对构造历史，跳过空的失败轮次，保留有正文的中断回复 |
| 回复过快时，界面可能未观察到 generating 状态，已发送草稿没有清空 | 使用 requestId 对应的原生命令确认；确认成功后清理该次草稿 |
| 旧错误或其他命令可能影响设置保存状态 | 仅消费同一 requestId 的成功或失败结果；拒绝时保留输入 |
| 进程重建后所选模型 ID 未同步到运行状态 | Application 从持久设置恢复 selectedModel |
| 排队任务暂停要等到前面任务结束 | 立即移出有效队列并持久化暂停，旧任务不能重新写回已删除条目 |
| 服务快速重建可能重叠写入同一模型文件 | Application 范围内共用传输锁，删除操作拒绝活动写入 |
| 旧启动请求和退出回调可能与新模型切换重叠 | 共享进程锁、请求代次校验和同步状态转换；启动前等待旧进程退出 |
| 续传可能拼接不同实体版本 | 强 ETag 用于 If-Range；206 返回不同 ETag 时拒绝追加并保留原进度 |
| 只修改局域网等部分设置时可能清空默认系统提示词 | 缺少的字段保持当前有效设置 |
| Android 13+ 通知请求可能反复弹出，返回处理仅使用旧接口 | 通知权限首次请求一次，并注册新版返回回调 |
| Lint 无法识别隔离辅助类的 API 边界、旧版广播分支及 URI 授权常量 | API 33 辅助类标注 TargetApi；仅对 API 28–32 的广播注册方法做精确豁免；确认实际读取授权后传入 READ 常量 |
| 旧编译产物或旧测试报告可能被误用 | 清理编译输出；APK、源码和测试输入按哈希关联，打包时拒绝过期证据 |

## 已执行的检查及边界

| 范围 | 证据 | 不能由此推断的事项 |
| --- | --- | --- |
| 生产后端 Java | 85 项检查，执行 Store、Downloads、Net、EngineHost、ChatRunner、ChatHistory、Protocol、ModelSettings、GgufMetadata；真实 TLS 连接、磁盘文件和子进程 | Android Context、Service、Preferences、SAF、StatFs 和 SQLite 接口使用明确的桌面替身；子进程是 HTTP 协议测试服务，不运行语言模型 |
| HF 与本地逻辑 | 45 项生产 HubClient / HubCatalog / Store 检查，覆盖分页、固定提交与哈希、去重、持久化、删除、过期请求、令牌主机及选择命令 | 使用确定性 API 响应与框架替身，未在 Android 执行 |
| HF 实时发现 | 5 项公开 HF Mirror API 检查，包含 GGUF / 全格式检索、游标分页、固定仓库提交及文件 SHA256 | 未使用真实令牌，未下载完整权重，未验证原站可达或受限仓库 |
| 下载失败与恢复 | 200 重启、206 断点、416 完整文件、错误起点、ETag 变化、真实 TLS 传输截断后续传、未知长度、哈希错误、HTML、协议降级、排队暂停、删除、服务重建、流式导入 | 不代表某个手机上的下载管理、省电策略或 SAF 提供器已通过 |
| 引擎控制与聊天 | 进程切换、快速连续切换、健康状态加模型别名、鉴权、SSE 中文和 emoji、思考流、部分回复保存、立即取消、崩溃恢复、端口冲突、三次恢复上限 | 没有执行 APK 中的 ARM 原生库，也没有测量模型首 token 延迟或 tokens/s |
| 协议核心 | 25 项 JVM 检查：SSE 边界、UTF-8、CRLF、多行、截断、长度限制、续传起点与溢出、路径及哈希格式 | 不代表 Android 网络实现完全相同 |
| 聊天查询 | 提取生产 Chats.java 中的建表与查询语句，在 SQLite 3.45.3 中执行 5 项检查；覆盖相同时间戳、最新 32 / 80 行、参数隔离、落盘重开 | 未执行 Android SQLiteOpenHelper；对应真机测试另有实现 |
| 界面 | 66 项浏览器检查，涵盖模型独立参数、预设 / 编辑 / 超限归位；375px、320px、平板、短横屏、150% 字体、主题、命令确认、草稿、防注入、对话删除、全部内置无审查标签及作者依据入口；无 JS 异常 | 使用测试桥接；未在 Android WebView 或真实输入法中执行 |
| 无审查模型准入 | 14 个作者模型卡均有无审查或去拒答依据，已固定说明版本、内容哈希，并核对固定 GGUF 的来源归属及权重 SHA256；应用没有新增内容审核或敏感词过滤路径 | 作者声明不是本应用测得的拒答率；手机实际输出仍未验证 |
| 模型网络 | 14 / 14 固定提交文件经 HF Mirror 返回 HTTP 206，Content-Range 总长与元数据吻合，读取到 GGUF v3；现有的 8 个预期哈希仍一致 | 当前网络直连 HF 超时；新增哈希来自镜像返回的上游元数据。没有下载完整权重，未在本机重新计算这些权重的整文件哈希 |
| 模型架构 | 读取每个固定 GGUF 的前 256 字节，核对 qwen2、qwen3、qwen35、llama、gemma3、lfm2；固定 llama.cpp 源码架构表和打包库中均有相应项 | 架构存在不保证具体张量布局、聊天模板或内存消耗在目标手机上正常 |
| Android APK | Java、AAPT2、DEX、ZIP、签名独立验证、身份及权限；14 个原生库 SHA256 与固定发行包一致，ARM64 依赖齐全，ELF LOAD 段和 APK 对齐满足 16KB；14 个二进制的 Android ident note 均为 API 28，启动文件入口非零并使用 /system/bin/linker64 | 静态检查不替代 Android 安装、链接器及 CPU 指令选择实测 |
| 原生启动配置 | 对照固定 llama.cpp 提交和打包库中的 15 个真实启动参数；核对 LLAMA_API_KEY 环境变量、Bearer 鉴权、可执行文件目录内的内核发现与 7 个 CPU 内核评分入口 | 源码与二进制字符串检查不能证明 Android 已执行这些路径，也不测量性能 |
| Android Lint | SDK 独立 Lint 8.9.0 离线执行默认规则，显式列入全部 16 个生产 Java 文件、3 个资源及 Manifest；0 错误、7 警告 | 没有执行 Gradle 或 Android 运行时；警告及适用边界见下表 |
| 服务声明 | 从 APK 中解析实际二进制 Manifest：specialUse、对应权限及用途、Service 非导出、不随任务划走停止 | 不代表厂商后台策略、锁屏存活、通知交互或开机恢复已通过 |
| 真机工具 | 独立 instrumentation APK 已完成编译、DEX、对齐和签名；ADB 预检记录 awaiting_physical_device | 工具本身尚未在真机执行；没有将其预期结果计入通过数 |

桌面进程测试显式关闭 Windows JDK 的独占绑定，以模拟 Android/Linux 的可复用监听端口；端口冲突测试另起独占监听进程。TLS 测试证书只进入隔离的测试 JVM，生产应用的证书校验没有放宽。

Lint 的 7 条警告完整保存在 `build/android-lint/report.txt`，结构化记录随源码 ZIP 的 `verification/android-lint.json` 交付，没有整体屏蔽警告：

| 警告 | 核对结果与边界 |
| --- | --- |
| OldTargetApi | 当前编译及目标为 API 35；尚未升级到更新目标 SDK，也未声称已在新版 Android 真机测试 |
| BatteryLife | 用户主动开启的本地服务提供电池优化设置入口；未提交 Play 商店或验证其分发政策适用性 |
| UseRequiresApi | 采用 SDK 自带 TargetApi，API 33 辅助类两个调用处均有 SDK_INT >= 33 判断；没有引入 AndroidX 注解依赖 |
| SetJavaScriptEnabled | 离线界面需要 JavaScript；WebView 请求只允许固定应用域名的随包资源，外链通过外部应用打开；模型和消息内容已做界面注入检查 |
| DataExtractionRules | allowBackup=false 已声明；Android 12+ 的独立云备份 / 设备迁移规则尚未配置，厂商迁移行为没有实测 |
| WakelockTimeout | 用户持续开启服务时保持 CPU 唤醒锁，在 onDestroy 中释放；未增加会截断长时服务的固定超时，实际耗电与释放仍需真机验证 |
| Recycle | 所选文档输入流随后进入 try-with-resources，与输出流一起关闭；HTTP 连接在 finally 中断开。尚未验证真实 SAF 提供器 |

## 模型目录的具体改动

Gemma 4B 来源改为 [作者的 GGUF 仓库](https://huggingface.co/mlabonne/gemma-3-4b-it-abliterated-v2-GGUF)，文件为 `gemma-3-4b-it-abliterated-v2.q4_k_m.gguf`，固定提交 `63e82692eb4361788cdfdf01491bdbda28858737`，2,489,893,696 字节，SHA256 为 `993552c1ea9880c6efac20bc98a6b590cff78643b343ab646ba8c930aea6a44e`。本应用只提供文本推理，不下载视觉投影器。

详细的 14 个文件记录在 `catalogue/verified-models.json`；独立架构对照在 `catalogue/architecture-check.json`。原生启动配置的固定源码地址、内容哈希和输入指纹在 `third_party/runtime-audit.json`。这些检查确认文件与静态架构信息，没有验证“无审查”命名对应的实际拒答率。

## 后台方案的核对

Android 14+ 要求声明具体前台服务类型和对应权限，specialUse 还需提供用途说明；当前 Manifest 已声明。[Android 官方服务类型说明](https://developer.android.com/develop/background-work/services/fgs/service-types#special-use)

Android 15 的六小时限制适用于 dataSync 和 mediaProcessing，shortService 另有较短限制。当前使用 specialUse，但这不意味着系统承诺永不终止服务。[Android 官方超时说明](https://developer.android.com/develop/background-work/services/fgs/timeout)

仍需实际验证厂商后台权限、电池策略、Doze、内存不足、发热与重启。外部 API 的单次输出仍受 EOS、max_tokens、上下文和客户端取消影响。

## 可重现命令

```powershell
python tools/build.py
python tools/test_protocol.py
python tools/test_backend.py
python tools/test_hub.py --live
python tools/test_sqlite.py
node tests/ui-smoke.cjs
python tools/audit_runtime.py
python tools/audit_uncensored.py
python tools/test_android_lint.py
python tools/verify_package.py
python tools/build_acceptance.py
python tools/device_check.py
python tools/package_delivery.py
```

界面脚本需要 Playwright 和 Edge / Chromium，支持 LMA_PLAYWRIGHT 和 LMA_BROWSER 路径变量。后端测试首次下载带固定 SHA256 的 org.json 测试依赖；它不进入 APK。未连接手机时，device_check 退出码为 2，并记录等待真机。

原生源码审计需要访问 GitHub API；Android Lint 使用本机 Android SDK Command-line Tools，离线运行，通过项目描述文件直接指定源码，缓存和报告保存在项目 build/android-lint/。两者都不调用 Gradle、模拟器或虚拟化环境。交付打包会检查这些报告与当前源码、APK 的关联，拒绝过期结果。

测试原始记录位于 build/；交付源码 ZIP 中的 verification/ 包含本轮结果和输入哈希。dist/validation.json 明确记录 fully_usable_on_phone_verified=false。

## 尚需真机验收

自动工具与运行方法见 [DEVICE_ACCEPTANCE.md](DEVICE_ACCEPTANCE.md)。最终仍需确认：

1. Android 9 / Z20 的安装、WebView、权限、文件选择器与真实 ARM 原生加载。
2. 0.5B、1.2B、1.7B 的完整下载、实际中英文输出；逐个验证其余 3B–4B 文件及内存占用。
3. 不附着 instrumentation 时的锁屏 API 流式请求，至少 15 分钟、1 小时及 4 / 8 / 24 小时持续请求；记录温度、失败率和速度。
4. 另一台局域网设备的连接与关闭 LAN 后的隔离；通知停止后进程与唤醒锁释放。
5. 系统回收、划走任务、强行停止、更新与重启后的恢复行为。强行停止与普通退到后台需分别记录。

在这些项目实测通过前，本次复查结论保持“待真机验收”。

dev.20：Stable Audio 144 = Java 51 + C++ 93；6 个实际主机子进程、6 次真实 LiteRT ADD / CAST 微型图运行和 Arm 采样等价校验；音频为静音 WAV 结构夹具，完整模型推理 / Android 为 0。基座 561、UI 287，Lint 0 错误 / 13 警告。见[详细边界](STABLE_AUDIO_ENGINE.md)和[更新回执](releases/v0.3.0-dev.20.md)。

## 旧 LTX 运算分步源码补充

新增[双语运算分步证据](LTX098_STAGING.md)：72 局部对照、四候选12次真实 T5 和三条原生主机链路。候选 A 通过，B 三项浮点门槛失败。现有原生基线六项失败记录保留，App/APK未改变；主机数值/媒体不替代手机、质量、后台或完整版本验收。见[本轮编号及完整待办](releases/v0.3.0-dev.23-ltx-staging.md)。

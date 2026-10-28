# SoulX：语言模型与完整主机链路

当前实现见 [dev.21 SoulX App 基座](SOULX_ENGINE.md)：共享源码已编译进生产 worker，接入用户模型包、任务与 API。以下正文保留 dev.20 研究检查点的历史范围；“未注册 / 未打包”指当时的独立研究执行器。其测试不追溯改标为 App 或手机证据。公开完整组件下载候选、语音质量与物理 Android 验收仍待完成。

[English](SOULX_LANGUAGE.en.md) · [参考与声学](SOULX_REFERENCE.md) · [编号交付](releases/v0.3.0-dev.20-soulx-language.md) · [完整版本要求](MULTIMODAL_RELEASE_PLAN.md)

本轮新增 Qwen3 文字到语义码的原生 CPU 执行、实际发布者分词器、最多四个参考说话人和跨轮窗口。完整主机检查把新文本依次送入已训练的 S3 / CAMPPlus、Qwen3、Flow / HiFT，写出24kHz WAV。这里的主机是开发用 Windows；这不是手机推理方案。Android ARM64 编译另计，App 的用户模型包、任务 / API、质量、资源和物理设备验收仍待完成。研究执行器未注册、未打包进 APK；公开版本仍 v0.2.0，开发 APK 仍 dev.20。

## 为什么不能直接使用普通聊天 GGUF

[官方模型](https://huggingface.co/Soul-AILab/SoulX-Podcast-1.7B/tree/c2af285fc7ec68a4d3402deae7d2e215ab67fb32)与[已核对的社区量化版本](https://huggingface.co/mradermacher/SoulX-Podcast-1.7B-GGUF/tree/400348052b80b513722ead19c4f09839ef0455a2)使用不同的语音词表布局。它们不应混用数值 ID。

| 布局 | 词表大小 | 第一个语义码 | 语音开始 | 语音结束 |
| --- | ---: | ---: | ---: | ---: |
| 官方固定修订，完整转换后 | 160156 | 153595 | 153477 | 153478 |
| 社区较早 Q4_K_M | 159488 | 152927 | 151674 | 151675 |

普通 Qwen EOS `151645` 不能用于结束语音。官方资产中的某些旧配置数字也不匹配其实际 tokenizer / 权重，因此执行器从所选 GGUF 的真实分词器解析标记，逐个验证全部6561个连续语义码、四个说话人及不冲突的控制标记。仅检查架构名称不算兼容。

当前官方导出使用全部三份 safetensors、全部311个张量和28层；没有裁层、随机初始化或以微型网络代替。严格来源锁见 [soulx-language-source-lock.json](../third_party/soulx-language-source-lock.json)。发布者输入约4.13GB，先完整导出 F16，再用与 App 既有文本引擎相同修订的 llama.cpp 量化为 Q4_K_M。转换器会校验完整布局和文件 hash；失败保留诊断目录，不覆盖原模型。Windows 中文路径分别使用 UTF-8 模型读取及量化工作目录中的 ASCII 输出文件名，未修改固定上游源码。

## 文字、历史和采样契约

| 编号 | 能力 | 实现与边界 |
| --- | --- | --- |
| SL-01 | 文字协议 | 严格 UTF-8，单段≤64KiB；执行上游三遍非重叠 CJK /英文空格规则和末尾标点；拒绝结构控制标记注入，保留普通表现性文本 |
| SL-02 | 参考与说话人 | 1–4份明确输入的参考码 /文字，每份1–375码，0–6560；目标只能选择已有参考；任务前缀仅在第一个参考出现 |
| SL-03 | 历史窗口 | 最多64轮，原始参考保留；最近完整语音轮及更早文字轮按独立窗口重建；每轮重新计算有界 KV，不跨请求隐式复用 |
| SL-04 | 资源边界 | 上下文256–8192、线程1–32、batch1–512、单轮输出1–3000码 / token预算，任务总语义码≤24000；参考 /历史 /目标 /预留无法容纳则明确失败 |
| SL-05 | RAS | 重复惩罚忽略提示，按已生成的不同 ID 各处理一次；min-new-tokens、temperature、top-k、top-p后作候选抽样，按最近窗口决定是否恢复原始 logits，再独立抽最终 token |
| SL-06 | 贪心扩展 | temperature=0要求显式 `use_ras=false`；用于确定性回归，不冒充上游默认随机配置 |
| SL-07 | 完成与截断 | 仅接受语义码或最后的真实语音 EOS；达到输出上限则明确标记未生成 EOS，只在历史中补分隔符，不能把该分隔符计为模型生成 |
| SL-08 | 生命周期 /取消 | 一个模型 /上下文、CPU、模型释放后写成功回执；加载前、真实 neural decode内、生成 token后分别检查取消，无成功文件则不报成功 |

默认采样为 temperature .6、重复惩罚1.25、top-k100、top-p .9、min8、max3000、RAS窗口25 /阈值.2；较小上下文需要用户明确降低输出预留。上游 RAS 的恢复操作会撤销**全部**处理器，包括 min-new-tokens 与过滤；文档不把它描述为不可突破的最小语音长度。发现非语义输出时本机失败，不擅自掩码或把任意 token 当音频码。

原生库为 [language.cpp](../research/soulx_language/language.cpp) / [policy.hpp](../research/soulx_language/policy.hpp)。Android 仅加载既有 `libllama.so` 同目录下固定的 baseline CPU 库，不扫描模型目录、CWD或环境变量中的动态后端；没有网络推理或子进程回退。Python、PyTorch及导出工具仅服务开发基准，未来用户不应安装开发环境或运行转换命令。

## 实际证据

| 编号 | 检查 | 本轮实际结果 |
| --- | --- | --- |
| V-01 | [语言检查](../verification/development/soulx-language.json) | 546项、20次原生主机子进程；真实完整 Q4 生成 /重复、分词、取消和独立上游比较 |
| V-02 | 处理器与窗口 | 115段标准化与实际分词、12组采样概率 /最终 token / RAS比较；1 /2 /4参考说话人的各12轮历史与实际发布者函数块一致 |
| V-03 | 完整原模型 forward | 原始全部 BF16 HF 权重 vs 原生 Q4，在一个43-token上下文上比较160156个 logits；cosine 0.999914、RMSE 0.187364、top20重合 0.85；预设门槛.99 / .5 / .4 |
| V-04 | [ARM64编译](../verification/development/soulx-language-arm64.json) | 327,576字节，NDK r30 /API28 /16KiB；固定既有 llama /ggml依赖，无网络 /进程导入；尚未 Android执行 |
| V-05 | [新文字完整训练主机链路](../verification/development/soulx-pipeline.json) | 60项、5次顺序原生子进程、4次参考图 /36次声学图，5个真实训练组件；两段新文字→WAV |

语言基准使用固定上游标准化 / RAS /历史函数块与实际 HF processors，神经 logits 基准直接加载原始全部发布者权重，不以待测量化结果生成自己的基准。数值一致性不等于可懂度、音色或量化质量验收。

完整主机链路以两段新合成参考 PCM 和英文 /中文新文本运行；输出1.44 / 1.76秒、24kHz /单声道 /16-bit WAV。参考没有对应真人语音或有效转录，因此这些文件只验证代码到波形的执行、范围、长度和格式；没有可懂度、说话人相似度、韵律或听感结论，也不作为产品语音演示。WAV和原始 /转换权重只留在忽略的 `build/`，不进入 Git、APK 或 Release。组件单独检查与整链路证据分开，旧253项声学重建仍标明“目标码来自 S3”，不重写为当时已经完成 TTS。

## 开发复现

先按[参考 /声学指南](SOULX_REFERENCE.md)显式准备四个配套训练组件及其当前证据。以下操作均为原生 Windows，项目 `build/` 保存缓存 /临时文件；不使用 Docker /WSL /虚拟机 /模拟器。源码取自固定修订，源码下载与模型下载独立：

```powershell
git clone --no-checkout https://github.com/ggml-org/llama.cpp.git build/native-src/llama-soulx
git -C build/native-src/llama-soulx checkout b29c606e28a01b1bc8c1351026a0fa6e616bf6c4
python -m pip install --target build/soulx-language-python --cache-dir build/pip-cache --no-deps sentencepiece==0.2.1
python tools/fetch_soulx_language.py
# 仅下面显式开关请求官方权重 /社区对照资产；缺失资产的检查不会自动下载。
python tools/fetch_soulx_language.py --download
python tools/fetch_soulx_language.py --community-gguf
python tools/build_soulx_language.py
python tools/export_soulx_language.py --output-dir build/soulx-language-official
python tools/test_soulx_language.py
python tools/build_soulx_language.py --android
python tools/test_soulx_pipeline.py
python tools/export_development.py
python tools/check_repository.py --development
```

已有克隆时仅核对 /checkout固定修订，不覆盖本地修改；已有导出目录不会被覆盖。`--origin https://hf-mirror.com` 仅是显式文件传输来源，仍验证同一发布者资产 SHA256。重建 host和Android时顺序执行，构建脚本仅移除自己创建的 SUBST 别名。

开发依赖实际版本为 torch2.14.0+cpu、transformers5.17.0、tokenizers0.23.2、numpy2.4.2、safetensors0.8.0、sentencepiece0.2.1；实际使用版本写入转换回执，不宣称与固定上游 requirements环境完全相同。全 HF 基准只读本地资产、禁用远程代码和 Hub访问。源码锁 / [NOTICE](../research/soulx_language/NOTICE)保留 SoulX Apache-2.0及 llama.cpp MIT；模型许可按对应来源核对，不推广到其他 HF 模型。

## 用户资产与同版待办

App只更新基座；完整用户包、词表、codec、音色 /语言包由用户选择、下载 /导入、暂停 /续传、更新 /删除并逐模型设置。安装、升级、浏览或缺资产不触发模型传输。全部模型平级，生文 /生图 /生视频 /生音频与基座标签独立；推荐 m08→m06→m01和 Uncensored独立标签保留。

本研究尚须接入同一 Android手机的显式完整 bundle、WAV输入、任务 /API /产物、资源准入和生命周期；继续完成完整模型新输入断网质量 /资源 /取消 /清理和物理 Android三次装卸、15分钟锁屏、1小时交替 API、升级保留资产 /设置。当前没有可用真机，不以主机链路或 ELF 编译替代这些门槛。

原有文本、F-01–F-12、01–14 /16 /17全部冻结子目标、九种 MOSS、SD1.5 /SDXL LoRA、旧 LTX-Video2B0.9.8distilled、A1–A11 /R-01–R-05仍属同一完整 v0.3.0。未缩减范围、拆分版本或提前发布 Release；本轮没有界面变更，既有截图 /录屏 /GIF仍标为 UI FIXTURE。

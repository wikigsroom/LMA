# MOSS-TTS-Nano 100M：真实资产、导入与生产链路

[English](MOSS_NANO_TRAINED.en.md) · [原生实现](MOSS_NANO_ENGINE.md) · [编号交付及全部待办](releases/v0.3.0-dev.24-moss-nano.md) · [完整版本范围](MULTIMODAL_RELEASE_PLAN.md)

当前 dev.24 后续提供可供用户导入的固定模型清单，并完成真实训练资产的生产 C++ 与 Java→原生主机验证。**未执行 Android 安装、SAF、Service、手机推理或后台测试，语音质量和编号09完整验收仍未通过。** 本轮不改变 APK 输入、版本、推荐顺序或公开发行；仍属于同一个完整 v0.3.0。

## 用户取得与使用

1. 取得 [moss-nano-100m-onnx.bundle.json](../catalogue/moss-nano-100m-onnx.bundle.json)，在 dev.24 的模型页面打开添加菜单，选择“导入模型包清单”，再用系统 JSON 选择器导入该文件。清单仅登记模型元数据，不安装、不下载。它是用户导入项，`catalogue:false`，不会成为内置已核对推荐。
2. 在“本地”打开这项模型，核对生音频、CPU、`moss_nano_ort`、依赖、许可及下载计划：**11组件，717,414,286字节（约684.18MiB）**。已有相同内容可复用；实际安装还需要输出、临时文件与运行内存。
3. 自行点击“下载所选模型包”，才从清单所列的固定 HF URL 下载。或者点击“从文件夹导入”，选择下述完整目录；图、权重、分词器与提示数据均由用户提供。目录导入不会以网络下载补齐缺项。
4. 安装完成后，在此模型的“本地”设置中编辑参数，再点击“使用”，填写新朗读文本并提交语音任务。成功结果保存到结果库；在手机上的全部分词、TTS和codec执行都由已安装基座承担。此操作流程已有生产源码；本轮验证通过的是带文件系统端口的 Java 主机链路，**不是手机操作验收**。
5. 模型可独立暂停、恢复、更新或删除。App 安装/升级/浏览不会下载或替换模型，缺资产时在本机失败。用户仍可通过 HF 全部/搜索选择其他模型；原推荐保持 `m08 → m06 → m01`。

下载入口和完整HF发现流程不等于所有格式、架构或手机都能运行。此清单只对应下述两个配套导出。所有模型保持平级；生音频功能标签、CPU/ONNX/引擎/组件依赖、证据、许可和内容标签相互独立。本模型未声明无审查；其他变体只有其独立来源标签，不影响模型层级。

```text
用户选择的文件夹/
  tts/
    browser_poc_manifest.json
    tts_browser_onnx_meta.json
    tokenizer.model
    moss_tts_prefill.onnx
    moss_tts_decode_step.onnx
    moss_tts_local_fixed_sampled_frame.onnx
    moss_tts_global_shared.data
    moss_tts_local_shared.data
  codec/
    codec_browser_onnx_meta.json
    moss_audio_tokenizer_decode_full.onnx
    moss_audio_tokenizer_decode_shared.data
```

## 资产与许可身份

TTS 来源为 [OpenMOSS官方100M ONNX](https://huggingface.co/OpenMOSS-Team/MOSS-TTS-Nano-100M-ONNX)，固定 `f52645cb467506d8e18e746ddd59482685b74e58`；codec 为 [官方Nano tokenizer ONNX](https://huggingface.co/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX)，固定 `ceff0d0749bfb3fa2d61149794ec6feef0d1e1ae`。发布者标注 Apache-2.0。完整 URL、每文件 SHA256、字节数及来源记录在[资产锁](../research/moss_nano_trained/assets.json)、[取得回执](../verification/development/moss-nano-assets.json)和用户清单中。

| 角色 | 文件 | 字节 |
| --- | --- | ---: |
| manifest | browser_poc_manifest.json | 503,354 |
| tts_meta | tts_browser_onnx_meta.json | 4,487 |
| codec_meta | codec_browser_onnx_meta.json | 17,036 |
| text_tokenizer | tokenizer.model | 470,897 |
| tts_prefill | moss_tts_prefill.onnx | 283,305 |
| tts_decode | moss_tts_decode_step.onnx | 291,483 |
| tts_local | moss_tts_local_fixed_sampled_frame.onnx | 471,262 |
| codec_decode | moss_audio_tokenizer_decode_full.onnx | 681,902 |
| tts_data_1 | moss_tts_global_shared.data | 440,813,568 |
| tts_data_2 | moss_tts_local_shared.data | 229,678,080 |
| codec_data_1 | moss_audio_tokenizer_decode_shared.data | 44,198,912 |

模型专用 manifest 包含音色提示 codes，属于模型资产；分词词表、ONNX图、外部权重均不进入 APK/Git。Git 仅含清单/校验元数据、代码、文档和本轮新文字产生的音频样例。开发取得工具须显式加 `--download`，不是 App 下载入口，也不成为用户必装步骤。

## 独立参数与执行路径

| 参数 | 默认值；可编辑范围 | 约束来源 |
| --- | --- | --- |
| speaker | 0；0–17 | 下载 manifest 实际含18音色；提交再次读取并归位 |
| threads | 2；1–16 | 应用保护，不是设备最优值 |
| maxFrames | 375；1–1500 | 应用保护，另受4096上下文行与60秒codec输出保护 |
| maxInputTokens | 1024；1–2048 | 应用保护，真实SentencePiece分词后校验 |
| seed | 1234；0–2147483647 | 应用保护，不保证跨运行时/手机逐字节相同 |

设置按模型记录保存；可编辑预设超限后归位，提交携带固定参数快照。0–17是此套资产实际音色范围，其他上限均不是经测量的模型理论极限。导出的 local sampling 图固定了 temperature/top-k 等采样常量，界面不提供无效调节。当前没有参考音频克隆、额外WeText规范化或流式音频接口。

真实路径为 SentencePiece → 用户下载的文字/音色提示 → prefill → decode/local采样 → codec decode_full → PCM16 WAV。prefill与TTS缓存依次释放，再加载codec。发布者codec原始输出48kHz双声道；当前worker平均合并为**48kHz单声道**，并非保留立体声。实际路径保护检查未选择的外部权重、路径越界及不匹配图；缺项直接失败。

## 本轮实际结果

固定CPU4线程、seed1234、maxInputTokens1024，通常maxFrames375。下表时间包含每个全新子进程的加载与写出，内存是Windows观察峰值工作集，**不能换算为努比亚Z20速度、可用内存或续航**。

| 真实任务 | 音色 | 音频秒 | 进程秒 | 主机峰值MiB | 结束 |
| --- | ---: | ---: | ---: | ---: | --- |
| 中文A | 0 | 4.32 | 22.32 | 588.0 | stop |
| 中文B，不同文本 | 0 | 5.04 | 18.02 | 593.5 | stop |
| A换音色 | 1 | 3.92 | 28.59 | 586.1 | stop |
| 英文 | 8 | 4.08 | 13.02 | 568.6 | stop |
| 日文 | 11 | 5.04 | 13.34 | 577.4 | stop |
| maxFrames=1 | 0 | 0.08 | 5.55 | 563.6 | length |
| 实际取消后恢复A | 0 | 4.32 | 13.14 | 587.5 | stop |

A与恢复A的完整WAV SHA256均为 `252b14ed3d1c1216518f2afb0b7fa0f78821931c7658984a371641e483347856`；不同文本、换音色的SHA各不相同。第5帧进度后实际终止，约0.063秒退出，不留成功WAV。另有6个错误请求：schema、音色18、分词预算1、帧上限1501、越出执行目录、缺外部global权重。7次成功+7个控制+info，共15个真实子进程。

生产Java链路另通过**40项检查、3个真实原生子进程**：完整717MB本地导入、11项哈希、零网络调用、参数归位与跨模型独立性、执行与取消恢复、租约/进程退出/工作目录清理及存储恢复。两个Java输出与直接worker的A逐字节相同。它使用真实 `BundleStore/BundleTransfers/MossNanoEngine/NativeWorker`，只有Application/AtomicFile为主机文件系统端口，不包含Android调度、SAF或前台服务。

Windows测试链接隔离的官方ORT **1.28.0/API28**，生产Android保留ORT **1.28.2/API28**。仅CRT路径、重定向和父进程保护有Windows适配；生产C++神经运算未改。API版本相同不证明两个运行时数值一致。

![真实主机波形，未做音量归一化](media/development/moss-nano-trained-contact-sheet.png)

[中文原始WAV](media/development/moss-nano-trained-zh.wav) · [英文原始WAV](media/development/moss-nano-trained-en.wav) · [日文原始WAV](media/development/moss-nano-trained-ja.wav) · [静音波形GIF](media/development/moss-nano-trained-waveforms.gif) · [含真实音频的波形轮播MP4](media/development/moss-nano-trained-speech.mp4) · [媒体来源/哈希](media/development/moss-nano-trained-media.json)

原始WAV没有改字节或归一化；MP4音频转AAC，GIF无音轨。二者是标明HOST的波形轮播，**不是App/手机录屏或生成速度演示**。有效WAV、差异输出和可重复性不能代替听感、可懂度、读音、音色相似度或全部18音色/语言质量验收；本轮只实际用了0/1/8/11。

## 开发复现与复核

在仓库目录运行原生Windows工具，准备[已有NDK/MSVC/固定源码依赖](BUILD.md)。不使用Docker/WSL/虚拟机/模拟器。所有模型、运行时与日志留在被忽略的`build/`，不修改全局Python ORT。

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:TEMP="$PWD/build/tmp"
$env:TMP="$PWD/build/tmp"
python tools/fetch_moss_nano_trained.py --download --origin https://hf-mirror.com
python tools/fetch_moss_nano_host_runtime.py --download
python tools/build_moss_nano_host.py
python tools/test_moss_nano_trained.py
python tools/test_moss_nano_app_host.py
python tools/check_moss_nano_trained_evidence.py --raw --self-test
python tools/render_moss_nano_trained.py
python tools/export_development.py
python tools/check_repository.py --development
```

两个fetch工具不带`--download`仅验已有文件，不隐式联网；资产工具也可显式选`https://huggingface.co`。分块下载检查精确Range/长度，最终核对整文件SHA后提交，保留身份不明或改变的已有文件。渲染工具不覆盖既有媒体；新训练运行会产生新的原始目录，改变公开媒体应保留既有发行附件并重新核对对应来源。

公开[训练结果](../verification/development/moss-nano-trained.json)、[Java结果](../verification/development/moss-nano-app-host.json)、[独立原始文件复核](../verification/development/moss-nano-capture-audit.json)、[主机构建](../verification/development/moss-nano-host-build.json)分别保存输入指纹与范围。复核重新读取65原始文件、15协议流、9份WAV和11个实际导入内容对象，并拒绝8种错误提升到Android/质量/完整目标/Release的标记。现有[190项Nano契约](../verification/development/moss-nano.json)仍是独立的早期结构/主机记录。

## 仍待完成

编号09还需Android完整用户取得与运行、语音质量/资源、每模型3次加载卸载、15分钟锁屏、1小时API和升级测试。手机不可用不改变验收结论。编号12的九种MOSS不能由Nano覆盖；F-01–F-12、既有生文、01–14/16/17全部冻结目标及A1–A11/R01–R05仍是同一个v0.3.0的必要范围。完整表见[本轮交付](releases/v0.3.0-dev.24-moss-nano.md)。

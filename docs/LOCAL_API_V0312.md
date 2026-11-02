# 本地多模态 API 与 Sub2API 接入

[English](LOCAL_API_V0312.en.md) · [实机测评](DEVICE_BENCHMARK_V0312.md) · [完整协议](SUB2API_OPENAI.md) · [OpenAPI](proposals/sub2api-openai.openapi.json)

v0.3.12/code62 为本机模型增加标准模型发现、图片和语音兼容层，以及视频、音乐、3D 的统一任务扩展。App 升级只安装基座；模型、依赖与逐模型参数仍由用户在“模型 → 本地”管理。原有 14 项推荐和标签保留，HF 全部／搜索入口不受推荐范围限制。

## 从安装到接口调用

1. 安装正式 APK，进入模型页，选择自己需要的模型包并主动下载或导入完整组件。
2. 在“本地”配置该模型。尺寸、线程、上下文、输出上限等按该模型保存；请求覆盖仅作用于本次任务，越界按模型约束修正。
3. 在“服务”启动 API。新“接口可用模型”面板显示实际公布的 ID、任务标签及当前状态。开启 LAN 监听是明确的用户操作；回环地址只属于手机自身。
4. 客户端访问手机可达地址 `/v1`，使用该手机的 Bearer 密钥。模型列表自动包含已完整安装、配置有效且存在运行器的模型，不要求先点“加载”。
5. 查询 `/v1/models/{id}` 的 `x_lma`，再按 `operations`、输入角色和参数 schema 提交。繁忙／未加载不等于删除模型；部分下载、缺组件、无效配置和独立 LoRA 不作为生成模型公布。

接口密钥相当于手机模型服务的所有者凭据。手机原生接口不提供多人账号隔离；面向多用户时使用下述网关，并保管上游密钥。公开视频不展示密钥、个人聊天或历史任务。

## 路由和明确的范围

| 编号 | 路由 | 当前行为 |
| --- | --- | --- |
| 01 | `GET/HEAD /v1/models`、`/v1/models/{id}` | 标准对象、稳定 ID／创建时间、持久实例 ID、目录修订、ETag／304；附加 `x_lma` 能力与设置 |
| 02 | `GET/HEAD /v1/capabilities`、`/v1/lma/capabilities` | 同一目录快照、输入角色、任务／基座／内容标签、后端选择和限制 |
| 03 | `POST /v1/chat/completions`、`/v1/completions` | 已安装 GGUF 文本模型按请求 ID 在共享执行槽内选择、加载；JSON／SSE 子集 |
| 04 | `POST /v1/images/generations` | 单张 PNG、`n=1`、`b64_json`；真实图片完成才返回标准 200 |
| 05 | `POST /v1/audio/speech` | 显式 `response_format="wav"`，返回真实音频二进制；`voice="default"` 或模型声明的说话人 |
| 06 | `/v1/lma/jobs`、`/preflight`、`/{id}`、`/cancel`、`/retry`、`/events`、`/audio` | 六类统一异步任务：生文／生图／视频／语音／音乐／3D；提交 202，完成后查询产物 |
| 07 | `/v1/lma/uploads`、`/{id}`、`/{id}/complete` | 显式目标模型、分块偏移、SHA256 校验和本地输入；不接受任意本机文件路径 |
| 08 | `/v1/lma/artifacts`、`/{id}`、`/{id}/content` | 产物列表／元数据／鉴权下载，支持真实 Range、If-Range 与 ETag 条件语义 |
| 09 | `/v1/images/edits`、Responses、Videos、Realtime | 当前未开放对应兼容模式，明确报错；图片输入使用模型声明的本地任务角色 |

不能将阶段事件称为图像 token，也不能把下载 WAV 的 HTTP 分块称为增量语音。目录的通用 `incremental_pcm` 保守标记为 false；各引擎已有试听能力需按其独立声明使用。缺省语音格式代表 MP3，当前会报错；不会用 WAV 冒充 MP3。未知的质量、音色、透明背景、批量、mask 或流式字段在提交前拒绝。

## 实际客户端示例

以下变量由使用者提供，不在仓库保存真实密钥。`MODEL_ID` 使用列表返回的原 ID；不要伪装成 GPT 型号。`allow_unmeasured` 是显式接受本机运行估算不足，并不授予下载、远程推理或质量通过。

```python
import os
from openai import OpenAI

client = OpenAI(base_url=os.environ["LMA_BASE_URL"],
                api_key=os.environ["LMA_API_KEY"],
                timeout=150, max_retries=0)
for model in client.models.list():
    print(model.id, model.x_lma["operations"])

wav = client.audio.speech.create(
    model=os.environ["LMA_SPEECH_MODEL"], input="你好，欢迎使用本地模型。",
    voice="default", response_format="wav",
    extra_headers={"Idempotency-Key": "my-speech-request-001"},
    extra_body={"lma": {"allow_unmeasured": True}})
wav.write_to_file("speech.wav")
```

```python
import base64, hashlib, json, time
from urllib.request import Request, urlopen
from openai import APIStatusError

api_root = os.environ["LMA_BASE_URL"].rstrip("/")
assert api_root.endswith("/v1")
api_root = api_root[:-3]
def local_bytes(path):
    assert path.startswith("/v1/lma/")
    req = Request(api_root + path,
                  headers={"Authorization": "Bearer " + os.environ["LMA_API_KEY"]})
    with urlopen(req, timeout=30) as response:
        return response.read()

try:
    result = client.images.generate(
        model=os.environ["LMA_IMAGE_MODEL"], prompt="An orange cube on white.",
        n=1, size="256x256", response_format="b64_json",
        extra_headers={"Idempotency-Key": "my-image-request-001"},
        extra_body={"lma": {"allow_unmeasured": True,
                             "parameters": {"steps": 4, "threads": 4}}})
    png = base64.b64decode(result.data[0].b64_json)
except APIStatusError as error:
    if error.status_code != 504:
        raise
    job_id = error.response.headers.get("X-LMA-Job-ID")
    if not job_id:
        raise
    while True:
        job = json.loads(local_bytes("/v1/lma/jobs/" + job_id))
        if job["state"] in ("failed", "cancelled", "interrupted"):
            raise RuntimeError(job["error"])
        if job["state"] == "succeeded":
            output = job["outputs"][0]
            png = local_bytes(output["content_path"])
            assert hashlib.sha256(png).hexdigest() == output["sha256"]
            break
        time.sleep(2)
open("image.png", "wb").write(png)
```

手机同步等待预算为 120 秒，最多 3 个等待名额；生成执行仍只有一个重型槽。较慢模型请优先使用异步任务。504 返回 `X-LMA-Job-ID` 和 `x_lma.job_id`，任务可能继续，按原键／原正文回查；禁止因为超时换键重复生成。

```json
{
  "model": "<INSTALLED_VIDEO_MODEL_ID>",
  "type": "video.generate",
  "input": {"prompt": "An orange cube on a white background."},
  "parameters": {"width": 128, "height": 128, "frames": 49,
                 "fps": 8, "steps": 4, "threads": 4,
                 "executionBackend": "cpu"},
  "allowUnmeasured": true
}
```

将 JSON POST 到 `/v1/lma/jobs`，带独立 `Idempotency-Key`。轮询 `GET /v1/lma/jobs/{id}`，成功后下载 `outputs[].content_path`。取消使用 **`POST /v1/lma/jobs/{id}/cancel`**；`DELETE /v1/lma/jobs/{id}` 删除已终止的历史记录。显式 `/retry` 创建新任务并需新键。图生 3D 的 `input.artifacts` 使用声明的角色，例如 `reference_image`；无需编造文本提示词。语音、音乐和多视图输入均以所选模型的 schema 为准。

模型加载与生成没有固定执行时限：移除原队列两小时和文本加载五分钟上限，文本生成读取持续等待。49 帧／8 fps 的视频目标为 6.125 秒。仍保留用户取消、输出长度约束、真实资源不足保护，以及独立的 HTTP 等待／断连限制；这些网络限制不会取消已接纳的异步任务。

历史 `/retry` 使用原参数；若要修正步数、引导或输入，请在“本地”修改该模型，再新建任务并使用新幂等键。3D 默认建议步数12、引导7.5；这不是本机画质或GLB成功保证。

## 持久化与性能

目录来自轻量资产／配置修订缓存。反复发现模型不扫描权重、不启动探测进程、不下载或加载模型。设置变更、安装完成与删除触发失效；请求覆盖不修改保存设置。公开参数会移除私人提示词、路径及凭据；内部配置修订仍反映真实变动。

手机与网关均在请求发送前持久化幂等意向，先按调用者／端点／键查找，再核对原正文。相同键不同正文 409；有效参数仅第一次解析时冻结。历史删除仍保留墓碑，终态至少保留 24 小时；窗口内原任务被清理则返回 410，不重新运行。手机进程重启可恢复记录，但中断任务没有模型计算检查点，不能宣称断点续算。

网关的聊天／文本请求使用独立传输，不受普通响应头等待上限影响；普通控制请求仍有网络预算。回归检查用真实 HTTP 延迟响应，验证文本请求能超过缩短后的普通网络等待预算。

## Sub2API 原生源码扩展

源码包位于 [integrations/sub2api](../integrations/sub2api/README.md)。针对官方 `Wei-Shaw/sub2api` **v0.2.19 / dece26153621959ccd7635814f4b2d08304e681a** 的 opt-in 扩展保留原鉴权、分组和模型白名单，在模型族校验前使用手机公布的能力路由，不伪造 GPT 模型。

这不是仅填一个 OpenAI base URL 就能启用的原版功能。使用 `tools/apply_sub2api.py --source <独立上游源码目录>` 安装扩展，再原生编译 Sub2API。脚本要求精确审计过的上游路由字节，拒绝未知版本。不要对生产进程盲目套用；本次发布未修改任何现网部署或数据库。

配置通过 `SUB2API_LMA_CONFIG` 指向私有 JSON，密钥仅从环境变量读取：

```json
{
  "state_file": "/private/lma-state.json",
  "accounts": [{"account_id": 1, "group_id": 2,
    "base_url": "http://PHONE_ADDRESS:8080",
    "key_env": "LMA_PHONE_KEY",
    "expected_instance_id": "<FROM_PHONE_CATALOGUE>",
    "aliases": {"my-local-speech": "<ACTUAL_INSTALLED_MODEL_ID>"}}]
}
```

`account_id` 是扩展私有注册表中的手机标识，`group_id` 必须对应管理员选择的独立 Sub2API 分组。**扩展不创建或覆写数据库账号／模型映射**。同分组的公开模型名与别名必须无冲突；冲突拒绝整个新目录，保留上一次有效快照。建议每台手机使用独立分组。未配置的分组继续使用原版路由。

网关每约 30 秒条件同步（±20% 抖动），连接 3 秒、读取 5 秒、失败退避最多 300 秒。首次目录未知返回 503；超过 90 秒的旧模型可见但不可新调度；实例身份变化拒绝接管。正文／任务／上传／产物映射与原手机绑定原子保存，普通调用者仅可见自己的资源；不会转发手机全库历史。

事件使用每手机共用的有界 JSON 缓存再向客户端输出 SSE，不为每个调用者占一个手机 SSE。缓存最多 1024 条、同时最多 64 位下游订阅者；游标截断返回 reset。原生手机直接 SSE 仍最多 2 路、单次 120 秒。媒体使用有界流转发，保留 Range／If-Range／ETag；不创建外部推理节点，不回退云模型。

网关合同测试、固定上游源码编译、真实手机转发和现网鉴权／计费是不同证据。本次没有部署生产 Sub2API，也没有验收生产数据库、余额扣费或价格映射；不会为本地生成伪造 token 用量或价格。

## 检查与实机证据

```text
python tools/test_api_publication.py
python tools/test_sub2api_gateway.py
python tools/device_check.py --serial SERIAL --run --install --existing-models --program-api --minutes 1
python tools/profile_device.py --serial SERIAL --label optimized --existing-models
python tools/device_sdk_integration.py --serial SERIAL
```

最后三项需要已授权真机；SDK 检查会使用已安装的语音／图像模型，创建自有测试素材和任务。完整实机结果、参数、超时、温度与证据哈希见[测评](DEVICE_BENCHMARK_V0312.md)。测试成功生成文件不能替代画质、音质、全模型覆盖或长期后台验收。

## 内网 HTTP 实测补充

开启“服务 → 允许局域网访问”后，使用手机Wi-Fi地址而非手机回环地址；从PC发起HTTP请求可直接访问模型与任务。本轮57项/128次请求验证、环境变量和curl示例见[局域网测试指南](LAN_HTTP_TEST.md)。ADB仅作UI设置，数据链路无端口转发或代理。

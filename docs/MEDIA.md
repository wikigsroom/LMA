# 截图与演示 / Screenshots and demonstrations

[文档目录 / Documentation](README.md)

## 来源与范围 / Source and scope

当前素材由 `tools/capture_media.cjs` 直接加载 `app/src/main/assets/` 中随 APK 分发的 HTML / CSS / JavaScript，通过明确的演示原生桥接录制。390 × 844 CSS 像素视口；截图为 2 倍像素比例。视频是浏览器页面实际录制，FFmpeg 转成 MP4 / GIF，非设计稿动画。

The capture script renders the exact shipped UI assets with an explicit demonstration native bridge, at a 390 × 844 CSS-pixel viewport. Screenshots use scale factor 2. The video is an actual browser-page recording, converted by FFmpeg, not an animation of design mockups.

**不是 Android 真机实录。Not a physical Android recording.** 下载状态为模拟；对话是带“非模型输出”标识的脚本文本；示例 IP 为 `192.0.2.20`，API 密钥是演示占位符。没有下载模型或执行推理。顶部全程显示 UI DEMO；不会移除标识后将素材冒充验收。

Downloads are simulated. Chat text explicitly says it is not model output. The IP and key are placeholders. No weights are downloaded and no inference runs. The permanent demo banner must remain when sharing these assets.

## 截图 / Screenshots

| 页面 / Page | 文件 / File |
| --- | --- |
| 无审查模型库 / Uncensored model library | [01-library.png](media/01-library.png) |
| 作者依据与哈希 / Publisher evidence and hash | [02-model-evidence.png](media/02-model-evidence.png) |
| 模拟下载与暂停 / Simulated download controls | [03-download.png](media/03-download.png) |
| 对话与代码 / Scripted chat and code | [04-chat.png](media/04-chat.png) |
| OpenAI 兼容服务 / API service controls | [05-api.png](media/05-api.png) |
| 参数设置 / Settings | [06-settings.png](media/06-settings.png) |
| 深色主题 / Dark theme | [07-dark.png](media/07-dark.png) |

<p>
  <img src="media/02-model-evidence.png" width="260" alt="Publisher evidence / 作者依据，演示数据">
  <img src="media/03-download.png" width="260" alt="Simulated download / 模拟下载">
  <img src="media/04-chat.png" width="260" alt="Scripted demonstration chat / 脚本对话">
</p>

## 录屏和 GIF / Recording and GIFs

- [lma-walkthrough.mp4](media/lma-walkthrough.mp4)：完整操作录屏 / Full UI walkthrough，约 25 秒 / approximately 25 seconds。
- [lma-walkthrough.gif](media/lma-walkthrough.gif)：完整 GIF / Full walkthrough GIF。
- [lma-api-theme.gif](media/lma-api-theme.gif)：API 与主题短片 / API and theme excerpt。
- [manifest.json](media/manifest.json)：输入指纹、截图清单、文件大小和 SHA256、视频探测信息与演示边界 / Input fingerprints, files/hashes, video probe, and simulation scope。

<p><img src="media/lma-api-theme.gif" width="320" alt="API and theme UI demo / API 与主题演示"></p>

## 复现 / Reproduce

需要 Node.js、Playwright、Edge / Chromium、Playwright 的 FFmpeg 组件，以及 PATH 中的 FFmpeg / FFprobe。Requires Node.js, Playwright, a browser, Playwright's FFmpeg component, and FFmpeg / FFprobe on PATH.

```powershell
# 可选：指定已有依赖 / Optional: select existing dependencies
$env:LMA_PLAYWRIGHT = 'C:/path/to/node_modules/playwright'
$env:LMA_BROWSER = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
node tools/capture_media.cjs
```

`LMA_FFMPEG`、`LMA_FFPROBE` 可指定可执行文件。服务器仅监听临时本机端口，网络路由阻止外部资源。原始视频与专用浏览器 profile 位于被忽略的 `build/media/`，不上传。finally 关闭所有录制页、context 和浏览器，并停止 HTTP 服务。

The server binds to a temporary loopback port and external requests are blocked. Raw video and the dedicated browser profile stay in ignored `build/media/`. Cleanup closes recording pages, context/browser, and the server even on failure.

## 后续补充 / Future device media

真机可用后，应单独补充安装、完整下载、实际生成及屏幕关闭期间客户端持续输出的录制，并关联设备、参数、模型哈希和验收结果。不要把屏幕录制本身当成无 ADB / 电池供电耐久证据。

When a phone becomes available, add separately labeled installation, real download/inference, and screen-off client recordings with device, parameters, model hash, and acceptance results. Screen recording alone is not evidence of unplugged, ADB-free endurance.

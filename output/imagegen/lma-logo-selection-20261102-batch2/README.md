# LMA · 第二批安卓与鲸鱼 Logo 选型 / Batch 2: Android, AI and whale

2026-11-02 · [离线选型页 / Offline selector](index.html) · [编号总览 / Overview](overview.jpg) · [小尺寸 / Small sizes](small-size-review.jpg)

第二批保留第一批归档，编号延续为 11–20：11–15 安卓＋AI，16–20 安卓＋鲸鱼（DeepSeek 风格蓝鲸）。按用户指定的 **sub2-image-gen** 技能，通过配置的 Sub2API 图像路线请求 **gpt-image-2.5 / high / 1024×1024 / PNG**，逐套独立生成。网关实际原图尺寸见 [manifest](manifest.json)；原始字节保留，1024/512/192/96/48/32px 为单独缩放版本。颜色、材质和核心符号均来自实际生成，拼图仅用于排版，未用绘图程序替代 Logo 生成。

Batch 2 contains Android + AI directions (11–15) and Android + blue-whale directions (16–20), inspired by the requested DeepSeek whale theme. Batch 1 is archived separately. Generated individually through the requested **sub2-image-gen / Sub2API** route with **gpt-image-2.5**, high quality and requested 1024×1024 PNG. Actual original dimensions are recorded in the manifest. Native image bytes are preserved; standard previews are resized copies. Code only lays out the comparison boards and creates previews.

| 编号 / ID | 名称 / Name | 风格 / Style | 核心元素 / Element | 查看 / View |
| --- | --- | --- | --- | --- |
| 11 | 智核安卓 / Android AI Core | 极简平面 / Flat mascot | 安卓头部＋AI 智核 | [原图 / Original](11-android-ai-core.png) |
| 12 | 芯片小安卓 / Chip Buddy | 像素玩具 / Pixel toy | 安卓全身＋胸前芯片 | [原图 / Original](12-android-chip-buddy.png) |
| 13 | 玻璃智脑 / Glass Mind | 磨砂玻璃 / Frosted glass | 安卓头部＋神经节点 | [原图 / Original](13-android-glass-mind.png) |
| 14 | 纸片助手 / Paper Assistant | 折纸形象 / Origami mascot | 安卓机器人＋对话卡片 | [原图 / Original](14-android-paper-assistant.png) |
| 15 | 星航安卓 / Cosmic Android | 软胶公仔 / Vinyl character | 安卓宇航员＋AI 核心 | [原图 / Original](15-android-space-ai.png) |
| 16 | 鲸化安卓 / Droid Whale | 极简融合 / Flat fusion | 蓝鲸轮廓＋安卓天线 | [原图 / Original](16-android-whale-fusion.png) |
| 17 | 鲸帽小安卓 / Whale Hood | 软陶吉祥物 / Clay mascot | 安卓脸＋蓝鲸连帽套装 | [原图 / Original](17-android-whale-hood.png) |
| 18 | 安卓鲸伴 / Droid & Whale | 扁平伙伴 / Flat character duo | 安卓机器人拥抱蓝鲸 | [原图 / Original](18-android-whale-partners.png) |
| 19 | 机械蓝鲸 / Mecha Whale | 等距机甲 / Isometric mecha | 机器人面板＋机械鲸身 | [原图 / Original](19-android-mecha-whale.png) |
| 20 | 鲸尾智环 / Whale Embrace | 双色图形 / Two-tone emblem | 安卓头部＋环抱鲸尾 | [原图 / Original](20-android-whale-embrace.png) |

## 如何选 / How to choose

1. 打开总览或离线网页，先挑 2–3 个方向。Open the overview or offline page and shortlist two or three directions.
2. 比较 96/48/32px 下的轮廓、配色与识别度。Compare silhouette and recognition in small previews.
3. 网页可以多选、切换深浅衬底并复制编号；不会联系网关或保存个人数据。The page supports selection, surface switching and copying IDs, with no network calls or personal-data storage.
4. 按编号说明喜欢的元素、配色和材质；选定后再精修、制作透明／单色版本与 Android adaptive icon。Choose direction/elements/colors before refinement and production icon adaptation.

当前为带深色底的栅格 PNG 候选，不是矢量文件或透明底成品，没有替换 App 图标／发布新 APK。No production icon has been selected or applied. These are opaque dark-background raster PNG directions, not SVGs, transparent masters or finished adaptive icons.

`prompts/` contains the ten public creative briefs. `manifest.json` records per-image hashes, actual dimensions and generation settings without gateway URLs, credentials or private request headers. The local ZIP is ignored in Git because its contents are already versioned separately.

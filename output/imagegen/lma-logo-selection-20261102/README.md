# LMA · 10 套 Logo 选型 / Ten logo directions

2026-11-02 · [离线选型页 / Offline selector](index.html) · [编号总览 / Overview](overview.jpg) · [小尺寸 / Small sizes](small-size-review.jpg)

按用户指定的 **sub2-image-gen** 技能，通过配置的 Sub2API 图像路线请求 **gpt-image-2.5 / high / 1024×1024 / PNG**，逐套独立生成。网关实际原图尺寸见 [manifest](manifest.json)；原始字节保留，1024/512/192/96/48/32px 为单独缩放版本。颜色、材质和核心符号均来自实际生成，拼图仅用于排版，未用绘图程序替代 Logo 生成。

Generated individually through the requested **sub2-image-gen / Sub2API** route with **gpt-image-2.5**, high quality and requested 1024×1024 PNG. Actual original dimensions are recorded in the manifest. Native image bytes are preserved; standard previews are resized copies. Code only lays out the comparison boards and creates previews.

| 编号 / ID | 名称 / Name | 风格 / Style | 核心元素 / Element | 查看 / View |
| --- | --- | --- | --- | --- |
| 01 | 折叠字标 / Folded Monogram | 极简几何 / Swiss geometric | LMA 字母与折叠结构 | [原图 / Original](01-folded-monogram.png) |
| 02 | 棱镜入口 / Prism Portal | 光学玻璃 / Optical glass | 三片棱镜与创作入口 | [原图 / Original](02-prism-portal.png) |
| 03 | 轨道镜头 / Orbit Lens | 精密线形 / Technical contour | 镜头与偏心轨道 | [原图 / Original](03-orbit-lens.png) |
| 04 | 声纹花 / Signal Bloom | 平面剪纸 / Flat cut-paper | 声波花瓣与创作绽放 | [原图 / Original](04-signal-bloom.png) |
| 05 | 像素织机 / Pixel Loom | 复古像素 / Pixel graphic | 像素拼接与模块编织 | [原图 / Original](05-pixel-loom.png) |
| 06 | 软陶伙伴 / Clay Companion | 软陶吉祥物 / Clay mascot | 口袋机器人与陪伴 | [原图 / Original](06-clay-companion.png) |
| 07 | 铜线门廊 / Copper Doorway | 装饰艺术 / Art Deco | 门廊与本地芯片 | [原图 / Original](07-copper-doorway.png) |
| 08 | 墨山印记 / Ink Mountain | 东方水墨 / Modern ink | 山形笔势与朱红太阳 | [原图 / Original](08-ink-mountain.png) |
| 09 | 流体对话 / Flux Dialogue | 流体动势 / Fluid gradient | 对话轮廓与流动丝带 | [原图 / Original](09-flux-dialogue.png) |
| 10 | 等距模块 / Modular Forge | 等距构造 / Isometric architecture | 三面模块与创作基座 | [原图 / Original](10-modular-forge.png) |

## 如何选 / How to choose

1. 打开总览或离线网页，先挑 2–3 个方向。Open the overview or offline page and shortlist two or three directions.
2. 比较 96/48/32px 下的轮廓、配色与识别度。Compare silhouette and recognition in small previews.
3. 网页可以多选、切换深浅衬底并复制编号；不会联系网关或保存个人数据。The page supports selection, surface switching and copying IDs, with no network calls or personal-data storage.
4. 按编号说明喜欢的元素、配色和材质；选定后再精修、制作透明／单色版本与 Android adaptive icon。Choose direction/elements/colors before refinement and production icon adaptation.

当前为带深色底的栅格 PNG 候选，不是矢量文件或透明底成品，没有替换 App 图标／发布新 APK。No production icon has been selected or applied. These are opaque dark-background raster PNG directions, not SVGs, transparent masters or finished adaptive icons.

`prompts/` contains the ten public creative briefs. `manifest.json` records per-image hashes, actual dimensions and generation settings without gateway URLs, credentials or private request headers. The local ZIP is ignored in Git because its contents are already versioned separately.

[Validation](validation.json): native/derived PNGs, hashes, sizes, local resources, script syntax and archive integrity; no browser/device/model-quality acceptance.

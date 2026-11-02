"""Prepare and package the ten LMA home-screen design directions (native tools only).

Images are generated separately with the explicitly requested sub2-image-gen skill.
This tool never configures a gateway, handles credentials, or changes the Android UI.
"""
from __future__ import annotations

import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output/imagegen/lma-home-ui-selection-20261103"

STYLES = [
    dict(id="01", slug="material-expressive", zh="灵动质感", en="Material Expressive", language="Material 3 / Android 原生", palette=["#101827", "#1E2D47", "#3A7BFA", "#AEEC57", "#ECF1FF"],
         visual="Confident Android Material 3 expressive design. Large asymmetric rounded containers, opaque tonal surface layers, a bold cobalt active segmented pill and lime accents. Clean humanist sans typography, generous but efficient grouping. Rounded square monogram model icons. Signature: a playful cobalt search capsule paired with a lime add action. No glass blur, no gradients, no soft embossed shadows.",
         signature="柔和异形圆角、色调分层、大号胶囊筛选", implementation="以不透明色块和局部圆角构成，适合优先落地。"),
    dict(id="02", slug="neo-flat", zh="清晰新扁平", en="Neo Flat", language="Flat 2.0 / 新扁平", palette=["#131C26", "#233346", "#4A8DFF", "#FF9B83", "#F5F7FA"],
         visual="Contemporary flat 2.0 interface. Sharp hierarchy through typography, 8px corner radii, clean thin dividers and solid two-dimensional color fields. White typography, muted blue-gray panels, coral secondary actions, cobalt primary actions. Small restrained flat geometric icons. Signature: a coral index bar aligned to the recommended model list. No gradient, glass, decorative illustration or embossed shadow.",
         signature="清楚的字级、紧凑列表、纯色色块与珊瑚点缀", implementation="使用纯色、边框与字级，低成本保持信息清晰。"),
    dict(id="03", slug="neumorphism", zh="石墨新拟物", en="Graphite Neumorphism", language="Neumorphism / 新拟物", palette=["#272D36", "#323945", "#8FC7FF", "#D2E2EF", "#F4F7FC"],
         visual="Dark graphite neumorphism with tactile soft-pressed controls. One coherent graphite substrate, raised cards cast paired upper-left pale highlights and lower-right dark shadows; the selected segmented tab and search well are inset. Icy blue accent and luminous white high-contrast text. Restrained volume, subtle shadow depth, not low-contrast gray text. Signature: an inset search slot and embossed model-icon medallions. No glass transparency, no neon, no hard offset shadows.",
         signature="同色基底、双向软阴影、内凹搜索与凸起卡片", implementation="文字与状态需额外保持对比；阴影限制在少量控件。"),
    dict(id="04", slug="frosted-glass", zh="雾蓝毛玻璃", en="Frosted Glass", language="Glassmorphism / 毛玻璃", palette=["#0B1424", "#1B3550", "#79D8EE", "#AAA1FF", "#EDF7FF"],
         visual="Elegant frosted-glass mobile UI over a restrained deep-blue atmospheric gradient. Thick smoke-blue translucent frosted panels with strong diffusion, delicate white hairline borders and matte blurred silhouettes behind them. Quiet cyan and lavender accents, legible white text. Signature: one broad frosted resource/status plate, smaller glass model cards. Frosted matte diffusion is essential. No transparent liquid lenses, no rainbow iridescence, no chrome.",
         signature="烟蓝半透明面板、漫射背景、细亮边框", implementation="实现时控制模糊层数量，提供无模糊的低开销回退。"),
    dict(id="05", slug="liquid-glass", zh="深海液态玻璃", en="Ocean Liquid Glass", language="Liquid Glass / 液态玻璃", palette=["#070E1B", "#102844", "#4FADFF", "#B2EBEC", "#F3FAFF"],
         visual="Premium liquid-glass interface on a very dark ocean-blue backdrop. Clear rounded lens-like floating controls, refractive curved edges, precise specular highlights and slight optical magnification at the rims. Keep card interiors optically calm and text perfectly crisp. Navy and ice-blue only, no bright rainbow. Signature: a floating clear-lens bottom navigation and luminous convex active tab. Distinct from frosted glass: clear polished refractive rims rather than matte blur. No 3D floating hardware.",
         signature="透明透镜边缘、镜面高光、悬浮导航", implementation="需单独评估可读性与低端机开销；选型不代表已实现折射。"),
    dict(id="06", slug="neo-brutalism", zh="硬边新粗野", en="Neo Brutalism", language="Neo-brutalism / 新粗野", palette=["#14151C", "#26315B", "#637DFF", "#D8F262", "#FFFFFF"],
         visual="Deliberate neo-brutalist mobile product interface in dark mode. Thick 2-3px light outlines, offset hard-edged shadows, mostly rectangular controls, assertive heavy grotesk typography. Cobalt and punchy lime blocks against deep charcoal. Square plus action, outlined model cards, boxed tag labels. Signature: hard offset lime shadows on the main download action and bold numbered content gutters. Functional and disciplined, not a poster, no excessive decoration, no soft shadows or blur.",
         signature="粗线框、硬投影、大字重、明确的按钮触感", implementation="可用边框和硬投影实现；需控制标签与描边的视觉密度。"),
    dict(id="07", slug="claymorphism", zh="软胶轻拟物", en="Soft Clay", language="Claymorphism / 软胶轻拟物", palette=["#1A2033", "#303B5C", "#86A7FF", "#D7B2EE", "#F5EEDC"],
         visual="Sophisticated claymorphism that complements the supplied vinyl-toy whale Android mascot. Dark periwinkle substrate, softly inflated matte rounded cards, subtle puffy lilac and blue controls, cream-white legible type. Tiny model-icon cushions and gently raised pills, tactile matte materials. Keep the exact supplied cobalt/lime/cream mascot identity. Signature: plump pill filters and small clay model-icon tiles. Avoid childish oversized toys, no full-screen mascot illustration, no glass, no hard shadows.",
         signature="哑光软胶体积、蓬松按钮、柔和蓝紫色阶", implementation="保留现有 Logo，轻量阴影模拟体积，避免大面积三维装饰。"),
    dict(id="08", slug="industrial-skeuomorphic", zh="精密仪表", en="Precision Instrument", language="Skeuomorphism / 工业拟物", palette=["#171C23", "#2F3B49", "#6488B1", "#EBC987", "#E9EFF5"],
         visual="Refined industrial skeuomorphism, a premium portable scientific instrument translated to a usable mobile application. Dark anodized blue-gray metal surfaces, tiny engraved labels, recessed display wells, subtle material grain, amber status LED and precise hairline rules. Download buttons feel like understated machined push switches; model cards like instrument slots. Signature: three compact recessed resource readouts. Texture stays very quiet; high legibility; no fake screws, dials, steampunk, holograms or giant decorative meters.",
         signature="阳极金属面板、嵌入式读数、细刻线与琥珀状态灯", implementation="材质应优先使用静态轻纹理；不加入与模型无关的仪表功能。"),
    dict(id="09", slug="minimal-typography", zh="极简字序", en="Type First", language="Minimal / 极简排版", palette=["#12151C", "#222A35", "#7FAEFF", "#A5B2C4", "#FAFBFF"],
         visual="Editorial precision and premium typographic minimalism for a serious local AI tool. Near-black blue-charcoal background, generous aligned margins, few fine blue-gray divider lines, white humanist sans typography with a strong but compact heading, cobalt accents only for primary actions. Mostly borderless model rows instead of heavy cards; small monogram icons and understated tags. Signature: remarkably clear model names and quiet unboxed three-column resource data. No gradients, textures, decorative shadows, glass or oversized whitespace.",
         signature="去除厚重卡片、字级主导、细分隔与单一蓝色强调", implementation="主要依赖排版和间距，可优先做轻量实现。"),
    dict(id="10", slug="fluent-bento", zh="云母分区", en="Mica Bento", language="Fluent 2 / Mica / Bento", palette=["#151A2B", "#242D47", "#8CB3FF", "#7ADCC3", "#F0F4FF"],
         visual="Fluent-inspired dark Mica interface adapted thoughtfully for an Android phone. Opaque layered blue-gray surfaces with the faintest mica color variation, restrained 6-10px rounded geometry, a small bento arrangement for the three resource tiles, precise thin outline icons, calm teal and cobalt accents. Structured segmented filters, compact softly separated model tiles. Signature: three unequal but aligned resource bento tiles with understated diagonal tonal variation. This is organized subtle surface layering, not transparent glass, not neon, not exaggerated 3D.",
         signature="云母色层、分区资源格、克制圆角和层叠关系", implementation="采用静态色层与布局，不依赖平台专属材质接口。"),
]

COMMON = """Create ONE finished, high-fidelity portrait mobile-app home screen design, 1024x1536 pixels. This is an Android local AI model workbench called LMA. Use the FIRST supplied image as the exact approved logo identity (cobalt-blue whale-costume Android, lime face and twin antennae, cream rim/belly). Keep that mascot as a small header logo only, preserve its identity and palette. The SECOND supplied image is an older real home-screen content reference, NOT a style target. Redesign its visual hierarchy and density using the style direction below. The current product remains a local model library; do not turn it into a dashboard, chat screen, landing page or image gallery.

COMPOSITION: straight-on full-bleed app UI artboard filling the entire image, no phone hardware, perspective, hands, surrounding room, separate palette board, style title, watermarks or marketing poster. Dark mode. A tidy narrow Android status bar with 9:41 at the top, compact brand/header, compact runtime strip, compact title and three resource readouts, search, two filter rows, recommended model list, and the existing five-item bottom navigation fully visible. Efficient vertical spacing: show at least TWO complete model cards and a THIRD visible card/row. Do not repeat the original screenshot's oversized empty vertical gaps. Body typography must look touch-friendly and readable. Strong contrast, coherent alignment, considered iconography, production-quality spacing.

CONTENT AND INTERACTION HIERARCHY, identical across all ten directions:
Header: small approved mascot + 'LMA', Chinese slogan exactly '把无审查 AI，装进口袋。' and English slogan exactly 'Uncensored AI, right in your pocket.' set smaller. Do not invent a different slogan.
Runtime strip: small neutral status dot, '尚未加载模型', and right-side '管理'. It is an idle screen, not an active inference benchmark.
Main title exactly '选择你的本地模型', a compact '+' action for adding a model. One very short secondary line '从推荐开始，探索 Hugging Face'.
Three compact resource values are illustrative UI data, not benchmark results: '设备内存' '8 GB'; '可用存储' '64 GB'; '已下载模型' '0'.
Search input with magnifying glass and placeholder '搜索 HF 模型'.
First segmented row, in this order: '推荐' selected, '本地', '轻量', '进阶', '全部'.
Second row: '所有功能' selected, '生文', '生图', '生视频', '生音频', '生 3D'. All must remain represented; no remote provider selector.
List header '推荐模型', compact trailing '14 个'.
Preserve the recommendation order exactly. First model 'Qwen 3 · 1.7B Abliterated', metadata 'Q4_K_M · 1.11 GB', separate small tags '生文' and '无审查', plus a clear '下载' action. Second 'LFM 2.5 · 1.2B Uncensored', metadata 'Q4_K_M · 731 MB', same separate tags and '下载'. Third 'Dolphin 3 · Qwen 0.5B', metadata 'Q4_K_M · 398 MB', same tags and action when space allows. Do not replace these with fictional image/video models. No claims of running, loaded, tok/s, NSFW output imagery or generated artwork thumbnails.
Bottom navigation in exact order: '模型库' active, '对话', '任务', '服务', '设置', each paired with a clear compact line icon. Make the current tab unmistakable.

All Chinese copy should be correctly typeset Simplified Chinese, not garbled glyphs. English model names and short numbers stay crisp. This is a visual direction proposal, not an implementation screenshot. Use all the available pixel resolution for the actual interface. The style's material treatment, geometry and typography must be immediately distinguishable from other directions, not merely a hue swap.
"""


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare() -> None:
    (OUTPUT / "prompts").mkdir(parents=True, exist_ok=True)
    (OUTPUT / "reference").mkdir(exist_ok=True)
    references = [
        ("docs/media/branding/lma-logo.png", "logo-21.png", "Approved Logo 21; preserve identity, not an alternative design"),
        ("docs/media/device/v0.3.13/01-recommended.png", "home-v0.3.13.png", "Historical physical v0.3.13 content reference; not current v0.4.0 UI evidence"),
    ]
    refs = []
    for source, target, note in references:
        shutil.copyfile(ROOT / source, OUTPUT / "reference" / target)
        refs.append(dict(source=source, file="reference/" + target, sha256=sha(ROOT / source), note=note))
    inputs = ["app/src/main/assets/index.html", "app/src/main/assets/app.css", "app/src/main/assets/app.js", "catalogue/verified-models.json"]
    source_context = dict(version="0.4.0", date="2026-11-03", inspected=[dict(file=name, sha256=sha(ROOT / name)) for name in inputs],
                          initialTab="models", initialFilter="recommended", recommendedPrefix=["m08", "m06", "m01"],
                          observations=["Title, resource data and two filter groups consume much of the initial viewport.", "Keep five navigation destinations, user-owned model downloads and independent task/content tags.", "Use compact grouping to expose more model choices without hiding controls."],
                          mockData="8 GB / 64 GB / 0 are illustrative design values, not physical-device measurements.", references=refs)
    write_json(OUTPUT / "source-context.json", source_context)
    for style in STYLES:
        prompt = COMMON + "\nSTYLE DIRECTION: " + style["language"] + " / " + style["en"] + ".\n" + style["visual"] + "\nPalette: " + ", ".join(style["palette"]) + ".\n"
        (OUTPUT / "prompts" / (style["id"] + "-" + style["slug"] + ".txt")).write_text(prompt, encoding="utf-8")
    write_json(OUTPUT / "directions.json", STYLES)
    print(f"Prepared {len(STYLES)} distinct directions in {OUTPUT}")


def build() -> None:
    from PIL import Image, ImageDraw, ImageFont, ImageOps

    preview_dir = OUTPUT / "previews"
    preview_dir.mkdir(exist_ok=True)
    fonts = Path("C:/Windows/Fonts")
    face = fonts / "msyh.ttc"
    bold = fonts / "msyhbd.ttc"
    def font(size, heavy=False):
        return ImageFont.truetype(str(bold if heavy else face), size)

    manifest = dict(schema="lma.home-ui-selection/1", date="2026-11-03", appVersion="0.4.0", status="awaiting_user_selection",
                    generator=dict(skill="sub2-image-gen", modelRequested="gpt-image-2.5", command="edit", endpoint="/v1/images/edits", sizeRequested="1024x1536", quality="high", format="png", imageReferences=["reference/logo-21.png", "reference/home-v0.3.13.png"]),
                    scope="AI-generated visual directions, not an implemented UI or physical-device screenshot; no performance benchmark", approvedLogo="21", approvedSlogan="04", defaultTheme="dark",
                    postprocessing="Original PNG bytes preserved; only previews and comparison boards are resized/composed. No program recoloring or logo replacement.",
                    sourceContext="source-context.json", directions=[])
    sizes = set()
    for style in STYLES:
        item = dict(style)
        stem = style["id"] + "-" + style["slug"]
        original = OUTPUT / (stem + ".png")
        with Image.open(original) as im:
            im.verify()
        with Image.open(original) as im:
            rgb = im.convert("RGB")
            sizes.add(rgb.size)
            preview = ImageOps.contain(rgb, (512, 768), Image.Resampling.LANCZOS)
            preview.save(preview_dir / (stem + ".jpg"), quality=91, optimize=True)
            dimensions = list(rgb.size)
        item.update(file=stem + ".png", preview="previews/" + stem + ".jpg", prompt="prompts/" + stem + ".txt", dimensions=dimensions,
                    bytes=original.stat().st_size, sha256=sha(original))
        manifest["directions"].append(item)
    assert sizes == {(1024, 1536)}, sizes
    assert len({item["sha256"] for item in manifest["directions"]}) == 10, "Duplicate original images"

    def board(items, file, title, columns):
        tile_w, image_h, label_h, margin, gap, top = 430, 645, 96, 32, 20, 104
        rows = (len(items) + columns - 1) // columns
        canvas = Image.new("RGB", (margin * 2 + columns * tile_w + (columns - 1) * gap, top + rows * (image_h + label_h + gap) + margin), "#0B1120")
        d = ImageDraw.Draw(canvas)
        d.text((margin, 22), title, font=font(30, True), fill="#EDF4FF")
        d.text((margin, 66), "AI 设计概念稿 · 相同首页内容 · 暗色方向 · Logo 21", font=font(17), fill="#B0C0D9")
        for index, item in enumerate(items):
            x, y = margin + (index % columns) * (tile_w + gap), top + (index // columns) * (image_h + label_h + gap)
            with Image.open(OUTPUT / item["preview"]) as im:
                canvas.paste(im.resize((tile_w, image_h), Image.Resampling.LANCZOS), (x, y))
            d.text((x, y + image_h + 11), item["id"] + "  " + item["zh"], font=font(23, True), fill="#F1F5FF")
            d.text((x, y + image_h + 48), item["en"], font=font(17), fill="#ACBDD9")
        canvas.save(OUTPUT / file, quality=94, optimize=True)

    board(manifest["directions"], "overview.jpg", "LMA / 首页 UI 风格选型 / 01—10", 5)
    board(manifest["directions"][:5], "overview-01-05.jpg", "LMA / 首页 UI 风格选型 / 01—05", 5)
    board(manifest["directions"][5:], "overview-06-10.jpg", "LMA / 首页 UI 风格选型 / 06—10", 5)
    write_json(OUTPUT / "manifest.json", manifest)
    (OUTPUT / "directions.js").write_text("window.LMA_DESIGN_DIRECTIONS = " + json.dumps(manifest["directions"], ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
    cards = []
    for item in manifest["directions"]:
        cards.append(f'''<article class="design-card" id="style-{item['id']}">
          <button class="artwork" data-view="{item['id']}" aria-label="放大 {item['id']} {escape(item['zh'])}"><img src="{item['preview']}" alt="{item['id']} {escape(item['language'])} 首页设计概念稿" width="512" height="768" loading="lazy"></button>
          <div class="card-copy"><div class="card-title"><span class="number">{item['id']}</span><h2>{escape(item['zh'])}<small>{escape(item['en'])}</small></h2></div><p>{escape(item['signature'])}</p>
          <div class="swatches" aria-label="候选色板">{''.join('<i style="background:' + color + '" title="' + color + '"></i>' for color in item['palette'])}</div>
          <div class="card-actions"><label><input type="checkbox" data-select="{item['id']}"> 加入对比</label><a href="{item['file']}" target="_blank" rel="noopener">PNG 原图 ↗</a></div></div>
        </article>''')
    page = '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>LMA · 首页风格选型 01—10</title><link rel="stylesheet" href="selection.css"><script src="directions.js" defer></script><script src="selection.js" defer></script></head><body>
<header class="masthead"><img src="reference/logo-21.png" alt="已定稿的 LMA Logo 21" width="64" height="64"><div><p class="eyebrow">LMA / VISUAL DIRECTIONS / 2026.11.03</p><h1>让本地 AI，有自己的界面。</h1><p>首页风格选型 · 10 种设计语言，同一套模型库内容。</p></div><a href="../../../docs/UI_HOME_SELECTION_20261103.md">设计说明 ↗</a></header>
<main><section class="intro"><div><h2>先比较风格，再统一落地。</h2><p>全部采用暗色方向，保留 Logo 21、推荐顺序和五项导航。点图查看大图，勾选最多 3 套并排比较，可复制编号和偏好。</p><p class="note">图片是 AI 生成概念稿，中文、尺寸和控件细节仍需定稿后校正。资源数值为示意；图片不代表已实现界面、手机运行效果或性能结果。</p></div><a class="outline" href="overview.jpg" target="_blank" rel="noopener">查看十套总览 ↗</a></section>
<section class="gallery" aria-label="十套首页设计稿">__CARDS__</section>
<section class="notes"><h2>如何给出你的选择</h2><p>例如：“采用 03 的卡片质感，配 01 的颜色，底部导航参考 09。”也可以只回复编号，保留一套完整设计语言。</p><p>原图包：<a href="LMA-home-ui-01-05.zip">01—05</a> · <a href="LMA-home-ui-06-10.zip">06—10</a> · <a href="manifest.json">尺寸与来源清单</a> · <a href="../../../docs/UI_HOME_SELECTION_20261103.en.md">English brief</a></p></section></main>
<aside class="selection-bar" aria-label="选择操作"><span id="selectionSummary" aria-live="polite">尚未选择</span><div><button id="clearSelection" class="quiet">清空</button><button id="copySelection" class="outline">复制选择</button><button id="compareSelection" class="primary">并排对比</button></div></aside>
<p id="notice" role="status"></p><dialog id="viewer" aria-labelledby="viewerTitle"><header class="viewer-header"><h2 id="viewerTitle">设计稿</h2><button id="closeViewer" aria-label="关闭大图">关闭 ×</button></header><div id="viewerBody"></div></dialog>
</body></html>'''
    (OUTPUT / "index.html").write_text(page.replace("__CARDS__", "\n".join(cards)), encoding="utf-8")
    # Copy selection assets from the source templates, so the offline result is self-contained.
    for name in ["selection.css", "selection.js"]:
        shutil.copyfile(ROOT / "tools/home_ui_selection" / name, OUTPUT / name)
    (OUTPUT / "README.txt").write_text("LMA 首页设计选型 / Home UI selection — 2026-11-03\n\nOpen index.html locally. Original PNGs are independent AI-generated concepts produced through sub2-image-gen / gpt-image-2.5, high, 1024x1536, with the approved Logo 21 and a historical v0.3.13 homepage as image references. Current v0.4.0 sources were inspected; the historical screenshot is not current physical evidence.\n\nThese are proposals, not deployed screens, model output or performance measurements. All original PNG bytes are preserved. JPEG previews and boards only resize/arrange those images. The ten directions retain dark mode, five navigation destinations, separate task/content tags and the m08/m06/m01 recommendation prefix.\n\nFull Chinese/English briefs: docs/UI_HOME_SELECTION_20261103.md and .en.md in the repository. The two ZIPs contain originals and prompts, not the entire offline selector.\n", encoding="utf-8")
    archives = []
    for start, label in [(0, "01-05"), (5, "06-10")]:
        archive = OUTPUT / ("LMA-home-ui-" + label + ".zip")
        names = ["README.txt", "manifest.json", "source-context.json"]
        for item in manifest["directions"][start:start + 5]:
            names += [item["file"], item["prompt"]]
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            for name in names:
                z.write(OUTPUT / name, name)
        assert archive.stat().st_size < 25 * 1024 * 1024
        archives.append(dict(file=archive.name, bytes=archive.stat().st_size, sha256=sha(archive)))
    validation = dict(schema="lma.home-ui-artifact-check/1", date="2026-11-03", originalImages=10, uniqueOriginalHashes=10,
                      dimensions=[1024, 1536], previewImages=10, comparisonBoards=3, archives=archives,
                      checkScope="Image decoding, uniqueness, dimensions and package identity only; selection JS syntax checked separately. No browser, Android, inference, usability or performance acceptance.",
                      imageReview="Inspect each raw image separately before publication; AI text/material fidelity is a visual-review concern.",
                      browserUsed=False, virtualizationUsed=False, appChanged=False, existingReleaseChanged=False)
    write_json(OUTPUT / "validation.json", validation)
    print(json.dumps(dict(originalImages=10, comparisonBoards=3, archives=archives), ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "build"])
    args = parser.parse_args()
    prepare() if args.action == "prepare" else build()


if __name__ == "__main__":
    main()

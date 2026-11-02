"""Compose the selected LMA logo and exact bilingual slogan into a README banner.

Uses existing artwork and local fonts. No model, network or browser is invoked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "output/imagegen/lma-logo-selection-20261102-batch3-whale17/21-cobalt-vinyl.png"
SOURCE_SHA256 = "f224b6e0fb1030fa894557bf6961d5d3e5d3b00430c5a0077bf9b85f3831282f"
OUT = ROOT / "docs/media/branding"
SLOGAN_ZH = "把无审查 AI，装进口袋。"
SLOGAN_EN = "Uncensored AI, right in your pocket."
PALETTE = {
    "navy": "#0E1726",
    "cream": "#F3F3E6",
    "cobalt": "#327AF4",
    "lime": "#A8E83B",
    "muted": "#B2BFD0",
    "line": "#26456F",
}


def font(path: Path, size: int, weight: int = 500):
    face = ImageFont.truetype(str(path), size)
    try:
        axes = face.get_variation_axes()
        values = [min(a["maximum"], max(a["minimum"], weight))
                  if a["name"] == b"Weight" else a["default"] for a in axes]
        face.set_variation_by_axes(values)
    except (AttributeError, OSError):
        pass
    return face


def character_for_composition(source: Image.Image) -> Image.Image:
    """Mask only dark background connected to the border; retain enclosed eyes.

    This derived mask is for this banner, not a production transparent master.
    The selected original is never overwritten.
    """
    r, g, b = source.convert("RGB").split()
    candidate = ImageChops.multiply(
        ImageChops.multiply(r.point(lambda x: 255 if x < 48 else 0),
                            g.point(lambda x: 255 if x < 60 else 0)),
        b.point(lambda x: 255 if x < 78 else 0),
    )
    ImageDraw.floodfill(candidate, (0, 0), 128)
    alpha = candidate.point(lambda x: 0 if x == 128 else 255)
    bounds = alpha.getbbox()
    if bounds is None:
        raise ValueError("The selected character mask is empty")
    result = source.convert("RGBA")
    result.putalpha(alpha.filter(ImageFilter.GaussianBlur(0.45)))
    return result.crop(bounds)


def render(font_zh: Path, font_display: Path):
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("The selected 21 artwork does not match its recorded identity")
    for path in (font_zh, font_display):
        if not path.is_file():
            raise FileNotFoundError(f"Font not found: {path}; supply --font-zh / --font-display")
    canvas = Image.new("RGBA", (1600, 720), PALETTE["navy"])
    glow = Image.new("RGBA", canvas.size)
    gd = ImageDraw.Draw(glow)
    gd.ellipse((922, 34, 1562, 706), fill=(30, 75, 145, 88))
    canvas = Image.alpha_composite(canvas, glow.filter(ImageFilter.GaussianBlur(90)))
    draw = ImageDraw.Draw(canvas)

    title = font(font_display, 164, 700)
    eyebrow = font(font_zh, 30)
    headline = font(font_zh, 64, 700)
    english = font(font_display, 46, 520)
    utility = font(font_zh, 25)
    draw.text((100, 72), "本地 AI / LOCAL AI", font=eyebrow, fill=PALETTE["muted"], anchor="lt")
    draw.text((90, 142), "LMA", font=title, fill=PALETTE["cream"], anchor="lt")

    max_width = 790
    while draw.textlength(SLOGAN_ZH, font=headline) > max_width:
        headline = font(font_zh, headline.size - 1, 700)
    cursor = 98.0
    for text, color in [("把无审查 ", "cream"), ("AI", "lime"), ("，装进口袋。", "cream")]:
        draw.text((cursor, 350), text, font=headline, fill=PALETTE[color], anchor="lt")
        cursor += draw.textlength(text, font=headline)
    english_lines = ["Uncensored AI,", "right in your pocket."]
    assert " ".join(english_lines) == SLOGAN_EN
    for y, line in zip((468, 525), english_lines):
        if draw.textlength(line, font=english) > max_width:
            raise ValueError("English slogan exceeds its text column")
        draw.text((100, y), line, font=english, fill=PALETTE["muted"], anchor="lt")
    draw.line((100, 629, 770, 629), fill=PALETTE["line"], width=2)
    draw.text((100, 659), "ANDROID · 自主选模 · 本地运行", font=utility,
              fill=PALETTE["muted"], anchor="lt")

    with Image.open(SOURCE) as original:
        mascot = character_for_composition(original)
    mascot.thumbnail((600, 600), Image.Resampling.LANCZOS)
    position = (935 + (600 - mascot.width)//2, 58 + (600 - mascot.height)//2)
    canvas.alpha_composite(mascot, position)
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "lma-banner.png"
    canvas.convert("RGB").save(target, optimize=True)
    metadata = {
        "schema": "lma.brand-banner/1",
        "decisionDate": "2026-11-02",
        "logo": {"selectedId": "21", "title": "Cobalt Vinyl / 钴蓝软胶",
                 "source": SOURCE.relative_to(ROOT).as_posix(), "sha256": SOURCE_SHA256,
                 "nativeArtworkPreserved": True},
        "slogan": {"selectedId": "04", "selectedBy": "user", "zh": SLOGAN_ZH, "en": SLOGAN_EN,
                   "collection": "Local AI and uncensored models"},
        "banner": {"file": target.name, "dimensions": [1600, 720],
                   "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                   "bytes": target.stat().st_size, "palette": PALETTE,
                   "displayFont": font_display.name, "chineseFont": font_zh.name},
        "composition": {"method": "Existing approved artwork and local typography, composed with Pillow",
                        "derivedAlphaForBannerOnly": True, "newAiImageGeneration": False,
                        "productionTransparentLogoMaster": False},
        "appOrPublishedReleaseChanged": False,
    }
    (OUT / "banner.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps({"banner": str(target), "dimensions": [1600, 720],
                      "bytes": target.stat().st_size, "logo": "21", "slogan": "04"}, ensure_ascii=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font-zh", type=Path, default=Path("C:/Windows/Fonts/msyhbd.ttc"))
    parser.add_argument("--font-display", type=Path, default=Path("C:/Windows/Fonts/bahnschrift.ttf"))
    args = parser.parse_args()
    render(args.font_zh, args.font_display)

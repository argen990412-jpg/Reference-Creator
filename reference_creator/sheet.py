"""Compose individual views into a single labelled turnaround sheet."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont


def _font(size: int):
    for name in ("DejaVuSans.ttf", "Arial.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def compose_sheet(
    panels: list[tuple[str, Image.Image]],
    title: str | None = None,
    guides: bool = True,
    panel_height: int = 900,
    background: str = "white",
) -> Image.Image:
    """Lay panels side by side at equal height with labels and optional height guides."""
    if not panels:
        raise ValueError("no panels")
    scaled = []
    for label, img in panels:
        s = panel_height / img.height
        scaled.append((label, img.convert("RGBA").resize((round(img.width * s), panel_height), Image.LANCZOS)))

    pad, label_h = 24, 48
    title_h = 64 if title else 0
    width = sum(i.width for _, i in scaled) + pad * (len(scaled) + 1)
    height = title_h + panel_height + label_h + pad * 2
    sheet = Image.new("RGBA", (width, height), background)
    draw = ImageDraw.Draw(sheet)
    font, tfont = _font(26), _font(36)

    if title:
        draw.text((pad, pad // 2), title, fill=(30, 30, 30), font=tfont)

    top = title_h + pad
    x = pad
    for label, img in scaled:
        sheet.alpha_composite(img, (x, top))
        tw = draw.textlength(label, font=font)
        draw.text((x + (img.width - tw) / 2, top + panel_height + 10), label, fill=(60, 60, 60), font=font)
        x += img.width + pad

    if guides:
        # head-top and ground lines matching postprocess.normalize defaults (subject_height=0.88)
        for frac in (0.06, 0.94):
            y = top + int(panel_height * frac)
            for gx in range(0, width, 16):
                draw.line([(gx, y), (gx + 8, y)], fill=(170, 190, 220), width=2)
    return sheet

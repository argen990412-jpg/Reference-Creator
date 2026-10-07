"""Make generated views line up as modeling blueprints.

Each view is cropped to the character, scaled so every view has the same
character height, and placed on an identical canvas with the feet on a shared
baseline. This is what lets the images be dropped into Blender/Maya as
front/side image planes without manual alignment.
"""

from __future__ import annotations

from PIL import Image, ImageChops, ImageFilter


def _background_color(img: Image.Image) -> tuple[int, int, int]:
    rgb = img.convert("RGB")
    w, h = rgb.size
    pts = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (0, h // 2), (w - 1, h // 2)]
    px = sorted((rgb.getpixel(p) for p in pts), key=sum)
    return px[len(px) // 2]  # median-ish, robust to one corner touching the subject


def subject_bbox(img: Image.Image, tolerance: int = 28) -> tuple[int, int, int, int] | None:
    """Bounding box of the non-background subject, or None if nothing found."""
    rgba = img.convert("RGBA")
    alpha = rgba.getchannel("A")
    if alpha.getextrema()[0] < 250:  # real transparency present
        mask = alpha.point(lambda a: 255 if a > 16 else 0)
    else:
        bg = Image.new("RGB", rgba.size, _background_color(rgba))
        # per-channel max, not luminance: skin on a light background differs mostly in hue
        r, g, b = ImageChops.difference(rgba.convert("RGB"), bg).split()
        diff = ImageChops.lighter(ImageChops.lighter(r, g), b)
        mask = diff.point(lambda d: 255 if d > tolerance else 0)
    mask = mask.filter(ImageFilter.MedianFilter(5))  # drop speckle / jpeg noise
    return mask.getbbox()


def normalize(
    img: Image.Image,
    canvas_size: tuple[int, int] = (1024, 1365),
    subject_height: float = 0.88,
    background: str | tuple[int, int, int, int] | None = None,
) -> Image.Image:
    """Crop to subject, scale to a fixed height and place feet on a common baseline."""
    w, h = canvas_size
    box = subject_bbox(img)
    opaque = alpha_is_opaque(img.convert("RGBA"))
    if background is None:  # keep the generated background so the crop edges stay invisible
        background = _background_color(img) if opaque else "white"
    canvas = Image.new("RGBA", canvas_size, background)
    if box is None:
        canvas.alpha_composite(img.convert("RGBA").resize(canvas_size))
        return canvas
    subject = img.convert("RGBA").crop(box)
    target_h = int(h * subject_height)
    scale = target_h / subject.height
    if subject.width * scale > w * 0.96:  # wide poses (T-pose) must still fit
        scale = (w * 0.96) / subject.width
    subject = subject.resize((max(1, round(subject.width * scale)), max(1, round(subject.height * scale))),
                             Image.LANCZOS)
    baseline = h - int(h * (1 - subject_height) / 2)
    x = (w - subject.width) // 2
    y = baseline - subject.height
    if opaque:
        canvas.paste(subject, (x, y))
    else:
        canvas.alpha_composite(subject, (x, y))
    return canvas


def alpha_is_opaque(img: Image.Image) -> bool:
    return img.getchannel("A").getextrema()[0] >= 250

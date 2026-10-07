from __future__ import annotations

import re

from PIL import Image, ImageOps

from .base import ImageProvider


class MockProvider(ImageProvider):
    """Offline provider for trying the pipeline without an API key.

    It does NOT generate new angles; it returns a placeholder derived from the
    reference so layout, normalization and sheet output can be checked.
    """

    name = "mock"

    def __init__(self):
        self.calls: list[tuple[str, int]] = []

    def generate(self, prompt, references, aspect_ratio="3:4"):
        self.calls.append((prompt, len(references)))
        src = references[-1].convert("RGBA")
        m = re.search(r"CAMERA: (.+?)\.", prompt)
        label = m.group(1)[:40] if m else "view"
        if "LEFT" in label or "BACK" in label:
            src = ImageOps.mirror(src)
        w, h = (768, 1024) if aspect_ratio in ("3:4", "2:3", "9:16") else (1024, 1024)
        # reuse the reference's own background so the subject stays detectable
        canvas = Image.new("RGBA", (w, h), src.getpixel((0, 0)))
        fit = ImageOps.contain(src, (int(w * 0.8), int(h * 0.85)))
        canvas.alpha_composite(fit, ((w - fit.width) // 2, (h - fit.height) // 2))
        canvas.info["mock_label"] = label
        return canvas

    def describe(self, image, prompt):
        return "ART STYLE: (mock) unknown\nIDENTITY: (mock)\n"

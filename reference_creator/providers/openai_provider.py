from __future__ import annotations

import base64
import io
import os

from PIL import Image

from .base import ImageProvider, ProviderError

DEFAULT_MODEL = "gpt-image-1.5"
DEFAULT_TEXT_MODEL = "gpt-5.4-mini"

# GPT image models only output a few fixed sizes.
_SIZES = {"1:1": "1024x1024", "3:4": "1024x1536", "2:3": "1024x1536", "9:16": "1024x1536",
          "4:3": "1536x1024", "3:2": "1536x1024", "16:9": "1536x1024"}


def _png_file(img: Image.Image, name: str):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return (name, buf, "image/png")


class OpenAIProvider(ImageProvider):
    """OpenAI GPT Image edits endpoint with high input fidelity."""

    name = "openai"

    def __init__(self, model: str | None = None, text_model: str | None = None,
                 quality: str = "high", api_key: str | None = None):
        try:
            import openai
        except ImportError as e:  # pragma: no cover
            raise ProviderError("pip install 'reference-creator[openai]' to use OpenAI") from e
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ProviderError("Set OPENAI_API_KEY to use the OpenAI provider")
        self.client = openai.OpenAI(api_key=key)
        self.model = model or os.environ.get("REFCREATOR_OPENAI_MODEL", DEFAULT_MODEL)
        self.text_model = text_model or os.environ.get("REFCREATOR_OPENAI_TEXT_MODEL", DEFAULT_TEXT_MODEL)
        self.quality = quality

    def generate(self, prompt, references, aspect_ratio="3:4"):
        kwargs = dict(
            model=self.model,
            image=[_png_file(r, f"ref{i}.png") for i, r in enumerate(references)],
            prompt=prompt,
            size=_SIZES.get(aspect_ratio, "1024x1536"),
            quality=self.quality,
        )
        # input_fidelity is only supported on gpt-image-1 / 1.5 (must be omitted for gpt-image-2).
        if self.model.startswith(("gpt-image-1", "chatgpt-image")) and self.model != "gpt-image-1-mini":
            kwargs["input_fidelity"] = "high"
        resp = self.client.images.edit(**kwargs)
        if not resp.data or not resp.data[0].b64_json:
            raise ProviderError("OpenAI returned no image")
        return Image.open(io.BytesIO(base64.b64decode(resp.data[0].b64_json))).convert("RGBA")

    def describe(self, image, prompt):
        buf = io.BytesIO()
        image.convert("RGB").save(buf, format="JPEG", quality=90)
        url = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        resp = self.client.responses.create(
            model=self.text_model,
            input=[{"role": "user", "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": url},
            ]}],
        )
        return resp.output_text

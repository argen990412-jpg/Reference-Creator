from __future__ import annotations

import io
import os

from PIL import Image

from .base import ImageProvider, ProviderError

DEFAULT_MODEL = "gemini-3.1-flash-image"
DEFAULT_TEXT_MODEL = "gemini-flash-latest"


class GeminiProvider(ImageProvider):
    """Google Gemini native image generation ("Nano Banana" family).

    Strong at keeping a character and art style consistent across edits, and accepts
    several reference images per request.
    """

    name = "gemini"

    def __init__(self, model: str | None = None, text_model: str | None = None,
                 image_size: str | None = "2K", api_key: str | None = None):
        try:
            from google import genai
            from google.genai import types
        except ImportError as e:  # pragma: no cover
            raise ProviderError("pip install 'reference-creator[gemini]' (google-genai) to use Gemini") from e
        key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise ProviderError("Set GEMINI_API_KEY to use the Gemini provider")
        self._types = types
        self.client = genai.Client(api_key=key)
        self.model = model or os.environ.get("REFCREATOR_GEMINI_MODEL", DEFAULT_MODEL)
        self.text_model = text_model or os.environ.get("REFCREATOR_GEMINI_TEXT_MODEL", DEFAULT_TEXT_MODEL)
        # gemini-2.5-flash-image has no image_size option; newer image models do.
        self.image_size = None if "2.5" in self.model else image_size

    def generate(self, prompt, references, aspect_ratio="3:4"):
        types = self._types
        image_config = types.ImageConfig(aspect_ratio=aspect_ratio)
        if self.image_size:
            image_config.image_size = self.image_size
        resp = self.client.models.generate_content(
            model=self.model,
            contents=[*references, prompt],
            config=types.GenerateContentConfig(response_modalities=["IMAGE"], image_config=image_config),
        )
        for cand in resp.candidates or []:
            for part in (cand.content.parts if cand.content else None) or []:
                if part.inline_data and part.inline_data.data:
                    return Image.open(io.BytesIO(part.inline_data.data)).convert("RGBA")
        reason = resp.candidates[0].finish_reason if resp.candidates else getattr(resp, "prompt_feedback", None)
        raise ProviderError(f"Gemini returned no image (reason: {reason})")

    def describe(self, image, prompt):
        resp = self.client.models.generate_content(model=self.text_model, contents=[image, prompt])
        return resp.text

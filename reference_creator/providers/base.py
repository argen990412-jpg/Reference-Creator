from __future__ import annotations

import abc

from PIL import Image


class ProviderError(RuntimeError):
    pass


class ImageProvider(abc.ABC):
    """Generates one image from a prompt plus reference images."""

    name: str = "base"

    @abc.abstractmethod
    def generate(self, prompt: str, references: list[Image.Image], aspect_ratio: str = "3:4") -> Image.Image:
        ...

    def describe(self, image: Image.Image, prompt: str) -> str | None:
        """Optional vision step that returns a text description. None if unsupported."""
        return None

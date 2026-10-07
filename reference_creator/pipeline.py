"""End-to-end: reference image -> style-consistent multi-angle views -> model sheet."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from PIL import Image, ImageOps

from .postprocess import normalize
from .prompts import STYLE_ANALYSIS_PROMPT, build_view_prompt
from .providers import ImageProvider, ProviderError
from .sheet import compose_sheet
from .views import View

MAX_REFERENCE_SIDE = 1536


@dataclass
class Options:
    pose: str = "a-pose"
    framing: str = "full"
    background: str = "plain flat white"
    aspect_ratio: str = "3:4"
    analyze_style: bool = True      # build a written character sheet first
    anchor_front: bool = True       # generate front first, use it as 2nd reference for other views
    normalize: bool = True          # align scale/baseline for modeling image planes
    sheet: bool = True
    retries: int = 2
    workers: int = 3
    extra_prompt: str | None = None


@dataclass
class ViewResult:
    key: str
    label: str
    path: str | None = None
    raw_path: str | None = None
    prompt: str = ""
    error: str | None = None
    seconds: float = 0.0


@dataclass
class RunResult:
    output_dir: str
    character_sheet: str | None = None
    views: list[ViewResult] = field(default_factory=list)
    sheet_path: str | None = None

    @property
    def ok(self) -> bool:
        return all(v.error is None for v in self.views)


def load_reference(path_or_image: str | Path | Image.Image) -> Image.Image:
    img = path_or_image if isinstance(path_or_image, Image.Image) else Image.open(path_or_image)
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        flat = Image.new("RGBA", img.size, "white")
        flat.alpha_composite(img)
        img = flat
    img = img.convert("RGB")
    img.thumbnail((MAX_REFERENCE_SIDE, MAX_REFERENCE_SIDE), Image.LANCZOS)
    return img


class ReferenceCreator:
    def __init__(self, provider: ImageProvider, options: Options | None = None,
                 log: Callable[[str], None] = print):
        self.provider = provider
        self.opt = options or Options()
        self.log = log

    def _generate(self, view: View, refs: list[Image.Image], sheet_text: str | None) -> tuple[Image.Image, str]:
        prompt = build_view_prompt(
            view, pose=self.opt.pose, framing=self.opt.framing, background=self.opt.background,
            character_sheet=sheet_text, has_anchor=len(refs) > 1, extra=self.opt.extra_prompt,
        )
        last: Exception | None = None
        for attempt in range(self.opt.retries + 1):
            try:
                return self.provider.generate(prompt, refs, self.opt.aspect_ratio), prompt
            except Exception as e:  # network / safety / empty response
                last = e
                if attempt < self.opt.retries:
                    wait = 2 ** (attempt + 1)
                    self.log(f"  ! {view.key}: {e} - retrying in {wait}s")
                    time.sleep(wait)
        raise ProviderError(str(last))

    def run(self, reference: str | Path | Image.Image, views: list[View], output_dir: str | Path) -> RunResult:
        out = Path(output_dir)
        (out / "raw").mkdir(parents=True, exist_ok=True)
        ref = load_reference(reference)
        ref.save(out / "reference.png")
        result = RunResult(output_dir=str(out))

        if self.opt.analyze_style:
            self.log("Analyzing character & art style...")
            try:
                result.character_sheet = self.provider.describe(ref, STYLE_ANALYSIS_PROMPT)
            except Exception as e:
                self.log(f"  ! style analysis failed ({e}); continuing with image reference only")
            if result.character_sheet:
                (out / "character_sheet.txt").write_text(result.character_sheet, encoding="utf-8")

        images: dict[str, Image.Image] = {}
        by_key: dict[str, ViewResult] = {}

        def do(view: View, refs: list[Image.Image]) -> None:
            vr = ViewResult(view.key, view.label)
            by_key[view.key] = vr
            t0 = time.time()
            try:
                img, vr.prompt = self._generate(view, refs, result.character_sheet)
                raw = out / "raw" / f"{view.key}.png"
                img.save(raw)
                vr.raw_path = str(raw)
                final = normalize(img) if self.opt.normalize else img
                path = out / f"{_index(views, view):02d}_{view.key}.png"
                final.save(path)
                vr.path = str(path)
                images[view.key] = final
                self.log(f"  ✓ {view.label}")
            except Exception as e:
                vr.error = str(e)
                self.log(f"  ✗ {view.label}: {e}")
            vr.seconds = round(time.time() - t0, 1)

        remaining = list(views)
        refs = [ref]
        front = next((v for v in views if v.key == "front"), None)
        if self.opt.anchor_front and front is not None and len(views) > 1:
            self.log("Generating anchor front view...")
            do(front, [ref])
            remaining.remove(front)
            raw_front = by_key["front"].raw_path
            if raw_front:
                refs = [ref, Image.open(raw_front).convert("RGB")]

        self.log(f"Generating {len(remaining)} view(s)...")
        with ThreadPoolExecutor(max_workers=max(1, self.opt.workers)) as pool:
            for f in as_completed([pool.submit(do, v, refs) for v in remaining]):
                f.result()

        result.views = [by_key[v.key] for v in views]

        if self.opt.sheet and images:
            panels = [(v.label, images[v.key]) for v in views if v.key in images]
            sheet = compose_sheet(panels, guides=self.opt.normalize)
            sheet_path = out / "turnaround_sheet.png"
            sheet.convert("RGB").save(sheet_path)
            result.sheet_path = str(sheet_path)
            self.log(f"Sheet: {sheet_path}")

        manifest = {
            "provider": self.provider.name,
            "model": getattr(self.provider, "model", None),
            "options": asdict(self.opt),
            **asdict(result),
        }
        (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return result


def _index(views: list[View], view: View) -> int:
    return views.index(view) + 1

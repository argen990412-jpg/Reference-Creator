from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .pipeline import Options, ReferenceCreator
from .prompts import FRAMINGS, POSES
from .providers import PROVIDERS, ProviderError, get_provider
from .views import PRESETS, VIEWS, resolve_views


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if v.strip():
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="reference-creator",
        description="Generate style-consistent multi-angle character views for 3D modeling.",
    )
    p.add_argument("image", help="character reference image (png/jpg/webp)")
    p.add_argument("-o", "--output", help="output directory (default: output/<image name>)")
    p.add_argument("-v", "--views", default="turnaround",
                   help=f"preset ({', '.join(PRESETS)}) or comma list of views ({', '.join(VIEWS)})")
    p.add_argument("-p", "--provider", default="gemini", choices=PROVIDERS)
    p.add_argument("-m", "--model", help="override the image model id")
    p.add_argument("--pose", default="a-pose", help=f"{', '.join(POSES)} or free text")
    p.add_argument("--framing", default="full", help=f"{', '.join(FRAMINGS)} or free text")
    p.add_argument("--background", default="plain flat white")
    p.add_argument("--aspect", default="3:4", help="aspect ratio, e.g. 3:4, 2:3, 1:1")
    p.add_argument("--prompt", dest="extra_prompt", help="extra notes appended to every view prompt")
    p.add_argument("--no-analyze", action="store_true", help="skip the written character/style sheet step")
    p.add_argument("--no-anchor", action="store_true", help="don't use the generated front view as extra reference")
    p.add_argument("--no-normalize", action="store_true", help="keep raw framing (no scale/baseline alignment)")
    p.add_argument("--no-sheet", action="store_true", help="don't compose turnaround_sheet.png")
    p.add_argument("--workers", type=int, default=3, help="parallel requests")
    p.add_argument("--retries", type=int, default=2)
    return p


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()
    args = build_parser().parse_args(argv)
    src = Path(args.image)
    if not src.is_file():
        print(f"error: {src} not found", file=sys.stderr)
        return 2
    try:
        views = resolve_views(args.views)
        kwargs = {"model": args.model} if args.model and args.provider != "mock" else {}
        provider = get_provider(args.provider, **kwargs)
    except (ValueError, ProviderError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    opts = Options(
        pose=args.pose, framing=args.framing, background=args.background, aspect_ratio=args.aspect,
        analyze_style=not args.no_analyze, anchor_front=not args.no_anchor,
        normalize=not args.no_normalize, sheet=not args.no_sheet,
        retries=args.retries, workers=args.workers, extra_prompt=args.extra_prompt,
    )
    out = Path(args.output) if args.output else Path("output") / src.stem
    print(f"{provider.name}: {len(views)} views -> {out}")
    result = ReferenceCreator(provider, opts).run(src, views, out)
    failed = [v.key for v in result.views if v.error]
    if failed:
        print(f"Failed views: {', '.join(failed)} (see manifest.json)", file=sys.stderr)
        return 1
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

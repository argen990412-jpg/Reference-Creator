import json

import pytest
from PIL import Image, ImageDraw

from reference_creator import Options, ReferenceCreator, resolve_views
from reference_creator.postprocess import normalize, subject_bbox
from reference_creator.prompts import build_view_prompt
from reference_creator.providers import get_provider
from reference_creator.views import VIEWS


def make_character(size=(400, 600), box=(150, 100, 250, 500), bg="white"):
    img = Image.new("RGB", size, bg)
    ImageDraw.Draw(img).rectangle(box, fill=(200, 60, 60))
    return img


def test_resolve_views_presets_and_dedup():
    keys = [v.key for v in resolve_views("ortho,front,back_left")]
    assert keys == ["front", "left", "back", "right", "back_left"]
    with pytest.raises(ValueError):
        resolve_views("sideways")


def test_prompt_contains_style_lock_and_sheet():
    p = build_view_prompt(VIEWS["left"], character_sheet="HAIR: red", has_anchor=True)
    assert "STYLE LOCK" in p and "HAIR: red" in p and "IMAGE 2" in p and "LEFT PROFILE" in p
    p2 = build_view_prompt(VIEWS["right"], pose="t-pose")
    assert "T-POSE" in p2 and "NOT a mirrored left" in p2


def test_subject_bbox_and_normalize_alignment():
    small = make_character(box=(150, 300, 200, 500))
    big = make_character(box=(100, 50, 300, 550))
    assert subject_bbox(small) == (150, 300, 201, 501)
    a, b = normalize(small), normalize(big)
    assert a.size == b.size
    ba, bb = subject_bbox(a), subject_bbox(b)
    # same character height and same ground line after normalization
    assert abs((ba[3] - ba[1]) - (bb[3] - bb[1])) <= 3
    assert abs(ba[3] - bb[3]) <= 3


def test_bbox_keeps_light_skin_on_light_background():
    img = Image.new("RGB", (300, 300), (240, 240, 240))
    ImageDraw.Draw(img).ellipse((100, 20, 200, 120), fill=(250, 210, 180))  # head
    ImageDraw.Draw(img).rectangle((100, 120, 200, 280), fill=(60, 90, 200))
    assert subject_bbox(img)[1] <= 22


def test_pipeline_with_mock(tmp_path):
    provider = get_provider("mock")
    views = resolve_views("ortho")
    result = ReferenceCreator(provider, Options(retries=0), log=lambda *_: None).run(
        make_character(), views, tmp_path)
    assert result.ok
    assert [v.key for v in result.views] == ["front", "left", "back", "right"]
    # front generated first with only the original; others also get the front anchor
    assert provider.calls[0][1] == 1
    assert all(n == 2 for _, n in provider.calls[1:])
    assert (tmp_path / "turnaround_sheet.png").is_file()
    assert (tmp_path / "character_sheet.txt").is_file()
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["provider"] == "mock" and len(manifest["views"]) == 4


def test_pipeline_reports_failures(tmp_path):
    class Broken:
        name = "broken"
        def generate(self, *a, **k):
            raise RuntimeError("boom")
        def describe(self, *a, **k):
            return None

    result = ReferenceCreator(Broken(), Options(retries=0, analyze_style=False), log=lambda *_: None).run(
        make_character(), resolve_views("minimal"), tmp_path)
    assert not result.ok and all(v.error for v in result.views)
    assert result.sheet_path is None

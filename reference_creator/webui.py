"""Minimal Gradio UI:  python -m reference_creator.webui"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

from .cli import _load_dotenv
from .pipeline import Options, ReferenceCreator
from .prompts import POSES
from .providers import PROVIDERS, get_provider
from .views import PRESETS, VIEWS, resolve_views


def run(image, provider_name, preset, custom_views, pose, analyze, anchor, normalize, extra):
    if image is None:
        raise ValueError("이미지를 업로드하세요")
    spec = custom_views.strip() or preset
    views = resolve_views(spec)
    out = Path(tempfile.gettempdir()) / "reference_creator" / time.strftime("%Y%m%d-%H%M%S")
    logs: list[str] = []
    creator = ReferenceCreator(
        get_provider(provider_name),
        Options(pose=pose, analyze_style=analyze, anchor_front=anchor, normalize=normalize,
                extra_prompt=extra or None),
        log=logs.append,
    )
    result = creator.run(image, views, out)
    gallery = [(v.path, v.label) for v in result.views if v.path]
    return result.sheet_path, gallery, result.character_sheet or "", "\n".join(logs) + f"\n\n저장 위치: {out}"


def build():
    import gradio as gr

    with gr.Blocks(title="Reference Creator") as demo:
        gr.Markdown("# Reference Creator\n캐릭터 이미지 한 장으로 그림체가 일관된 다각도 모델링 레퍼런스를 만듭니다.")
        with gr.Row():
            with gr.Column(scale=1):
                image = gr.Image(type="pil", label="캐릭터 이미지")
                provider = gr.Dropdown(list(PROVIDERS), value="gemini", label="프로바이더")
                preset = gr.Dropdown(list(PRESETS), value="turnaround", label="뷰 프리셋")
                custom = gr.Textbox(label="직접 지정 (선택)", placeholder=", ".join(VIEWS))
                pose = gr.Dropdown(list(POSES), value="a-pose", label="포즈", allow_custom_value=True)
                analyze = gr.Checkbox(True, label="스타일 분석 (캐릭터 시트 작성)")
                anchor = gr.Checkbox(True, label="정면 앵커 사용")
                normalize = gr.Checkbox(True, label="크기/바닥선 정렬")
                extra = gr.Textbox(label="추가 지시 (선택)")
                btn = gr.Button("생성", variant="primary")
            with gr.Column(scale=2):
                sheet = gr.Image(label="턴어라운드 시트")
                gallery = gr.Gallery(label="개별 뷰", columns=4)
                char_sheet = gr.Textbox(label="캐릭터/스타일 시트", lines=8)
                log = gr.Textbox(label="로그", lines=6)
        btn.click(run, [image, provider, preset, custom, pose, analyze, anchor, normalize, extra],
                  [sheet, gallery, char_sheet, log])
    return demo


if __name__ == "__main__":
    _load_dotenv()
    build().launch()

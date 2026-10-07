"""Prompt construction.

Consistency comes from three layers, all expressed here:
1. A *style lock* block that tells the model to copy the source rendering exactly.
2. A *character sheet* (optional, produced by a vision model) describing identity,
   outfit and style in words, so every view is conditioned on the same facts.
3. A *staging* block (pose, framing, background) identical for every view, so the
   images line up when used as modeling blueprints.
"""

from __future__ import annotations

from .views import MIRROR_OF, View

POSES = {
    "a-pose": "a neutral A-POSE: standing straight, arms relaxed and angled about 30-45 degrees away "
              "from the body, palms facing the thighs, feet shoulder-width apart, looking straight ahead",
    "t-pose": "a neutral T-POSE: standing straight, arms extended horizontally to the sides at shoulder "
              "height, palms down, feet shoulder-width apart, looking straight ahead",
    "relaxed": "a neutral relaxed standing pose: arms hanging naturally at the sides, feet slightly apart, "
               "looking straight ahead",
    "keep": "the SAME pose as in the reference image, only rotated to the requested camera angle",
}

FRAMINGS = {
    "full": "FULL BODY from the top of the head (including hair/hat) to the soles of the feet, "
            "nothing cropped, with a small margin above the head and below the feet",
    "bust": "BUST shot from the top of the head to mid-chest",
    "head": "HEAD ONLY from the top of the hair to the base of the neck",
}

STYLE_ANALYSIS_PROMPT = """You are preparing a model sheet for a 3D modeler.
Look at the attached character image and write a precise, factual description that another
artist could use to redraw this exact character from any angle in exactly the same style.
Use these headings and short bullet points, no preamble:

ART STYLE: medium (e.g. 2D cel-shaded anime, painterly, 3D render, photo), line work (weight,
color, presence or absence of outlines), shading method (flat/cel/soft/realistic), number of
shading tones, color palette and saturation, texture/brush feel, level of detail, proportions
(head-to-body ratio, stylization).
IDENTITY: apparent age range, body type, height impression, skin tone, face shape, eyes (shape,
color), eyebrows, nose, mouth, distinctive marks.
HAIR: color(s), length, style, parting, how it looks from the side and back if inferable.
OUTFIT: every garment and accessory from head to toe with colors, materials, patterns,
asymmetries (state which side, from the CHARACTER'S perspective).
UNSEEN AREAS: your best consistent guess for what the back and hidden sides look like.
"""


def build_view_prompt(
    view: View,
    *,
    pose: str = "a-pose",
    framing: str = "full",
    background: str = "plain flat white",
    character_sheet: str | None = None,
    has_anchor: bool = False,
    extra: str | None = None,
) -> str:
    pose_text = POSES.get(pose, pose)
    framing_text = FRAMINGS.get(framing, framing)

    refs = (
        "IMAGE 1 is the original character reference. IMAGE 2 is an already-approved FRONT view of the "
        "same character in the target pose; match its proportions, scale and rendering exactly."
        if has_anchor
        else "The attached image is the character reference."
    )

    parts = [
        f"Create a character model-sheet image of the EXACT same character for 3D modeling. {refs}",
        "",
        "STYLE LOCK (most important):",
        "- Reproduce the reference's art style exactly: same medium, same line weight and line color, "
        "same shading technique and number of tones, same color palette and saturation, same level of "
        "detail and the same body proportions / head-to-body ratio.",
        "- It must look like it was drawn or rendered by the same artist in the same session as the reference. "
        "Do NOT make it more realistic, more detailed, more stylized, or switch to 3D/photo if it is 2D (or vice versa).",
        "- Keep identity, face, hairstyle, hair color, eye color, skin tone, outfit, colors, patterns and "
        "accessories identical. Do not add, remove or redesign anything.",
        "",
        f"CAMERA: {view.description}",
        "Use an orthographic-looking camera at the character's chest height with no perspective "
        "distortion, no tilt, no dramatic angle.",
        "",
        f"POSE: {pose_text}.",
        f"FRAMING: {framing_text}, character centered horizontally.",
        f"BACKGROUND: {background} background, even neutral lighting, no cast shadow on the ground, "
        "no props, no text, no labels, no borders, a single character only.",
    ]
    if view.key in MIRROR_OF:
        parts.append(
            f"Note: the reference may only show the other side; keep any asymmetric details on the "
            f"correct side of the character's body (this is NOT a mirrored {MIRROR_OF[view.key]} view)."
        )
    if character_sheet:
        parts += ["", "CHARACTER SHEET (ground truth, follow it):", character_sheet.strip()]
    if extra:
        parts += ["", f"ADDITIONAL NOTES: {extra.strip()}"]
    return "\n".join(parts)

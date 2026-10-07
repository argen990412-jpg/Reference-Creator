"""Camera view definitions and presets for character turnarounds.

Left/right always refer to the *character's* own left/right, which is the
convention used on modeling sheets. When the character's left side faces the
camera, their nose points toward the left edge of the image.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class View:
    key: str
    label: str
    yaw: int  # degrees the character is rotated away from the camera (0 = front, 180 = back)
    description: str


VIEWS: dict[str, View] = {
    v.key: v
    for v in [
        View(
            "front", "Front", 0,
            "straight-on FRONT view. The character faces the camera directly; "
            "the face, chest and toes point at the viewer; body perfectly symmetric to the frame.",
        ),
        View(
            "front_left", "Front 3/4 (L)", 45,
            "THREE-QUARTER FRONT view of the character's LEFT side. The character is turned 45 degrees "
            "so their face points toward the left edge of the image; the left side of the face and body "
            "is closer to the camera.",
        ),
        View(
            "left", "Left Side", 90,
            "exact LEFT PROFILE view (90 degrees). Only the character's left side is visible; "
            "the nose and toes point toward the left edge of the image; one eye visible.",
        ),
        View(
            "back_left", "Back 3/4 (L)", 135,
            "THREE-QUARTER BACK view from the character's LEFT-rear. We mostly see the back and the left "
            "side; the face is turned away, only the edge of the cheek/ear is visible.",
        ),
        View(
            "back", "Back", 180,
            "straight-on BACK view. The character faces directly away from the camera; we see the back "
            "of the head, hair, back of clothing and heels. No face visible.",
        ),
        View(
            "back_right", "Back 3/4 (R)", 225,
            "THREE-QUARTER BACK view from the character's RIGHT-rear. We mostly see the back and the right "
            "side; the face is turned away.",
        ),
        View(
            "right", "Right Side", 270,
            "exact RIGHT PROFILE view (90 degrees). Only the character's right side is visible; "
            "the nose and toes point toward the right edge of the image; one eye visible.",
        ),
        View(
            "front_right", "Front 3/4 (R)", 315,
            "THREE-QUARTER FRONT view of the character's RIGHT side. The character is turned 45 degrees "
            "so their face points toward the right edge of the image.",
        ),
        View(
            "top", "Top", -1,
            "TOP-DOWN view looking straight down from above the head, character standing upright.",
        ),
    ]
}

PRESETS: dict[str, list[str]] = {
    # classic orthographic modeling sheet
    "ortho": ["front", "left", "back", "right"],
    # orthographic + 3/4 views (most common character turnaround)
    "turnaround": ["front", "front_left", "left", "back", "right", "front_right"],
    # full 45-degree ring
    "full": ["front", "front_left", "left", "back_left", "back", "back_right", "right", "front_right"],
    "minimal": ["front", "left", "back"],
}

# Views whose content mirrors another (useful hint for the model; never used to fake output).
MIRROR_OF = {"right": "left", "front_right": "front_left", "back_right": "back_left"}


def resolve_views(spec: str) -> list[View]:
    """Turn 'turnaround' or 'front,left,back' into View objects (deduplicated, ordered)."""
    keys: list[str] = []
    for token in (t.strip() for t in spec.split(",")):
        if not token:
            continue
        if token in PRESETS:
            keys.extend(PRESETS[token])
        elif token in VIEWS:
            keys.append(token)
        else:
            raise ValueError(
                f"Unknown view or preset '{token}'. "
                f"Views: {', '.join(VIEWS)}; presets: {', '.join(PRESETS)}"
            )
    seen: set[str] = set()
    ordered = [k for k in keys if not (k in seen or seen.add(k))]
    if not ordered:
        raise ValueError("No views selected")
    return [VIEWS[k] for k in ordered]

"""把配色方案导出为 JSON / CSS / 预览图。"""

from __future__ import annotations

import json
import re
from typing import Dict

import numpy as np

_PREVIEW_ROLES = [
    "primary",
    "onPrimary",
    "primaryContainer",
    "onPrimaryContainer",
    "secondary",
    "secondaryContainer",
    "tertiary",
    "tertiaryContainer",
    "surface",
    "onSurface",
    "surfaceVariant",
    "outline",
    "error",
]

def to_hex(rgb) -> str:
    rgb = np.clip(np.asarray(rgb, dtype=np.float64), 0.0, 1.0)
    r, g, b = np.round(rgb * 255.0).astype(int).tolist()
    return f"#{r:02X}{g:02X}{b:02X}"

def scheme_to_hex(scheme: Dict[str, np.ndarray]) -> Dict[str, str]:
    return {k: to_hex(v) for k, v in scheme.items()}

def _kebab(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()

def to_json(result, indent: int = 2) -> str:
    data = {
        "seeds": [
            {
                "hex": to_hex(s.to_rgb()),
                "hue": round(s.hue, 2),
                "chroma": round(s.chroma, 2),
                "tone": round(s.tone, 2),
            }
            for s in result.seeds
        ],
        "light": scheme_to_hex(result.light),
        "dark": scheme_to_hex(result.dark),
    }
    return json.dumps(data, indent=indent, ensure_ascii=False)

def to_css(
    result,
    prefix: str = "md-sys-color",
    selector: str = ":root",
    dark_selector: str = '[data-theme="dark"]',
) -> str:
    lines = [f"{selector} {{"]
    for k, v in result.light.items():
        lines.append(f"  --{prefix}-{_kebab(k)}: {to_hex(v)};")
    lines.append("}")
    lines.append("")
    lines.append(f"{dark_selector} {{")
    for k, v in result.dark.items():
        lines.append(f"  --{prefix}-{_kebab(k)}: {to_hex(v)};")
    lines.append("}")
    return "\n".join(lines)

def render_preview(result, path: str, cell: int = 84, gap: int = 10) -> None:
    """生成一张浅色/深色对照的色卡预览图。"""
    from PIL import Image, ImageDraw

    cols = len(_PREVIEW_ROLES)
    rows = 2
    label_h = 20
    width = gap + cols * (cell + gap)
    height = gap + rows * (label_h + cell + gap)

    img = Image.new("RGB", (width, height), (250, 250, 250))
    draw = ImageDraw.Draw(img)

    for ri, (label, scheme) in enumerate(
        (("Light", result.light), ("Dark", result.dark))
    ):
        y = gap + ri * (label_h + cell + gap)
        draw.text((gap, y), label, fill=(30, 30, 30))
        for ci, role in enumerate(_PREVIEW_ROLES):
            x = gap + ci * (cell + gap)
            rgb = tuple(int(c) for c in np.round(np.clip(scheme[role], 0, 1) * 255))
            draw.rectangle(
                [x, y + label_h, x + cell, y + label_h + cell],
                fill=rgb,
                outline=(210, 210, 210),
            )
            draw.text((x + 2, y + label_h + cell - 12), role[:10], fill=(120, 120, 120))

    img.save(path)
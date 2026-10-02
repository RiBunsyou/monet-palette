"""主流程：图片 → 像素 → 量化 → 种子色 → 调色板 → 主题。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Union

import numpy as np

from .color import Hct
from .quantize import quantize_wu, refine_wsmeans
from .scheme import CorePalette, build_scheme
from .score import pick_seeds

ImageLike = Union[str, "object", np.ndarray]

@dataclass
class MonetResult:
    seeds: List[Hct]
    core: CorePalette
    light: Dict[str, np.ndarray]
    dark: Dict[str, np.ndarray]
    quantized: List[Tuple[np.ndarray, float]] = field(default_factory=list)

def load_pixels(image: ImageLike, max_side: int = 256) -> np.ndarray:
    """把图片读成 (N, 3) 的 uint8 像素数组。

    会先把长边缩到 max_side —— 既加速量化，也贴近 Material 自身的做法
    （壁纸在做色彩分析前同样会被降采样）。
    """
    from PIL import Image

    if isinstance(image, (str, bytes)) or hasattr(image, "__fspath__"):
        img = Image.open(image)
    elif isinstance(image, Image.Image):
        img = image
    else:
        arr = np.asarray(image)
        if arr.dtype != np.uint8:
            arr = np.clip(arr, 0, 255).astype(np.uint8)
        if arr.ndim == 3 and arr.shape[2] == 4:
            img = Image.fromarray(arr, "RGBA")
        else:
            img = Image.fromarray(arr, "RGB")

    img = img.convert("RGB")
    w, h = img.size
    scale = max_side / float(max(w, h))
    if scale < 1.0:
        img = img.resize(
            (max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS
        )
    return np.asarray(img, dtype=np.uint8).reshape(-1, 3)

def quantize(
    pixels: np.ndarray, max_colors: int = 128, refine: bool = True
) -> List[Tuple[np.ndarray, float]]:
    result = quantize_wu(pixels, max_colors)
    if refine and len(result) > 1:
        try:
            result = refine_wsmeans(pixels, result)
        except Exception:  # pragma: no cover - 精炼失败时退回 Wu 结果
            pass
    return result

def generate(
    image: ImageLike,
    max_colors: int = 128,
    seed_count: int = 4,
    is_content: bool = False,
    refine: bool = True,
    max_side: int = 256,
) -> MonetResult:
    """从一张图片生成完整的 Monet 配色方案。"""
    pixels = load_pixels(image, max_side=max_side)
    quantized = quantize(pixels, max_colors=max_colors, refine=refine)
    seeds = pick_seeds(quantized, count=seed_count)
    core = CorePalette(seeds[0], is_content=is_content)
    return MonetResult(
        seeds=seeds,
        core=core,
        light=build_scheme(core, dark=False),
        dark=build_scheme(core, dark=True),
        quantized=quantized,
    )
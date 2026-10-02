"""Monet Palette —— Material You (Monet) 动态取色算法的 Python 实现。

最常用的入口：

    from monet_palette import generate, to_hex, to_css

    result = generate("wallpaper.jpg")

    result.seeds                 # List[Hct]  种子色
    result.light["primary"]      # np.ndarray (0..1 RGB)
    result.dark["surface"]       # np.ndarray

    to_hex(result.light["primary"])   # '#415F86'
    to_css(result)                    # CSS 文本
"""

from .color import Hct
from .engine import MonetResult, generate, load_pixels, quantize
from .export import (
    render_preview,
    scheme_to_hex,
    to_css,
    to_hex,
    to_json,
)
from .scheme import CorePalette, TonalPalette, build_scheme
from .score import pick_seeds, score_colors

__version__ = "0.1.0"

__all__ = [
    # 主流程
    "generate",
    "MonetResult",
    "load_pixels",
    "quantize",
    # 色彩空间
    "Hct",
    # 调色板
    "CorePalette",
    "TonalPalette",
    "build_scheme",
    # 评分
    "pick_seeds",
    "score_colors",
    # 导出
    "to_hex",
    "to_css",
    "to_json",
    "scheme_to_hex",
    "render_preview",
]
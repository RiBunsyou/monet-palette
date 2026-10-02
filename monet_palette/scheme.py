"""TonalPalette / CorePalette / M3 颜色角色映射。

一个种子色会派生出 5 组基础调色板（accent1/2/3 + neutral1/2），
每组都围绕种子色相、以固定色度展开；
再按「色调编号 → 语义角色」的规则表，组装出浅色与深色两套主题。
"""

from __future__ import annotations

from typing import Dict

import numpy as np

from .color import Hct

ERROR_HUE = 25.0
ERROR_CHROMA = 84.0

class TonalPalette:
    """单组色调调色板：固定色相与色度，按 Tone 取色。"""

    __slots__ = ("hue", "chroma", "_cache")

    def __init__(self, hue: float, chroma: float):
        self.hue = float(hue) % 360.0
        self.chroma = max(0.0, float(chroma))
        self._cache: Dict[int, np.ndarray] = {}

    def tone(self, t: float) -> np.ndarray:
        key = max(0, min(100, int(round(t))))
        cached = self._cache.get(key)
        if cached is None:
            cached = Hct(self.hue, self.chroma, key).to_rgb()
            self._cache[key] = cached
        return cached

class CorePalette:
    """由种子色派生的 5 组基础调色板。"""

    def __init__(self, seed: Hct, is_content: bool = False):
        hue, chroma = seed.hue, seed.chroma

        if is_content:
            # content 风格：完全忠实于源图色度
            self.a1 = TonalPalette(hue, chroma)
            self.a2 = TonalPalette(hue, chroma / 3.0)
            self.a3 = TonalPalette(hue + 60.0, chroma / 2.0)
            self.n1 = TonalPalette(hue, min(chroma / 12.0, 4.0))
            self.n2 = TonalPalette(hue, min(chroma / 6.0, 8.0))
        else:
            # tonal-spot 风格：Material You 默认
            self.a1 = TonalPalette(hue, max(48.0, chroma))
            self.a2 = TonalPalette(hue, 16.0)
            self.a3 = TonalPalette(hue + 60.0, 24.0)
            self.n1 = TonalPalette(hue, 4.0)
            self.n2 = TonalPalette(hue, 8.0)

        self.error = TonalPalette(ERROR_HUE, ERROR_CHROMA)

# ---------------------------------------------------------------------------
# 颜色角色 → (调色板, Tone)
# ---------------------------------------------------------------------------

_LIGHT: Dict[str, tuple] = {
    "primary": ("a1", 40),
    "onPrimary": ("a1", 100),
    "primaryContainer": ("a1", 90),
    "onPrimaryContainer": ("a1", 10),
    "secondary": ("a2", 40),
    "onSecondary": ("a2", 100),
    "secondaryContainer": ("a2", 90),
    "onSecondaryContainer": ("a2", 10),
    "tertiary": ("a3", 40),
    "onTertiary": ("a3", 100),
    "tertiaryContainer": ("a3", 90),
    "onTertiaryContainer": ("a3", 10),
    "error": ("error", 40),
    "onError": ("error", 100),
    "errorContainer": ("error", 90),
    "onErrorContainer": ("error", 10),
    "background": ("n1", 99),
    "onBackground": ("n1", 10),
    "surface": ("n1", 99),
    "onSurface": ("n1", 10),
    "surfaceVariant": ("n2", 90),
    "onSurfaceVariant": ("n2", 30),
    "outline": ("n2", 50),
    "outlineVariant": ("n2", 80),
    "inverseSurface": ("n1", 20),
    "inverseOnSurface": ("n1", 95),
    "inversePrimary": ("a1", 80),
    "shadow": ("n1", 0),
    "scrim": ("n1", 0),
    "surfaceTint": ("a1", 40),
}

_DARK: Dict[str, tuple] = {
    "primary": ("a1", 80),
    "onPrimary": ("a1", 20),
    "primaryContainer": ("a1", 30),
    "onPrimaryContainer": ("a1", 90),
    "secondary": ("a2", 80),
    "onSecondary": ("a2", 20),
    "secondaryContainer": ("a2", 30),
    "onSecondaryContainer": ("a2", 90),
    "tertiary": ("a3", 80),
    "onTertiary": ("a3", 20),
    "tertiaryContainer": ("a3", 30),
    "onTertiaryContainer": ("a3", 90),
    "error": ("error", 80),
    "onError": ("error", 20),
    "errorContainer": ("error", 30),
    "onErrorContainer": ("error", 90),
    "background": ("n1", 10),
    "onBackground": ("n1", 90),
    "surface": ("n1", 10),
    "onSurface": ("n1", 90),
    "surfaceVariant": ("n2", 30),
    "onSurfaceVariant": ("n2", 80),
    "outline": ("n2", 60),
    "outlineVariant": ("n2", 30),
    "inverseSurface": ("n1", 90),
    "inverseOnSurface": ("n1", 20),
    "inversePrimary": ("a1", 40),
    "shadow": ("n1", 0),
    "scrim": ("n1", 0),
    "surfaceTint": ("a1", 80),
}

def build_scheme(core: CorePalette, dark: bool = False) -> Dict[str, np.ndarray]:
    """按 M3 规则表把核心调色板映射为语义化颜色角色。"""
    table = _DARK if dark else _LIGHT
    return {name: getattr(core, pal).tone(tone) for name, (pal, tone) in table.items()}
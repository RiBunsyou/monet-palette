"""种子色评分与选择。

候选色来自上一步的量化结果。评分同时考虑两件事：
  1. 色相「兴奋度」—— 30° 邻域内聚集了多少像素（保证主题色有代表性）
  2. 色度与目标值 48 的偏离（鼓励鲜艳但不过分）
低色度或占比过低的颜色会被直接淘汰。
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

import numpy as np

from .color import Hct

TARGET_CHROMA = 48.0
WEIGHT_PROPORTION = 0.7
WEIGHT_CHROMA_ABOVE = 0.3
WEIGHT_CHROMA_BELOW = 0.1
CUTOFF_CHROMA = 5.0
CUTOFF_EXCITED_PROPORTION = 0.01
HUE_WINDOW = 15

# 找不到任何合格种子时使用的兜底蓝
FALLBACK_SEED = np.array([0x1B / 255.0, 0x6E / 255.0, 0xF3 / 255.0])

_MIN_HUE_GAP = 15.0

def score_colors(
    color_weights: Sequence[Tuple[np.ndarray, float]],
) -> List[Tuple[float, Hct, float]]:
    """返回按得分降序排列的 [(score, Hct, weight), ...]。"""
    entries: List[Tuple[Hct, float]] = []
    hue_pop = np.zeros(360, dtype=np.float64)
    total = 0.0

    for rgb, w in color_weights:
        if w <= 0.0:
            continue
        hct = Hct.from_rgb(rgb)
        entries.append((hct, w))
        hue_pop[int(hct.hue) % 360] += w
        total += w

    if total <= 0.0:
        return []

    scored: List[Tuple[float, Hct, float]] = []
    for hct, w in entries:
        if hct.chroma < CUTOFF_CHROMA:
            continue
        if w / total <= CUTOFF_EXCITED_PROPORTION:
            continue

        hue = int(hct.hue)
        excited = 0.0
        for offset in range(-HUE_WINDOW, HUE_WINDOW):
            excited += hue_pop[(hue + offset) % 360]
        excited /= total

        proportion_score = excited * 100.0 * WEIGHT_PROPORTION
        chroma_weight = (
            WEIGHT_CHROMA_BELOW if hct.chroma < TARGET_CHROMA else WEIGHT_CHROMA_ABOVE
        )
        chroma_score = (hct.chroma - TARGET_CHROMA) * chroma_weight
        scored.append((proportion_score + chroma_score, hct, w))

    scored.sort(key=lambda x: -x[0])
    return scored

def pick_seeds(
    color_weights: Sequence[Tuple[np.ndarray, float]], count: int = 4
) -> List[Hct]:
    """挑选若干色相彼此拉开距离的种子色。"""
    ranked = score_colors(color_weights)
    if not ranked:
        return [Hct.from_rgb(FALLBACK_SEED)]

    seeds: List[Hct] = []
    for _, hct, _ in ranked:
        if len(seeds) >= count:
            break
        if all(_hue_distance(hct.hue, s.hue) >= _MIN_HUE_GAP for s in seeds):
            seeds.append(hct)

    # 色相过于集中时放宽限制补足数量
    if not seeds:
        seeds = [ranked[0][1]]
    for _, hct, _ in ranked:
        if len(seeds) >= count:
            break
        if all(abs(hct.hue - s.hue) > 1e-6 for s in seeds):
            seeds.append(hct)

    return seeds[:count]

def _hue_distance(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)
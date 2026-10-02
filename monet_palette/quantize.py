"""图像量化：Wu 量化 + K-Means 精炼。

第一步把上百万像素压到 32³ 的 5-bit 直方图；
第二步用带动态规划思想的 Wu 算法把色彩立方体切成 N 个簇；
第三步用 K-Means（对应 Material 的 WSMeans）微调簇心。
"""

from __future__ import annotations

import heapq
from typing import List, Sequence, Tuple

import numpy as np

_BINS = 32
_PREFIX = _BINS + 1
_STEP = 256.0 / _BINS  # 每个 bin 覆盖 8 级
_SIZE = _BINS ** 3
_SHAPE = (_BINS, _BINS, _BINS)

Cube = Tuple[int, int, int, int, int, int]  # r0,r1,g0,g1,b0,b1（左闭右开）

# ---------------------------------------------------------------------------
# 直方图与 3D 前缀和
# ---------------------------------------------------------------------------

def _build_histograms(pixels: np.ndarray):
    """构建 4 个 33³ 前缀和：像素数、R/G/B 一阶矩。"""
    q = (pixels >> 3).astype(np.int64)
    idx = q[:, 0] * (_BINS * _BINS) + q[:, 1] * _BINS + q[:, 2]

    # 用 bin 中心值代表该 bin 内的颜色
    rv = q[:, 0] * _STEP + _STEP / 2.0
    gv = q[:, 1] * _STEP + _STEP / 2.0
    bv = q[:, 2] * _STEP + _STEP / 2.0

    def _prefix(weights):
        h = np.bincount(idx, weights=weights, minlength=_SIZE).reshape(_SHAPE)
        p = np.zeros((_PREFIX, _PREFIX, _PREFIX), dtype=np.float64)
        p[1:, 1:, 1:] = h
        return p.cumsum(0).cumsum(1).cumsum(2)

    return _prefix(None), _prefix(rv), _prefix(gv), _prefix(bv)

def _vol(P, r0, r1, g0, g1, b0, b1) -> float:
    """查询立方体 [r0,r1)×[g0,g1)×[b0,b1) 内的矩之和。"""
    return float(
        P[r1, g1, b1]
        - P[r0, g1, b1]
        - P[r1, g0, b1]
        - P[r1, g1, b0]
        + P[r0, g0, b1]
        + P[r0, g1, b0]
        + P[r1, g0, b0]
        - P[r0, g0, b0]
    )

def _sub_cube(cube: Cube, direction: int, lo: int, hi: int) -> Cube:
    r0, r1, g0, g1, b0, b1 = cube
    if direction == 0:
        return (lo, hi, g0, g1, b0, b1)
    if direction == 1:
        return (r0, r1, lo, hi, b0, b1)
    return (r0, r1, g0, g1, lo, hi)

# ---------------------------------------------------------------------------
# Wu 切分
# ---------------------------------------------------------------------------

def _best_cut(cube: Cube, hist):
    """在当前立方体上寻找收益最大的切分。

    收益 = 切分后两半的一阶矩平方和 / 权重 之和
    （等价于「切分后簇内方差下降最多」）。
    """
    Pw, Pr, Pg, Pb = hist
    r0, r1, g0, g1, b0, b1 = cube
    starts = (r0, g0, b0)
    ends = (r1, g1, b1)

    w = _vol(Pw, r0, r1, g0, g1, b0, b1)
    if w <= 0.0:
        return 0, -1, 0.0
    wr = _vol(Pr, r0, r1, g0, g1, b0, b1)
    wg = _vol(Pg, r0, r1, g0, g1, b0, b1)
    wb = _vol(Pb, r0, r1, g0, g1, b0, b1)

    best_d, best_cut, best_profit = 0, -1, 0.0

    for d in range(3):
        s, e = starts[d], ends[d]
        if e - s <= 1:
            continue
        for cut in range(s + 1, e):
            b = _sub_cube(cube, d, s, cut)
            hw = _vol(Pw, *b)
            if hw <= 0.0 or hw >= w:
                continue
            hr = _vol(Pr, *b)
            hg = _vol(Pg, *b)
            hb = _vol(Pb, *b)
            rw = w - hw
            rr, rg, rb = wr - hr, wg - hg, wb - hb
            profit = (hr * hr + hg * hg + hb * hb) / hw + (
                rr * rr + rg * rg + rb * rb
            ) / rw
            if profit > best_profit:
                best_profit = profit
                best_d, best_cut = d, cut

    return best_d, best_cut, best_profit

def quantize_wu(pixels: np.ndarray, max_colors: int) -> List[Tuple[np.ndarray, float]]:
    """Wu 量化。返回 [(rgb01, weight), ...]。"""
    pixels = np.asarray(pixels, dtype=np.uint8)
    hist = _build_histograms(pixels)

    root: Cube = (0, _BINS, 0, _BINS, 0, _BINS)
    cubes: List[Cube] = [root]

    heap = []
    counter = 0
    d, cut, profit = _best_cut(root, hist)
    if cut >= 0:
        heapq.heappush(heap, (-profit, counter, root, d, cut))

    while len(cubes) < max_colors and heap:
        _, _, cube, d, cut = heapq.heappop(heap)
        if cube not in cubes:
            continue
        cubes.remove(cube)

        s, e = cube[2 * d], cube[2 * d + 1]
        for sub in (_sub_cube(cube, d, s, cut), _sub_cube(cube, d, cut, e)):
            cubes.append(sub)
            d2, cut2, p2 = _best_cut(sub, hist)
            if cut2 >= 0:
                counter += 1
                heapq.heappush(heap, (-p2, counter, sub, d2, cut2))

    Pw, Pr, Pg, Pb = hist
    result: List[Tuple[np.ndarray, float]] = []
    for cube in cubes:
        w = _vol(Pw, *cube)
        if w <= 0.0:
            continue
        r = _vol(Pr, *cube) / w / 255.0
        g = _vol(Pg, *cube) / w / 255.0
        b = _vol(Pb, *cube) / w / 255.0
        result.append((np.array([r, g, b]), w))
    return result

# ---------------------------------------------------------------------------
# K-Means 精炼（对应 Material 的 WSMeans）
# ---------------------------------------------------------------------------

_CHUNK = 4096

def _nearest_labels(points: np.ndarray, centers: np.ndarray) -> np.ndarray:
    labels = np.empty(len(points), dtype=np.int64)
    for s in range(0, len(points), _CHUNK):
        part = points[s : s + _CHUNK]
        d = ((part[:, None, :] - centers[None, :, :]) ** 2).sum(-1)
        labels[s : s + _CHUNK] = d.argmin(1)
    return labels

def refine_wsmeans(
    pixels: np.ndarray,
    initial: Sequence[Tuple[np.ndarray, float]],
    max_iter: int = 32,
    sample_size: int = 8192,
    seed: int = 12345,
) -> List[Tuple[np.ndarray, float]]:
    """以 Wu 的结果为初值做 K-Means 迭代，提高簇心质量。"""
    if len(initial) < 2:
        return list(initial)

    rng = np.random.default_rng(seed)
    pix = np.asarray(pixels, dtype=np.float64) / 255.0
    n = len(pix)
    sample = (
        pix[rng.choice(n, sample_size, replace=False)] if n > sample_size else pix
    )

    centers = np.array([c for c, _ in initial], dtype=np.float64)

    for _ in range(max_iter):
        labels = _nearest_labels(sample, centers)
        new_centers = centers.copy()
        for k in range(len(centers)):
            mask = labels == k
            if mask.any():
                new_centers[k] = sample[mask].mean(0)
        if np.allclose(new_centers, centers, atol=1e-4):
            centers = new_centers
            break
        centers = new_centers

    # 用全量像素统计最终权重
    labels = _nearest_labels(pix, centers)
    counts = np.bincount(labels, minlength=len(centers)).astype(np.float64)

    out: List[Tuple[np.ndarray, float]] = []
    for k in range(len(centers)):
        if counts[k] > 0:
            out.append((centers[k], float(counts[k])))
    return out
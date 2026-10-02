"""色彩空间转换：sRGB ↔ CIE XYZ(D65) ↔ CAM16 ↔ HCT。

HCT 是 Material You 的核心色彩空间：
    H(hue)   —— 来自 CAM16 的色相
    C(chroma)—— 来自 CAM16 的色度
    T(tone)  —— 来自 CIE L* 的明度
把感知上的色相/色度与明度解耦，才能保证生成的调色板
在不同明暗档位下始终保持一致的色相观感。
"""

from __future__ import annotations

import math

import numpy as np

# ---------------------------------------------------------------------------
# sRGB ↔ CIE XYZ (D65)
# ---------------------------------------------------------------------------

WHITE_POINT_D65 = np.array([95.047, 100.0, 108.883])

_SRGB_TO_XYZ = np.array(
    [
        [0.41233895, 0.35762064, 0.18051042],
        [0.2126, 0.7152, 0.0722],
        [0.01932141, 0.11916382, 0.95034478],
    ]
)

_XYZ_TO_SRGB = np.array(
    [
        [3.240969941904521, -1.537383177570093, -0.498610760293],
        [-0.96924363628087, 1.87596750150772, 0.041555057407175],
        [0.055630079696993, -0.20397695888897, 1.056971514242878],
    ]
)

_LINEAR_CUTOFF = 0.040449936
_SRGB_CUTOFF = 0.0031308

def _srgb_to_linear(c: np.ndarray) -> np.ndarray:
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= _LINEAR_CUTOFF, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def _linear_to_srgb(c: np.ndarray) -> np.ndarray:
    c = np.asarray(c, dtype=np.float64)
    a = np.abs(c)
    out = np.where(
        a <= _SRGB_CUTOFF,
        a * 12.92,
        1.055 * np.power(a, 1.0 / 2.4) - 0.055,
    )
    return np.sign(c) * out

def srgb_to_xyz(rgb: np.ndarray) -> np.ndarray:
    """sRGB(0..1) → XYZ(D65)，Y 归一到 100。"""
    lin = _srgb_to_linear(np.asarray(rgb, dtype=np.float64))
    return (lin @ _SRGB_TO_XYZ.T) * 100.0

def xyz_to_srgb(xyz: np.ndarray) -> np.ndarray:
    """XYZ(D65, Y∈0..100) → sRGB(0..1)。可能越界，调用方自行裁剪。"""
    lin = (np.asarray(xyz, dtype=np.float64) / 100.0) @ _XYZ_TO_SRGB.T
    return _linear_to_srgb(lin)

# ---------------------------------------------------------------------------
# CIE L* 明度
# ---------------------------------------------------------------------------

_LSTAR_EPS = 216.0 / 24389.0  # (6/29)^3
_LSTAR_KAPPA = 24389.0 / 27.0  # (29/3)^3

def y_from_lstar(lstar: float) -> float:
    """CIE L* → 相对亮度 Y（0..100）。"""
    lstar = float(lstar)
    if lstar > 8.0:
        return (((lstar + 16.0) / 116.0) ** 3) * 100.0
    return lstar / _LSTAR_KAPPA * 100.0

def lstar_from_y(y: float) -> float:
    """相对亮度 Y（0..100）→ CIE L*。"""
    t = float(y) / 100.0
    if t > _LSTAR_EPS:
        return 116.0 * (t ** (1.0 / 3.0)) - 16.0
    return _LSTAR_KAPPA * t

# ---------------------------------------------------------------------------
# CAM16
# ---------------------------------------------------------------------------

class ViewingConditions:
    """CAM16 观察条件。

    默认参数对应 Material 的标准环境：
        white point  = D65
        background   = L* 50
        surround     = 2.0 (average)
        discounting  = False
    """

    __slots__ = (
        "n",
        "aw",
        "nbb",
        "ncb",
        "c",
        "nc",
        "rgb_d",
        "fl",
        "fl_root",
        "z",
    )

    def __init__(
        self,
        white_point=WHITE_POINT_D65,
        adapting_luminance=11.725677948856951,
        background_lstar=50.0,
        surround=2.0,
        discounting=False,
    ):
        wp = np.asarray(white_point, dtype=np.float64)

        # 白点的锥体响应
        rgb_w = np.array(
            [
                wp[0] * 0.401288 + wp[1] * 0.650173 + wp[2] * -0.051461,
                wp[0] * -0.250268 + wp[1] * 1.204414 + wp[2] * 0.045854,
                wp[0] * -0.002079 + wp[1] * 0.048952 + wp[2] * 0.953127,
            ]
        )

        f = 0.8 + surround / 10.0
        if f >= 0.9:
            c = 0.59 + (0.69 - 0.59) * (f - 0.9) * 10.0
        else:
            c = 0.525 + (0.59 - 0.525) * (f - 0.8) * 10.0

        if discounting:
            d = 1.0
        else:
            d = f * (1.0 - (1.0 / 3.6) * math.exp((-adapting_luminance - 42.0) / 92.0))
        d = min(1.0, max(0.0, d))

        nc = f
        rgb_d = np.array([d * (100.0 / rgb_w[i]) + 1.0 - d for i in range(3)])

        k = 1.0 / (5.0 * adapting_luminance + 1.0)
        k4 = k ** 4
        k4f = 1.0 - k4
        fl = k4 * adapting_luminance + 0.1 * k4f * k4f * (
            (5.0 * adapting_luminance) ** (1.0 / 3.0)
        )

        n = y_from_lstar(background_lstar) / wp[1]
        z = 1.48 + math.sqrt(n)
        nbb = 0.725 * (n ** -0.2)
        ncb = nbb

        factors = np.array(
            [(fl * rgb_d[i] * rgb_w[i] / 100.0) ** 0.42 for i in range(3)]
        )
        rgb_a = 400.0 * factors / (factors + 27.13)
        aw = (40.0 * rgb_a[0] + 20.0 * rgb_a[1] + rgb_a[2]) / 20.0 * nbb

        self.n = n
        self.aw = aw
        self.nbb = nbb
        self.ncb = ncb
        self.c = c
        self.nc = nc
        self.rgb_d = rgb_d
        self.fl = fl
        self.fl_root = fl ** 0.25
        self.z = z

DEFAULT_VIEWING_CONDITIONS = ViewingConditions()

def cam16_hue_chroma(
    xyz: np.ndarray, vc: ViewingConditions = DEFAULT_VIEWING_CONDITIONS
):
    """XYZ → CAM16 的 (hue, chroma)。"""
    x, y, z = float(xyz[0]), float(xyz[1]), float(xyz[2])

    r_c = 0.401288 * x + 0.650173 * y - 0.051461 * z
    g_c = -0.250268 * x + 1.204414 * y + 0.045854 * z
    b_c = -0.002079 * x + 0.048952 * y + 0.953127 * z

    r_d = vc.rgb_d[0] * r_c
    g_d = vc.rgb_d[1] * g_c
    b_d = vc.rgb_d[2] * b_c

    def _adapt(v: float) -> float:
        t = (vc.fl * abs(v) / 100.0) ** 0.42
        return math.copysign(400.0 * t / (t + 27.13), v)

    r_a = _adapt(r_d)
    g_a = _adapt(g_d)
    b_a = _adapt(b_d)

    a = (11.0 * r_a - 12.0 * g_a + b_a) / 11.0
    b = (r_a + g_a - 2.0 * b_a) / 9.0
    u = (20.0 * r_a + 20.0 * g_a + 21.0 * b_a) / 20.0
    p2 = (40.0 * r_a + 20.0 * g_a + b_a) / 20.0

    hue = math.degrees(math.atan2(b, a)) % 360.0

    ac = p2 * vc.nbb
    if ac <= 0.0:
        j = 0.0
    else:
        j = 100.0 * ((ac / vc.aw) ** (vc.c * vc.z))

    p1 = 50000.0 / 13.0 * vc.nc * vc.ncb
    t = p1 * math.hypot(a, b) / (u + 0.305)
    alpha = (t ** 0.9) * ((1.64 - 0.29 ** vc.n) ** 0.73)
    chroma = alpha * math.sqrt(max(j, 0.0) / 100.0)

    return hue, chroma

def cam16_xyz_from_jch(
    j: float, chroma: float, hue: float, vc: ViewingConditions = DEFAULT_VIEWING_CONDITIONS
) -> np.ndarray:
    """CAM16 逆变换：(J, C, h) → XYZ。"""
    if j <= 1e-9:
        return np.zeros(3)

    alpha = 0.0 if chroma <= 0.0 else chroma / math.sqrt(j / 100.0)
    denom = (1.64 - 0.29 ** vc.n) ** 0.73
    t = (alpha / denom) ** (1.0 / 0.9) if alpha > 0.0 else 0.0

    h_rad = math.radians(hue)
    e_hue = 0.25 * (math.cos(h_rad + 2.0) + 3.8)
    ac = vc.aw * ((j / 100.0) ** (1.0 / vc.c / vc.z))
    p1 = e_hue * (50000.0 / 13.0) * vc.nc * vc.ncb
    p2 = ac / vc.nbb

    h_sin = math.sin(h_rad)
    h_cos = math.cos(h_rad)

    d2 = 23.0 * p1 + 11.0 * t * h_cos + 108.0 * t * h_sin
    gamma = 0.0 if abs(d2) < 1e-12 else 23.0 * (p2 + 0.305) * t / d2

    a = gamma * h_cos
    b = gamma * h_sin

    r_a = (460.0 * p2 + 451.0 * a + 288.0 * b) / 1403.0
    g_a = (460.0 * p2 - 891.0 * a - 261.0 * b) / 1403.0
    b_a = (460.0 * p2 - 220.0 * a - 6300.0 * b) / 1403.0

    def _unadapt(v: float) -> float:
        av = min(abs(v), 399.99)
        base = (27.13 * av) / (400.0 - av)
        return math.copysign((100.0 / vc.fl) * (base ** (1.0 / 0.42)), v)

    r_c = _unadapt(r_a) / vc.rgb_d[0]
    g_c = _unadapt(g_a) / vc.rgb_d[1]
    b_c = _unadapt(b_a) / vc.rgb_d[2]

    x = 1.86206786 * r_c - 1.01125463 * g_c + 0.14918677 * b_c
    y = 0.38752654 * r_c + 0.62144744 * g_c - 0.00897398 * b_c
    z = -0.01584150 * r_c - 0.03412294 * g_c + 1.04996444 * b_c
    return np.array([x, y, z])

# ---------------------------------------------------------------------------
# HCT 空间与求解器
# ---------------------------------------------------------------------------

_GAMUT_EPS = 1e-4
_TONE_EPS = 0.5
_J_STEPS = 24
_CHROMA_STEPS = 20

class Hct:
    """Hue / Chroma / Tone 色彩空间。"""

    __slots__ = ("hue", "chroma", "tone")

    def __init__(self, hue: float, chroma: float, tone: float):
        self.hue = float(hue) % 360.0
        self.chroma = max(0.0, float(chroma))
        self.tone = min(100.0, max(0.0, float(tone)))

    # -- 构造 --------------------------------------------------------------

    @classmethod
    def from_rgb(cls, rgb: np.ndarray) -> "Hct":
        xyz = srgb_to_xyz(np.asarray(rgb, dtype=np.float64))
        hue, chroma = cam16_hue_chroma(xyz)
        return cls(hue, chroma, lstar_from_y(xyz[1]))

    @classmethod
    def from_int(cls, argb: int) -> "Hct":
        r = ((argb >> 16) & 0xFF) / 255.0
        g = ((argb >> 8) & 0xFF) / 255.0
        b = (argb & 0xFF) / 255.0
        return cls.from_rgb(np.array([r, g, b]))

    # -- 转换 --------------------------------------------------------------

    def to_rgb(self) -> np.ndarray:
        return solve_hct(self.hue, self.chroma, self.tone)

    def to_int(self) -> int:
        rgb = np.clip(self.to_rgb(), 0.0, 1.0)
        r, g, b = (np.round(rgb * 255.0)).astype(int)
        return (0xFF << 24) | (int(r) << 16) | (int(g) << 8) | int(b)

    def __repr__(self) -> str:  # pragma: no cover
        return f"Hct(hue={self.hue:.2f}, chroma={self.chroma:.2f}, tone={self.tone:.2f})"

def _solve_j_and_rgb(hue: float, chroma: float, tone: float, vc):
    """给定 (h, C, T)，二分查找 CAM16 的 J 使 L*(Y) == T。

    返回 (rgb, ok)：ok 表示结果既落在 sRGB 色域内，又确实达到了目标明度。
    """
    lo, hi = 0.0, 100.0
    for _ in range(_J_STEPS):
        mid = 0.5 * (lo + hi)
        xyz = cam16_xyz_from_jch(mid, chroma, hue, vc)
        if lstar_from_y(xyz[1]) < tone:
            lo = mid
        else:
            hi = mid

    j = 0.5 * (lo + hi)
    xyz = cam16_xyz_from_jch(j, chroma, hue, vc)
    rgb = xyz_to_srgb(xyz)
    lstar = lstar_from_y(xyz[1])

    ok = (
        abs(lstar - tone) <= _TONE_EPS
        and rgb.min() >= -_GAMUT_EPS
        and rgb.max() <= 1.0 + _GAMUT_EPS
    )
    return rgb, ok

def solve_hct(
    hue: float, chroma: float, tone: float, vc=DEFAULT_VIEWING_CONDITIONS
) -> np.ndarray:
    """HCT → sRGB。

    若请求的 chroma 在目标明度下超出 sRGB 色域，自动降低色度直至可表示
    （这正是 Monet 能在极端明度档位下依然生成合法颜色的关键）。
    """
    tone = min(100.0, max(0.0, float(tone)))
    if tone <= 1e-6:
        return np.zeros(3)
    if tone >= 100.0 - 1e-6:
        return np.ones(3)

    chroma = max(0.0, float(chroma))

    # 无色度 → 纯灰，直接由 L* 反推 Y
    if chroma < 1e-6:
        y = y_from_lstar(tone)
        xyz = WHITE_POINT_D65 * (y / 100.0)
        return np.clip(xyz_to_srgb(xyz), 0.0, 1.0)

    rgb, ok = _solve_j_and_rgb(hue, chroma, tone, vc)
    if ok:
        return np.clip(rgb, 0.0, 1.0)

    # 色域外：二分可表示的最大色度
    lo, hi = 0.0, chroma
    for _ in range(_CHROMA_STEPS):
        mid = 0.5 * (lo + hi)
        _, ok = _solve_j_and_rgb(hue, mid, tone, vc)
        if ok:
            lo = mid
        else:
            hi = mid

    rgb, _ = _solve_j_and_rgb(hue, lo, tone, vc)
    return np.clip(rgb, 0.0, 1.0)
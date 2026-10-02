"""pytest 共享 fixture。"""

import numpy as np
import pytest

from monet_palette import generate

@pytest.fixture
def fake_image():
    """生成一张确定性的渐变测试图（64×64）。"""
    size = 64
    x = np.linspace(0, 255, size)
    y = np.linspace(0, 255, size)
    xx, yy = np.meshgrid(x, y)
    r = xx.astype(np.uint8)
    g = yy.astype(np.uint8)
    b = ((xx + yy) / 2).astype(np.uint8)
    return np.stack([r, g, b], axis=-1)

@pytest.fixture
def result(fake_image):
    """一份生成好的 MonetResult"""
    return generate(fake_image, max_side=64)

@pytest.fixture
def example_image_path():
    """examples/hiro.jpg 的路径。"""
    from pathlib import Path

    p = Path(__file__).parent.parent / "examples" / "hiro.jpg"
    if not p.exists():
        pytest.skip(f"缺少示例图片: {p}")
    return str(p)